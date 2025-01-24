//
//  SelectPrivileges.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/15/2024.
//

import { Component, Watch, mixins } from 'vue-facing-decorator';
import { reactive } from 'vue';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import SelectedStatePurchaseInformation from '@components/SelectedStatePurchaseInformation/SelectedStatePurchaseInformation.vue';
import LoadingSpinner from '@components/LoadingSpinner/LoadingSpinner.vue';
import InputCheckbox from '@components/Forms/InputCheckbox/InputCheckbox.vue';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import { Compact } from '@models/Compact/Compact.model';
import { FormInput } from '@/models/FormInput/FormInput.model';
import { License, LicenseStatus } from '@/models/License/License.model';
import { Licensee } from '@models/Licensee/Licensee.model';
import { LicenseeUser } from '@/models/LicenseeUser/LicenseeUser.model';
import { PrivilegePurchaseOption } from '@models/PrivilegePurchaseOption/PrivilegePurchaseOption.model';
import { PrivilegeAttestation } from '@models/PrivilegeAttestation/PrivilegeAttestation.model';
import { State } from '@/models/State/State.model';
import { dataApi } from '@network/data.api';

@Component({
    name: 'SelectPrivileges',
    components: {
        InputCheckbox,
        InputSubmit,
        InputButton,
        SelectedStatePurchaseInformation,
        LoadingSpinner
    }
})
export default class SelectPrivileges extends mixins(MixinForm) {
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

        if (this.alreadyObtainedPrivilegeStates?.length) {
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

    get alreadyObtainedPrivilegeStates(): Array<string> {
        const licenseList = this.licenseList.concat(this.privilegeList);
        const stateList: Array<string> = [];

        licenseList.forEach((license) => {
            if (license?.issueState?.abbrev) {
                stateList.push(license?.issueState?.abbrev);
            }
        });

        return stateList;
    }

    get disabledPrivilegeStateChoices(): Array<string> {
        const licenseList = this.licenseList.concat(this.privilegeList);
        const stateList: Array<string> = [];

        licenseList.forEach((license) => {
            if (
                license?.issueState?.abbrev
                && license?.expireDate === this.activeLicense?.expireDate
                && license.statusState === LicenseStatus.ACTIVE
            ) {
                stateList.push(license?.issueState?.abbrev);
            }
        });

        return stateList;
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
        return this.licenseList?.find((license) => license.statusState === LicenseStatus.ACTIVE) || null;
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

    //
    // Methods
    //
    initFormInputs(): void {
        const initFormData: any = {
            stateCheckList: [],
            jurisprudenceConfirmations: {},
            scopeOfPracticeConfirmations: {},
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

    handleSubmit() {
        if (this.isAtLeastOnePrivilegeChosen && this.areAllAttesationsConfirmed) {
            const selectedStates = this.formData.stateCheckList.filter((input) => input.value).map((input) => input.id);

            this.$store.dispatch('user/savePrivilegePurchaseChoicesToStore', selectedStates);
            this.$store.dispatch('user/setAttestations', this.attestationRecords);

            this.$router.push({
                name: 'PrivilegePurchaseAttestation',
                params: { compact: this.currentCompactType }
            });
        }
    }

    handleCancelClicked() {
        if (this.currentCompactType) {
            this.$router.push({
                name: 'LicenseeDashboard',
                params: { compact: this.currentCompactType }
            });
        }
    }

    handleBackClicked() {
        if (this.currentCompactType) {
            this.$router.push({
                name: 'LicenseeDashboard',
                params: { compact: this.currentCompactType }
            });
        }
    }

    deselectState(stateAbbrev) {
        this.formData.stateCheckList.find((checkBox) => (checkBox.id === stateAbbrev)).value = false;
        delete this.formData.jurisprudenceConfirmations[stateAbbrev];
        delete this.formData.scopeOfPracticeConfirmations[stateAbbrev];
    }

    toggleStateSelected(stateFormInput) {
        const newStateFormInputValue = !stateFormInput.value;
        const stateAbbrev = stateFormInput.id;

        stateFormInput.value = newStateFormInputValue;

        if (newStateFormInputValue) {
            if (stateAbbrev) {
                this.formData.scopeOfPracticeConfirmations[stateAbbrev] = new FormInput({
                    id: `${stateAbbrev}-scope`,
                    name: `${stateAbbrev}-scope`,
                    label: this.scopeOfPracticeText,
                    value: false
                });

                if (this.selectedStatesWithJurisprudenceRequired.includes(stateAbbrev)) {
                    this.formData.jurisprudenceConfirmations[stateAbbrev] = new FormInput({
                        id: `${stateAbbrev}-jurisprudence`,
                        name: `${stateAbbrev}-jurisprudence`,
                        label: this.jurisprudenceExplanationText,
                        value: false
                    });
                }
            }
        } else {
            delete this.formData.jurisprudenceConfirmations[stateAbbrev];
            delete this.formData.scopeOfPracticeConfirmations[stateAbbrev];
        }
    }

    checkIfStateSelectIsDisabled(state): boolean {
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

    @Watch('alreadyObtainedPrivilegeStates.length') reInitForm() {
        this.initFormInputs();
    }
}
