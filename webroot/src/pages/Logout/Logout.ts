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
        const loginScopes = 'email openid phone profile';
        const loginResponseType = 'code';
        const loginRedirectPath = '/auth/callback';
        const loginUriQuery = [
            `?client_id=${cognitoClientIdStaff}`,
            `&response_type=${loginResponseType}`,
            `&scope=${encodeURIComponent(loginScopes)}`,
            `&state=${AuthTypes.STAFF}`,
            `&redirect_uri=${encodeURIComponent(`${domain}${loginRedirectPath}`)}`,
        ].join('');
        const idpPath = '/logout';
        const loginUri = `${cognitoAuthDomainStaff}${idpPath}${loginUriQuery}`;

        return loginUri;
    }

    get hostedLogoutUriLicensee(): string {
        const { domain, cognitoAuthDomainLicensee, cognitoClientIdLicensee } = this.$envConfig;
        const loginScopes = 'email openid phone profile aws.cognito.signin.user.admin';
        const loginResponseType = 'code';
        const loginRedirectPath = '/auth/callback';
        const loginUriQuery = [
            `?client_id=${cognitoClientIdLicensee}`,
            `&response_type=${loginResponseType}`,
            `&scope=${encodeURIComponent(loginScopes)}`,
            `&state=${AuthTypes.LICENSEE}`,
            `&redirect_uri=${encodeURIComponent(`${domain}${loginRedirectPath}`)}`,
        ].join('');
        const idpPath = '/logout';
        const loginUri = `${cognitoAuthDomainLicensee}${idpPath}${loginUriQuery}`;

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
