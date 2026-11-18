//
//  ApplicationStart.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/17/2026.
//

import { Component, mixins, toNative } from 'vue-facing-decorator';
import {
    reactive,
    computed,
    nextTick,
    ComputedRef
} from 'vue';
import { stateList } from '@/app.config';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import InputCheckbox from '@components/Forms/InputCheckbox/InputCheckbox.vue';
import InputSelect from '@components/Forms/InputSelect/InputSelect.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import MockPopulate from '@components/Forms/MockPopulate/MockPopulate.vue';
import RibbonIcon from '@components/Icons/RibbonIcon/RibbonIcon.vue';
import GraduationCapIcon from '@components/Icons/GraduationCapIcon/GraduationCapIcon.vue';
import ShieldCheckIcon from '@components/Icons/ShieldCheckIcon/ShieldCheckIcon.vue';
import CreditCardIcon from '@components/Icons/CreditCardIcon/CreditCardIcon.vue';
import ClockIcon from '@components/Icons/ClockIcon/ClockIcon.vue';
import ExternalLinkIcon from '@components/Icons/ExternalLinkIcon/ExternalLinkIcon.vue';
import { ApplicationType } from '@models/Application/Application.model';
import { ApplicationConfig } from '@models/ApplicationConfig/ApplicationConfig.model';
import { State } from '@models/State/State.model';
import { FormInput } from '@models/FormInput/FormInput.model';
import Joi from 'joi';

interface SelectOption {
    value: string | number;
    name: string | ComputedRef<string>;
    isDisabled?: boolean;
}

interface ApplicationTypeConfig {
    key?: string;
    abbrev?: string;
    fullName?: string;
    description?: string;
}

@Component({
    name: 'ApplicationStart',
    components: {
        InputCheckbox,
        InputSelect,
        InputSubmit,
        MockPopulate,
        RibbonIcon,
        GraduationCapIcon,
        ShieldCheckIcon,
        CreditCardIcon,
        ClockIcon,
        ExternalLinkIcon,
    }
})
class ApplicationStart extends mixins(MixinForm) {
    //
    // Data
    //
    ePassportUrl = 'https://example.com';
    ipcUrl = 'https://example.com';

    //
    // Lifecycle
    //
    async created() {
        this.initFormInputs();
        await this.fetchConfigData();
        this.formData.licenseState.valueOptions = this.stateOptions;
    }

    //
    // Computed
    //
    get applicationType(): typeof ApplicationType {
        return ApplicationType;
    }

    get userStore(): any {
        return this.$store.state.user;
    }

    get compactType(): string {
        return this.userStore.currentCompact?.type || String(this.$route.params.compact || '');
    }

    get memberStates(): Array<State> {
        return this.userStore.currentCompact?.memberStates || [];
    }

    get applicationConfig(): ApplicationConfig | null {
        return this.userStore.applicationConfig;
    }

    get applicationTypeConfigs(): Array<ApplicationTypeConfig> {
        return this.$tm('application.applicationTypes') || [];
    }

    get preselectedTypes(): Array<ApplicationType> {
        const queryTypes = String(this.$route.query?.types || '').split(',');

        return Object.values(ApplicationType).filter((type) => queryTypes.includes(type));
    }

    get selectedTypes(): Array<ApplicationType> {
        return Object.values(ApplicationType).filter((type) => Boolean(this.formData[type]?.value));
    }

    get isApitSelected(): boolean {
        return this.selectedTypes.includes(ApplicationType.APIT);
    }

    get isTapSelected(): boolean {
        return this.selectedTypes.includes(ApplicationType.TAP);
    }

    get totalFee(): number {
        return this.applicationConfig?.totalFeeForTypes(this.selectedTypes) || 0;
    }

    get isFeeUnavailable(): boolean {
        return !this.applicationConfig && this.selectedTypes.length > 0;
    }

    get totalFeeDisplay(): string {
        return `$${this.totalFee.toFixed(2)}`;
    }

    get stateOptions(): Array<SelectOption> {
        const memberStateValues = this.memberStates.map((state) => (state.abbrev || '').toLowerCase());
        const options: Array<SelectOption> = [{ value: '', name: `- ${this.$t('common.select')} -`, isDisabled: true }];

        stateList.forEach((stateAbbrev) => {
            const value = stateAbbrev.toLowerCase();
            const stateName = new State({ abbrev: stateAbbrev }).name();
            const isParticipating = memberStateValues.includes(value);

            options.push({
                value,
                name: (isParticipating) ? stateName : `${stateName} ${this.$t('application.notParticipating')}`,
                isDisabled: !isParticipating,
            });
        });

        return options;
    }

    get submitLabel(): string {
        return (this.isFormLoading)
            ? this.$t('application.creatingApplication')
            : this.$t('application.startApplication');
    }

    get isMockPopulateEnabled(): boolean {
        return Boolean(this.$envConfig.isDevelopment);
    }

    //
    // Methods
    //
    async fetchConfigData(): Promise<void> {
        const requests: Array<Promise<any>> = [
            this.$store.dispatch('user/getApplicationConfigRequest', { compact: this.compactType }),
        ];

        if (!this.memberStates.length) {
            requests.push(this.$store.dispatch('user/getCompactStatesRequest', { compact: this.compactType }));
        }

        await Promise.all(requests);
    }

    getTypeConfig(type: ApplicationType): ApplicationTypeConfig {
        return this.applicationTypeConfigs.find((config) => config.key === type) || {};
    }

    getTypeLabel(type: ApplicationType): string {
        const { abbrev = '', fullName = '' } = this.getTypeConfig(type);

        return (fullName) ? `${abbrev} (${fullName})` : abbrev;
    }

    getTypeDescription(type: ApplicationType): string {
        return this.getTypeConfig(type).description || '';
    }

    initFormInputs(): void {
        this.formData = reactive({
            apit: new FormInput({
                id: 'type-apit',
                name: 'type-apit',
                label: computed(() => this.getTypeLabel(ApplicationType.APIT)),
                value: this.preselectedTypes.includes(ApplicationType.APIT),
            }),
            tap: new FormInput({
                id: 'type-tap',
                name: 'type-tap',
                label: computed(() => this.getTypeLabel(ApplicationType.TAP)),
                value: this.preselectedTypes.includes(ApplicationType.TAP),
                shouldHideErrorMessage: true,
                // Validates the APIT / TAP group as a whole, so the group error renders below the last option
                validation: Joi.any()
                    .custom((value, helpers) => ((this.selectedTypes.length) ? value : helpers.error('any.invalid')))
                    .messages({ 'any.invalid': this.$t('application.applyTypeRequired') }),
            }),
            licenseState: new FormInput({
                id: 'license-state',
                name: 'license-state',
                label: computed(() => this.$t('application.eligibilityStateLabel')),
                validation: Joi.string().required().messages(this.joiMessages.string),
                valueOptions: this.stateOptions,
            }),
            submit: new FormInput({
                isSubmitInput: true,
                id: 'submit-start-application',
            }),
        });
        this.watchFormInputs(); // Important if you want automated form validation
    }

    validateTypeSelection(): void {
        this.formData.tap.validate();
        this.checkValidForAll();
    }

    async mockPopulate(): Promise<void> {
        const firstEnabledState = this.stateOptions.find((option) => option.value && !option.isDisabled);

        this.formData.apit.value = true;
        this.formData.tap.value = true;
        this.formData.licenseState.value = firstEnabledState?.value || '';
        this.validateAll({ asTouched: true });

        await nextTick();
        document.getElementById(this.formData.submit.id)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    prepRequestData(): object {
        return {
            types: this.selectedTypes,
            licenseJurisdiction: this.formValues.licenseState,
        };
    }

    async handleSubmit(): Promise<void> {
        this.validateAll({ asTouched: true });

        if (this.isFormValid && !this.isFeeUnavailable) {
            this.startFormLoading();

            await this.$store.dispatch('user/createApplicationRequestLicensee', {
                data: this.prepRequestData(),
            }).then((application) => {
                if (application) {
                    this.$router.replace({
                        name: 'ApplicationChecklist',
                        params: { compact: this.compactType, applicationId: application.id },
                    });
                }
            }).catch((err) => {
                this.setError(err?.message || this.$t('serverErrors.networkError'));
            });

            this.endFormLoading();
        }
    }
}

export default toNative(ApplicationStart);

// export default ApplicationStart;
