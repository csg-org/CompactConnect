//
//  ChangePassword.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/4/2024.
//

import { Component, mixins, toNative } from 'vue-facing-decorator';
import { reactive, computed } from 'vue';
import { authStorage, AuthTypes, tokens } from '@/app.config';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import InputPassword from '@components/Forms/InputPassword/InputPassword.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import { User } from '@models/User/User.model';
import { FormInput } from '@models/FormInput/FormInput.model';
import { dataApi } from '@network/data.api';
import Joi from 'joi';
import { joiPasswordExtendCore } from 'joi-password';

const joiPassword = Joi.extend(joiPasswordExtendCore);

@Component({
    name: 'ChangePassword',
    components: {
        InputPassword,
        InputSubmit,
    },
})
class ChangePassword extends mixins(MixinForm) {
    //
    // Lifecycle
    //
    created() {
        this.initFormInputs();
    }

    //
    // Computed
    //
    //
    get globalStore() {
        return this.$store.state;
    }

    get userStore() {
        return this.$store.state.user;
    }

    get authType(): AuthTypes {
        return this.globalStore.authType;
    }

    get isStaff(): boolean {
        return this.authType === AuthTypes.STAFF;
    }

    get isLicensee(): boolean {
        return this.authType === AuthTypes.LICENSEE;
    }

    get authToken(): string {
        let token = '';

        if (this.isStaff) {
            token = authStorage.getItem(tokens?.staff?.AUTH_TOKEN) || '';
        } else if (this.isLicensee) {
            token = authStorage.getItem(tokens?.licensee?.AUTH_TOKEN) || '';
        }

        return token;
    }

    get user(): User {
        return this.userStore.model || new User();
    }

    get submitLabel(): string {
        return (this.isFormLoading) ? this.$t('common.saving') : this.$t('common.changePassword');
    }

    //
    // Methods
    //
    initFormInputs(): void {
        this.formData = reactive({
            currentPassword: new FormInput({
                id: 'current-password',
                name: 'current-password',
                label: computed(() => this.$t('common.currentPassword')),
                placeholder: computed(() => this.$t('common.currentPassword')),
                autocomplete: 'current-password',
                validation: Joi.string().required().messages(this.joiMessages.string),
            }),
            newPassword: new FormInput({
                id: 'new-password',
                name: 'new-password',
                label: computed(() => this.$t('common.newPassword')),
                placeholder: computed(() => this.$t('common.newPassword')),
                autocomplete: 'new-password',
                validation: joiPassword
                    .string()
                    .min(12)
                    .doesNotInclude([
                        this.user.email,
                        this.user.firstName,
                        this.user.lastName,
                        'password',
                    ])
                    .messages({
                        ...this.joiMessages.string,
                        ...this.joiMessages.password,
                    }),
            }),
            confirmPassword: new FormInput({
                id: 'confirm-password',
                name: 'confirm-password',
                label: computed(() => this.$t('common.confirmNewPassword')),
                placeholder: computed(() => this.$t('common.confirmNewPassword')),
                autocomplete: 'new-password',
            }),
            submit: new FormInput({
                isSubmitInput: true,
                id: 'submit-change-password',
            }),
        });
        this.watchFormInputs(); // Important if you want automated form validation
    }

    async handleSubmit(): Promise<void> {
        this.validateAll({ asTouched: true });
        this.validateNewPassword();

        if (this.isFormValid) {
            this.startFormLoading();

            await this.changePasswordRequest().catch((errMessage) => {
                this.setError(errMessage);
            });

            if (!this.isFormError) {
                this.isFormSuccessful = true;
                this.updateFormSubmitSuccess(this.$t('common.success'));
            }

            this.endFormLoading();
        }
    }

    validateNewPassword(): void {
        const { confirmPassword: confirmPasswordInput } = this.formData;
        const { newPassword, confirmPassword } = this.formValues;

        if (confirmPasswordInput.isTouched && newPassword !== confirmPassword) {
            confirmPasswordInput.errorMessage = this.$t('common.passwordsMustMatch');
            confirmPasswordInput.isValid = false;
        } else {
            confirmPasswordInput.errorMessage = '';
            confirmPasswordInput.isValid = true;
        }
    }

    async changePasswordRequest(): Promise<void> {
        const { currentPassword, newPassword } = this.formValues;
        const requestData = {
            AccessToken: this.authToken,
            PreviousPassword: currentPassword,
            ProposedPassword: newPassword,
        };

        await dataApi.updateAuthenticatedUserPassword(requestData).catch((axiosError) => {
            const { data } = axiosError.response;
            const errMessage = data?.message || this.$t('common.passwordResetError');

            throw new Error(errMessage);
        });
    }
}

export default toNative(ChangePassword);

// export default ChangePassword;
