//
//  AuthCallback.ts
//  CompactConnect
//
//  Created by InspiringApps on 8/12/2024.
//

import { nextTick } from 'vue';
import { Component, Vue } from 'vue-facing-decorator';
import localStorage, { tokens, AUTH_LOGIN_GOTO_PATH } from '@store/local.storage';
import axios from 'axios';
import moment from 'moment';

@Component({
    name: 'AuthCallback',
    components: {}
})
export default class AuthCallback extends Vue {
    //
    // Data
    //
    isError = false;

    //
    // Lifecycle
    //
    async created() {
        await this.getTokensStaff();
        await this.redirectUser();
    }

    //
    // Computed
    //
    get authorizationCode(): string {
        return this.$route.query?.code?.toString() || '';
    }

    //
    // Methods
    //
    async getTokensStaff(): Promise<void> {
        const { domain, cognitoAuthDomainStaff, cognitoClientIdStaff } = this.$envConfig;
        const params = new URLSearchParams();

        params.append('grant_type', 'authorization_code');
        params.append('client_id', cognitoClientIdStaff || '');
        params.append('redirect_uri', `${domain}${this.$route.path}`);
        params.append('code', this.authorizationCode);

        try {
            const { data } = await axios.post(`${cognitoAuthDomainStaff}/oauth2/token`, params);

            this.storeTokensStaff(data);
        } catch (err) {
            this.isError = true;
        }
    }

    storeTokensStaff(tokenResponse: any): void {
        const {
            access_token: accessToken,
            token_type: tokenType,
            expires_in: expiresIn,
            id_token: idToken,
            refresh_token: refreshToken,
        } = tokenResponse || {};

        if (accessToken) {
            localStorage.setItem(tokens.staff.AUTH_TOKEN, accessToken);
        }

        if (tokenType) {
            localStorage.setItem(tokens.staff.AUTH_TOKEN_TYPE, tokenType);
        }

        if (expiresIn) {
            const expiry = moment().add(expiresIn, 'seconds').format('YYYY-MM-DD:HH:mm:ss');

            localStorage.setItem(tokens.staff.AUTH_TOKEN_EXPIRY, expiry);
        }

        if (idToken) {
            localStorage.setItem(tokens.staff.ID_TOKEN, idToken);
        }

        if (refreshToken) {
            localStorage.setItem(tokens.staff.AUTH_TOKEN, refreshToken);
        }

        this.$store.dispatch('user/loginSuccess');
    }

    async redirectUser(): Promise<void> {
        const goto = localStorage.getItem(AUTH_LOGIN_GOTO_PATH);

        if (goto) {
            localStorage.removeItem(AUTH_LOGIN_GOTO_PATH);
            this.$router.push({ path: goto });
        } else {
            await nextTick();
            this.$router.push({ name: 'Home' });
        }
    }
}
