//
//  Logout.ts
//  CompactConnect
//
//  Created by InspiringApps on 8/12/2024.
//

import { Component, Vue } from 'vue-facing-decorator';
import { authStorage, AuthTypes, AUTH_LOGIN_GOTO_PATH } from '@/app.config';

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

    get hostedLogoutUriStaff(): string {
        const { domain, cognitoAuthDomainStaff, cognitoClientIdStaff } = this.$envConfig;
        const logoutLink = encodeURIComponent(`${(domain as string)}/Logout`);
        const logoutUriQuery = [
            `?client_id=${cognitoClientIdStaff}`,
            `&logout_uri=${logoutLink}`
        ].join('');
        const idpPath = '/logout';
        const logoutUri = `${cognitoAuthDomainStaff}${idpPath}${logoutUriQuery}`;

        return logoutUri;
    }

    get loginURL(): string {
        const { domain } = this.$envConfig;

        return `${(domain as string)}/Login`;
    }

    get hostedLogoutUriLicensee(): string {
        const { cognitoAuthDomainLicensee, cognitoClientIdLicensee } = this.$envConfig;
        const logoutUriQuery = [
            `?client_id=${cognitoClientIdLicensee}`,
            `&logout_uri=${encodeURIComponent(this.loginURL)}`
        ].join('');
        const idpPath = '/logout';
        const logoutUri = `${cognitoAuthDomainLicensee}${idpPath}${logoutUriQuery}`;

        return logoutUri;
    }

    //
    // Methods
    //
    async logout(): Promise<void> {
        if (this.isLoggedIn) {
            const isLoggedInAsLicenseeOnly = this.$store.getters['user/highestPermissionAuthType']() === AuthTypes.LICENSEE;

            await this.logoutChecklist();
            this.redirectToHighestPermissionHostedLogout(isLoggedInAsLicenseeOnly);
        } else {
            window.location.replace(this.loginURL);
        }
    }

    async logoutChecklist(): Promise<void> {
        this.$store.dispatch('user/clearRefreshTokenTimeout');
        this.stashWorkingUri();
        await this.$store.dispatch('user/logoutRequest', this.$store.getters['user/highestPermissionAuthType']());
    }

    stashWorkingUri(): void {
        const { workingUri } = this;

        if (workingUri) {
            authStorage.setItem(AUTH_LOGIN_GOTO_PATH, workingUri);
        }
    }

    get isLoggedIn(): boolean {
        return this.userStore.isLoggedIn;
    }

    redirectToHighestPermissionHostedLogout(isLoggedInAsLicenseeOnly): void {
        let logOutUrl = this.hostedLogoutUriStaff;

        if (isLoggedInAsLicenseeOnly) {
            logOutUrl = this.hostedLogoutUriLicensee;
        }

        window.location.replace(logOutUrl);
    }
}
