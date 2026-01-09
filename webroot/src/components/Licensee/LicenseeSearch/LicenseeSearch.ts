//
//  LicenseeSearch.ts
//  CompactConnect
//
//  Created by InspiringApps on 12/1/2025.
//

import {
    Component,
    mixins,
    Prop,
    Watch,
    toNative
} from 'vue-facing-decorator';
import {
    reactive,
    computed,
    ComputedRef,
    nextTick
} from 'vue';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import InputRadioGroup from '@components/Forms/InputRadioGroup/InputRadioGroup.vue';
import InputText from '@components/Forms/InputText/InputText.vue';
import InputSelect from '@components/Forms/InputSelect/InputSelect.vue';
import InputDate from '@components/Forms/InputDate/InputDate.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import SearchIcon from '@components/Icons/LicenseSearchAlt/LicenseSearchAlt.vue';
import MockPopulate from '@components/Forms/MockPopulate/MockPopulate.vue';
import { CompactType, CompactSerializer } from '@models/Compact/Compact.model';
import { State } from '@models/State/State.model';
import { FormInput } from '@models/FormInput/FormInput.model';
import Joi from 'joi';
import moment from 'moment';

export enum SearchTypes {
    PROVIDER = 'provider',
    PRIVILEGE = 'privilege',
}

export interface LicenseSearch {
    searchType: SearchTypes;
    isDirectExport?: boolean;
    compact?: string;
    firstName?: string;
    lastName?: string;
    homeState?: string;
    privilegeState?: string;
    privilegePurchaseStartDate?: string;
    privilegePurchaseEndDate?: string;
    militaryStatus?: string;
    investigationStatus?: string;
    encumberStartDate?: string;
    encumberEndDate?: string;
    npi?: string;
}

@Component({
    name: 'LicenseeSearch',
    components: {
        InputRadioGroup,
        InputText,
        InputSelect,
        InputDate,
        InputSubmit,
        SearchIcon,
        MockPopulate,
    },
    emits: [ 'searchParams' ],
})
class LicenseeSearch extends mixins(MixinForm) {
    @Prop({ default: {}}) searchParams!: LicenseSearch;
    @Prop({ default: false }) isPublicSearch!: boolean;
    @Prop({ default: '' }) errorOverride?: string;

    //
    // Data
    //
    selectedSearchType: SearchTypes | null = null;

    //
    // Lifecycle
    //
    created() {
        this.initFormInputs();
    }

    //
    // Computed
    //
    get licenseStore(): any {
        return this.$store.state.license;
    }

    get userStore() {
        return this.$store.state.user;
    }

    get compactType(): CompactType | null {
        return this.userStore.currentCompact?.type;
    }

    get compactOptions(): Array<{ value: string, name: string | ComputedRef }> {
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

    get stateOptions(): Array<{ value: string | undefined, name: string | ComputedRef }> {
        const compactMemberStates: Array<{ value: string | undefined, name: string | ComputedRef }> = this.compactStates
            .map((state) => ({
                value: state.abbrev, name: state.name()
            }));

        compactMemberStates.unshift({
            value: '',
            name: (compactMemberStates.length) ? computed(() => this.$t('common.selectOption')) : '',
        });

        return compactMemberStates;
    }

    get searchTypeOptions(): Array<{ value: string | undefined, name: string | ComputedRef }> {
        return [
            {
                value: SearchTypes.PROVIDER,
                name: this.$t('licensing.providers'),
            },
            {
                value: SearchTypes.PRIVILEGE,
                name: this.$t('licensing.privileges'),
            },
        ];
    }

    get isSearchByProviders(): boolean {
        return this.selectedSearchType === SearchTypes.PROVIDER;
    }

    get isSearchByPrivileges(): boolean {
        return this.selectedSearchType === SearchTypes.PRIVILEGE;
    }

    get militaryStatusOptions(): Array<{ value: string, name: string | ComputedRef }> {
        const options = this.$tm('military.militaryStatusOptions').map((option) => ({
            value: option.key,
            name: option.name,
        }));

        options.unshift({
            value: '',
            name: computed(() => this.$t('common.selectOption')),
        });

        return options;
    }

    get investigationStatusOptions(): Array<{ value: string, name: string | ComputedRef }> {
        const options = this.$tm('licensing.investigationStatusOptions').map((option) => ({
            value: option.key,
            name: option.name,
        }));

        options.unshift({
            value: '',
            name: computed(() => this.$t('common.selectOption')),
        });

        return options;
    }

    get isSearchButtonEnabled(): boolean {
        return this.isSearchByProviders;
    }

    get isExportButtonEnabled(): boolean {
        return this.isSearchByPrivileges && !this.licenseStore.isExporting;
    }

    get isMockPopulateEnabled(): boolean {
        return Boolean(this.$envConfig.isDevelopment);
    }

    //
    // Methods
    //
    initFormInputs(): void {
        this.selectedSearchType = SearchTypes.PROVIDER;
        this.formData = reactive({
            searchType: new FormInput({
                id: 'search-type',
                name: 'search-type',
                label: computed(() => this.$t('licensing.searchTypeTitle')),
                validation: Joi.string().required().messages(this.joiMessages.string),
                valueOptions: this.searchTypeOptions,
                value: this.selectedSearchType || '',
            }),
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
            homeState: new FormInput({
                id: 'home-state',
                name: 'home-state',
                label: computed(() => this.$t('licensing.homeState')),
                valueOptions: this.stateOptions,
                value: this.searchParams.homeState || '',
                isDisabled: computed(() => this.enableCompactSelect && !this.compactType),
            }),
            privilegeState: new FormInput({
                id: 'privilege-state',
                name: 'privilege-state',
                label: computed(() => this.$t('licensing.privilegeState')),
                valueOptions: this.stateOptions,
                value: this.searchParams.privilegeState || '',
            }),
            privilegePurchaseStartDate: new FormInput({
                id: 'privilege-purchase-start-date',
                name: 'privilege-purchase-start-date',
                label: computed(() => this.$t('common.startDate')),
                value: this.searchParams.privilegePurchaseStartDate || '',
            }),
            privilegePurchaseEndDate: new FormInput({
                id: 'privilege-purchase-end-date',
                name: 'privilege-purchase-end-date',
                label: computed(() => this.$t('common.endDate')),
                value: this.searchParams.privilegePurchaseEndDate || '',
            }),
            militaryStatus: new FormInput({
                id: 'military-status',
                name: 'military-status',
                label: computed(() => this.$t('military.militaryStatusTitle')),
                valueOptions: this.militaryStatusOptions,
                value: this.searchParams.militaryStatus || '',
            }),
            investigationStatus: new FormInput({
                id: 'investigation-status',
                name: 'investigation-status',
                label: computed(() => this.$t('licensing.underInvestigationStatusSearch')),
                valueOptions: this.investigationStatusOptions,
                value: this.searchParams.investigationStatus || '',
            }),
            encumberStartDate: new FormInput({
                id: 'encumber-start-date',
                name: 'encumber-start-date',
                label: computed(() => this.$t('common.startDate')),
                value: this.searchParams.encumberStartDate || '',
            }),
            encumberEndDate: new FormInput({
                id: 'encumber-end-date',
                name: 'encumber-end-date',
                label: computed(() => this.$t('common.endDate')),
                value: this.searchParams.encumberEndDate || '',
            }),
            npi: new FormInput({
                id: 'npi',
                name: 'npi',
                label: computed(() => this.$t('licensing.npi')),
                placeholder: computed(() => this.$t('licensing.searchPlaceholderNpi')),
                validation: Joi.string().min(0).max(100).messages(this.joiMessages.string),
                value: this.searchParams.npi || '',
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
        }
    }

    updateSearchType(): void {
        const searchType = this.formData.searchType.value;

        this.selectedSearchType = searchType;
    }

    async handleSubmit(): Promise<void> {
        this.validateAll({ asTouched: true });

        if (this.isFormValid) {
            this.startFormLoading();

            const allowedSearchProps = [
                'compact',
                'firstName',
                'lastName',
                'homeState',
                'privilegeState',
                'privilegePurchaseStartDate',
                'privilegePurchaseEndDate',
                'militaryStatus',
                'investigationStatus',
                'encumberStartDate',
                'encumberEndDate',
                'npi',
            ];
            const searchProps: LicenseSearch = {
                searchType: this.selectedSearchType || SearchTypes.PROVIDER,
                isDirectExport: this.isSearchByPrivileges,
            };

            allowedSearchProps.forEach((searchProp) => { searchProps[searchProp] = this.formValues[searchProp]; });
            this.$emit('searchParams', searchProps);

            this.endFormLoading();
        }
    }

    resetForm(): void {
        this.formData.firstName.value = '';
        this.formData.lastName.value = '';
        this.formData.homeState.value = '';
        this.formData.privilegeState.value = '';
        this.formData.privilegePurchaseStartDate.value = '';
        this.formData.privilegePurchaseEndDate.value = '';
        this.formData.militaryStatus.value = '';
        this.formData.investigationStatus.value = '';
        this.formData.encumberStartDate.value = '';
        this.formData.encumberEndDate.value = '';
        this.formData.npi.value = '';
        this.isFormLoading = false;
        this.isFormSuccessful = false;
        this.isFormError = false;
        this.updateFormSubmitSuccess('');
        this.updateFormSubmitError('');
    }

    async mockPopulate(): Promise<void> {
        this.formData.firstName.value = 'Test';
        this.formData.lastName.value = 'User';
        this.formData.homeState.value = 'co';
        this.formData.privilegeState.value = 'co';
        this.formData.privilegePurchaseStartDate.value = moment().startOf('month').format('YYYY-MM-DD');
        this.formData.privilegePurchaseEndDate.value = moment().endOf('month').format('YYYY-MM-DD');
        // this.formData.militaryStatus.value = 'approved'; // @TODO: Adding this in next PR with military status updates
        this.formData.investigationStatus.value = 'underInvestigation';
        this.formData.encumberStartDate.value = moment().startOf('month').format('YYYY-MM-DD');
        this.formData.encumberEndDate.value = moment().endOf('month').format('YYYY-MM-DD');
        this.formData.npi.value = 'ABC123';

        this.validateAll({ asTouched: true });
        await nextTick();
        const submitButton = document.getElementById('submit');

        submitButton?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    //
    // Watch
    //
    @Watch('compactStates') updateStateInput() {
        this.formData.homeState.valueOptions = this.stateOptions;
        this.formData.privilegeState.valueOptions = this.stateOptions;
    }

    @Watch('errorOverride') updateError() {
        const { errorOverride } = this;

        if (errorOverride) {
            this.updateFormSubmitError(errorOverride);
        } else {
            this.validateAll();
        }
    }
}

export default toNative(LicenseeSearch);

// export default LicenseeSearch;
