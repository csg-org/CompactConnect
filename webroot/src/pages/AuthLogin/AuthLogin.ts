//
//  AuthLogin.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/22/2026.
//

import {
    Component,
    mixins,
    toNative
} from 'vue-facing-decorator';
import { reactive, computed, nextTick } from 'vue';
import { AppModes } from '@/app.config';
import {
    authStorage,
    AuthTypes,
    AUTH_LOGIN_GOTO_COMPACT,
    AUTH_LOGIN_GOTO_PATH,
    AUTH_LOGIN_GOTO_PATH_AUTH_TYPE,
    getCognitoConfig
} from '@utils/auth';
import {
    CompactType,
    getCompactSetup,
    getImpliedCompactForAppMode
} from '@utils/compactConfig';
import { getCompactConfig } from '@plugins/Compacts/compacts.plugin';
import cognitoAuth, {
    CognitoAuthResult,
    CognitoAuthStep,
    formatAuthCountdown,
    getTotpIssuer,
    OAuthTokenResponse
} from '@utils/cognitoAuth';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import Section from '@components/Section/Section.vue';
import Card from '@components/Card/Card.vue';
import InputText from '@components/Forms/InputText/InputText.vue';
import InputPassword from '@components/Forms/InputPassword/InputPassword.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import { FormInput } from '@models/FormInput/FormInput.model';
import Joi from 'joi';
import { joiPasswordExtendCore } from 'joi-password';
import QRCode from 'qrcode';

const joiPassword = Joi.extend(joiPasswordExtendCore);
const successMessageKeys = ['auth.codeSent', 'auth.passwordUpdated'];

@Component({
    name: 'AuthLogin',
    components: {
        Section,
        Card,
        InputText,
        InputPassword,
        InputSubmit,
        InputButton,
    },
})
class AuthLogin extends mixins(MixinForm) {
    //
    // Data
    //
    step: CognitoAuthStep = CognitoAuthStep.LOGIN;
    appMode: AppModes = AppModes.JCC;
    authType: AuthTypes = AuthTypes.STAFF;
    isSupportedTarget = false;
    totpSecret = '';
    qrCodeDataUrl = '';
    mfaSetupExpiresAt = 0;
    remainingMs = 0;
    countdownTimerId: number | null = null;
    didCopyKey = false;
    copyStatus = '';
    resetUsername = '';

    //
    // Lifecycle
    //
    created(): void {
        this.applyRoute();
        this.initFormInputs();
    }

    beforeUnmount(): void {
        this.clearCountdown();
    }

    //
    // Computed
    //
    get isLoginStep(): boolean {
        return this.step === CognitoAuthStep.LOGIN;
    }

    get isNewPasswordStep(): boolean {
        return this.step === CognitoAuthStep.NEW_PASSWORD;
    }

    get isMfaSetupStep(): boolean {
        return this.step === CognitoAuthStep.MFA_SETUP;
    }

    get isMfaCodeStep(): boolean {
        return this.step === CognitoAuthStep.MFA_CODE;
    }

    get isForgotPasswordStep(): boolean {
        return this.step === CognitoAuthStep.FORGOT_PASSWORD;
    }

    get isForgotPasswordConfirmStep(): boolean {
        return this.step === CognitoAuthStep.FORGOT_PASSWORD_CONFIRM;
    }

    get showsEmail(): boolean {
        return this.isLoginStep || this.isForgotPasswordStep || this.isForgotPasswordConfirmStep;
    }

    get showsLoginPassword(): boolean {
        return this.isLoginStep;
    }

    get showsNewPassword(): boolean {
        return this.isNewPasswordStep || this.isForgotPasswordConfirmStep;
    }

    get showsMfaCode(): boolean {
        return this.isMfaSetupStep || this.isMfaCodeStep;
    }

    get isMfaSetupExpired(): boolean {
        return this.isMfaSetupStep && this.mfaSetupExpiresAt > 0 && this.remainingMs <= 0;
    }

    get title(): string {
        let title = this.$t('auth.staffLoginTitle');

        if (this.authType === AuthTypes.LICENSEE) {
            title = this.$t('auth.practitionerLoginTitle');
        }

        if (this.isNewPasswordStep) {
            title = this.$t('auth.newPasswordTitle');
        } else if (this.isMfaSetupStep) {
            title = this.$t('auth.mfaSetupTitle');
        } else if (this.isMfaCodeStep) {
            title = this.$t('auth.mfaCodeTitle');
        } else if (this.isForgotPasswordStep) {
            title = this.$t('auth.forgotPasswordTitle');
        } else if (this.isForgotPasswordConfirmStep) {
            title = this.$t('auth.confirmForgotPasswordTitle');
        }

        return title;
    }

    get compactLabel(): string {
        const storedCompact = authStorage.getItem(AUTH_LOGIN_GOTO_COMPACT);
        const storedSetup = getCompactSetup(storedCompact);
        const compactType = (storedSetup?.appMode === this.appMode)
            ? storedCompact
            : getImpliedCompactForAppMode(this.appMode);
        const compact = getCompactConfig(compactType);
        const shouldAddAbbrev = compact?.type === CompactType.ASLP || compact?.type === CompactType.OT;
        let label = compact?.name || '';

        if (shouldAddAbbrev && compact?.abbrev) {
            label = `${label} (${compact.abbrev})`;
        }

        return label;
    }

    get instructions(): string {
        let instructions = '';

        if (this.isNewPasswordStep) {
            instructions = this.$t('auth.newPasswordInstructions');
        } else if (this.isMfaSetupStep) {
            instructions = this.$t('auth.mfaSetupInstructions');
        } else if (this.isMfaCodeStep) {
            instructions = this.$t('auth.mfaCodeInstructions');
        } else if (this.isForgotPasswordStep) {
            instructions = this.$t('auth.forgotPasswordInstructions');
        } else if (this.isForgotPasswordConfirmStep) {
            instructions = this.$t('auth.confirmForgotPasswordInstructions');
        }

        return instructions;
    }

    get countdownLabel(): string {
        return this.$t('auth.timeRemaining', { time: formatAuthCountdown(this.remainingMs) });
    }

    get copyLabel(): string {
        let label = this.$t('auth.copyKey');

        if (this.didCopyKey) {
            label = this.$t('auth.copiedKey');
        }

        return label;
    }

    get submitLabel(): string {
        let label = this.$t('navigation.login');

        if (this.isFormLoading && this.isLoginStep) {
            label = this.$t('auth.loggingIn');
        } else if (this.isFormLoading && this.isForgotPasswordStep) {
            label = this.$t('auth.sendingCode');
        } else if (this.isFormLoading && this.isMfaCodeStep) {
            label = this.$t('auth.verifyingCode');
        } else if (this.isFormLoading) {
            label = this.$t('common.saving');
        } else if (this.isForgotPasswordStep) {
            label = this.$t('auth.sendCode');
        } else if (this.isNewPasswordStep || this.isForgotPasswordConfirmStep) {
            label = this.$t('common.confirm');
        } else if (this.isMfaSetupStep || this.isMfaCodeStep) {
            label = this.$t('common.continue');
        }

        return label;
    }

    get isSubmitEnabled(): boolean {
        return !this.isFormLoading && !this.isMfaSetupExpired;
    }

    get totpIssuer(): string {
        return getTotpIssuer(this.appMode);
    }

    //
    // Methods
    //
    applyRoute(): void {
        const authTypeParam = String(this.$route.params.authType || '');
        const appModeParam = String(this.$route.params.appMode || '');
        const stepParam = String(this.$route.query.step || '');
        const isStaff = authTypeParam === AuthTypes.STAFF;
        const isLicensee = authTypeParam === AuthTypes.LICENSEE;
        const isKnownMode = Object.values(AppModes).some((mode) => mode === appModeParam);
        let supported = false;

        if ((isStaff || isLicensee) && isKnownMode) {
            supported = Boolean(getCognitoConfig(appModeParam as AppModes, authTypeParam as AuthTypes).clientId);
        }

        this.isSupportedTarget = supported;

        if (supported) {
            this.authType = authTypeParam as AuthTypes;
            this.appMode = appModeParam as AppModes;
            this.$store.dispatch('setAppMode', this.appMode);

            if (stepParam === CognitoAuthStep.FORGOT_PASSWORD) {
                this.step = CognitoAuthStep.FORGOT_PASSWORD;
            }
        }
    }

    passwordValidation(): Joi.Schema {
        return joiPassword
            .string()
            .min(12)
            .minOfLowercase(1)
            .minOfNumeric(1)
            .messages({
                ...this.joiMessages.string,
                ...this.joiMessages.password,
            });
    }

    initFormInputs(): void {
        const formData: Record<string, FormInput> = {};

        if (this.showsEmail) {
            formData.email = new FormInput({
                id: 'auth-email',
                name: 'email',
                label: computed(() => this.$t('common.emailAddress')),
                placeholder: computed(() => this.$t('common.emailAddress')),
                autocomplete: 'username',
                value: this.resetUsername,
                validation: Joi.string().email({ tlds: false }).required()
                    .messages(this.joiMessages.string),
            });
        }

        if (this.showsLoginPassword) {
            formData.password = new FormInput({
                id: 'auth-password',
                name: 'password',
                label: computed(() => this.$t('common.password')),
                placeholder: computed(() => this.$t('common.password')),
                autocomplete: 'current-password',
                validation: Joi.string().required().messages(this.joiMessages.string),
            });
        }

        if (this.isForgotPasswordConfirmStep) {
            formData.resetCode = new FormInput({
                id: 'auth-reset-code',
                name: 'reset-code',
                label: computed(() => this.$t('auth.resetCode')),
                placeholder: computed(() => this.$t('auth.resetCode')),
                autocomplete: 'one-time-code',
                validation: Joi.string().required().messages(this.joiMessages.string),
            });
        }

        if (this.showsNewPassword) {
            formData.newPassword = new FormInput({
                id: 'auth-new-password',
                name: 'new-password',
                label: computed(() => this.$t('common.newPassword')),
                placeholder: computed(() => this.$t('common.newPassword')),
                autocomplete: 'new-password',
                validation: this.passwordValidation(),
            });
            formData.confirmPassword = new FormInput({
                id: 'auth-confirm-password',
                name: 'confirm-password',
                label: computed(() => this.$t('common.confirmNewPassword')),
                placeholder: computed(() => this.$t('common.confirmNewPassword')),
                autocomplete: 'new-password',
                validation: Joi.string().required().messages(this.joiMessages.string),
            });
        }

        if (this.showsMfaCode) {
            formData.mfaCode = new FormInput({
                id: 'auth-mfa-code',
                name: 'mfa-code',
                label: computed(() => this.$t('auth.mfaCode')),
                placeholder: computed(() => this.$t('auth.mfaCode')),
                autocomplete: 'one-time-code',
                validation: Joi.string().length(6).pattern(/^\d+$/).required()
                    .messages(this.joiMessages.string),
            });
        }

        formData.submit = new FormInput({
            isSubmitInput: true,
            id: 'auth-submit',
        });
        this.formData = reactive(formData);
        this.watchFormInputs();
    }

    validatePasswordMatch(): void {
        const confirmPasswordInput = this.formData.confirmPassword;
        const { newPassword, confirmPassword } = this.formValues;

        if (confirmPasswordInput && confirmPasswordInput.isTouched && newPassword !== confirmPassword) {
            confirmPasswordInput.errorMessage = this.$t('common.passwordsMustMatch');
            confirmPasswordInput.isValid = false;
            this.checkValidForAll();
        } else if (confirmPasswordInput && confirmPasswordInput.isTouched) {
            confirmPasswordInput.errorMessage = '';
            confirmPasswordInput.isValid = true;
            this.checkValidForAll();
        }
    }

    validateAll(config: any = {}): void {
        const shouldSkipFieldFocus = !config.asTouched;
        const nextConfig = {
            ...config,
            skipErrorScroll: shouldSkipFieldFocus || Boolean(config.skipErrorScroll),
        };

        MixinForm.prototype.validateAll.call(this, nextConfig);
    }

    async handleSubmit(): Promise<void> {
        this.validateAll({ asTouched: true });
        this.validatePasswordMatch();

        if (this.isFormValid && !this.isMfaSetupExpired) {
            this.startFormLoading();
            await this.submitCurrentStep().catch(() => {
                this.setError(this.$t('auth.genericError'));
            });
            this.endFormLoading();
        } else if (this.isMfaSetupExpired) {
            this.setError(this.$t('auth.sessionExpired'));
        }
    }

    async submitCurrentStep(): Promise<void> {
        const {
            email,
            password,
            newPassword,
            confirmPassword,
            resetCode,
            mfaCode,
        } = this.formValues;
        let result: CognitoAuthResult = {};

        if (this.isLoginStep) {
            result = await cognitoAuth.signInWithPassword(
                this.appMode,
                this.authType,
                email,
                password,
                this.totpIssuer
            );
        } else if (this.isNewPasswordStep) {
            result = await cognitoAuth.confirmChallenge(newPassword, this.totpIssuer);
        } else if (this.isMfaSetupStep || this.isMfaCodeStep) {
            result = await cognitoAuth.confirmChallenge(mfaCode, this.totpIssuer);
        } else if (this.isForgotPasswordStep) {
            result = await cognitoAuth.requestPasswordReset(this.appMode, this.authType, email);
        } else if (this.isForgotPasswordConfirmStep) {
            result = await cognitoAuth.confirmPasswordReset(email || '', resetCode, newPassword || confirmPassword);
        }

        await this.applyAuthResult(result);
    }

    async applyAuthResult(result: CognitoAuthResult): Promise<void> {
        const isSuccessMessage = Boolean(result.messageKey) && successMessageKeys.indexOf(result.messageKey || '') !== -1;

        if (result.tokenResponse) {
            await this.finishLogin(result.tokenResponse);
        } else {
            this.rememberEmail();

            if (result.step) {
                await this.setStep(result.step, result);
            }

            if (result.messageKey && isSuccessMessage) {
                this.updateFormSubmitSuccess(this.$t(result.messageKey));
            } else if (result.messageKey) {
                this.setError(this.$t(result.messageKey));
            }
        }
    }

    async setStep(step: CognitoAuthStep, result: CognitoAuthResult = {}): Promise<void> {
        this.step = step;
        this.didCopyKey = false;
        this.copyStatus = '';
        this.totpSecret = result.totpSecret || '';
        this.qrCodeDataUrl = '';
        this.mfaSetupExpiresAt = result.mfaSetupExpiresAt || 0;
        this.remainingMs = (this.mfaSetupExpiresAt) ? this.mfaSetupExpiresAt - Date.now() : 0;
        this.clearCountdown();
        this.initFormInputs();

        if (result.totpSetupUri) {
            this.qrCodeDataUrl = await QRCode.toDataURL(result.totpSetupUri, { margin: 1, width: 220 });
        }

        if (this.mfaSetupExpiresAt) {
            this.startCountdown();
        }

        await this.focusStepTitle();
    }

    async focusStepTitle(): Promise<void> {
        await nextTick();
        const title = this.$refs.stepTitle as HTMLElement | undefined;

        if (title) {
            if (typeof title.scrollIntoView === 'function') {
                title.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }

            title.focus();
        }
    }

    rememberEmail(): void {
        if (this.formValues.email) {
            this.resetUsername = this.formValues.email;
        }
    }

    startCountdown(): void {
        this.clearCountdown();
        this.countdownTimerId = window.setInterval(() => {
            this.remainingMs = this.mfaSetupExpiresAt - Date.now();

            if (this.remainingMs <= 0) {
                this.remainingMs = 0;
                this.clearCountdown();
                this.setError(this.$t('auth.sessionExpired'));
            }
        }, 1000);
    }

    clearCountdown(): void {
        if (this.countdownTimerId !== null) {
            window.clearInterval(this.countdownTimerId);
            this.countdownTimerId = null;
        }
    }

    async copySetupKey(): Promise<void> {
        let didCopy = false;

        if (this.totpSecret && navigator.clipboard) {
            await navigator.clipboard.writeText(this.totpSecret).then(() => {
                didCopy = true;
            }).catch(() => {
                didCopy = false;
            });
        }

        this.didCopyKey = didCopy;
        this.copyStatus = '';

        if (didCopy) {
            await nextTick();
            this.copyStatus = this.$t('auth.copiedKey');
        }
    }

    showForgotPassword(): Promise<void> {
        this.rememberEmail();

        return this.setStep(CognitoAuthStep.FORGOT_PASSWORD);
    }

    showLogin(): Promise<void> {
        this.rememberEmail();

        return this.setStep(CognitoAuthStep.LOGIN);
    }

    async finishLogin(tokenResponse: OAuthTokenResponse): Promise<void> {
        const goto = authStorage.getItem(AUTH_LOGIN_GOTO_PATH);
        const gotoAuthType = authStorage.getItem(AUTH_LOGIN_GOTO_PATH_AUTH_TYPE);

        authStorage.removeItem(AUTH_LOGIN_GOTO_PATH);
        authStorage.removeItem(AUTH_LOGIN_GOTO_PATH_AUTH_TYPE);
        this.$store.dispatch('setAppMode', this.appMode);
        await this.$store.dispatch('user/updateAuthTokens', { tokenResponse, authType: this.authType });
        await this.$store.dispatch('user/loginSuccess', this.authType);

        if (goto && (!gotoAuthType || gotoAuthType === this.authType)) {
            this.$router.push({ path: goto });
        } else {
            await nextTick();
            this.$router.push({ name: 'Home' });
        }
    }
}

export default toNative(AuthLogin);
