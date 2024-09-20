//
//  Logout.ts
//  CompactConnect
//
//  Created by InspiringApps on 8/12/2024.
//

import { Component, Vue } from 'vue-facing-decorator';
import { authStorage, AUTH_LOGIN_GOTO_PATH } from '@/app.config';

@Component({
    name: 'Logout',
    components: {}
})
export default class Logout extends Vue {
    //
    // Lifecycle
    //
    async created() {
        await this.logout();
    }

    //
    // Computed
    //
    get userStore() {
        return this.$store.state.user;
    }

    get workingUri(): string {
        return this.$route.query?.goto?.toString() || '';
    }

    //
    // Methods
    //
    async logout(): Promise<void> {
        await this.logoutChecklist();
        this.logoutRedirect();
    }

    async logoutChecklist(): Promise<void> {
        this.$store.dispatch('user/clearRefreshTokenTimeout');
        this.stashWorkingUri();
        await this.$store.dispatch('user/logoutRequest');
    }

    stashWorkingUri(): void {
        const { workingUri } = this;

        if (workingUri) {
            authStorage.setItem(AUTH_LOGIN_GOTO_PATH, workingUri);
        }
    }

    logoutRedirect(): void {
        this.$router.push({ name: 'Login', query: { logout: 'true' }});
    }
}
