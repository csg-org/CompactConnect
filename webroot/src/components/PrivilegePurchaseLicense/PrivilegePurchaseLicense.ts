//
//  PrivilegePurchaseLicense.ts
//  CompactConnect
//
//  Created by InspiringApps on 3/3/2025.
//

import {
    Component,
    toNative,
    mixins,
    Prop,
    Watch
} from 'vue-facing-decorator';
import { reactive, computed } from 'vue';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import LoadingSpinner from '@components/LoadingSpinner/LoadingSpinner.vue';
import InputSelect from '@components/Forms/InputSelect/InputSelect.vue';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import { Compact } from '@models/Compact/Compact.model';
import { FormInput } from '@/models/FormInput/FormInput.model';
import { License } from '@/models/License/License.model';
import { Licensee } from '@models/Licensee/Licensee.model';
import { LicenseeUser } from '@/models/LicenseeUser/LicenseeUser.model';
import { PurchaseFlowStep } from '@/models/PurchaseFlowStep/PurchaseFlowStep.model';
import Joi from 'joi';

@Component({
    name: 'PrivilegePurchaseLicense',
    components: {
        InputSelect,
        InputSubmit,
        InputButton,
        LoadingSpinner,
    }
})
class PrivilegePurchaseLicense extends mixins(MixinForm) {
    @Prop({ default: 0 }) flowStep!: number;

    //
    // Data
    //
    isLoading = false;
    areFormInputsSet = false;

    //
    // Lifecycle
    //
    async created() {
        this.initPage();
    }

    //
    // Computed
    //
    get userStore(): any {
        return this.$store.state.user;
    }

    get user(): LicenseeUser | null {
        return this.userStore.model;
    }

    get licensee(): Licensee | null {
        return this.user?.licensee || null;
    }

    get homeStateLicenses(): Array<License> {
        console.log('huh', this.licensee?.homeJurisdictionLicenses());

        return this.licensee?.homeJurisdictionLicenses() || [];
    }

    get currentCompact(): Compact | null {
        return this.userStore?.currentCompact || null;
    }

    get currentCompactType(): string | null {
        return this.currentCompact?.type || null;
    }

    get licenseList(): Array<License> {
        return this.licensee?.licenses || [];
    }

    get homeStateLicenseOptions(): Array<any> {
        const homeStateLicenseOptions: Array<any> = [{ value: '', name: this.$t('common.select') }];

        this.homeStateLicenses.forEach((license: License) => {
            homeStateLicenseOptions.push({
                value: license.id,
                name: license.displayName()
            });
        });

        return homeStateLicenseOptions;
    }

    get backText(): string {
        return this.$t('common.back');
    }

    get cancelText(): string {
        return this.$t('common.cancel');
    }

    get submitLabel(): string {
        let label = this.$t('common.next');

        if (this.isFormLoading) {
            label = this.$t('common.loading');
        }

        return label;
    }

    //
    // Methods
    //
    initFormInputs(): void {
        this.formData = reactive({
            licenseSelect: new FormInput({
                id: 'license',
                name: 'license',
                label: computed(() => this.$t('licensing.license')),
                validation: Joi.string().required().messages(this.joiMessages.string),
                valueOptions: this.homeStateLicenseOptions,
            }),
            submit: new FormInput({
                isSubmitInput: true,
                id: 'submit',
            })
        });
    }

    initPage() {
        if (this.homeStateLicenses.length === 1) {
            this.$store.dispatch('user/saveFlowStep', new PurchaseFlowStep({
                stepNum: this.flowStep,
                licenseSelected: this.homeStateLicenses[0]
            }));

            this.$router.push({
                name: 'PrivilegePurchaseInformationConfirmation',
                params: { compact: this.currentCompactType }
            });
        } else {
            this.initFormInputs();
        }
    }

    handleSubmit() {
        this.validateAll({ asTouched: true });

        if (this.isFormValid) {
            this.startFormLoading();

            this.$store.dispatch('user/saveFlowStep', new PurchaseFlowStep({
                stepNum: this.flowStep,
                licenseSelected: this.formData.licenseSelect.value
            }));

            this.$router.push({
                name: 'PrivilegePurchaseInformationConfirmation',
                params: { compact: this.currentCompactType }
            });

            this.endFormLoading();
        }
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
        this.$store.dispatch('user/resetToPurchaseFlowStep', 0);

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
    @Watch('homeStateLicenses.length') currentCompactSet() {
        this.initPage();
    }
}

export default toNative(PrivilegePurchaseLicense);

// export default PrivilegePurchaseLicense;
