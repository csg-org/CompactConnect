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
import {
    authStorage,
    AuthTypes,
    relativeTimeFormats,
    tokens
} from '@/app.config';
import { CompactType, CompactSerializer } from '@models/Compact/Compact.model';
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
            let authType = AuthTypes.LICENSEE;

            if (authStorage.getItem(tokens?.staff?.AUTH_TOKEN)) {
                authType = AuthTypes.STAFF;
            }
            this.$store.dispatch('user/startRefreshTokenTimer', authType);

            if (!this.userStore.currentCompact) {
                this.setCurrentCompact();
            }
        }

        this.setRelativeTimeFormats();
    }

    //
    // Computed
    //
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
    async setCurrentCompact() {
        const compact = CompactSerializer.fromServer({ type: CompactType.ASLP }); // Temp until server endpoints define the user's compact

        await this.$store.dispatch('user/setCurrentCompact', compact);

        return compact;
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

    @Watch('userStore.isLoggedIn') onLogout() {
        if (!this.userStore.isLoggedIn) {
            this.$router.push({ name: 'Logout' });
        }
    }
}

export default toNative(App);

export { App };
