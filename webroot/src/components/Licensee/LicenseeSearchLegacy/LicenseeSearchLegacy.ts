//
//  LicenseeSearchLegacy.ts
//  CompactConnect
//
//  Created by InspiringApps on 9/12/2024.
//

import {
    Component,
    mixins,
    Prop,
    Watch,
    toNative
} from 'vue-facing-decorator';
import { reactive, computed, nextTick } from 'vue';
import { AppModes } from '@/app.config';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import InputText from '@components/Forms/InputText/InputText.vue';
import InputSelect from '@components/Forms/InputSelect/InputSelect.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import SearchIcon from '@components/Icons/LicenseSearchAlt/LicenseSearchAlt.vue';
import MockPopulate from '@components/Forms/MockPopulate/MockPopulate.vue';
import { CompactType, CompactSerializer } from '@models/Compact/Compact.model';
import { State } from '@models/State/State.model';
import { FormInput } from '@models/FormInput/FormInput.model';
import Joi from 'joi';

export interface LicenseSearchLegacy {
    compact?: string;
    firstName?: string;
    lastName?: string;
    state?: string;
    licenseNumber?: string;
}

@Component({
    name: 'LicenseeSearchLegacy',
    components: {
        InputText,
        InputSelect,
        InputSubmit,
        SearchIcon,
        MockPopulate,
    },
    emits: [ 'searchParams' ],
})
class LicenseeSearch extends mixins(MixinForm) {
    @Prop({ default: {}}) searchParams!: LicenseSearchLegacy;
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
    get globalStore() {
        return this.$store.state;
    }

    get userStore() {
        return this.$store.state.user;
    }

    get appMode(): AppModes {
        return this.globalStore.appMode;
    }

    get AppModes(): typeof AppModes {
        return AppModes;
    }

    get isAppModeJcc(): boolean {
        return this.$store.getters.isAppModeJcc;
    }

    get isAppModeCosmetology(): boolean {
        return this.$store.getters.isAppModeCosmetology;
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

    get compactStates(): Array<State> {
        return this.userStore.currentCompact?.memberStates || [];
    }

    get stateOptions(): Array<any> {
        const compactMemberStates = this.compactStates.map((state) => ({
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

    get isMockPopulateEnabled(): boolean {
        return Boolean(this.$envConfig.isDevelopment);
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
                validation: Joi.string().min(0).max(100).messages(this.joiMessages.string),
                value: this.searchParams.firstName || '',
                enforceMax: true,
            }),
            lastName: new FormInput({
                id: 'last-name',
                name: 'last-name',
                label: computed(() => this.$t('common.lastName')),
                placeholder: computed(() => this.$t('licensing.searchPlaceholderName')),
                validation: Joi.string().min(0).max(100).messages(this.joiMessages.string),
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
            licenseNumber: new FormInput({
                id: 'license-number',
                name: 'license-number',
                label: computed(() => this.$t('licensing.licenseNumber')),
                placeholder: '',
                validation: Joi.string().min(0).max(100).messages(this.joiMessages.string),
                value: this.searchParams.licenseNumber || '',
                enforceMax: true,
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
            this.validateAll({ asTouched: false });
        }
    }

    async handleSubmit(): Promise<void> {
        this.validateAll({ asTouched: true });
        this.customValidateLastName();

        if (this.isFormValid) {
            this.startFormLoading();

            const searchProps: LicenseSearchLegacy = {};
            const allowedSearchProps = [
                // Common search props
                'compact',
                'firstName',
                'lastName',
                'state'
            ];

            // Per compact search props
            if (this.appMode === AppModes.COSMETOLOGY) {
                allowedSearchProps.push('licenseNumber');
            }

            allowedSearchProps.forEach((searchProp) => { searchProps[searchProp] = this.formValues[searchProp]; });
            this.$emit('searchParams', searchProps);

            this.endFormLoading();
        }
    }

    // Last name is currently optional overall, but required if first name is included; therefore needs this non-trivial validation logic
    customValidateLastName(asTouched = true): void {
        const { isAppModeJcc } = this;
        const { firstName, lastName } = this.formData;
        const shouldSkip = (asTouched) ? false : !lastName.isTouched;

        if (isAppModeJcc) { // Currently only JCC requires this check
            if (!shouldSkip && firstName.value && !lastName.value) {
                lastName.isValid = false;
                lastName.errorMessage = this.$t('inputErrors.lastNameRequired');
            } else if (!lastName.isValid) {
                lastName.isValid = true;
                lastName.errorMessage = '';
            }
        }

        this.checkValidForAll();
    }

    async resetForm(): Promise<void> {
        if (this.enableCompactSelect) {
            this.formData.compact.value = '';
            await this.$store.dispatch('user/setCurrentCompact', null);
        }

        this.formData.firstName.value = '';
        this.formData.lastName.value = '';
        this.formData.state.value = '';
        this.formData.licenseNumber.value = '';
        this.isFormLoading = false;
        this.isFormSuccessful = false;
        this.isFormError = false;
        this.updateFormSubmitSuccess('');
        this.updateFormSubmitError('');
    }

    async mockPopulate(): Promise<void> {
        if (this.enableCompactSelect) {
            this.formData.compact.value = (this.isAppModeCosmetology)
                ? CompactType.COSMETOLOGY
                : CompactType.OT;

            await this.updateCurrentCompact();
        }

        this.formData.firstName.value = 'Test';
        this.formData.lastName.value = 'User';
        this.formData.state.value = 'co';

        if (this.isAppModeCosmetology) {
            this.formData.licenseNumber.value = 'ABC123';
        }

        this.validateAll({ asTouched: true });
        await nextTick();
        const submitButton = document.getElementById('submit');

        submitButton?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    //
    // Watch
    //
    @Watch('compactStates') updateStateInput() {
        this.formData.state.valueOptions = this.stateOptions;
    }
}

export default toNative(LicenseeSearch);

// export default LicenseeSearch;
