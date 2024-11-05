//
//  PrivilegePurchaseAttestation.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/4/2024.
//

import { Component, mixins } from 'vue-facing-decorator';
import { reactive } from 'vue';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import { Compact } from '@models/Compact/Compact.model';
import { FormInput } from '@/models/FormInput/FormInput.model';

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

    //
    // Lifecycle
    //
    created() {
        this.$store.dispatch('user/setAttestationsAccepted', true);
        this.initFormInputs();
    }

    //
    // Computed
    //
    get backText(): string {
        return this.$t('common.back');
    }

    get cancelText(): string {
        return this.$t('common.cancel');
    }

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
    initFormInputs(): void {
        const initFormData: any = {
            submit: new FormInput({
                isSubmitInput: true,
                id: 'submit',
            }),
        };

        this.formData = reactive(initFormData);
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
}
