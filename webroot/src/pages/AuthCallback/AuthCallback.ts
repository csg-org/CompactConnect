//
//  AuthCallback.ts
//  CompactConnect
//
//  Created by InspiringApps on 8/12/2024.
//

import { nextTick } from 'vue';
import { Component, Vue } from 'vue-facing-decorator';
import Section from '@components/Section/Section.vue';
import Card from '@components/Card/Card.vue';
import { authStorage, AUTH_LOGIN_GOTO_PATH } from '@/app.config';
import axios from 'axios';

@Component({
    name: 'AuthCallback',
    components: {
        Section,
        Card,
    }
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
        await this.getTokens();
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
    async getTokens(): Promise<void> {
        this.$store.dispatch('startLoading');

        await this.getTokensStaff().catch(() => {
            this.isError = true;
        });

        this.$store.dispatch('endLoading');

        if (!this.isError) {
            await this.redirectUser();
        }
    }

    async getTokensStaff(): Promise<void> {
        const { domain, cognitoAuthDomainStaff, cognitoClientIdStaff } = this.$envConfig;
        const params = new URLSearchParams();

        params.append('grant_type', 'authorization_code');
        params.append('client_id', cognitoClientIdStaff || '');
        params.append('redirect_uri', `${domain}${this.$route.path}`);
        params.append('code', this.authorizationCode);

        const { data } = await axios.post(`${cognitoAuthDomainStaff}/oauth2/token`, params);

        await this.$store.dispatch('user/storeAuthTokensStaff', data);
        await this.$store.dispatch('user/loginSuccess');
    }

    async redirectUser(): Promise<void> {
        const goto = authStorage.getItem(AUTH_LOGIN_GOTO_PATH);

        if (goto) {
            authStorage.removeItem(AUTH_LOGIN_GOTO_PATH);
            this.$router.push({ path: goto });
        } else {
            await nextTick();
            this.$router.push({ name: 'Home' });
        }
    }
}
