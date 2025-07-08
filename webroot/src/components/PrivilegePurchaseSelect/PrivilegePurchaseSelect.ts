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
import { reactive, nextTick } from 'vue';
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
    get purchaseDataList(): Array<PrivilegePurchaseOption> {
        const privilegePurchaseOptions = [...this.currentCompact?.privilegePurchaseOptions || []];

        privilegePurchaseOptions.sort((a: PrivilegePurchaseOption, b: PrivilegePurchaseOption) => {
            let toReturn = 0;
            const nameA = a.jurisdiction?.name().toLowerCase();
            const nameB = b.jurisdiction?.name().toLowerCase();

            if (nameA && nameB) {
                if (nameA < nameB) {
                    toReturn = -1;
                }
                if (nameA > nameB) {
                    toReturn = 1;
                }
            }

            return toReturn;
        });

        return privilegePurchaseOptions;
    }

    get currentCompact(): Compact | null {
        return this.userStore?.currentCompact || null;
    }

    get currentCompactType(): string | null {
        return this.currentCompact?.type || null;
    }

    get userStore(): any {
        return this.$store.state.user;
    }

    get user(): LicenseeUser | null {
        return this.userStore.model;
    }

    get licensee(): Licensee | null {
        return this.user?.licensee || null;
    }

    get userFullName(): string {
        let name = '';

        if (this.user) {
            name = this.user.getFullName();
        }

        return name;
    }

    get isPhone(): boolean {
        return this.$matches.phone.only;
    }

    get privilegeList(): Array<License> {
        return this.licensee?.privileges || [];
    }

    get licenseList(): Array<License> {
        return this.licensee?.licenses || [];
    }

    get disabledPrivilegeStateChoices(): Array<string> {
        const disabledStateList: Array<string> = [];
        const { privilegeList } = this;
        const purchaseLicense = this.selectedPurchaseLicense;

        if (purchaseLicense) {
            privilegeList.filter((privilege) =>
                (privilege.licenseType === purchaseLicense.licenseType)).forEach((privilege) => {
                if (
                    privilege?.issueState?.abbrev
                    && moment(privilege?.expireDate).isSameOrAfter(purchaseLicense.expireDate)
                    && privilege.status === LicenseStatus.ACTIVE
                ) {
                    disabledStateList.push(privilege?.issueState?.abbrev);
                }
            });

            disabledStateList.push(purchaseLicense?.issueState?.abbrev || '');
        }

        return disabledStateList;
    }

    get backText(): string {
        return this.$t('common.back');
    }

    get cancelText(): string {
        return this.$t('common.cancel');
    }

    get stateCheckList(): Array<FormInput> {
        return this.formData.stateCheckList;
    }

    get isAtLeastOnePrivilegeChosen(): boolean {
        return this.formData.stateCheckList?.filter((formInput) =>
            (formInput.value === true)).length > 0;
    }

    get submitLabel(): string {
        let label = this.$t('common.next');

        if (this.isFormLoading) {
            label = this.$t('common.loading');
        }

        return label;
    }

    get isDesktop(): boolean {
        return this.$matches.desktop.min;
    }

    get isMobile(): boolean {
        return !this.isDesktop;
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

    get jurisprudenceExplanationText(): string {
        return this.$t('licensing.jurisprudenceExplanationText');
    }

    get activeLicense(): License | null {
        return this.licenseList?.find((license) => license.status === LicenseStatus.ACTIVE) || null;
    }

    get selectPrivilegesTitleText(): string {
        return this.$t('licensing.selectPrivileges');
    }

    get areAllJurisprudenceConfirmed(): boolean {
        let allConfirmed = true;

        if (this.formData?.jurisprudenceConfirmations) {
            const jurisprudenceConfirmations = Object.keys(this.formData.jurisprudenceConfirmations);

            jurisprudenceConfirmations.forEach((state) => {
                if (!this.formData.jurisprudenceConfirmations[state].value) {
                    allConfirmed = false;
                }
            });
        }

        return allConfirmed;
    }

    get areAllScopesConfirmed(): boolean {
        let allConfirmed = true;

        if (this.formData?.scopeOfPracticeConfirmations) {
            const scopeOfPracticeConfirmations = Object.keys(this.formData.scopeOfPracticeConfirmations);

            scopeOfPracticeConfirmations.forEach((state) => {
                if (!this.formData.scopeOfPracticeConfirmations[state].value) {
                    allConfirmed = false;
                }
            });
        }

        return allConfirmed;
    }

    get areAllAttesationsConfirmed(): boolean {
        return this.areAllScopesConfirmed && this.areAllJurisprudenceConfirmed;
    }

    get scopeOfPracticeText(): string {
        return this.$t('licensing.scopeAttestLabel');
    }

    get jurisprudenceAttestation(): PrivilegeAttestation {
        return this.attestationRecords.find((record) => ((record as any)?.id === 'jurisprudence-confirmation')) || new PrivilegeAttestation();
    }

    get scopeAttestation(): PrivilegeAttestation {
        return this.attestationRecords.find((record) => ((record as any)?.id === 'scope-of-practice-attestation')) || new PrivilegeAttestation();
    }

    get isMockPopulateEnabled(): boolean {
        return Boolean(this.$envConfig.isDevelopment);
    }

    get selectedPurchaseLicense(): License | null {
        return this.$store.getters['user/getLicenseSelected']();
    }

    //
    // Methods
    //
    initFormInputs(): void {
        const initFormData: any = {
            stateCheckList: [],
            submit: new FormInput({
                isSubmitInput: true,
                id: 'submit',
            })
        };

        this.purchaseDataList?.forEach((purchaseOption) => {
            const { jurisdiction = new State() } = purchaseOption;

            if (jurisdiction) {
                const { abbrev } = jurisdiction;

                if (abbrev) {
                    initFormData.stateCheckList.push(new FormInput({
                        id: abbrev,
                        name: `${abbrev}-check`,
                        label: jurisdiction.name(),
                        value: false,
                        isDisabled: true
                    }));
                }
            }
        });

        this.formData = reactive(initFormData);
    }

    // Add attestation FormInputs as top-level properties
    addStateAttestationInputs(stateAbbrev: string) {
        // Find the state object in purchaseDataList
        const stateObj = this.purchaseDataList.find(
            (option) => option.jurisdiction?.abbrev === stateAbbrev
        );

        // Only add jurisprudence attestation if required
        if (stateObj?.isJurisprudenceRequired) {
            this.formData[`jurisprudence-${stateAbbrev}`] = new FormInput({
                id: `jurisprudence-${stateAbbrev}`,
                name: `jurisprudence-${stateAbbrev}`,
                label: this.jurisprudenceExplanationText,
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
            label: this.scopeOfPracticeText,
            value: false,
            validation: Joi.boolean().invalid(false).required().messages(this.joiMessages.boolean),
        });
    }

    // Remove attestation FormInputs from top-level properties
    removeStateAttestationInputs(stateAbbrev: string) {
        delete this.formData[`jurisprudence-${stateAbbrev}`];
        delete this.formData[`scope-${stateAbbrev}`];
    }

    // Update state selection logic
    toggleStateSelected(stateFormInput) {
        const newStateFormInputValue = !stateFormInput.value;
        const stateAbbrev = stateFormInput.id;

        stateFormInput.value = newStateFormInputValue;

        if (newStateFormInputValue) {
            this.addStateAttestationInputs(stateAbbrev);
        } else {
            this.removeStateAttestationInputs(stateAbbrev);
        }
    }

    handleSubmit() {
        // Always validate all before checking isFormValid
        this.validateAll({ asTouched: true });

        if (this.isAtLeastOnePrivilegeChosen && this.isFormValid) {
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

    handleCancelClicked() {
        this.$store.dispatch('user/resetToPurchaseFlowStep', 0);

        if (this.currentCompactType) {
            this.$router.push({
                name: 'LicenseeDashboard',
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

    handleBackClicked() {
        if (this.currentCompactType) {
            this.$router.push({
                name: 'PrivilegePurchaseInformationConfirmation',
                params: { compact: this.currentCompactType }
            });
        }
    }

    deselectState(stateAbbrev) {
        this.formData.stateCheckList.find((checkBox) => (checkBox.id === stateAbbrev)).value = false;
        delete this.formData.jurisprudenceConfirmations[stateAbbrev];
        delete this.formData.scopeOfPracticeConfirmations[stateAbbrev];
    }

    isStateSelectDisabled(state): boolean {
        return this.disabledPrivilegeStateChoices.includes(state.id);
    }

    findStatePurchaseInformation(stateSelectInput): PrivilegePurchaseOption | null {
        const stateAbbrev = stateSelectInput.id;

        const statePurchaseData = this.selectedStatePurchaseDataList.find((purchaseData) =>
            (purchaseData.jurisdiction?.abbrev === stateAbbrev)) || null;

        return statePurchaseData;
    }

    async fetchAttestations(): Promise<void> {
        if (this.currentCompactType) {
            this.attestationRecords = await Promise.all((this.attestationIds[this.currentCompactType] as Array<any>)
                .map(async (attesationId) => (dataApi.getAttestation(this.currentCompactType, attesationId))));
        }
    }

    async mockPopulate(): Promise<void> {
        this.stateCheckList.forEach((state) => {
            if (!this.isStateSelectDisabled(state)) {
                this.toggleStateSelected(state);

                this.$nextTick(() => {
                    if (this.formData.jurisprudenceConfirmations[state.id]) {
                        this.formData.jurisprudenceConfirmations[state.id].value = true;
                    }
                    if (this.formData.scopeOfPracticeConfirmations[state.id]) {
                        this.formData.scopeOfPracticeConfirmations[state.id].value = true;
                    }
                });
            }
        });

        await nextTick();
        const formButtons = document.getElementById('button-row');

        formButtons?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    @Watch('disabledPrivilegeStateChoices.length') reInitForm() {
        this.initFormInputs();
    }
}
