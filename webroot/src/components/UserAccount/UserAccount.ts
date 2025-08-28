//
//  UserAccount.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/4/2024.
//

import {
    Component,
    mixins,
    Watch,
    toNative
} from 'vue-facing-decorator';
import { reactive, computed, nextTick } from 'vue';
import { AuthTypes } from '@/app.config';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import Card from '@components/Card/Card.vue';
import InputText from '@components/Forms/InputText/InputText.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import ChangePassword from '@components/ChangePassword/ChangePassword.vue';
import Modal from '@components/Modal/Modal.vue';
import CheckCircleIcon from '@components/Icons/CheckCircle/CheckCircle.vue';
import MockPopulate from '@components/Forms/MockPopulate/MockPopulate.vue';
import { User } from '@models/User/User.model';
import { LicenseeUser } from '@models/LicenseeUser/LicenseeUser.model';
import { StaffUser } from '@models/StaffUser/StaffUser.model';
import { FormInput } from '@models/FormInput/FormInput.model';
import { dataApi } from '@network/data.api';
import Joi from 'joi';
import UpdateHomeJurisdiction from '@components/UpdateHomeJurisdiction/UpdateHomeJurisdiction.vue';

@Component({
    name: 'UserAccount',
    components: {
        MockPopulate,
        InputButton,
        Card,
        InputText,
        InputSubmit,
        Modal,
        CheckCircleIcon,
        ChangePassword,
        UpdateHomeJurisdiction,
    }
})
class UserAccount extends mixins(MixinForm) {
    //
    // Data
    //
    initialUserEmail = '';
    isEmailVerificationModalDisplayed = false;
    isEmailVerificationModalSuccess = false;
    emailVerificationErrorMessage = '';

    //
    // Lifecycle
    //
    created() {
        this.initFormInputs();
    }

    //
    // Computed
    //
    get globalStore() {
        return this.$store.state;
    }

    get userStore() {
        return this.$store.state.user;
    }

    get currentCompactType(): string | null {
        return this.userStore?.currentCompact?.type || null;
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

    get user(): User | LicenseeUser | StaffUser {
        return this.userStore.model || new User();
    }

    get email(): string {
        return this.user?.compactConnectEmail || '';
    }

    get submitLabel(): string {
        return (this.isFormLoading) ? this.$t('common.saving') : this.$t('common.saveChanges');
    }

    //
    // Methods
    //
    initFormInputs(): void {
        if (this.isEmailVerificationModalDisplayed) {
            this.initFormInputsEmailVerification();
        } else {
            this.initFormInputsAccount();
        }
    }

    initFormInputsAccount(): void {
        this.initialUserEmail = this.email;
        this.formData = reactive({
            firstName: new FormInput({
                id: 'first-name',
                name: 'first-name',
                label: computed(() => this.$t('common.firstName')),
                placeholder: computed(() => this.$t('common.firstName')),
                autocomplete: 'given-name',
                value: this.user.firstName,
                validation: Joi.string().required().messages(this.joiMessages.string),
                isDisabled: this.isLicensee,
            }),
            lastName: new FormInput({
                id: 'last-name',
                name: 'last-name',
                label: computed(() => this.$t('common.lastName')),
                placeholder: computed(() => this.$t('common.lastName')),
                autocomplete: 'family-name',
                value: this.user.lastName,
                validation: Joi.string().required().messages(this.joiMessages.string),
                isDisabled: this.isLicensee,
            }),
            email: new FormInput({
                id: 'email',
                name: 'email',
                label: computed(() => this.$t('common.emailAddress')),
                placeholder: computed(() => this.$t('common.emailAddress')),
                autocomplete: 'email',
                value: this.email,
                validation: Joi.string().email({ tlds: false }).messages(this.joiMessages.string),
                isDisabled: this.isStaff,
            }),
            submitUserUpdate: new FormInput({
                isSubmitInput: true,
                id: 'submit-user-info',
            }),
        });
        this.watchFormInputs(); // Important if you want automated form validation
    }

    initFormInputsEmailVerification(): void {
        this.formData = reactive({
            emailVerificationCode: new FormInput({
                id: 'verification-code',
                name: 'verification-code',
                label: computed(() => this.$t('account.enterCode')),
                autocomplete: 'off',
                validation: Joi.string().required().max(12).messages(this.joiMessages.string),
                enforceMax: true,
            }),
            submitEmailVerification: new FormInput({
                isSubmitInput: true,
                id: 'confirm-modal-submit-button',
            }),
        });
        this.watchFormInputs(); // Important if you want automated form validation
    }

    async handleSubmit(): Promise<void> {
        this.validateAll({ asTouched: true });
        await nextTick();

        if (this.isFormValid) {
            const { isStaff, isLicensee } = this;

            if (isStaff) {
                await this.updateUserRequestStaff();
            } else if (isLicensee) {
                await this.updateUserRequestLicensee();
            }
        }
    }

    async updateUserRequestStaff(): Promise<void> {
        const { firstName, lastName } = this.formValues;
        const requestData = {
            attributes: {
                givenName: firstName,
                familyName: lastName,
            },
        };

        this.startFormLoading();

        await dataApi.updateAuthenticatedStaffUser(requestData)
            .then((response) => {
                this.$store.dispatch(`user/setStoreUser`, response);
            })
            .catch((err) => {
                this.setError(err.message);
            });

        await nextTick();
        (this.$refs.confirmEmailModalContent as HTMLElement)?.focus();

        if (!this.isFormError) {
            this.isFormSuccessful = true;
            this.updateFormSubmitSuccess(this.$t('common.success'));
        }

        this.endFormLoading();
    }

    async updateUserRequestLicensee(): Promise<void> {
        const { formValues, initialUserEmail } = this;
        const isEmailChanged = formValues.email !== initialUserEmail;
        const requestData = { newEmailAddress: formValues.email };

        if (!isEmailChanged) {
            this.setError(this.$t('account.noValuesChanged'));
        } else {
            this.startFormLoading();
            await dataApi.updateAuthenticatedLicenseeUserEmail(requestData)
                .then(() => {
                    this.openEmailVerificationModal();
                })
                .catch((err) => {
                    this.setError(err.message);
                });
            this.endFormLoading();
        }

        await nextTick();
        (this.$refs.confirmEmailModalContent as HTMLElement)?.focus();
    }

    async openEmailVerificationModal(): Promise<void> {
        this.isEmailVerificationModalDisplayed = true;
        this.initFormInputs();
    }

    async closeEmailVerificationModal(): Promise<void> {
        this.isEmailVerificationModalDisplayed = false;
        this.isEmailVerificationModalSuccess = false;
        this.emailVerificationErrorMessage = '';
        this.initFormInputs();
        await nextTick();
        document.getElementById(this.formData.submitUserUpdate.id)?.focus();
    }

    focusTrapEmailVerificationModal(event: KeyboardEvent): void {
        const firstTabIndex = (this.isEmailVerificationModalSuccess)
            ? document.getElementById('confirm-modal-submit-button')
            : document.getElementById(this.formData.emailVerificationCode.id);
        const lastTabIndex = (this.isEmailVerificationModalSuccess)
            ? document.getElementById('confirm-modal-submit-button')
            : document.getElementById('confirm-modal-cancel-button');

        if (event.shiftKey) {
            // shift + tab to last input
            if (document.activeElement === firstTabIndex) {
                lastTabIndex?.focus();
                event.preventDefault();
            }
        } else if (document.activeElement === lastTabIndex) {
            // Tab to first input
            firstTabIndex?.focus();
            event.preventDefault();
        }
    }

    async submitEmailVerification(): Promise<void> {
        this.emailVerificationErrorMessage = '';
        this.validateAll({ asTouched: true });
        await nextTick();

        if (this.isFormValid) {
            const { formValues, isLicensee } = this;
            const requestData = { verificationCode: formValues.emailVerificationCode };
            let isError = false;

            if (isLicensee) {
                this.startFormLoading();
                await dataApi.verifyAuthenticatedLicenseeUserEmail(requestData).catch((err) => {
                    this.emailVerificationErrorMessage = err?.message || this.$t('serverErrors.networkError');
                    isError = true;
                });

                if (!isError) {
                    this.isEmailVerificationModalSuccess = true;
                    await this.$store.dispatch(`user/getLicenseeAccountRequest`);
                }

                this.endFormLoading();
            }

            await nextTick();
            (this.$refs.confirmEmailModalContent as HTMLElement)?.focus();
        }
    }

    viewMilitaryStatus(): void {
        if (this.currentCompactType) {
            this.$router.push({ name: 'MilitaryStatus', params: { compact: this.currentCompactType }});
        }
    }

    //
    // Watchers
    //
    @Watch('user') userData() {
        this.initFormInputs();
    }
}

export default toNative(UserAccount);

// export default UserAccount;
