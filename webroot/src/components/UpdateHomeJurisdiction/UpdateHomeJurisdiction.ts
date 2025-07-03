//
//  UpdateHomeJurisdiction.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/1/2025.
//

import {
    Component,
    mixins,
    toNative,
    Watch
} from 'vue-facing-decorator';
import { reactive, computed, ComputedRef } from 'vue';
import { stateList } from '@/app.config';
import InputSelect from '@components/Forms/InputSelect/InputSelect.vue';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import CheckCircleIcon from '@components/Icons/CheckCircle/CheckCircle.vue';
import Modal from '@components/Modal/Modal.vue';
import { FormInput } from '@models/FormInput/FormInput.model';
import Joi from 'joi';
import { State } from '@models/State/State.model';
import { LicenseeUser } from '@/models/LicenseeUser/LicenseeUser.model';
import { Licensee } from '@models/Licensee/Licensee.model';
import MixinForm from '@components/Forms/_mixins/form.mixin';

interface SelectOption {
    value: string | number;
    name: string | ComputedRef<string>;
    isDisabled?: boolean;
}

@Component({
    name: 'UpdateHomeJurisdiction',
    components: {
        InputSelect,
        InputButton,
        InputSubmit,
        CheckCircleIcon,
        Modal,
    }
})
class UpdateHomeJurisdiction extends mixins(MixinForm) {
    //
    // Data
    //
    isConfirmJurisdictionModalOpen = false;
    isSuccess = false;
    isError = false;
    isFormLoading = false;
    errorMessage = '';
    formData: any = {};

    //
    // Lifecycle
    //
    created() {
        this.initHomeJurisdictionForm();
    }

    //
    // Computed
    //
    get userStore() {
        return this.$store.state.user;
    }

    get user(): LicenseeUser | null {
        return this.userStore.model;
    }

    get licensee(): Licensee {
        return this.user?.licensee || new Licensee();
    }

    get homeJurisdiction(): State | null {
        return this.licensee?.homeJurisdiction || null;
    }

    get homeJurisdictionName(): string {
        return this.homeJurisdiction?.name() || '';
    }

    get homeJurisdictionOptions(): Array<SelectOption> {
        const options = [{ value: '', name: `- ${this.$t('common.select')} -`, isDisabled: true }];

        stateList?.forEach((state) => {
            const stateObject = new State({ abbrev: state });
            const value = stateObject?.abbrev?.toLowerCase();
            const name = stateObject?.name();

            if (name && value) {
                options.push({ value, name, isDisabled: false });
            }
        });
        return options;
    }

    get modalTitle(): string {
        let title = '';

        if (!this.isSuccess) {
            if (this.isError) {
                title = this.$t('common.somethingWentWrong');
            } else {
                const newState = this.$tm('common.states')
                    .find((s) => s.abbrev.toLowerCase() === this.formData.newHomeJurisdiction.value)?.full
                    || this.formData.newHomeJurisdiction.value;

                title = this.$t('homeJurisdictionChange.modalTitle', { newState });
            }
        }

        return title;
    }

    //
    // Methods
    //
    initHomeJurisdictionForm(): void {
        this.formData = reactive({
            newHomeJurisdiction: new FormInput({
                id: 'new-home-jurisdiction',
                name: 'new-home-jurisdiction',
                label: computed(() => this.$t('homeJurisdictionChange.newHomeJurisdictionLabel')),
                valueOptions: this.homeJurisdictionOptions,
                validation: Joi.string().required().messages(this.joiMessages.string),
            }),
            submit: new FormInput({
                isSubmitInput: true,
                id: 'submit-home-jurisdiction',
            })
        });
    }

    handleSubmit(): void {
        this.validateAll({ asTouched: true });

        if (this.isFormValid) {
            this.openConfirmJurisdictionModal();
        }
    }

    openConfirmJurisdictionModal(): void {
        this.isConfirmJurisdictionModalOpen = true;
        this.isSuccess = false;
        this.isError = false;
        this.errorMessage = '';
    }

    closeConfirmJurisdictionModal(): void {
        this.isConfirmJurisdictionModalOpen = false;
        this.isSuccess = false;
        this.isError = false;
        this.errorMessage = '';
        this.formData.newHomeJurisdiction.value = '';
    }

    async submitHomeJurisdictionChange(): Promise<void> {
        this.formData.newHomeJurisdiction.validate({ asTouched: true });

        if (this.formData.newHomeJurisdiction.isValid) {
            this.isFormLoading = true;
            this.isError = false;
            this.errorMessage = '';
            const newHomeJurisdiction = this.formData.newHomeJurisdiction.value;
            const jurisdictionUpdateData = {
                jurisdiction: newHomeJurisdiction
            };

            await this.$store.dispatch('user/updateHomeJurisdictionRequest', jurisdictionUpdateData).then(() => {
                this.isSuccess = true;
            }).catch((err: any) => {
                this.isError = true;
                this.errorMessage = err?.message || this.$t('common.tryAgain');
            });

            this.isFormLoading = false;
        }
    }

    focusTrapJurisdiction(event: KeyboardEvent): void {
        // IDs must match those used in the template
        const firstTabIndex = document.getElementById('jurisdiction-cancel-btn');
        const lastTabIndex = document.getElementById('jurisdiction-submit-btn');

        if (event.shiftKey) {
            // shift + tab to last input
            if (document.activeElement === firstTabIndex) {
                lastTabIndex?.focus();
                event.preventDefault();
            }
        } else if (document.activeElement === lastTabIndex) {
            // Tab to first input
            firstTabIndex?.focus();
            event.preventDefault();
        }
    }

    @Watch('user') onUserChanged() {
        if (this.formData?.newHomeJurisdiction) {
            this.formData.newHomeJurisdiction.value = '';
        }
    }
}

export default toNative(UpdateHomeJurisdiction);
