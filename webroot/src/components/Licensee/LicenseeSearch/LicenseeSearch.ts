//
//  LicenseeSearch.ts
//  CompactConnect
//
//  Created by InspiringApps on 9/12/2024.
//

import {
    Component,
    mixins,
    Prop,
    toNative
} from 'vue-facing-decorator';
import { reactive, computed } from 'vue';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import InputText from '@components/Forms/InputText/InputText.vue';
import InputSelect from '@components/Forms/InputSelect/InputSelect.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import SearchIcon from '@components/Icons/Search/Search.vue';
import { CompactType } from '@models/Compact/Compact.model';
import { FormInput } from '@models/FormInput/FormInput.model';
import Joi from 'joi';

export interface LicenseSearch {
    firstName?: string;
    lastName?: string;
    ssn?: string;
    state?: string;
}

@Component({
    name: 'LicenseeSearch',
    components: {
        InputText,
        InputSelect,
        InputSubmit,
        SearchIcon,
    },
    emits: [ 'searchParams' ],
})
class LicenseeSearch extends mixins(MixinForm) {
    @Prop({ default: {}}) searchParams!: LicenseSearch;

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

    get compactType(): CompactType | null {
        return this.userStore.currentCompact?.type;
    }

    get stateOptions(): Array<any> {
        const { currentCompact } = this.userStore;
        const compactMemberStates = (currentCompact?.memberStates || []).map((state) => ({
            value: state.abbrev, name: state.name()
        }));
        const defaultSelectOption: any = { value: '' };

        if (!compactMemberStates.length) {
            defaultSelectOption.name = '';
        } else {
            defaultSelectOption.name = computed(() => this.$t('common.selectOption'));
        }

        compactMemberStates.unshift(defaultSelectOption);

        return compactMemberStates;
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
                placeholder: computed(() => this.$t('licensing.searchPlaceholderName')),
                validation: Joi.string().min(0).max(10).messages(this.joiMessages.string),
                value: this.searchParams.firstName || '',
                enforceMax: true,
            }),
            lastName: new FormInput({
                id: 'last-name',
                name: 'last-name',
                label: computed(() => this.$t('common.lastName')),
                placeholder: computed(() => this.$t('licensing.searchPlaceholderName')),
                validation: Joi.string().min(0).max(10).messages(this.joiMessages.string),
                value: this.searchParams.lastName || '',
                enforceMax: true,
            }),
            ssn: new FormInput({
                id: 'ssn',
                name: 'ssn',
                label: computed(() => this.$t('licensing.ssn')),
                placeholder: '000-00-0000',
                validation: Joi.string().pattern(/^([0-9]){3}-([0-9]{2}-([0-9]{4}$))/).allow('').messages({
                    ...this.joiMessages.string,
                    'string.pattern.base': this.$t('inputErrors.ssnFormat'),
                }),
                value: this.searchParams.ssn || '',
            }),
            state: new FormInput({
                id: 'state',
                name: 'state',
                label: computed(() => this.$t('common.stateJurisdiction')),
                valueOptions: this.stateOptions,
                value: this.searchParams.state || '',
            }),
            submit: new FormInput({
                isSubmitInput: true,
                id: 'submit',
            }),
        });
        this.watchFormInputs(); // Important if you want automated form validation
    }

    formatSsn(): void {
        const { ssn } = this.formData;
        const format = (ssnInputVal) => {
            // Remove all non-dash and non-numerals
            let formatted = ssnInputVal.replace(/[^\d-]/g, '');

            // Add the first dash if a number from the second group appears
            formatted = formatted.replace(/^(\d{3})-?(\d{1,2})/, '$1-$2');

            // Add the second dash if a number from the third group appears
            formatted = formatted.replace(/^(\d{3})-?(\d{2})-?(\d{1,4})/, '$1-$2-$3');

            // Remove misplaced dashes
            formatted = formatted.split('').filter((val, idx) => val !== '-' || idx === 3 || idx === 6).join('');

            // Enforce max length
            return formatted.substring(0, 11);
        };

        ssn.value = format(ssn.value);
    }

    async handleSubmit(): Promise<void> {
        this.validateAll({ asTouched: true });
        this.customValidateLastName();

        if (this.isFormValid) {
            this.startFormLoading();

            const allowedSearchProps = [
                'firstName',
                'lastName',
                'ssn',
                'state'
            ];
            const searchProps: LicenseSearch = {};

            allowedSearchProps.forEach((searchProp) => { searchProps[searchProp] = this.formValues[searchProp]; });
            this.$emit('searchParams', searchProps);

            this.endFormLoading();
        }
    }

    // Last name is currently optional overall, but required if first name is included; therefore needs this non-trivial validation logic
    customValidateLastName(asTouched = true): void {
        const { firstName, lastName } = this.formData;
        const shouldSkip = (asTouched) ? false : !lastName.isTouched;

        if (!shouldSkip && firstName.value && !lastName.value) {
            lastName.isValid = false;
            lastName.errorMessage = this.$t('inputErrors.lastNameRequired');
        } else if (!lastName.isValid) {
            lastName.isValid = true;
            lastName.errorMessage = '';
        }

        this.checkValidForAll();
    }
}

export default toNative(LicenseeSearch);

// export default LicenseeSearch;
