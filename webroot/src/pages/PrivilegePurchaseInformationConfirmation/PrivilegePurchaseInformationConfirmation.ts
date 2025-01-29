//
//  PrivilegePurchaseInformationConfirmation.ts
//  CompactConnect
//
//  Created by InspiringApps on 1/28/2025.
//

import { Component, mixins } from 'vue-facing-decorator';
import { reactive } from 'vue';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import { Compact } from '@models/Compact/Compact.model';
import { Licensee } from '@models/Licensee/Licensee.model';
import { LicenseeUser } from '@/models/LicenseeUser/LicenseeUser.model';
import { FormInput } from '@/models/FormInput/FormInput.model';

@Component({
    name: 'PrivilegePurchaseInformationConfirmation',
    components: {
        InputSubmit,
        InputButton
    }
})
export default class PrivilegePurchaseInformationConfirmation extends mixins(MixinForm) {
    //
    // Data
    //

    //
    // Lifecycle
    //
    async created() {
        // if (this.alreadyObtainedPrivilegeStates?.length) {
        this.initFormInputs();
        // }
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
    initFormInputs(): void {
        const initFormData: any = {
            stateCheckList: [],
            jurisprudenceConfirmations: {},
            submit: new FormInput({
                isSubmitInput: true,
                id: 'submit',
            })
        };

        this.formData = reactive(initFormData);
    }

    handleSubmit() {
        if (this.areAllAttestationsChecked) {
            // TODO: Save attestations to store

            this.$router.push({
                name: 'SelectPrivileges',
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
}
