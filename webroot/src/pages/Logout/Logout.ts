//
//  Logout.ts
//  CompactConnect
//
//  Created by InspiringApps on 8/12/2024.
//

import { Component, Vue } from 'vue-facing-decorator';
import localStorage, { AUTH_LOGIN_GOTO_PATH } from '@store/local.storage';

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
        this.stashWorkingUri();
        await this.$store.dispatch('user/logoutRequest');
    }

    stashWorkingUri(): void {
        const { workingUri } = this;

        if (workingUri) {
            localStorage.setItem(AUTH_LOGIN_GOTO_PATH, workingUri);
        }
    }

    logoutRedirect(): void {
        this.$router.push({ name: 'Login' });
    }
}
