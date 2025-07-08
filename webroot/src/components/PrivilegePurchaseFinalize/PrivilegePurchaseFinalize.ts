//
//  PrivilegePurchaseFinalize.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/28/2024.
//

import { Component, mixins, Prop } from 'vue-facing-decorator';
import { reactive, nextTick } from 'vue';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import PrivilegePurchaseAcceptUI, { AcceptUiResponse } from '@components/PrivilegePurchaseAcceptUI/PrivilegePurchaseAcceptUI.vue';
import CollapseCaretButton from '@components/CollapseCaretButton/CollapseCaretButton.vue';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import InputText from '@components/Forms/InputText/InputText.vue';
import InputSelect from '@components/Forms/InputSelect/InputSelect.vue';
import InputCheckbox from '@components/Forms/InputCheckbox/InputCheckbox.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import MockPopulate from '@components/Forms/MockPopulate/MockPopulate.vue';
import { Compact } from '@models/Compact/Compact.model';
import { PaymentSdkConfig } from '@models/CompactFeeConfig/CompactFeeConfig.model';
import { FormInput } from '@models/FormInput/FormInput.model';
import { LicenseeUser, LicenseeUserPurchaseSerializer } from '@models/LicenseeUser/LicenseeUser.model';
import { License } from '@models/License/License.model';
import { Licensee } from '@models/Licensee/Licensee.model';
import { PrivilegePurchaseOption } from '@models/PrivilegePurchaseOption/PrivilegePurchaseOption.model';
import { PurchaseFlowState } from '@/models/PurchaseFlowState/PurchaseFlowState.model';
import { PurchaseFlowStep } from '@/models/PurchaseFlowStep/PurchaseFlowStep.model';
import Joi from 'joi';

@Component({
    name: 'PrivilegePurchaseFinalize',
    components: {
        MockPopulate,
        PrivilegePurchaseAcceptUI,
        InputText,
        InputSelect,
        InputCheckbox,
        InputSubmit,
        InputButton,
        CollapseCaretButton
    }
})
export default class PrivilegePurchaseFinalize extends mixins(MixinForm) {
    @Prop({ default: 0 }) flowStep!: number;

    //
    // Data
    //
    formErrorMessage = '';

    //
    // Lifecycle
    //
    created() {
        if (!this.statesSelected) {
            this.handleCancelClicked();
        }

        this.initFormInputs();
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

    get user(): LicenseeUser | null {
        return this.userStore.model;
    }

    get licensee(): Licensee | null {
        return this.user?.licensee || null;
    }

    get selectedPurchaseLicense(): License | null {
        return this.$store.getters['user/getLicenseSelected']();
    }

    get licenseTypeSelected(): string {
        return this.selectedPurchaseLicense?.licenseTypeAbbreviation()?.toLowerCase() || '';
    }

    get selectionText(): string {
        return `${this.licenseTypeSelected.toLocaleUpperCase()} ${this.$t('licensing.privilege')} ${this.$t('common.selection')}`;
    }

    get privilegeCount(): number {
        return this.selectedStatePurchaseDataList?.length || 0;
    }

    get purchaseFlowState(): PurchaseFlowState {
        return this.userStore?.purchase || new PurchaseFlowState();
    }

    get attestationsSelected(): Array<string> {
        let attestationsAccepted = [];

        this.purchaseFlowState.steps?.forEach((step: PurchaseFlowStep) => {
            if (step.attestationsAccepted) {
                attestationsAccepted = attestationsAccepted.concat(step.attestationsAccepted);
            }
        });

        return attestationsAccepted;
    }

    get statesSelected(): Array<string> {
        let statesSelected = [];

        this.purchaseFlowState.steps?.forEach((step: PurchaseFlowStep) => {
            if (step.selectedPrivilegesToPurchase) {
                statesSelected = statesSelected.concat(step.selectedPrivilegesToPurchase);
            }
        });

        return statesSelected;
    }

    get selectedStatePurchaseDataList(): Array<PrivilegePurchaseOption> {
        return this.purchaseDataList.filter((option) => {
            let includes = false;

            const stateAbbrev = option?.jurisdiction?.abbrev;

            if (stateAbbrev) {
                includes = this.statesSelected?.includes(stateAbbrev);
            }

            return includes;
        });
    }

    get selectedStatePurchaseDisplayDataList(): Array<object> {
        const licenseTypeKey = this.licenseTypeSelected;

        return this.selectedStatePurchaseDataList.map((state) => {
            const feeConfig = state?.fees?.[licenseTypeKey];

            let stateFeeText = '';
            let stateFeeDisplay = '';

            if (feeConfig) {
                const shouldUseMilitaryRate = this.shouldUseMilitaryRate(feeConfig);

                stateFeeText = `${state?.jurisdiction?.name()} ${shouldUseMilitaryRate
                    ? this.$t('payment.compactPrivilegeStateFeeMilitary')
                    : this.$t('payment.compactPrivilegeStateFee')
                }`;

                if (shouldUseMilitaryRate) {
                    stateFeeDisplay = feeConfig.militaryRate.toFixed(2);
                } else {
                    stateFeeDisplay = (feeConfig?.baseRate || 0).toFixed(2);
                }
            }

            return {
                ...state,
                stateFeeDisplay,
                stateFeeText,
            };
        });
    }

    get purchaseDataList(): Array<PrivilegePurchaseOption> {
        return this.currentCompact?.privilegePurchaseOptions || [];
    }

    get currentCompactPaymentSdkConfig(): PaymentSdkConfig | null {
        return this.currentCompact?.fees?.paymentSdkConfig || null;
    }

    get currentCompactCommissionFee(): number | null {
        return this.currentCompact?.fees?.compactCommissionFee || null;
    }

    get compactCommissionFeeText(): string | null {
        return `${this.$t('payment.compactCommissionFee')} ($${this.currentCompactCommissionFee?.toFixed(2)} x ${this.privilegeCount})`;
    }

    get totalCompactCommissionFee(): number {
        let total = 0;

        if (this.currentCompactCommissionFee) {
            total = this.privilegeCount * this.currentCompactCommissionFee;
        }

        return total;
    }

    get totalCompactCommissionFeeDisplay(): string {
        return this.totalCompactCommissionFee?.toFixed(2) || '';
    }

    get isPerPrivilegeTransactionFeeActive(): boolean {
        return this.currentCompact?.fees?.isPerPrivilegeTransactionFeeActive || false;
    }

    get creditCardFeesTotal(): number {
        const numPrivileges = this.selectedStatePurchaseDataList?.length || 0;
        const feePerPrivilege = this.currentCompact?.fees?.perPrivilegeTransactionFeeAmount || 0;
        let feesTotal = 0;

        if (this.isPerPrivilegeTransactionFeeActive) {
            feesTotal = numPrivileges * feePerPrivilege;
        }

        return feesTotal;
    }

    get creditCardFeesTotalDisplay(): string {
        return this.creditCardFeesTotal.toFixed(2);
    }

    get totalPurchasePrice(): number {
        let total = this.totalCompactCommissionFee + this.creditCardFeesTotal;

        const licenseTypeKey = this.licenseTypeSelected;

        this.selectedStatePurchaseDataList.forEach((stateSelected) => {
            const feeConfig = stateSelected?.fees?.[licenseTypeKey];

            if (feeConfig) {
                const shouldUseMilitaryRate = this.shouldUseMilitaryRate(feeConfig);

                if (shouldUseMilitaryRate) {
                    total += feeConfig.militaryRate;
                } else {
                    total += feeConfig.baseRate;
                }
            }
        });

        return total;
    }

    get totalPurchasePriceDisplay(): string {
        return this.totalPurchasePrice?.toFixed(2) || '';
    }

    get isSubmitEnabled(): boolean {
        return this.isFormValid && this.formData.noRefunds.value && !this.isFormLoading;
    }

    get isMockPopulateEnabled(): boolean {
        return Boolean(this.$envConfig.isDevelopment);
    }

    //
    // Methods
    //
    initFormInputs(): void {
        this.formData = reactive({
            noRefunds: new FormInput({
                id: 'no-refunds-check',
                name: 'no-refunds-check',
                label: this.$t('licensing.noRefundsMessage'),
                validation: Joi.boolean().invalid(false).required().messages(this.joiMessages.boolean),
                value: false,
                isDisabled: false
            }),
            submit: new FormInput({
                isSubmitInput: true,
                id: 'submit',
            }),
        });
        this.watchFormInputs();
    }

    shouldUseMilitaryRate(feeConfig): boolean {
        const { militaryRate } = feeConfig || {};
        const hasMilitaryRate = Boolean(militaryRate || militaryRate === 0);

        return Boolean(hasMilitaryRate && this.licensee?.isMilitaryStatusActive());
    }

    async acceptUiSuccessResponse(response: AcceptUiResponse): Promise<void> {
        await this.handleSubmitOverride(response?.opaqueData || {});
    }

    async acceptUiErrorResponse(): Promise<void> {
        this.isFormError = true;
        this.formErrorMessage = this.$t('payment.confirmCardDetailsError');
        await this.scrollIntoView('button-row');
    }

    async scrollIntoView(id: string): Promise<void> {
        const formMessageElement = document.getElementById(id);

        if (formMessageElement?.scrollIntoView) {
            await nextTick();
            formMessageElement?.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }

    async handleSubmitOverride(opaqueData: object): Promise<void> {
        this.validateAll({ asTouched: true });

        if (this.isFormValid) {
            this.startFormLoading();
            this.isFormError = false;
            this.formErrorMessage = '';

            const {
                statesSelected,
                attestationsSelected,
                selectedPurchaseLicense
            } = this;
            const serverData = LicenseeUserPurchaseSerializer.toServer({
                statesSelected,
                attestationsSelected,
                selectedPurchaseLicense,
                opaqueData
            });
            const purchaseServerEvent = await this.$store.dispatch('user/postPrivilegePurchases', serverData);

            this.endFormLoading();

            if (purchaseServerEvent?.message === 'Successfully processed charge') {
                this.$store.dispatch('user/saveFlowStep', new PurchaseFlowStep({
                    stepNum: this.flowStep
                }));

                this.$router.push({
                    name: 'PrivilegePurchaseSuccessful',
                    params: { compact: this.currentCompactType }
                });
            } else if (purchaseServerEvent?.message) {
                this.isFormError = true;
                this.formErrorMessage = purchaseServerEvent?.message;
                await this.scrollIntoView('button-row');
            }
        } else {
            this.isFormError = true;
            this.formErrorMessage = this.$t('common.formValidationErrorMessage');
        }
    }

    handleCancelClicked(): void {
        this.$store.dispatch('user/resetToPurchaseFlowStep', 0);

        if (this.currentCompactType) {
            this.$router.push({
                name: 'LicenseeDashboard',
                params: { compact: this.currentCompactType }
            });
        }
    }

    handleBackClicked(): void {
        if (this.currentCompactType) {
            this.$router.push({
                name: 'PrivilegePurchaseAttestation',
                params: { compact: this.currentCompactType }
            });
        }
    }

    async mockPopulate(): Promise<void> {
        // It's handy to have certain values copied to the clipboard during local development;
        // The following are applicable depending on the testing scenario:
        navigator.clipboard.writeText(`5424 0000 0000 0015`); // Test CC number
        // navigator.clipboard.writeText(`01/30`); // Test CC expiry
        // navigator.clipboard.writeText(`900`); // Test CC CVV
        // navigator.clipboard.writeText(`Test`); // Test CC first name
        // navigator.clipboard.writeText(`User`); // Test CC last name
        // navigator.clipboard.writeText(`46214`); // Test CC zip code
        this.formData.noRefunds.value = true;
        this.validateAll({ asTouched: true });
        await nextTick();
        const formButtons = document.getElementById('button-row');

        formButtons?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    handlePaymentButtonClick(): void {
        // Validate all inputs first to ensure we have current validation state
        this.validateAll({ asTouched: true });

        if (!this.isFormValid) {
            this.showInvalidFormError();
        }
    }
}
