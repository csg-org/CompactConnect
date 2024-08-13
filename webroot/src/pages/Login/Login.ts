//
//  Login.ts
//  CompactConnect
//
//  Created by InspiringApps on 8/12/2024.
//

import { Component, Vue } from 'vue-facing-decorator';

@Component({
    name: 'Login',
    components: {}
})
export default class Login extends Vue {
    //
    // Lifecycle
    //
    created() {
        this.redirectToHostedLogin();
    }

    //
    // Computed
    //
    get hostedLoginUriStaff(): string {
        const { domain, cognitoAuthDomainStaff, cognitoClientIdStaff } = this.$envConfig;
        const loginScopes = 'email openid phone profile';
        const loginResponseType = 'code';
        const loginRedirectPath = '/auth/callback';
        const loginUriQuery = [
            `?client_id=${cognitoClientIdStaff}`,
            `&response_type=${loginResponseType}`,
            `&scope=${encodeURIComponent(loginScopes)}`,
            `&redirect_uri=${encodeURIComponent(`${domain}${loginRedirectPath}`)}`,
        ].join('');
        const loginUri = `${cognitoAuthDomainStaff}/logout${loginUriQuery}`;

        return loginUri;
    }

    //
    // Methods
    //
    redirectToHostedLogin(): void {
        window.location.replace(this.hostedLoginUriStaff);
    }
}
