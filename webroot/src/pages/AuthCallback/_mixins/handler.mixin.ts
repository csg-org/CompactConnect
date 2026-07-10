//
//  handler.mixin.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 6/24/2026.
//

import { AppModes } from '@/app.config';
import {
    authStorage,
    AuthTypes,
    AUTH_TYPE,
    AUTH_LOGIN_GOTO_PATH,
    AUTH_LOGIN_GOTO_PATH_AUTH_TYPE,
    consumeAuthCsrfState,
    consumePkceCodeVerifier
} from '@utils/auth';
import { nextTick } from 'vue';
import { Component, Vue } from 'vue-facing-decorator';
import Section from '@components/Section/Section.vue';
import Card from '@components/Card/Card.vue';
import axios from 'axios';

@Component({
    name: 'MixinAuthCallbackHandler',
    components: {
        Section,
        Card,
    },
})
class MixinAuthCallbackHandler extends Vue {
    //
    // Data (defaults)
    //
    appMode: AppModes = AppModes.JCC;
    authType: AuthTypes = AuthTypes.LICENSEE;
    cognitoAuthDomain = '';
    cognitoClientId = '';
    isError = false;

    //
    // Lifecycle
    //
    async created() {
        const {
            appMode,
            authType,
            cognitoAuthDomain,
            cognitoClientId
        } = this;

        // Verify the OAuth `state` param matches the CSRF token stored before redirecting to the hosted UI.
        // If it doesn't match, abort before exchanging the authorization code (possible CSRF / forged callback).
        if (!this.verifyCsrfState()) {
            this.isError = true;

            return;
        }

        await this.getTokens(appMode, authType, cognitoAuthDomain, cognitoClientId);
    }

    //
    // Computed
    //
    // https://docs.aws.amazon.com/cognito/latest/developerguide/authorization-endpoint.html
    get authorizationCode(): string {
        return this.$route.query?.code?.toString() || '';
    }

    get stateParam(): string {
        return this.$route.query?.state?.toString() || '';
    }

    //
    // Methods
    //
    verifyCsrfState(): boolean {
        const storedState = consumeAuthCsrfState(); // Reads and removes the stored token (single-use)

        return Boolean(storedState) && storedState === this.stateParam;
    }

    async getTokens(appMode: AppModes, authType: AuthTypes, cognitoAuthDomain, cognitoClientId): Promise<void> {
        this.$store.dispatch('startLoading');
        this.$store.dispatch('setAppMode', appMode);

        await this.fetchCognitoTokens(authType, cognitoAuthDomain, cognitoClientId).catch(() => {
            this.isError = true;
        });

        this.$store.dispatch('endLoading');

        if (!this.isError) {
            await this.redirectUser();
        }
    }

    async fetchCognitoTokens(authType: AuthTypes, cognitoAuthDomain, cognitoClientId): Promise<void> {
        const { domain } = this.$envConfig;
        const params = new URLSearchParams();

        if (authType && cognitoAuthDomain && cognitoClientId) {
            params.append('grant_type', 'authorization_code');
            params.append('client_id', cognitoClientId || '');
            params.append('redirect_uri', `${domain}${this.$route.path}`);
            params.append('code', this.authorizationCode);
            params.append('code_verifier', consumePkceCodeVerifier() || '');

            const { data } = await axios.post(`${cognitoAuthDomain}/oauth2/token`, params);

            await this.$store.dispatch('user/updateAuthTokens', { tokenResponse: data, authType });
            await this.$store.dispatch('user/loginSuccess', authType);
        } else {
            throw new Error(`missing parameters for token fetch`);
        }
    }

    async redirectUser(): Promise<void> {
        const goto = authStorage.getItem(AUTH_LOGIN_GOTO_PATH);
        const gotoAuthType = authStorage.getItem(AUTH_LOGIN_GOTO_PATH_AUTH_TYPE);
        const currentAuthType = authStorage.getItem(AUTH_TYPE);

        authStorage.removeItem(AUTH_LOGIN_GOTO_PATH);
        authStorage.removeItem(AUTH_LOGIN_GOTO_PATH_AUTH_TYPE);

        // If user had a previous path stored then redirect there
        if (goto && (!gotoAuthType || gotoAuthType === currentAuthType)) {
            this.$router.push({ path: goto });
        } else {
            // Otherwise let the Home page determine the default page
            await nextTick();
            this.$router.push({ name: 'Home' });
        }
    }
}

// export default toNative(MixinAuthCallbackHandler);

export default MixinAuthCallbackHandler;
