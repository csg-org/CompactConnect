//
//  ExampleForm.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/3/2021.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

import { Component, mixins, toNative } from 'vue-facing-decorator';
import { reactive, computed } from 'vue';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import Section from '@components/Section/Section.vue';
import InputText from '@components/Forms/InputText/InputText.vue';
import InputTextarea from '@components/Forms/InputTextarea/InputTextarea.vue';
import InputSelect from '@components/Forms/InputSelect/InputSelect.vue';
import InputCheckbox from '@components/Forms/InputCheckbox/InputCheckbox.vue';
import InputRadioGroup from '@components/Forms/InputRadioGroup/InputRadioGroup.vue';
import InputDate from '@components/Forms/InputDate/InputDate.vue';
import InputFile from '@components/Forms/InputFile/InputFile.vue';
import InputPassword from '@components/Forms/InputPassword/InputPassword.vue';
import InputPhone from '@components/Forms/InputPhone/InputPhone.vue';
import InputRange from '@components/Forms/InputRange/InputRange.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
// import { User } from '@models/User/User.model';
import { FormInput } from '@models/FormInput/FormInput.model';
import Joi from 'joi';
import { joiPasswordExtendCore } from 'joi-password';

const joiPassword = Joi.extend(joiPasswordExtendCore);

@Component({
    name: 'ExampleForm',
    components: {
        Section,
        InputText,
        InputTextarea,
        InputSelect,
        InputCheckbox,
        InputRadioGroup,
        InputDate,
        InputFile,
        InputPassword,
        InputPhone,
        InputRange,
        InputSubmit,
    }
})
class ExampleForm extends mixins(MixinForm) {
    //
    // Data
    //
    isFormLoading = false; // This would normally be a computed based on (e.g.) store loading state.

    //
    // Lifecycle
    //
    created() {
        this.initFormInputs();
    }

    //
    // Computed
    //
    get submitLabel(): string {
        let label = this.$t('common.submit');

        if (this.isFormLoading) {
            label = this.$t('common.loading');
        }

        return label;
    }

    get states(): any {
        return this.$tm('common.states');
    }

    get statusOptions(): any {
        return this.$tm('styleGuide.statusOptions');
    }

    //
    // Methods
    //
    initFormInputs(): void {
        this.formData = reactive({
            firstName: new FormInput({
                id: 'first-name',
                name: 'first-name',
                label: computed(() => this.$t('common.firstName')),
                placeholder: computed(() => this.$t('common.firstName')),
                validation: Joi.string().min(2).messages(this.joiMessages.string),
            }),
            lastName: new FormInput({
                id: 'last-name',
                name: 'last-name',
                label: computed(() => this.$t('common.lastName')),
                placeholder: computed(() => this.$t('common.lastName')),
                validation: Joi.string().min(2).messages(this.joiMessages.string),
            }),
            email: new FormInput({
                id: 'email',
                name: 'email',
                label: computed(() => this.$t('common.emailAddress')),
                placeholder: computed(() => this.$t('common.emailAddress')),
                validation: Joi.string().email({ tlds: false }).allow('').messages(this.joiMessages.string),
            }),
            description: new FormInput({
                id: 'description',
                name: 'description',
                label: computed(() => this.$t('common.description')),
                placeholder: computed(() => this.$t('common.description')),
                validation: Joi.string().max(20).allow('').messages(this.joiMessages.string),
                showMax: true,
                enforceMax: true,
            }),
            state: new FormInput({
                id: 'state',
                name: 'state',
                label: computed(() => this.$t('common.state')),
                placeholder: computed(() => this.$t('common.state')),
                validation: Joi.string().required().messages(this.joiMessages.string),
                valueOptions: [{ value: '', name: computed(() => this.$t('common.chooseOne')) }]
                    .concat(this.states.map((state) => ({ value: state.abbrev, name: state.full }))),
            }),
            isSubscribed: new FormInput({
                id: 'subscribe',
                name: 'subscribe',
                label: computed(() => this.$t('styleGuide.subscribe')),
                placeholder: computed(() => this.$t('styleGuide.subscribe')),
                value: false,
            }),
            status: new FormInput({
                id: 'status',
                name: 'status',
                label: computed(() => this.$t('styleGuide.status')),
                placeholder: computed(() => this.$t('styleGuide.status')),
                validation: Joi.string().required().messages(this.joiMessages.string),
                valueOptions: this.statusOptions.map((option) => ({ ...option })),
            }),
            dob: new FormInput({
                id: 'dob',
                name: 'dob',
                label: computed(() => this.$t('common.dateOfBirth')),
                placeholder: computed(() => this.$t('common.dateOfBirth')),
                // value: '1990-01-01',
            }),
            documents: new FormInput({
                id: 'documents',
                name: 'documents',
                label: computed(() => this.$t('styleGuide.documents')),
                placeholder: computed(() => this.$t('styleGuide.documents')),
                value: [],
                validation: Joi.array().min(1),
                fileConfig: {
                    accepts: [`application/pdf`, `application/csv`],
                    allowMultiple: false,
                    maxSizeMbPer: 1,
                    maxSizeMbAll: 5,
                },
            }),
            password: new FormInput({
                id: 'password',
                name: 'password',
                label: computed(() => this.$t('common.password')),
                placeholder: computed(() => this.$t('common.password')),
                autocomplete: 'current-password',
                validation: joiPassword
                    .string()
                    .min(8)
                    .minOfSpecialCharacters(1)
                    .minOfLowercase(1)
                    .minOfUppercase(1)
                    .minOfNumeric(1)
                    // .noWhiteSpaces()
                    // .onlyLatinCharacters()
                    .doesNotInclude(['password'])
                    .messages({
                        ...this.joiMessages.string,
                        ...this.joiMessages.password,
                    }),
            }),
            phone: new FormInput({
                id: 'phone',
                name: 'phone',
                label: computed(() => this.$t('common.phoneNumber')),
                placeholder: computed(() => this.$t('common.phoneNumber')),
            }),
            happiness: new FormInput({
                id: 'happiness',
                name: 'happiness',
                label: computed(() => this.$t('styleGuide.happiness')),
                rangeConfig: {
                    min: 0,
                    max: 100,
                    stepInterval: 5,
                    displayFormatter: (value: any) => new Intl.NumberFormat().format(value),
                },
                value: 100,
            }),
            submit: new FormInput({
                isSubmitInput: true,
                id: 'submit',
            }),
        });
        this.watchFormInputs(); // Important if you want automated form validation
        this.populateFormFields();
    }

    populateFormFields(): void {
        this.populateFormInput(this.formData.firstName, 'aa'); // Could be used to populate value from (e.g.) store model
    }

    handleSubmit(): void {
        this.isFormLoading = true;
        this.updateFormSubmitSuccess('');
        this.updateFormSubmitError('');

        setTimeout(() => {
            this.isFormLoading = false;
            this.updateFormSubmitSuccess(this.$t('common.success'));
            console.log(this.formValues);
        }, 2000);
    }
}

export default toNative(ExampleForm);

// export { ExampleForm };
