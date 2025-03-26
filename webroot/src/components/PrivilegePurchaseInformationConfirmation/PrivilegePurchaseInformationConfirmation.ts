//
//  PrivilegePurchaseInformationConfirmation.ts
//  CompactConnect
//
//  Created by InspiringApps on 1/28/2025.
//

import {
    Component,
    mixins,
    Watch,
    Prop
} from 'vue-facing-decorator';
import { reactive } from 'vue';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import SelectedLicenseInfo from '@components/SelectedLicenseInfo/SelectedLicenseInfo.vue';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import InputCheckbox from '@components/Forms/InputCheckbox/InputCheckbox.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import LoadingSpinner from '@components/LoadingSpinner/LoadingSpinner.vue';
import MockPopulate from '@components/Forms/MockPopulate/MockPopulate.vue';
import { Address } from '@models/Address/Address.model';
import { Compact } from '@models/Compact/Compact.model';
import { Licensee } from '@models/Licensee/Licensee.model';
import { LicenseeUser } from '@/models/LicenseeUser/LicenseeUser.model';
import { PrivilegeAttestation } from '@models/PrivilegeAttestation/PrivilegeAttestation.model';
import { AcceptedAttestationToSend } from '@models/AcceptedAttestationToSend/AcceptedAttestationToSend.model';
import { FormInput } from '@/models/FormInput/FormInput.model';
import { License } from '@/models/License/License.model';
import { PurchaseFlowState } from '@/models/PurchaseFlowState/PurchaseFlowState.model';
import { PurchaseFlowStep } from '@/models/PurchaseFlowStep/PurchaseFlowStep.model';
import { dataApi } from '@network/data.api';
import Joi from 'joi';

@Component({
    name: 'PrivilegePurchaseInformationConfirmation',
    components: {
        InputSubmit,
        InputButton,
        InputCheckbox,
        LoadingSpinner,
        SelectedLicenseInfo,
        MockPopulate
    }
})
export default class PrivilegePurchaseInformationConfirmation extends mixins(MixinForm) {
    @Prop({ default: 0 }) flowStep!: number;

    //
    // Data
    //
    attestationIds = {
        aslp: [
            'personal-information-address-attestation',
            'personal-information-home-state-attestation',
        ],
        coun: [
            'personal-information-address-attestation',
            'personal-information-home-state-attestation',
        ],
        octp: [
            'personal-information-address-attestation',
            'personal-information-home-state-attestation',
        ],
    }
    attestationRecords: Array<PrivilegeAttestation> = []; // eslint-disable-line lines-between-class-members
    areFormInputsSet = false;

    //
    // Lifecycle
    //
    async created() {
        if (this.currentCompact) {
            await this.initFormInputs();
        }
    }

    //
    // Computed
    //
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

    get purchaseFlowState(): PurchaseFlowState {
        return this.userStore.purchaseFlowState;
    }

    get licensee(): Licensee | null {
        return this.user?.licensee || null;
    }

    get userFullName(): string {
        return this.user?.getFullName() || '';
    }

    get phoneNumber(): string {
        return this.licensee?.phoneNumberDisplay() || '';
    }

    get licenseNumber(): string {
        return this.licenseSelected?.licenseNumber || '';
    }

    get backText(): string {
        return this.$t('common.back');
    }

    get cancelText(): string {
        return this.$t('common.cancel');
    }

    get licenseSelected(): License {
        return this.$store.getters['user/getLicenseSelected']();
    }

    get homeStateText(): string {
        return this.licensee?.homeJurisdiction?.name() || '';
    }

    get licenseExpirationDate(): string {
        return this.licenseSelected?.expireDateDisplay() || '';
    }

    get licenseSelectedMailingAddress(): Address {
        return this.licenseSelected?.mailingAddress || new Address();
    }

    get mailingAddessStateDisplay(): string {
        return this.licenseSelected?.mailingAddress?.state?.abbrev?.toUpperCase() || '';
    }

    get stateProvidedEmail(): string {
        return this.user?.stateProvidedEmail || '';
    }

    get accountEmail(): string {
        return this.user?.compactConnectEmail || '';
    }

    get isMockPopulateEnabled(): boolean {
        return Boolean(this.$envConfig.isDevelopment);
    }

    //
    // Methods
    //
    async initFormInputs(): Promise<void> {
        await this.fetchAttestations();

        this.formData = reactive({
            homeState: new FormInput({
                id: 'home-state',
                name: 'home-state',
                label: this.getAttestation('personal-information-home-state-attestation')?.text || '',
                validation: Joi.boolean().invalid(false).messages(this.joiMessages.boolean),
                value: false,
            }),
            address: new FormInput({
                id: 'address',
                name: 'address',
                label: this.getAttestation('personal-information-address-attestation')?.text || '',
                validation: Joi.boolean().invalid(false).messages(this.joiMessages.boolean),
                value: false,
            }),
            submit: new FormInput({
                isSubmitInput: true,
                id: 'submit',
            })
        });

        this.watchFormInputs(); // Important if you want automated form validation

        this.areFormInputsSet = true;
    }

    async fetchAttestations(): Promise<void> {
        const compact: string = this.currentCompactType || '';
        const attestationIds = this.attestationIds[compact] || [];
        const attestationRecords = await Promise.all(attestationIds.map((attestationId) =>
            dataApi.getAttestation(compact, attestationId)));

        this.attestationRecords = attestationRecords;
    }

    getAttestation(attestationId: string | null | undefined): PrivilegeAttestation | null {
        return this.attestationRecords.find((attestationRecord) => attestationRecord.id === attestationId) || null;
    }

    handleSubmit() {
        this.validateAll({ asTouched: true });

        if (this.isFormValid) {
            this.startFormLoading();

            const attestationData = this.prepareAttestations();

            this.$store.dispatch('user/saveFlowStep', new PurchaseFlowStep({
                stepNum: this.flowStep,
                attestationsAccepted: attestationData,
            }));

            if (!this.isFormError) {
                this.isFormSuccessful = true;
                this.endFormLoading();
                this.$router.push({
                    name: 'PrivilegePurchaseSelect',
                    params: { compact: this.currentCompactType }
                });
            }

            this.endFormLoading();
        }
    }

    prepareAttestations(): Array<any> {
        return this.attestationRecords.map((attestation) => (new AcceptedAttestationToSend({
            attestationId: attestation.id,
            version: attestation.version,
        })));
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

    handleBackClicked() {
        if (this.currentCompactType) {
            if (this.licensee && this.licensee.homeJurisdictionLicenses().length > 1) {
                this.$router.push({
                    name: 'PrivilegePurchaseSelectLicense',
                    params: { compact: this.currentCompactType }
                });
            } else {
                this.$router.push({
                    name: 'LicenseeDashboard',
                    params: { compact: this.currentCompactType }
                });
            }
        }
    }

    async mockPopulate(): Promise<void> {
        this.formData.address.value = true;
        this.formData.homeState.value = true;

        this.validateAll({ asTouched: true });
    }

    //
    // Watchers
    //
    @Watch('currentCompact') currentCompactSet() {
        if (this.currentCompact && !this.areFormInputsSet) {
            this.initFormInputs();
        }
    }
}
