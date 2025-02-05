//
//  PrivilegePurchaseAttestation.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/4/2024.
//

import { Component, mixins, Watch } from 'vue-facing-decorator';
import { reactive, computed, ComputedRef } from 'vue';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import LoadingSpinner from '@components/LoadingSpinner/LoadingSpinner.vue';
import InputRadioGroup from '@components/Forms/InputRadioGroup/InputRadioGroup.vue';
import InputCheckbox from '@components/Forms/InputCheckbox/InputCheckbox.vue';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import MockPopulate from '@components/Forms/MockPopulate/MockPopulate.vue';
import { Compact } from '@models/Compact/Compact.model';
import { PrivilegeAttestation } from '@models/PrivilegeAttestation/PrivilegeAttestation.model';
import { FormInput } from '@/models/FormInput/FormInput.model';
import { dataApi } from '@network/data.api';
import Joi from 'joi';

interface AttestationOption {
    value: string;
    name: string | ComputedRef<string>;
}

@Component({
    name: 'PrivilegePurchaseAttestation',
    components: {
        LoadingSpinner,
        MockPopulate,
        InputRadioGroup,
        InputCheckbox,
        InputButton,
        InputSubmit,
    }
})
export default class PrivilegePurchaseAttestation extends mixins(MixinForm) {
    //
    // Data
    //
    attestationIds = {
        aslp: [
            'not-under-investigation-attestation',
            'under-investigation-attestation',
            'discipline-no-current-encumbrance-attestation',
            'discipline-no-prior-encumbrance-attestation',
            'provision-of-true-information-attestation',
            'military-affiliation-confirmation-attestation',
        ],
        coun: [
            'not-under-investigation-attestation',
            'under-investigation-attestation',
            'discipline-no-current-encumbrance-attestation',
            'discipline-no-prior-encumbrance-attestation',
            'provision-of-true-information-attestation',
            'military-affiliation-confirmation-attestation',
        ],
        octp: [
            'not-under-investigation-attestation',
            'under-investigation-attestation',
            'discipline-no-current-encumbrance-attestation',
            'discipline-no-prior-encumbrance-attestation',
            'provision-of-true-information-attestation',
            'military-affiliation-confirmation-attestation',
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
    get userStore(): any {
        return this.$store.state.user;
    }

    get currentCompact(): Compact | null {
        return this.userStore?.currentCompact || null;
    }

    get currentCompactType(): string | null {
        return this.currentCompact?.type || null;
    }

    get investigationsOptions(): Array<AttestationOption> {
        const attestationIds: Array<string | null | undefined> = [
            'not-under-investigation-attestation',
            'under-investigation-attestation',
        ];
        const attestations = this.attestationRecords.filter((record) => attestationIds.includes(record.id));
        const options: Array<AttestationOption> = attestations.map((attestation) => ({
            value: attestation.id || '',
            name: attestation.textDisplay() || '',
        }));

        return options;
    }

    get submitLabel(): string {
        return this.$t('payment.continueToPurchase');
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
            investigations: new FormInput({
                id: 'investigations',
                name: 'investigations',
                label: computed(() => this.$t('licensing.investigations')),
                validation: Joi.string().required().messages(this.joiMessages.string),
                valueOptions: this.investigationsOptions,
            }),
            disciplineCurrent: new FormInput({
                id: 'discipline-current',
                name: 'discipline-current',
                label: this.getAttestation('discipline-no-current-encumbrance-attestation')?.textDisplay() || '',
                validation: Joi.boolean().invalid(false).messages(this.joiMessages.boolean),
                value: false,
            }),
            disciplinePrior: new FormInput({
                id: 'discipline-prior',
                name: 'discipline-prior',
                label: this.getAttestation('discipline-no-prior-encumbrance-attestation')?.textDisplay() || '',
                validation: Joi.boolean().invalid(false).messages(this.joiMessages.boolean),
                value: false,
            }),
            trueInformation: new FormInput({
                id: 'true-information',
                name: 'true-information',
                label: this.getAttestation('provision-of-true-information-attestation')?.textDisplay() || '',
                validation: Joi.boolean().invalid(false).messages(this.joiMessages.boolean),
                value: false,
            }),
            militaryAffiliation: new FormInput({
                id: 'military-affiliation',
                name: 'military-affiliation',
                label: this.getAttestation('military-affiliation-confirmation-attestation')?.textDisplay() || '',
                validation: Joi.boolean().invalid(false).messages(this.joiMessages.boolean),
                value: false,
            }),
            submit: new FormInput({
                isSubmitInput: true,
                id: 'submit',
            }),
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
                name: 'SelectPrivileges',
                params: { compact: this.currentCompactType }
            });
        }
    }

    handleSubmit() {
        this.validateAll({ asTouched: true });

        if (this.isFormValid) {
            this.startFormLoading();

            const attestationData = this.prepareAttestations();

            this.$store.dispatch('user/setAttestations', attestationData);

            if (!this.isFormError) {
                this.isFormSuccessful = true;
                this.$store.dispatch('user/setAttestationsAccepted', true);
                this.endFormLoading();
                this.$router.push({
                    name: 'FinalizePrivilegePurchase',
                    params: { compact: this.currentCompactType }
                });
            }

            this.endFormLoading();
        }
    }

    prepareAttestations(): object {
        const radioAttestations = this.attestationRecords.filter((attestation) => {
            const checkboxAttestationIds = [
                this.formData.investigations.value,
            ];

            return checkboxAttestationIds.includes(attestation.id);
        }).map((attestation) => ({
            attestationId: attestation.id,
            version: attestation.version,
        }));
        const checkboxAttestations = this.attestationRecords.filter((attestation) => {
            const checkboxAttestationIds: Array<string | null | undefined> = [
                'discipline-no-current-encumbrance-attestation',
                'discipline-no-prior-encumbrance-attestation',
                'provision-of-true-information-attestation',
                'military-affiliation-confirmation-attestation',
            ];

            return checkboxAttestationIds.includes(attestation.id);
        }).map((attestation) => ({
            attestationId: attestation.id,
            version: attestation.version,
        }));
        const attestations = radioAttestations.concat(checkboxAttestations);

        return attestations;
    }

    async mockPopulate(): Promise<void> {
        this.formData.investigations.value = 'not-under-investigation-attestation';
        this.formData.disciplineCurrent.value = true;
        this.formData.disciplinePrior.value = true;
        this.formData.trueInformation.value = true;
        this.formData.militaryAffiliation.value = true;
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
