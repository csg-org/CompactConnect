//
//  Login.ts
//  CompactConnect
//
//  Created by InspiringApps on 8/12/2024.
//

import { Component, Vue } from 'vue-facing-decorator';
import { AuthTypes } from '@/app.config';

@Component({
    name: 'Login',
    components: {}
})
export default class Login extends Vue {
    //
    // Computed
    //
    get shouldRemoteLogout(): boolean {
        const logoutQuery: string = (this.$route.query?.logout as string) || '';

        return logoutQuery.toLowerCase() === 'true';
    }

    get hostedLoginUriStaff(): string {
        const { domain, cognitoAuthDomainStaff, cognitoClientIdStaff } = this.$envConfig;
        const loginScopes = 'email openid phone profile aws.cognito.signin.user.admin';
        const loginResponseType = 'code';
        const loginRedirectPath = '/auth/callback';
        const loginUriQuery = [
            `?client_id=${cognitoClientIdStaff}`,
            `&response_type=${loginResponseType}`,
            `&scope=${encodeURIComponent(loginScopes)}`,
            `&state=${AuthTypes.STAFF}`,
            `&redirect_uri=${encodeURIComponent(`${domain}${loginRedirectPath}`)}`,
        ].join('');
        const idpPath = (this.shouldRemoteLogout) ? '/logout' : '/login';
        const loginUri = `${cognitoAuthDomainStaff}${idpPath}${loginUriQuery}`;

        return loginUri;
    }

    get hostedLoginUriLicensee(): string {
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
        const idpPath = (this.shouldRemoteLogout) ? '/logout' : '/login';
        const loginUri = `${cognitoAuthDomainLicensee}${idpPath}${loginUriQuery}`;

        return loginUri;
    }

    get isUsingMockApi(): boolean {
        return this.$envConfig.isUsingMockApi || false;
    }

    //
    // Methods
    //
    redirectToHostedLogin(): void {
        window.location.replace(this.hostedLoginUriStaff);
    }

    setMockAuthTokens(): void {
        const data = {
            access_token: 'accessToken',
            token_type: 'Bearer',
            expires_in: '',
            id_token: 'idToken',
            refresh_token: 'refreshToken'
        };

        this.$store.dispatch('user/storeAuthTokens', { tokenResponse: data, authType: AuthTypes.STAFF });
        this.$store.dispatch('user/storeAuthTokens', { tokenResponse: data, authType: AuthTypes.LICENSEE });
        this.$store.dispatch('user/loginSuccess');
    }
}
