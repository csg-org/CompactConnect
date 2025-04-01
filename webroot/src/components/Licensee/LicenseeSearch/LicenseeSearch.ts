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
import SearchIcon from '@components/Icons/LicenseSearchAlt/LicenseSearchAlt.vue';
import { CompactType, CompactSerializer } from '@models/Compact/Compact.model';
import { FormInput } from '@models/FormInput/FormInput.model';
import Joi from 'joi';

export interface LicenseSearch {
    compact?: string;
    firstName?: string;
    lastName?: string;
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
    @Prop({ default: false }) isPublicSearch!: boolean;

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

    get compactOptions(): Array<any> {
        const options = this.$tm('compacts').map((compact) => ({
            value: compact.key,
            name: compact.name,
        }));

        options.unshift({
            value: '',
            name: computed(() => this.$t('common.selectOption')),
        });

        return options;
    }

    get enableCompactSelect(): boolean {
        return this.isPublicSearch;
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
            state: new FormInput({
                id: 'state',
                name: 'state',
                label: computed(() => this.$t('common.stateJurisdiction')),
                valueOptions: this.stateOptions,
                value: this.searchParams.state || '',
                isDisabled: computed(() => this.enableCompactSelect && !this.compactType),
            }),
            submit: new FormInput({
                isSubmitInput: true,
                id: 'submit',
            }),
        });

        if (this.enableCompactSelect) {
            this.formData.compact = new FormInput({
                id: 'search-compact',
                name: 'search-compact',
                label: computed(() => this.$t('licensing.licenseTypeSearch')),
                validation: Joi.string().required().messages(this.joiMessages.string),
                valueOptions: this.compactOptions,
                value: this.searchParams.compact || this.compactType || '',
            });
        }

        this.watchFormInputs(); // Important if you want automated form validation
    }

    async updateCurrentCompact(): Promise<void> {
        const { compact: selectedCompactType, state } = this.formData;

        if (this.enableCompactSelect) {
            await this.$store.dispatch('user/setCurrentCompact', CompactSerializer.fromServer({ type: selectedCompactType.value }));
            state.value = '';
            state.valueOptions = this.stateOptions;
        }
    }

    async handleSubmit(): Promise<void> {
        this.validateAll({ asTouched: true });
        this.customValidateLastName();

        if (this.isFormValid) {
            this.startFormLoading();

            const allowedSearchProps = [
                'compact',
                'firstName',
                'lastName',
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
