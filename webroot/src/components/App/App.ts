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
    tokens
} from '@/app.config';
import { CompactType } from '@models/Compact/Compact.model';
import PageContainer from '@components/Page/PageContainer/PageContainer.vue';
import Modal from '@components/Modal/Modal.vue';
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

    //
    // Lifecycle
    //
    async created() {
        if (this.userStore.isLoggedIn) {
            await this.handleAuth();
        }

        this.setRelativeTimeFormats();
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
        }
    }

    setAuthType() {
        let authType: AuthTypes;

        if (authStorage.getItem(tokens.staff.AUTH_TYPE) === AuthTypes.STAFF) {
            authType = AuthTypes.STAFF;
        } else if (authStorage.getItem(tokens.licensee.AUTH_TYPE) === AuthTypes.LICENSEE) {
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

    @Watch('userStore.isLoggedIn') async loginState() {
        if (!this.userStore.isLoggedIn) {
            this.$router.push({ name: 'Logout' });
        } else {
            await this.handleAuth();
        }
    }
}

export default toNative(App);

export { App };
