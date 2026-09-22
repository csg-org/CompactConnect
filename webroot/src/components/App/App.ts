//
//  App.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

import {
    Component,
    Vue,
    Watch,
    toNative
} from 'vue-facing-decorator';
import { RouteRecordName } from 'vue-router';
import { relativeTimeFormats } from '@/app.config';
import {
    getAppModeForCompact,
    getLockedAppMode,
    getSoleCompactForAppMode
} from '@utils/compactConfig';
import {
    authStorage,
    AuthTypes,
    AUTH_TYPE,
    AUTH_LOGIN_GOTO_COMPACT
} from '@utils/auth';
import { Compact, CompactType } from '@models/Compact/Compact.model';
import PageContainer from '@components/Page/PageContainer/PageContainer.vue';
import Modal from '@components/Modal/Modal.vue';
import AutoLogout from '@components/AutoLogout/AutoLogout.vue';
import { StatsigUser } from '@statsig/js-client';
import moment from 'moment';

const appWindow = window as any;

@Component({
    name: 'App',
    components: {
        PageContainer,
        Modal,
        AutoLogout,
    },
    emits: [
        'trigger-scroll-behavior'
    ],
})
class App extends Vue {
    //
    // Data
    //
    body = document.body;
    featureGateFetchIntervalId: number | undefined = undefined;

    //
    // Lifecycle
    //
    async created() {
        this.setPageData();
        await this.$router.isReady();
        this.setAppModeFromCompact(this.routeCompactType);

        if (this.userStore.isLoggedIn) {
            await this.handleAuth();
        }

        // Host-seeded defaults skip setCurrentCompact, so memberStates stay empty unless we fetch them here
        await this.ensureCompactStates();

        this.setRelativeTimeFormats();
        this.setFeatureGateRefetchInterval();
        this.addAppModeDebugger();
    }

    async beforeUnmount() {
        this.clearFeatureGateRefetchInterval();
    }

    //
    // Computed
    //
    get routeCompactType(): CompactType | null {
        return (this.$route.params.compact as CompactType) || null;
    }

    get lockedCompactType(): CompactType | null {
        return getSoleCompactForAppMode(getLockedAppMode());
    }

    get globalStore() {
        return this.$store.state;
    }

    get userStore() {
        return this.$store.state.user;
    }

    get messages() {
        return this.globalStore.messages;
    }

    get showMessageModal(): boolean {
        return Boolean(this.messages.length);
    }

    get isModalOpen(): boolean {
        return this.globalStore.isModalOpen;
    }

    get isErrorModal() {
        return Boolean(this.globalStore.messages.find((m) => m.type === 'error'));
    }

    //
    // Methods
    //
    async handleAuth() {
        const authType = this.setAuthType();

        this.setAppModeFromCompact(this.routeCompactType);

        if (authType !== AuthTypes.PUBLIC) {
            this.$store.dispatch('user/startRefreshTokenTimer', authType);
            await this.getAccount();
            await this.setCurrentCompact();
        }
    }

    setAppModeFromCompact(compact: CompactType | null): void {
        const { appMode } = this.globalStore;
        const { lockedCompactType } = this;

        if (lockedCompactType) {
            // Host-pinned mode: keep currentCompact aligned, whatever the route or user permissions say
            if (this.userStore.currentCompact?.type !== lockedCompactType) {
                this.$store.dispatch('user/setCurrentCompact', new Compact({ type: lockedCompactType }));
            }
        } else if (!appMode) {
            this.$store.dispatch('setAppMode', getAppModeForCompact(compact));
        }
    }

    setAuthType() {
        let authType: AuthTypes;

        if (authStorage.getItem(AUTH_TYPE) === AuthTypes.STAFF) {
            authType = AuthTypes.STAFF;
        } else if (authStorage.getItem(AUTH_TYPE) === AuthTypes.LICENSEE) {
            authType = AuthTypes.LICENSEE;
        } else {
            authType = AuthTypes.PUBLIC;
        }

        this.$store.dispatch('setAuthType', authType);

        return authType;
    }

    async getAccount(): Promise<void> {
        const { authType } = this.globalStore;

        if (authType === AuthTypes.STAFF) {
            await this.$store.dispatch('user/getStaffAccountRequest');
        } else if (authType === AuthTypes.LICENSEE) {
            await this.$store.dispatch('user/getLicenseeAccountRequest');
        }

        this.updateAnalyticsUser(); // Not awaiting analytics so it doesn't block other critical steps
    }

    async updateAnalyticsUser(): Promise<void> {
        const { model: appUser } = this.userStore;
        const analyticsUser: StatsigUser = {};

        if (appUser?.id) {
            analyticsUser.userID = appUser.id;
        }
        if (appUser?.compactConnectEmail) {
            analyticsUser.email = appUser.compactConnectEmail;
        }

        try {
            await this.$analytics.updateUserAsync(analyticsUser);
        } catch (err) {
            // Continue
        }
    }

    setFeatureGateRefetchInterval(): void {
        const refetchIntervalMs = moment.duration(1, 'minute').asMilliseconds();

        this.featureGateFetchIntervalId = (window as Window).setInterval(() => {
            this.updateAnalyticsUser();
        }, refetchIntervalMs);
    }

    clearFeatureGateRefetchInterval(): void {
        (window as Window).clearInterval(this.featureGateFetchIntervalId);
    }

    async setCurrentCompact(): Promise<void> {
        const { authType } = this.globalStore;
        const { currentCompact, model: user } = this.userStore;
        const preLoginCompactType = authStorage.getItem(AUTH_LOGIN_GOTO_COMPACT);
        let userDefaultCompact;
        let isCompactPartOfUserPermissions;

        authStorage.removeItem(AUTH_LOGIN_GOTO_COMPACT);

        // Host-pinned mode: ignore the user's other compacts rather than switching mode or redirecting the route
        if (this.lockedCompactType) {
            this.setAppModeFromCompact(this.lockedCompactType);

            return;
        }

        if (authType === AuthTypes.STAFF) {
            const { permissions = [] } = user || {};
            const preLoginCompact = permissions?.find((permission) =>
                permission.compact.type === preLoginCompactType)?.compact || null;
            const firstCompactFromServer = permissions?.[0]?.compact || null;

            userDefaultCompact = preLoginCompact || firstCompactFromServer;
            isCompactPartOfUserPermissions = permissions.some((permission) =>
                permission.compact.type === currentCompact?.type);
        } else if (authType === AuthTypes.LICENSEE) {
            const { licenses = [] } = user?.licensee || {};
            const firstCompactFromServer = licenses?.[0]?.compact || null;

            userDefaultCompact = firstCompactFromServer;
            isCompactPartOfUserPermissions = licenses.some((license) => license.compact.type === currentCompact?.type);
        }

        // If a current compact is not set or the current compact is not part of the user permissions
        if ((!currentCompact || !isCompactPartOfUserPermissions) && userDefaultCompact) {
            await this.$store.dispatch('user/setCurrentCompact', userDefaultCompact);

            // If the current route is not matching the newly set compact, then redirect
            if (this.routeCompactType && this.routeCompactType !== userDefaultCompact?.type) {
                this.$router.replace({
                    name: (this.$route.name as RouteRecordName),
                    params: { compact: userDefaultCompact.type }
                });
            }
        }

        // Set the app mode based on the current compact
        this.setAppModeFromCompact(userDefaultCompact?.type || null);
    }

    async ensureCompactStates(): Promise<void> {
        const { currentCompact, isLoadingCompactStates } = this.userStore;

        if (currentCompact?.type && !currentCompact.memberStates?.length && !isLoadingCompactStates) {
            await this.$store.dispatch('user/getCompactStatesRequest', { compact: currentCompact.type });
        }
    }

    setRelativeTimeFormats() {
        // https://momentjs.com/docs/#/customization/relative-time/
        moment.updateLocale('en', {
            relativeTime: relativeTimeFormats
        });
    }

    closeModal() {
        this.$store.dispatch('clearMessages');
    }

    setPageData(): void {
        const appName = (this.$isAppModePsyPact) ? this.$t('common.appNamePsyPact') : this.$t('common.appName');
        const { origin } = this.$envConfig;

        document.title = appName;
        this.setMetaContent('meta[name="description"]', appName);
        this.setMetaContent('meta[property="og:title"]', appName);
        this.setMetaContent('meta[property="og:description"]', appName);
        this.setMetaContent('meta[property="og:url"]', (origin as string));
        this.setMetaContent('meta[property="og:image"]', `${origin}/img/icons/mstile-310x310.png`);
        document.querySelector('link[rel="canonical"]')?.setAttribute('href', (origin as string));
    }

    setMetaContent(selector: string, content: string): void {
        document.querySelector(selector)?.setAttribute('content', content);
    }

    addAppModeDebugger(): void {
        appWindow.ccModeToggle = () => {
            if (this.globalStore.isAppModeDisplayed) {
                this.$store.dispatch('setAppModeDisplay', false);
                console.log('CompactConnect app mode display: DISABLED');
            } else {
                this.$store.dispatch('setAppModeDisplay', true);
                console.log('CompactConnect app mode display: ENABLED');
            }
        };
    }

    //
    // Watchers
    //
    @Watch('$appMode') onAppModeChange() {
        this.setPageData();
        this.$store.dispatch('user/clearSearchStores');
    }

    @Watch('isModalOpen') onIsModalOpenChange() {
        this.body.style.overflow = (this.globalStore.isModalOpen) ? 'hidden' : 'visible';
    }

    @Watch('userStore.isLoggedInAsLicensee') async handleLicenseeLogin() {
        if (!this.userStore.isLoggedIn) {
            this.$router.push({ name: 'Logout' });
        } else if (this.userStore.isLoggedInAsLicensee) {
            await this.handleAuth();
        }
    }

    @Watch('userStore.isLoggedInAsStaff') async handleStaffLogin() {
        if (!this.userStore.isLoggedIn) {
            this.$router.push({ name: 'Logout' });
        } else if (this.userStore.isLoggedInAsStaff) {
            await this.handleAuth();
        }
    }
}

export default toNative(App);

export { App };
