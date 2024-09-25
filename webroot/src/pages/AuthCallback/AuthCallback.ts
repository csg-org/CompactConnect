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
import { authStorage, AuthTypes, AUTH_LOGIN_GOTO_PATH } from '@/app.config';
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

    get userType(): string {
        return this.$route.query?.state?.toString() || '';
    }

    //
    // Methods
    //
    async getTokens(): Promise<void> {
        this.$store.dispatch('startLoading');

        if (this.userType === AuthTypes.STAFF) {
            await this.getTokensStaff().catch(() => {
                this.isError = true;
            });
        } else if (this.userType === AuthTypes.LICENSEE) {
            await this.getTokensLicensee().catch(() => {
                this.isError = true;
            });
        } else {
            // If the state query param is absent or not matching we will
            // still try to get tokens, if the user just logged in one of the two
            // user pools will successfully return tokens. If neither do we enter
            // the error state

            let errorCount = 0;

            await this.getTokensStaff().catch(() => {
                errorCount += 1;
            });

            if (errorCount > 0) {
                await this.getTokensLicensee().catch(() => {
                    errorCount += 1;
                });
            }

            if (errorCount > 1) {
                this.isError = true;
            }
        }

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

        await this.$store.dispatch('user/storeAuthTokens', { tokenResponse: data, authType: AuthTypes.STAFF });
        await this.$store.dispatch('user/loginSuccess');
    }

    async getTokensLicensee(): Promise<void> {
        const { domain, cognitoAuthDomainLicensee, cognitoClientIdLicensee } = this.$envConfig;
        const params = new URLSearchParams();

        params.append('grant_type', 'authorization_code');
        params.append('client_id', cognitoClientIdLicensee || '');
        params.append('redirect_uri', `${domain}${this.$route.path}`);
        params.append('code', this.authorizationCode);

        const { data } = await axios.post(`${cognitoAuthDomainLicensee}/oauth2/token`, params);

        await this.$store.dispatch('user/storeAuthTokens', { tokenResponse: data, authType: AuthTypes.LICENSEE });
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
