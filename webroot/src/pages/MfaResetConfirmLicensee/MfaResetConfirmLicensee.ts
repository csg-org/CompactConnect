//
//  MfaResetConfirmLicensee.ts
//  CompactConnect
//
//  Created by InspiringApps on 8/22/2025.
//

import {
    Component,
    Vue,
    Watch,
    toNative
} from 'vue-facing-decorator';
import {
    authStorage,
    AppModes,
    AuthTypes,
    getHostedLoginUri,
    AUTH_LOGIN_GOTO_PATH,
    AUTH_LOGIN_GOTO_PATH_AUTH_TYPE
} from '@/app.config';
import Section from '@components/Section/Section.vue';
import Card from '@components/Card/Card.vue';
import LoadingSpinner from '@components/LoadingSpinner/LoadingSpinner.vue';
import CheckCircle from '@components/Icons/CheckCircle/CheckCircle.vue';
import AlertTriangle from '@components/Icons/AlertTriangle/AlertTriangle.vue';
import InputButton from '@components/Forms/InputButton/InputButton.vue';

@Component({
    name: 'MfaResetConfirmLicensee',
    components: {
        Section,
        Card,
        LoadingSpinner,
        CheckCircle,
        AlertTriangle,
        InputButton,
    },
})
class MfaResetConfirmLicensee extends Vue {
    //
    // Data
    //
    recaptchaCheckIntervalId: number | null = null;
    isRecaptchaLoaded = false;
    isLoading = true;
    isSuccess = false;
    serverMessage = '';

    //
    // Lifecycle
    //
    mounted(): void {
        this.initRecaptcha();
    }

    beforeUnmount(): void {
        this.removeRecaptchaCheck();
    }

    //
    // Computed
    //
    get appMode(): AppModes {
        return this.$store.state.appMode;
    }

    get compactQuery(): string {
        const compact: string = (this.$route.query?.compact as string) || '';

        return compact.toLowerCase();
    }

    get providerIdQuery(): string {
        return (this.$route.query?.providerId as string) || '';
    }

    get recoveryIdQuery(): string {
        return (this.$route.query?.recoveryId as string) || '';
    }

    get hostedLoginUriLicensee(): string {
        return getHostedLoginUri(this.appMode, AuthTypes.LICENSEE, '/login');
    }

    get isUsingMockApi(): boolean {
        return this.$envConfig.isUsingMockApi || false;
    }

    //
    // Methods
    //
    initRecaptcha(): void {
        const recaptchaContainer: HTMLElement = this.$refs.recaptcha as HTMLElement;
        const scriptEl = document.createElement('script');
        const src = `https://www.google.com/recaptcha/api.js?render=${this.$envConfig.recaptchaKey}`;
        const windowRef = window as any;

        scriptEl.setAttribute('src', src);
        recaptchaContainer.appendChild(scriptEl);

        this.recaptchaCheckIntervalId = windowRef.setInterval(() => {
            if (windowRef.grecaptcha && typeof windowRef.grecaptcha.ready === 'function') {
                this.isRecaptchaLoaded = true;
            }
        }, 2000);
    }

    removeRecaptchaCheck(): void {
        (window as any).clearInterval(this.recaptchaCheckIntervalId);
        this.recaptchaCheckIntervalId = null;
    }

    async initiateRecoveryConfirmation(): Promise<void> {
        const { compactQuery, providerIdQuery, recoveryIdQuery } = this;
        const firstName = document.getElementById('first-name') as HTMLInputElement;
        let isError = false;

        if (compactQuery && providerIdQuery && recoveryIdQuery && !firstName?.value) {
            const data = {
                compact: compactQuery,
                providerId: providerIdQuery,
                recoveryToken: recoveryIdQuery,
                recaptchaToken: '',
            };

            await this.handleRecaptcha(data).catch(() => {
                this.serverMessage = this.$t('account.requestErrorRecaptcha');
                isError = true;
            });

            if (!isError) {
                await this.$store.dispatch('user/confirmMfaLicenseeAccountRequest', { data }).catch((err) => {
                    this.serverMessage = this.handleErrorResponse(err);
                    isError = true;
                });
            }

            if (!isError) {
                this.isSuccess = true;
            }
        }

        this.isLoading = false;
    }

    async handleRecaptcha(data): Promise<void> {
        const { recaptchaKey, isUsingMockApi } = this.$envConfig;

        if (!isUsingMockApi) {
            const { grecaptcha } = window as any; // From the SDK loaded in initRecaptcha() above
            const recaptchaToken = await new Promise((resolve, reject) => {
                grecaptcha.ready(() => {
                    grecaptcha.execute(recaptchaKey, { action: 'submit' }).then((token) => {
                        resolve(token);
                    }).catch((err) => {
                        reject(err);
                    });
                });
            }).catch((err) => { throw err; });

            data.recaptchaToken = recaptchaToken;
        }
    }

    handleErrorResponse(err): string {
        const { message = '', responseStatus } = err || {};
        let errorMessage = '';

        switch (responseStatus) {
        case 400:
            errorMessage = message || this.$t('serverErrors.networkError');
            break;
        case 429:
            errorMessage = this.$t('serverErrors.rateLimit');
            break;
        default:
            errorMessage = message;
            break;
        }

        return errorMessage;
    }

    goToLogin(): void {
        if (this.isUsingMockApi) {
            this.mockLicenseeLogin();
        } else {
            window.location.replace(this.hostedLoginUriLicensee);
        }
    }

    goToDashboard(): void {
        this.$router.replace({ name: 'DashboardPublic' });
    }

    async mockLicenseeLogin(): Promise<void> {
        const goto = authStorage.getItem(AUTH_LOGIN_GOTO_PATH);
        const gotoAuthType = authStorage.getItem(AUTH_LOGIN_GOTO_PATH_AUTH_TYPE);
        const data = {
            access_token: 'mock_access_token',
            token_type: 'Bearer',
            expires_in: '100000000',
            id_token: 'mock_id_token',
            refresh_token: 'mock_refresh_token'
        };

        authStorage.removeItem(AUTH_LOGIN_GOTO_PATH);
        authStorage.removeItem(AUTH_LOGIN_GOTO_PATH_AUTH_TYPE);
        await this.$store.dispatch('user/updateAuthTokens', { tokenResponse: data, authType: AuthTypes.LICENSEE });
        this.$store.dispatch('user/loginSuccess', AuthTypes.LICENSEE);

        if (goto && (!gotoAuthType || gotoAuthType === AuthTypes.LICENSEE)) {
            this.$router.replace({ path: goto });
        } else {
            this.$router.replace({ name: 'Home' });
        }
    }

    //
    // Watch
    //
    @Watch('isRecaptchaLoaded') recaptchaLoaded() {
        if (this.isRecaptchaLoaded) {
            this.removeRecaptchaCheck();
            this.initiateRecoveryConfirmation();
        }
    }
}

export default toNative(MfaResetConfirmLicensee);

// export default MfaResetConfirmLicensee;
