//
//  PrivilegePurchaseSelect.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/15/2024.
//

import {
    Component,
    Watch,
    mixins,
    Prop
} from 'vue-facing-decorator';
import { reactive, computed, nextTick } from 'vue';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import SelectedStatePurchaseInformation from '@components/SelectedStatePurchaseInformation/SelectedStatePurchaseInformation.vue';
import LoadingSpinner from '@components/LoadingSpinner/LoadingSpinner.vue';
import InputCheckbox from '@components/Forms/InputCheckbox/InputCheckbox.vue';
import SelectedLicenseInfo from '@components/SelectedLicenseInfo/SelectedLicenseInfo.vue';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import MockPopulate from '@components/Forms/MockPopulate/MockPopulate.vue';
import { Compact } from '@models/Compact/Compact.model';
import { FormInput } from '@/models/FormInput/FormInput.model';
import { License, LicenseStatus } from '@/models/License/License.model';
import { Licensee } from '@models/Licensee/Licensee.model';
import { LicenseeUser } from '@/models/LicenseeUser/LicenseeUser.model';
import { PrivilegePurchaseOption } from '@models/PrivilegePurchaseOption/PrivilegePurchaseOption.model';
import { AcceptedAttestationToSend } from '@models/AcceptedAttestationToSend/AcceptedAttestationToSend.model';
import { PrivilegeAttestation } from '@models/PrivilegeAttestation/PrivilegeAttestation.model';
import { PurchaseFlowStep } from '@/models/PurchaseFlowStep/PurchaseFlowStep.model';
import { State } from '@/models/State/State.model';
import { dataApi } from '@network/data.api';
import moment from 'moment';
import Joi from 'joi';

@Component({
    name: 'PrivilegePurchaseSelect',
    components: {
        InputCheckbox,
        InputSubmit,
        InputButton,
        SelectedStatePurchaseInformation,
        LoadingSpinner,
        SelectedLicenseInfo,
        MockPopulate
    }
})
export default class PrivilegePurchaseSelect extends mixins(MixinForm) {
    @Prop({ default: 0 }) flowStep!: number;

    //
    // Data
    //
    isLoading = false;
    jurisprudencePendingConfirmation = '';
    attestationIds = {
        aslp: [
            'jurisprudence-confirmation',
            'scope-of-practice-attestation'
        ],
        coun: [
            'jurisprudence-confirmation',
            'scope-of-practice-attestation'
        ],
        octp: [
            'jurisprudence-confirmation',
            'scope-of-practice-attestation'
        ],
    }
    attestationRecords: Array<PrivilegeAttestation> = []; // eslint-disable-line lines-between-class-members
    areFormInputsSet = false;
    formErrorMessage = '';

    //
    // Lifecycle
    //
    async created() {
        this.isLoading = true;
        await this.$store.dispatch('user/getPrivilegePurchaseInformationRequest');
        await this.fetchAttestations();

        if (this.disabledPrivilegeStateChoices?.length) {
            this.initFormInputs();
        }
        this.isLoading = false;
    }

    //
    // Computed
    //
    get userStore(): any {
        return this.$store.state.user;
    }

    get currentCompact(): Compact | null {
        return this.userStore?.currentCompact || null;
    }

    get currentCompactType(): string | null {
        return this.currentCompact?.type || null;
    }

    get user(): LicenseeUser | null {
        return this.userStore.model;
    }

    get userFullName(): string {
        let name = '';

        if (this.user) {
            name = this.user.getFullName();
        }

        return name;
    }

    get licensee(): Licensee | null {
        return this.user?.licensee || null;
    }

    get licenseList(): Array<License> {
        return this.licensee?.licenses || [];
    }

    get privilegeList(): Array<License> {
        return this.licensee?.privileges || [];
    }

    get selectedPurchaseLicense(): License | null {
        return this.$store.getters['user/getLicenseSelected']();
    }

    get activeLicense(): License | null {
        return this.licenseList?.find((license) => license.status === LicenseStatus.ACTIVE) || null;
    }

    get purchaseDataList(): Array<PrivilegePurchaseOption> {
        const privilegePurchaseOptions = [...this.currentCompact?.privilegePurchaseOptions || []];

        privilegePurchaseOptions.sort((a: PrivilegePurchaseOption, b: PrivilegePurchaseOption) => {
            const nameA = a.jurisdiction?.name().toLowerCase();
            const nameB = b.jurisdiction?.name().toLowerCase();
            let sort = 0;

            if (nameA && nameB) {
                if (nameA < nameB) {
                    sort = -1;
                }
                if (nameA > nameB) {
                    sort = 1;
                }
            }

            return sort;
        });

        return privilegePurchaseOptions;
    }

    get disabledPrivilegeStateChoices(): Array<string> {
        const disabledStateList: Array<string> = [];
        const { privilegeList } = this;
        const purchaseLicense = this.selectedPurchaseLicense;

        if (purchaseLicense) {
            // Disable privilege selection for valid privileges the user already holds
            privilegeList
                .filter((privilege) => (privilege.licenseType === purchaseLicense.licenseType))
                .forEach((privilege) => {
                    if (
                        privilege?.issueState?.abbrev
                        && moment(privilege?.expireDate).isSameOrAfter(purchaseLicense.expireDate)
                        && privilege.status === LicenseStatus.ACTIVE
                    ) {
                        disabledStateList.push(privilege?.issueState?.abbrev);
                    }
                });

            // Disable privilege selection for the user's license home state
            disabledStateList.push(purchaseLicense?.issueState?.abbrev || '');
        }

        return disabledStateList;
    }

    get stateCheckList(): Array<FormInput> {
        return this.formData.stateCheckList;
    }

    get statesSelected(): Array <string> {
        return this.formData.stateCheckList?.filter((formInput) =>
            (formInput.value === true)).map((input) => input.id);
    }

    get selectedStatePurchaseDataList(): Array<PrivilegePurchaseOption> {
        return this.purchaseDataList.filter((option) => {
            let includes = false;

            const stateAbbrev = option?.jurisdiction?.abbrev;

            if (stateAbbrev) {
                includes = this.statesSelected?.includes(stateAbbrev);
            }

            return includes;
        });
    }

    get selectedStatesWithJurisprudenceRequired(): Array<string> {
        const selectedStatesWithJurisprudenceRequired: Array<string> = [];
        const privPurchaseStatesRequiringJurisprudence = this.selectedStatePurchaseDataList
            .filter((state) => state.isJurisprudenceRequired);

        privPurchaseStatesRequiringJurisprudence.forEach((state) => {
            if (state?.jurisdiction?.abbrev) {
                selectedStatesWithJurisprudenceRequired.push(state.jurisdiction.abbrev);
            }
        });

        return selectedStatesWithJurisprudenceRequired;
    }

    get numPrivilegesChosen(): number {
        return this.formData.stateCheckList?.filter((formInput) => (formInput.value === true)).length;
    }

    get isAtLeastOnePrivilegeChosen(): boolean {
        return this.numPrivilegesChosen > 0;
    }

    get jurisprudenceAttestation(): PrivilegeAttestation {
        return this.attestationRecords.find((record) => ((record as any)?.id === 'jurisprudence-confirmation')) || new PrivilegeAttestation();
    }

    get scopeAttestation(): PrivilegeAttestation {
        return this.attestationRecords.find((record) => ((record as any)?.id === 'scope-of-practice-attestation')) || new PrivilegeAttestation();
    }

    get submitLabel(): string {
        let label = this.$t('common.next');

        if (this.isFormLoading) {
            label = this.$t('common.loading');
        }

        return label;
    }

    get isPhone(): boolean {
        return this.$matches.phone.only;
    }

    get isMockPopulateEnabled(): boolean {
        return Boolean(this.$envConfig.isDevelopment);
    }

    //
    // Methods
    //
    async fetchAttestations(): Promise<void> {
        if (this.currentCompactType) {
            this.attestationRecords = await Promise.all((this.attestationIds[this.currentCompactType] as Array<any>)
                .map(async (attesationId) => (dataApi.getAttestation(this.currentCompactType, attesationId))));
        }
    }

    initFormInputs(): void {
        this.formData = reactive({
            stateCheckList: [],
            submit: new FormInput({
                isSubmitInput: true,
                id: 'submit',
            })
        });

        this.purchaseDataList?.forEach((purchaseOption) => {
            const { jurisdiction = new State() } = purchaseOption;

            if (jurisdiction) {
                const { abbrev } = jurisdiction;

                if (abbrev) {
                    this.formData.stateCheckList.push(new FormInput({
                        id: abbrev,
                        name: `${abbrev}-check`,
                        label: jurisdiction.name(),
                        value: false,
                        isDisabled: true
                    }));
                }
            }
        });

        this.watchFormInputs();
    }

    addStateAttestationInputs(stateAbbrev: string): void {
        const stateObj = this.purchaseDataList.find(
            (option) => option.jurisdiction?.abbrev === stateAbbrev
        );

        // Only add jurisprudence attestation if required
        if (stateObj?.isJurisprudenceRequired) {
            this.formData[`jurisprudence-${stateAbbrev}`] = new FormInput({
                id: `jurisprudence-${stateAbbrev}`,
                name: `jurisprudence-${stateAbbrev}`,
                label: computed(() => this.$t('licensing.jurisprudenceExplanationText')),
                value: false,
                validation: Joi.boolean().invalid(false).required().messages(this.joiMessages.boolean),
            });
        } else {
            delete this.formData[`jurisprudence-${stateAbbrev}`];
        }

        // Always add scope attestation
        this.formData[`scope-${stateAbbrev}`] = new FormInput({
            id: `scope-${stateAbbrev}`,
            name: `scope-${stateAbbrev}`,
            label: computed(() => this.$t('licensing.scopeAttestLabel')),
            value: false,
            validation: Joi.boolean().invalid(false).required().messages(this.joiMessages.boolean),
        });
    }

    removeStateAttestationInputs(stateAbbrev: string): void {
        delete this.formData[`jurisprudence-${stateAbbrev}`];
        delete this.formData[`scope-${stateAbbrev}`];
    }

    toggleStateSelected(stateFormInput): void {
        const newStateFormInputValue = !stateFormInput.value;
        const stateAbbrev = stateFormInput.id;

        stateFormInput.value = newStateFormInputValue;

        if (newStateFormInputValue) {
            this.addStateAttestationInputs(stateAbbrev);
        } else {
            this.removeStateAttestationInputs(stateAbbrev);
        }

        if (this.numPrivilegesChosen <= 20) {
            this.formErrorMessage = '';
        }
    }

    deselectState(stateAbbrev: string): void {
        this.formData.stateCheckList.find((checkBox) => (checkBox.id === stateAbbrev)).value = false;
        this.removeStateAttestationInputs(stateAbbrev);
        this.formErrorMessage = '';
    }

    isStateSelectDisabled(state: FormInput): boolean {
        return this.disabledPrivilegeStateChoices.includes(state.id);
    }

    findStatePurchaseInformation(stateSelectInput: FormInput): PrivilegePurchaseOption | null {
        const stateAbbrev = stateSelectInput.id;

        const statePurchaseData = this.selectedStatePurchaseDataList.find((purchaseData) =>
            (purchaseData.jurisdiction?.abbrev === stateAbbrev)) || null;

        return statePurchaseData;
    }

    async handleSubmit(): Promise<void> {
        this.validateAll({ asTouched: true });

        if (this.numPrivilegesChosen > 20) {
            this.formErrorMessage = this.$t('licensing.privilegePurchaseLimit');
            await nextTick();
            document.getElementById('form-error-message')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
        } else if (this.isAtLeastOnePrivilegeChosen && this.isFormValid) {
            const selectedStates = this.formData.stateCheckList.filter((input) => input.value).map((input) => input.id);
            const attestationData = this.prepareAttestations();

            this.$store.dispatch('user/saveFlowStep', new PurchaseFlowStep({
                stepNum: this.flowStep,
                attestationsAccepted: attestationData,
                selectedPrivilegesToPurchase: selectedStates
            }));

            this.$router.push({
                name: 'PrivilegePurchaseAttestation',
                params: { compact: this.currentCompactType }
            });
        }
    }

    prepareAttestations(): Array<any> {
        return this.attestationRecords.map((attestation) => (new AcceptedAttestationToSend({
            attestationId: attestation.id,
            version: attestation.version,
        })));
    }

    handleCancelClicked(): void {
        this.$store.dispatch('user/resetToPurchaseFlowStep', 0);

        if (this.currentCompactType) {
            this.$router.push({
                name: 'LicenseeDashboard',
                params: { compact: this.currentCompactType }
            });
        }
    }

    handleBackClicked(): void {
        if (this.currentCompactType) {
            this.$router.push({
                name: 'PrivilegePurchaseInformationConfirmation',
                params: { compact: this.currentCompactType }
            });
        }
    }

    async mockPopulate(shouldPopulateAll = false): Promise<void> {
        const checkStateAttestations = (state: FormInput) => {
            this.$nextTick(() => {
                const jurisprudenceCheckInput = this.formData[`jurisprudence-${state.id}`];
                const scopeCheckInput = this.formData[`scope-${state.id}`];

                if (jurisprudenceCheckInput) {
                    jurisprudenceCheckInput.value = true;
                }
                if (scopeCheckInput) {
                    scopeCheckInput.value = true;
                }
            });
        };
        let foundSelection = false;

        this.stateCheckList.forEach((state) => {
            if (!this.isStateSelectDisabled(state)) {
                if (shouldPopulateAll && !state.value) {
                    this.toggleStateSelected(state);
                    checkStateAttestations(state);
                } else if (!shouldPopulateAll) {
                    if (!foundSelection) {
                        if (!state.value) {
                            this.toggleStateSelected(state);
                        }
                        checkStateAttestations(state);
                        foundSelection = true;
                    } else if (foundSelection && state.value) {
                        this.toggleStateSelected(state);
                    }
                }
            }
        });

        await nextTick();
        const formButtons = document.getElementById('button-row');

        formButtons?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    //
    // Watchers
    //
    @Watch('disabledPrivilegeStateChoices.length') reInitForm() {
        this.initFormInputs();
    }
}
