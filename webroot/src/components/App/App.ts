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
import {
    authStorage,
    AuthTypes,
    relativeTimeFormats,
    AUTH_TYPE
} from '@/app.config';
import { CompactType } from '@models/Compact/Compact.model';
import PageContainer from '@components/Page/PageContainer/PageContainer.vue';
import Modal from '@components/Modal/Modal.vue';
import { StatsigUser } from '@statsig/js-client';
import moment from 'moment';

@Component({
    name: 'App',
    components: {
        PageContainer,
        Modal,
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
    autoLogoutEventsController: AbortController | null = null;

    //
    // Lifecycle
    //
    async created() {
        if (this.userStore.isLoggedIn) {
            await this.handleAuth();
        }

        this.setRelativeTimeFormats();
        this.setFeatureGateRefetchInterval();
    }

    async beforeUnmount() {
        this.clearFeatureGateRefetchInterval();
        this.removeAutoLogoutEvents();
    }

    //
    // Computed
    //
    get routeCompactType(): CompactType | null {
        return (this.$route.params.compact as CompactType) || null;
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

        if (authType !== AuthTypes.PUBLIC) {
            this.$store.dispatch('user/startRefreshTokenTimer', authType);
            await this.getAccount();
            await this.setCurrentCompact();
            this.startAutoLogoutTimer();
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
        let userDefaultCompact;
        let isCompactPartOfUserPermissions;

        if (authType === AuthTypes.STAFF) {
            const { permissions = [] } = user || {};

            userDefaultCompact = permissions?.[0]?.compact || null;
            isCompactPartOfUserPermissions = permissions.some((permission) =>
                permission.compact.type === currentCompact?.type);
        } else if (authType === AuthTypes.LICENSEE) {
            const { licenses = [] } = user?.licensee || {};

            userDefaultCompact = licenses?.[0]?.compact || null;
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
    }

    startAutoLogoutTimer(): void {
        const resetEvents = [
            'mousemove',
            'mousedown',
            'click',
            'keypress',
            'touchstart',
            'touchend',
            'touchmove',
            'onscroll',
            'wheel',
            'mousewheel',
        ];
        const debounce = (func, delay) => {
            let timer;

            return (...args) => {
                clearTimeout(timer);
                timer = setTimeout(() => {
                    func.apply(this, args);
                }, delay);
            };
        };
        const eventHandler = (event) => {
            console.log(`event: ${event.type}`);
            this.$store.dispatch('user/startAutoLogoutTokenTimer');
            this.startAutoLogoutTimer();
        };
        const debouncedEventHandler = debounce(eventHandler, 1000);
        const controller = new AbortController();
        const { isLoggedIn, isAutoLogoutWarning } = this.userStore;

        this.removeAutoLogoutEvents();

        if (isLoggedIn && !isAutoLogoutWarning) {
            this.$store.dispatch('user/startAutoLogoutTokenTimer');
            this.autoLogoutEventsController = controller;
            resetEvents.forEach((resetEvent) => {
                document.addEventListener(resetEvent, debouncedEventHandler, {
                    capture: false,
                    once: true,
                    passive: true,
                    signal: controller.signal,
                });
            });
        }
    }

    removeAutoLogoutEvents(): void {
        const { autoLogoutEventsController } = this;

        if (autoLogoutEventsController) {
            autoLogoutEventsController.abort();
            this.autoLogoutEventsController = null;
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

    //
    // Watchers
    //
    @Watch('isModalOpen') onIsModalOpenChange() {
        this.body.style.overflow = (this.globalStore.isModalOpen) ? 'hidden' : 'visible';
    }

    @Watch('userStore.isLoggedInAsLicensee') async handleLicenseeLogin() {
        if (!this.userStore.isLoggedIn) {
            this.removeAutoLogoutEvents();
            this.$router.push({ name: 'Logout' });
        } else if (this.userStore.isLoggedInAsLicensee) {
            await this.handleAuth();
        }
    }

    @Watch('userStore.isLoggedInAsStaff') async handleStaffLogin() {
        if (!this.userStore.isLoggedIn) {
            this.removeAutoLogoutEvents();
            this.$router.push({ name: 'Logout' });
        } else if (this.userStore.isLoggedInAsStaff) {
            await this.handleAuth();
        }
    }
}

export default toNative(App);

export { App };
