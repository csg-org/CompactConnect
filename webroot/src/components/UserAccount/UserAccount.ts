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
import MixinForm from '@components/Forms/_mixins/form.mixin';
import Card from '@components/Card/Card.vue';
import InputText from '@components/Forms/InputText/InputText.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import ChangePassword from '@components/ChangePassword/ChangePassword.vue';
import { User } from '@models/User/User.model';
import { FormInput } from '@models/FormInput/FormInput.model';
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
    get userStore() {
        return this.$store.state.user;
    }

    get user(): User {
        return this.userStore.model || new User();
    }

    get submitLabel(): string {
        return (this.isFormLoading) ? this.$t('common.saving') : this.$t('common.saveChanges');
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
                isDisabled: false,
            }),
            lastName: new FormInput({
                id: 'last-name',
                name: 'last-name',
                label: computed(() => this.$t('common.lastName')),
                placeholder: computed(() => this.$t('common.lastName')),
                autocomplete: 'family-name',
                value: this.user.lastName,
                validation: Joi.string().required().messages(this.joiMessages.string),
                isDisabled: false,
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

            // @TODO
            await new Promise((resolve) => setTimeout(() => resolve(true), 2000));

            if (!this.isFormError) {
                this.isFormSuccessful = true;
                this.updateFormSubmitSuccess(this.$t('common.success'));
            }

            this.endFormLoading();
        }
    }

    //
    // Watchers
    //
    @Watch('user') userData() {
        const { user } = this;

        if (user.firstName) {
            this.formData.firstName.value = user.firstName;
        }

        if (user.lastName) {
            this.formData.lastName.value = user.lastName;
        }
    }
}

export default toNative(UserAccount);

// export default UserAccount;
