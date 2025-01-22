//
//  PrivilegePurchaseAttestation.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/4/2024.
//

import { Component, mixins, Watch } from 'vue-facing-decorator';
import { reactive } from 'vue';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import { Compact } from '@models/Compact/Compact.model';
import { PrivilegeAttestation } from '@models/PrivilegeAttestation/PrivilegeAttestation.model';
import { FormInput } from '@/models/FormInput/FormInput.model';
import { dataApi } from '@network/data.api';
// import Joi from 'joi';

@Component({
    name: 'PrivilegePurchaseAttestation',
    components: {
        InputButton,
        InputSubmit
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
        // this.$store.dispatch('user/setAttestationsAccepted', true);
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

    get submitLabel(): string {
        return this.$t('payment.continueToPurchase');
    }

    //
    // Methods
    //
    async initFormInputs(): Promise<void> {
        await this.fetchAttestations();
        this.formData = reactive({
            submit: new FormInput({
                isSubmitInput: true,
                id: 'submit',
            }),
        });

        this.areFormInputsSet = true;
    }

    async fetchAttestations(): Promise<void> {
        console.log('fetch');
        const x = await dataApi.getAttestation('aslp', 'not-under-investigation-attestation');

        console.log(x);
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
        if (this.currentCompactType) {
            this.$router.push({
                name: 'FinalizePrivilegePurchase',
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
