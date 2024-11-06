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
import { reactive, computed } from 'vue';
import { AuthTypes } from '@/app.config';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import Card from '@components/Card/Card.vue';
import InputText from '@components/Forms/InputText/InputText.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import ChangePassword from '@components/ChangePassword/ChangePassword.vue';
import { User } from '@models/User/User.model';
import { FormInput } from '@models/FormInput/FormInput.model';
import { dataApi } from '@network/data.api';
import Joi from 'joi';

@Component({
    name: 'UserAccount',
    components: {
        Card,
        InputText,
        InputSubmit,
        ChangePassword,
    }
})
class UserAccount extends mixins(MixinForm) {
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

    get authType(): AuthTypes {
        return this.globalStore.authType;
    }

    get isStaff(): boolean {
        return this.authType === AuthTypes.STAFF;
    }

    get isLicensee(): boolean {
        return this.authType === AuthTypes.LICENSEE;
    }

    get user(): User {
        return this.userStore.model || new User();
    }

    get submitLabel(): string {
        return (this.isFormLoading) ? this.$t('common.saving') : this.$t('common.saveChanges');
    }

    get isSubmitVisible(): boolean {
        const { formData } = this;
        const enabledInputKeys = this.formKeys.filter((key) => {
            const { isSubmitInput, isDisabled } = formData[key];

            return !isSubmitInput && !isDisabled;
        });

        return enabledInputKeys.length > 0;
    }

    //
    // Methods
    //
    initFormInputs(): void {
        this.formData = reactive({
            firstName: new FormInput({
                id: 'first-name',
                name: 'last-name',
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
                value: this.user.email,
                validation: Joi.string().email({ tlds: false }).messages(this.joiMessages.string),
                isDisabled: true,
            }),
            submit: new FormInput({
                isSubmitInput: true,
                id: 'submit-user-info',
            }),
        });
        this.watchFormInputs(); // Important if you want automated form validation
    }

    async handleSubmit(): Promise<void> {
        this.validateAll({ asTouched: true });

        if (this.isFormValid) {
            this.startFormLoading();
            await this.updateUserRequest();

            if (!this.isFormError) {
                this.isFormSuccessful = true;
                this.updateFormSubmitSuccess(this.$t('common.success'));
            }

            this.endFormLoading();
        }
    }

    async updateUserRequest(): Promise<void> {
        const { firstName, lastName } = this.formValues;
        const requestData = {
            attributes: {
                givenName: firstName,
                familyName: lastName,
            },
        };

        if (this.isStaff) {
            await dataApi.updateAuthenticatedStaffUser(requestData)
                .then((response) => {
                    this.$store.dispatch(`user/setStoreUser`, response);
                })
                .catch((err) => {
                    this.setError(err.message);
                });
        }
    }

    //
    // Watchers
    //
    @Watch('user') userData() {
        const { user } = this;

        this.formData.firstName.value = user.firstName;
        this.formData.lastName.value = user.lastName;
        this.formData.email.value = user.email;
    }
}

export default toNative(UserAccount);

// export default UserAccount;
