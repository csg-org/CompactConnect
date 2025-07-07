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
import {
    reactive,
    computed,
    ComputedRef,
    nextTick
} from 'vue';
import { stateList } from '@/app.config';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import InputSelect from '@components/Forms/InputSelect/InputSelect.vue';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import CheckCircleIcon from '@components/Icons/CheckCircle/CheckCircle.vue';
import Modal from '@components/Modal/Modal.vue';
import { FormInput } from '@models/FormInput/FormInput.model';
import { State } from '@models/State/State.model';
import { LicenseeUser } from '@/models/LicenseeUser/LicenseeUser.model';
import { License } from '@/models/License/License.model';
import { Licensee } from '@models/Licensee/Licensee.model';
import Joi from 'joi';

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

    get purchaseEligibleLicenses(): Array<License> {
        return this.licensee?.purchaseEligibleLicenses() || [];
    }

    get homeJurisdiction(): State | null {
        return this.licensee?.homeJurisdiction || null;
    }

    get homeJurisdictionName(): string {
        return this.homeJurisdiction?.name() || '';
    }

    get homeJurisdictionOptions(): Array<SelectOption> {
        const options = [{
            value: '',
            name: `- ${this.$t('common.select')} -`,
            isDisabled: true
        }];

        stateList?.forEach((state) => {
            const stateObject = new State({ abbrev: state });
            const value = stateObject?.abbrev?.toLowerCase();
            const name = stateObject?.name();

            if (name && value) {
                let label = '';
                // Find eligible license for this state
                const eligibleLicense = this.purchaseEligibleLicenses.find(
                    (license: License) => license.issueState?.abbrev?.toLowerCase() === value
                );

                if (eligibleLicense) {
                    const licenseTypeName = (eligibleLicense.licenseType) ? (
                        eligibleLicense.$tm?.('licensing.licenseTypes')?.find((type: any) =>
                            type.key === eligibleLicense.licenseType)?.abbrev.toUpperCase()
                            || eligibleLicense.licenseType
                    ) : '';

                    label = this.$t('homeJurisdictionChange.eligibleLicenseOption', {
                        state: name,
                        licenseType: licenseTypeName
                    });
                } else {
                    label = this.$t('homeJurisdictionChange.noEligibleLicenseOption', {
                        state: name
                    });
                }

                options.push({
                    value,
                    name: label,
                    isDisabled: false
                });
            }
        });

        return options;
    }

    get jurisdictionModalTitle(): string {
        let title = ' ';

        if (!this.isSuccess) {
            if (this.isError) {
                title = this.$t('common.somethingWentWrong');
            } else {
                const newState = this.$tm('common.states').find((state) =>
                    state.abbrev.toLowerCase() === this.formData.newHomeJurisdiction.value)?.full
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

    async openConfirmJurisdictionModal() {
        this.isConfirmJurisdictionModalOpen = true;
        this.isSuccess = false;
        this.isError = false;
        this.errorMessage = '';
        await nextTick();
        document.getElementById('jurisdiction-cancel-btn')?.focus();
    }

    closeConfirmJurisdictionModal(): void {
        this.isConfirmJurisdictionModalOpen = false;
        this.isSuccess = false;
        this.isError = false;
        this.errorMessage = '';
        this.formData.newHomeJurisdiction.value = '';
    }

    async submitHomeJurisdictionChange(): Promise<void> {
        this.validateAll({ asTouched: true });

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
        const modal = document.getElementById('home-jurisdiction-modal');

        if (modal) {
            const focusableSelectors = [
                'a[href]', 'area[href]', 'input:not([disabled])', 'select:not([disabled])',
                'textarea:not([disabled])', 'button:not([disabled])', '[tabindex]:not([tabindex="-1"])'
            ];
            const focusableElements = Array.from(
                modal.querySelectorAll(focusableSelectors.join(','))
            ).filter((element) => (element as HTMLElement).offsetParent !== null) as HTMLElement[];

            if (focusableElements.length > 0) {
                const firstElement = focusableElements[0];
                const lastElement = focusableElements[focusableElements.length - 1];

                if (event.key === 'Tab') {
                    if (event.shiftKey && document.activeElement === firstElement) {
                        lastElement.focus();
                        event.preventDefault();
                    } else if (document.activeElement === lastElement) {
                        firstElement.focus();
                        event.preventDefault();
                    }
                }
            }
        }
    }

    @Watch('user') onUserChanged() {
        this.initHomeJurisdictionForm();
    }
}

export default toNative(UpdateHomeJurisdiction);
