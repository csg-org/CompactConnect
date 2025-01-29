//
//  PrivilegePurchaseInformationConfirmation.ts
//  CompactConnect
//
//  Created by InspiringApps on 1/28/2025.
//

import { Component, mixins, Watch } from 'vue-facing-decorator';
import { reactive } from 'vue';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import InputCheckbox from '@components/Forms/InputCheckbox/InputCheckbox.vue';
import LoadingSpinner from '@components/LoadingSpinner/LoadingSpinner.vue';
import { Compact } from '@models/Compact/Compact.model';
import { Licensee } from '@models/Licensee/Licensee.model';
import { LicenseeUser } from '@/models/LicenseeUser/LicenseeUser.model';
import { FormInput } from '@/models/FormInput/FormInput.model';
import Joi from 'joi';

@Component({
    name: 'PrivilegePurchaseInformationConfirmation',
    components: {
        InputSubmit,
        InputButton,
        InputCheckbox,
        LoadingSpinner
    }
})
export default class PrivilegePurchaseInformationConfirmation extends mixins(MixinForm) {
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
    // attestationRecords: Array<PrivilegeAttestation> = []; // eslint-disable-line lines-between-class-members
    attestationRecords: Array<any> = []; // eslint-disable-line lines-between-class-members
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
        console.log('this.user', this.userStore.model);
        return this.userStore.model;
    }

    get licensee(): Licensee | null {
        console.log('this.user?.licensee', this.user?.licensee);

        return this.user?.licensee || null;
    }

    get userFullName(): string {
        return this.user?.getFullName() || '';
    }

    get phoneNumber(): string {
        return this.licensee?.phoneNumberDisplay() || '';
    }

    get licenseNumber(): string {
        // TODO: temp come back and fix
        return 'DA-743963';
    }

    get areAllAttestationsChecked(): boolean {
        return true;
    }

    get backText(): string {
        return this.$t('common.back');
    }

    get cancelText(): string {
        return this.$t('common.cancel');
    }

    //
    // Methods
    //

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
        console.log('fetch');
        // const compact: string = this.currentCompactType || '';
        // const attestationIds = this.attestationIds[compact] || [];
        // const attestationRecords = await Promise.all(attestationIds.map((attestationId) =>
        //     dataApi.getAttestation(compact, attestationId)));

        // this.attestationRecords = attestationRecords;
    }

    getAttestation(attestationId: string | null | undefined): any | null {
        return { text: attestationId, attestationId, version: '1' };
    }

    // getAttestation(attestationId: string | null | undefined): PrivilegeAttestation | null {
    //     return this.attestationRecords.find((attestationRecord) => attestationRecord.id === attestationId) || null;
    // }

    handleSubmit() {
        this.validateAll({ asTouched: true });

        console.log('here');

        if (this.isFormValid) {
            this.startFormLoading();

            const attestationData = this.prepareAttestations();

            this.$store.dispatch('user/setAttestations', attestationData);

            if (!this.isFormError) {
                this.isFormSuccessful = true;
                this.$store.dispatch('user/setAttestationsAccepted', true);
                this.endFormLoading();
                this.$router.push({
                    name: 'SelectPrivileges',
                    params: { compact: this.currentCompactType }
                });
            }

            this.endFormLoading();
        }
    }

    prepareAttestations(): object {
        return this.attestationRecords.map((attestation) => ({
            attestationId: attestation.id,
            version: attestation.version,
        }));
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

    //
    // Watchers
    //
    @Watch('currentCompact') currentCompactSet() {
        if (this.currentCompact && !this.areFormInputsSet) {
            this.initFormInputs();
        }
    }
}
