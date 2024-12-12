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
        const { cognitoAuthDomainStaff, cognitoClientIdStaff } = this.$envConfig;
        const logoutUriQuery = [
            `?client_id=${cognitoClientIdStaff}`,
            `&logout_uri=${encodeURIComponent(this.hostedLogoutUriLicensee)}`
        ].join('');
        const idpPath = '/logout';
        const loginUri = `${cognitoAuthDomainStaff}${idpPath}${logoutUriQuery}`;

        return loginUri;
    }

    get hostedLogoutUriLicensee(): string {
        const { domain, cognitoAuthDomainLicensee, cognitoClientIdLicensee } = this.$envConfig;
        const disambiguationLink = encodeURIComponent(`${(domain as string)}/Login`);
        const logoutUriQuery = [
            `?client_id=${cognitoClientIdLicensee}`,
            `&logout_uri=${disambiguationLink}`
        ].join('');
        const idpPath = '/logout';
        const loginUri = `${cognitoAuthDomainLicensee}${idpPath}${logoutUriQuery}`;

        return loginUri;
    }

    //
    // Methods
    //
    async logout(): Promise<void> {
        const isLoggedInAsLicenseeOnly = this.$store.getters['user/highestPermissionAuthType']() === AuthTypes.LICENSEE;

        await this.logoutChecklist();
        this.redirectToHighestPermissionHostedLogout(isLoggedInAsLicenseeOnly);
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

    redirectToHighestPermissionHostedLogout(isLoggedInAsLicenseeOnly): void {
        let logOutUrl = this.hostedLogoutUriStaff;

        if (isLoggedInAsLicenseeOnly) {
            logOutUrl = this.hostedLogoutUriLicensee;
        }

        window.location.replace(logOutUrl);
    }
}
