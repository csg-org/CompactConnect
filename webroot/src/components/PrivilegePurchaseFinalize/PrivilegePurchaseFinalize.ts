//
//  PrivilegePurchaseFinalize.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/28/2024.
//

import { Component, mixins, Prop } from 'vue-facing-decorator';
import { reactive, computed } from 'vue';
import { stateList } from '@/app.config';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import CollapseCaretButton from '@components/CollapseCaretButton/CollapseCaretButton.vue';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import InputText from '@components/Forms/InputText/InputText.vue';
import InputSelect from '@components/Forms/InputSelect/InputSelect.vue';
import InputCheckbox from '@components/Forms/InputCheckbox/InputCheckbox.vue';
import InputCreditCard from '@components/Forms/InputCreditCard/InputCreditCard.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import MockPopulate from '@components/Forms/MockPopulate/MockPopulate.vue';
import { Compact } from '@models/Compact/Compact.model';
import { State } from '@models/State/State.model';
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
        InputText,
        InputSelect,
        InputCheckbox,
        InputSubmit,
        InputButton,
        InputCreditCard,
        CollapseCaretButton
    }
})
export default class PrivilegePurchaseFinalize extends mixins(MixinForm) {
    @Prop({ default: 0 }) flowStep!: number;

    //
    // Data
    //
    formErrorMessage = '';
    expYearRef;
    cvvRef;
    shouldShowPaymentSection = true;

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

    get user(): LicenseeUser | null {
        return this.userStore.model;
    }

    get licensee(): Licensee | null {
        return this.user?.licensee || null;
    }

    get currentCompact(): Compact | null {
        return this.userStore?.currentCompact || null;
    }

    get currentCompactType(): string | null {
        return this.currentCompact?.type || null;
    }

    get isPerPrivilegeTransactionFeeActive(): boolean {
        return this.currentCompact?.fees?.isPerPrivilegeTransactionFeeActive || false;
    }

    get currentCompactCommissionFee(): number | null {
        return this.currentCompact?.fees?.compactCommissionFee || null;
    }

    get isDesktop(): boolean {
        return this.$matches.desktop.min;
    }

    get isMobile(): boolean {
        return !this.isDesktop;
    }

    get isPhone(): boolean {
        return !this.$matches.tablet.min;
    }

    get stateOptions() {
        const stateOptions = [{ value: '', name: this.$t('common.select') }];

        stateList?.forEach((state) => {
            const stateObject = new State({ abbrev: state });
            const value = stateObject?.abbrev?.toLowerCase();
            const name = stateObject?.name();

            if (name && value) {
                stateOptions.push({ value, name });
            }
        });

        return stateOptions;
    }

    get zipLabel(): string {
        return this.$t('common.zipCode');
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
            const hasMilitaryRate = Boolean(feeConfig && (feeConfig.militaryRate || feeConfig.militaryRate === 0));

            const stateFeeText = `${state?.jurisdiction?.name()} ${hasMilitaryRate
                ? this.$t('military.militaryDiscountText')
                : this.$t('payment.compactPrivilegeStateFee')
            }`;

            let stateFeeDisplay = '';

            if (feeConfig) {
                if (hasMilitaryRate) {
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

    get compactCommissionFeeText(): string | null {
        return `${this.$t('payment.compactCommissionFee')} ($${this.currentCompactCommissionFee?.toFixed(2)} x ${this.privCount})`;
    }

    get privCount(): number {
        return this.selectedStatePurchaseDataList?.length || 0;
    }

    get totalCompactCommissionFee(): number {
        let total = 0;

        if (this.currentCompactCommissionFee) {
            total = this.privCount * this.currentCompactCommissionFee;
        }

        return total;
    }

    get totalPurchasePrice(): number {
        let total = this.totalCompactCommissionFee + this.creditCardFeesTotal;

        const licenseTypeKey = this.licenseTypeSelected;

        // TODO probably total is wrong need to fix

        this.selectedStatePurchaseDataList.forEach((stateSelected) => {
            console.log('stateSelected', stateSelected);

            if (stateSelected?.fees?.[licenseTypeKey]) {
                total += stateSelected.fees[licenseTypeKey];
            }
        });

        console.log('total', total);

        return total;
    }

    get totalCompactCommissionFeeDisplay(): string {
        return this.totalCompactCommissionFee?.toFixed(2) || '';
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

    get selectedPurchaseLicense(): License | null {
        return this.$store.getters['user/getLicenseSelected']();
    }

    get licenseTypeSelected(): string {
        return this.selectedPurchaseLicense?.licenseTypeAbbreviation()?.toLowerCase() || '';
    }

    get selectionText(): string {
        return `${this.licenseTypeSelected.toLocaleUpperCase()} ${this.$t('licensing.privilege')} ${this.$t('common.selection')}`;
    }

    //
    // Methods
    //
    initFormInputs(): void {
        this.formData = reactive({
            creditCard: new FormInput({
                id: 'card',
                name: 'card',
                label: this.$t('payment.cardNumber'),
                shouldHideLabel: false,
                shouldHideMargin: true,
                placeholder: '0000 0000 0000 0000',
                autocomplete: 'cc-number',
                validation: Joi.string().required().regex(new RegExp('(^[0-9]{4} [0-9]{4} [0-9]{4} [0-9]{4})')).messages(this.joiMessages.creditCard),
            }),
            expMonth: new FormInput({
                id: 'exp-month',
                name: 'exp-month',
                label: computed(() => this.$t('payment.cardExpirationMonth')),
                shouldHideLabel: true,
                shouldHideMargin: true,
                placeholder: '00',
                autocomplete: 'cc-exp-month',
                shouldHideErrorMessage: true,
                enforceMax: true,
                validation: Joi.string().required().regex(new RegExp('(^[0-1][0-9]$)')).max(2),
            }),
            expYear: new FormInput({
                id: 'exp-year',
                name: 'exp-year',
                label: computed(() => this.$t('payment.cardExpirationYear')),
                shouldHideLabel: true,
                shouldHideMargin: true,
                placeholder: '00',
                autocomplete: 'cc-exp-year',
                shouldHideErrorMessage: true,
                enforceMax: true,
                validation: Joi.string().required().regex(new RegExp('(^[0-9]{2}$)')).max(2),
            }),
            cvv: new FormInput({
                id: 'cvv',
                name: 'cvv',
                label: this.$t('payment.cvv'),
                shouldHideLabel: false,
                shouldHideMargin: true,
                placeholder: '000',
                autocomplete: 'cc-csc',
                shouldHideErrorMessage: true,
                enforceMax: true,
                validation: Joi.string().required().regex(new RegExp('(^[0-9]{3,4}$)')).max(4),
            }),
            firstName: new FormInput({
                id: 'first-name',
                name: 'first-name',
                label: this.$t('common.firstName'),
                shouldHideLabel: false,
                shouldHideMargin: true,
                autocomplete: 'given-name',
                placeholder: this.$t('payment.enterFirstName'),
                validation: Joi.string().required().messages(this.joiMessages.string),
            }),
            lastName: new FormInput({
                id: 'last-name',
                name: 'last-name',
                label: this.$t('common.lastName'),
                shouldHideLabel: false,
                shouldHideMargin: true,
                autocomplete: 'family-name',
                placeholder: this.$t('payment.enterLastName'),
                validation: Joi.string().required().messages(this.joiMessages.string),
            }),
            streetAddress1: new FormInput({
                id: 'street-address-1',
                name: 'street-address-1',
                label: this.$t('payment.streetAddress'),
                shouldHideLabel: false,
                shouldHideMargin: true,
                autocomplete: 'address-line1',
                validation: Joi.string().required().messages(this.joiMessages.string),
                placeholder: this.$t('payment.enterStreetAddress'),
            }),
            streetAddress2: new FormInput({
                id: 'street-address-2',
                name: 'street-address-2',
                label: this.$t('payment.streetAddress2'),
                shouldHideLabel: false,
                shouldHideMargin: true,
                autocomplete: 'address-line2',
                placeholder: this.$t('payment.apptUnitNumber')
            }),
            stateSelect: new FormInput({
                id: 'state-select',
                name: 'state-select',
                label: this.$t('common.state'),
                shouldHideLabel: false,
                shouldHideMargin: true,
                placeholder: computed(() => this.$t('common.select')),
                validation: Joi.string().required().messages(this.joiMessages.string),
                value: '',
                valueOptions: this.stateOptions,
            }),
            zip: new FormInput({
                id: 'zip-code',
                name: 'zip-code',
                label: this.$t('common.zipCode'),
                shouldHideLabel: false,
                shouldHideMargin: true,
                placeholder: '00000',
                autocomplete: 'postal-code',
                shouldHideErrorMessage: true,
                validation: Joi.string().required().regex(new RegExp('(^[0-9]{5}$)|(^[0-9]{5}-[0-9]{4}$)')),
            }),
            noRefunds: new FormInput({
                id: 'no-refunds-check',
                name: 'no-refunds-check',
                label: this.$t('licensing.noRefundsMessage'),
                validation: Joi.boolean().required(),
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

    async handleSubmit(): Promise<void> {
        this.validateAll({ asTouched: true });

        if (this.isFormValid) {
            this.startFormLoading();
            this.isFormError = false;
            this.formErrorMessage = '';

            const {
                formValues,
                statesSelected,
                attestationsSelected,
                selectedPurchaseLicense
            } = this;
            const serverData = LicenseeUserPurchaseSerializer.toServer({
                formValues,
                statesSelected,
                attestationsSelected,
                selectedPurchaseLicense
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

    handleExpYearRefEmitted(inputData): void {
        this.expYearRef = inputData.ref;
    }

    handleCVVRefEmitted(inputData): void {
        this.cvvRef = inputData.ref;
    }

    togglePaymentCollapsed(): void {
        this.shouldShowPaymentSection = !this.shouldShowPaymentSection;
    }

    formatCreditCard(): void {
        const { creditCard } = this.formData;
        const format = (ccInputVal) => {
            // Remove all non-numerals
            let formatted = ccInputVal.replace(/[^\d]/g, '');

            // Add the first space if a number from the second group appears
            formatted = formatted.replace(/^(\d{4}) ?(\d{1,4})/, '$1 $2');

            // Add the second space if a number from the third group appears
            formatted = formatted.replace(/^(\d{4}) ?(\d{4}) ?(\d{1,4})/, '$1 $2 $3');

            // Add the third space if a number from the fourth group appears
            formatted = formatted.replace(/^(\d{4}) ?(\d{4}) ?(\d{4}) ?(\d{1,4})/, '$1 $2 $3 $4');

            // Enforce max length
            return formatted.substring(0, 19);
        };

        creditCard.value = format(creditCard.value);
    }

    handleExpMonthInput(formInput): void {
        // Remove all non-numerals
        formInput.value = formInput.value.replace(/[^\d]/g, '');

        if (formInput.value && formInput.value.length > 1 && this.expYearRef) {
            this.expYearRef.focus();
        }
    }

    handleExpYearInput(formInput): void {
        // Remove all non-numerals
        formInput.value = formInput.value.replace(/[^\d]/g, '');

        if (formInput.value && formInput.value.length > 1 && this.cvvRef) {
            this.cvvRef.focus();
        }
    }

    handleCVVInput(formInput): void {
        // Remove all non-numerals
        formInput.value = formInput.value.replace(/[^\d]/g, '');
    }

    handleZipInput(formInput): void {
        // Remove all non-numerals
        formInput.value = formInput.value.replace(/[^\d]/g, '');
    }

    mockPopulate(): void {
        this.formData.creditCard.value = `5424 0000 0000 0015`;
        this.formData.expMonth.value = `01`;
        this.formData.expYear.value = `29`;
        this.formData.cvv.value = `900`;
        this.formData.firstName.value = `Test`;
        this.formData.lastName.value = `User`;
        this.formData.streetAddress1.value = `123 Fake St`;
        this.formData.stateSelect.value = `ca`;
        this.formData.zip.value = `46214`;
        this.formData.noRefunds.value = true;
        this.validateAll({ asTouched: true });
    }
}
