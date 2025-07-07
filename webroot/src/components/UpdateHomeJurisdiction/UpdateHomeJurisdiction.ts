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
    otherStateOption = 'other';

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
        const options = [
            {
                value: '',
                name: `- ${this.$t('common.select')} -`,
                isDisabled: true,
            },
            {
                value: this.otherStateOption,
                name: `${this.$t('homeJurisdictionChange.notListedOption')}`,
                isDisabled: false,
            }
        ];

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
                    let licenseTypeName = '';

                    if (eligibleLicense.licenseType) {
                        const licenseTypeKey = eligibleLicense.licenseType;
                        const licenseTypes = eligibleLicense.$tm?.('licensing.licenseTypes') || [];
                        const matchedType = licenseTypes.find((type) => type.key === licenseTypeKey);
                        const matchedAbbrev = matchedType?.abbrev?.toUpperCase();

                        licenseTypeName = matchedAbbrev || licenseTypeKey;
                    }

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

        if (this.isError) {
            title = this.$t('common.somethingWentWrong');
        } else if (!this.isSuccess) {
            const selectedState = this.formData.newHomeJurisdiction.value;

            const newState = (selectedState === this.otherStateOption) ? this.$t('homeJurisdictionChange.notListedOption') : new State({ abbrev: selectedState }).name();

            title = this.$t('homeJurisdictionChange.modalTitle', { newState });
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

    async openConfirmJurisdictionModal(): Promise<void> {
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

            await this.$store.dispatch('user/updateHomeJurisdictionRequest', jurisdictionUpdateData).then(async () => {
                this.isSuccess = true;
                await nextTick();
                document.getElementById('jurisdiction-close-btn')?.focus();
            }).catch((err: any) => {
                this.isError = true;
                this.errorMessage = err?.message || this.$t('common.tryAgain');
            });

            this.isFormLoading = false;
        }
    }

    focusTrapJurisdiction(event: KeyboardEvent): void {
        const firstTabIndex = document.getElementById('jurisdiction-cancel-btn');
        const lastTabIndex = document.getElementById('jurisdiction-submit-btn');

        if (event.key === 'Tab') {
            if (firstTabIndex && lastTabIndex) {
                // If Shift+Tab on first, cycle to last
                if (event.shiftKey && document.activeElement === firstTabIndex) {
                    lastTabIndex.focus();
                    event.preventDefault();
                } else if (!event.shiftKey && document.activeElement === lastTabIndex) {
                    firstTabIndex.focus();
                    event.preventDefault();
                } else if (
                    document.activeElement !== firstTabIndex
                    && document.activeElement !== lastTabIndex
                ) {
                    firstTabIndex.focus();
                    event.preventDefault();
                }
            }
        }
    }

    @Watch('user') onUserChanged() {
        this.initHomeJurisdictionForm();
    }
}

export default toNative(UpdateHomeJurisdiction);
