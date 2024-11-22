//
//  FinalizePrivilegePurchase.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/28/2024.
//

import { Component, mixins } from 'vue-facing-decorator';
import { reactive, computed } from 'vue';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import CollapseCaretButton from '@components/CollapseCaretButton/CollapseCaretButton.vue';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import InputText from '@components/Forms/InputText/InputText.vue';
import InputSelect from '@components/Forms/InputSelect/InputSelect.vue';
import InputCheckbox from '@components/Forms/InputCheckbox/InputCheckbox.vue';
import InputCreditCard from '@components/Forms/InputCreditCard/InputCreditCard.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import { Compact } from '@models/Compact/Compact.model';
import { FormInput } from '@models/FormInput/FormInput.model';
import { LicenseeUserPurchaseSerializer } from '@models/LicenseeUser/LicenseeUser.model';
import { PrivilegePurchaseOption } from '@models/PrivilegePurchaseOption/PrivilegePurchaseOption.model';
import Joi from 'joi';

@Component({
    name: 'FinalizePrivilegePurchase',
    components: {
        InputText,
        InputSelect,
        InputCheckbox,
        InputSubmit,
        InputButton,
        InputCreditCard,
        CollapseCaretButton
    }
})
export default class FinalizePrivilegePurchase extends mixins(MixinForm) {
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
        if (!this.statesSelected || !this.arePurchaseAttestationsAccepted) {
            this.handleCancelClicked();
        }

        this.initFormInputs();
    }

    //
    // Computed
    //
    get firstNameInputLabel(): string {
        return this.$t('common.firstname');
    }

    get firstNamePlaceHolderText(): string {
        return this.$t('payment.firstNameOnCard');
    }

    get lastNameInputLabel(): string {
        return this.$t('common.lastname');
    }

    get lastNamePlaceHolderText(): string {
        return this.$t('payment.lastNameOnCard');
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

    get cancelText(): string {
        return this.$t('common.cancel');
    }

    get backText(): string {
        return this.$t('common.back');
    }

    get submitLabel(): string {
        return this.$t('payment.completePurchase');
    }

    get paymentTitleText(): string {
        return this.$t('payment.payment');
    }

    get noRefundsAcknowledgement(): string {
        return this.$t('licensing.noRefundsMessage');
    }

    get streetAddress1Label(): string {
        return this.$t('payment.streetAddress');
    }

    get streetAddress1PlaceHolderText(): string {
        return this.$t('payment.enterStreetAddress');
    }

    get streetAddress2Label(): string {
        return this.$t('payment.streetAddress2');
    }

    get streetAddress2PlaceHolderText(): string {
        return this.$t('payment.apptUnitNumber');
    }

    get creditCardTitleText(): string {
        return this.$t('payment.creditCardTitle');
    }

    get billingAddressTitleText(): string {
        return this.$t('payment.billingAddressTitle');
    }

    get stateText(): string {
        return this.$t('common.state');
    }

    get cardNumberLabel(): string {
        return this.$t('payment.cardNumber');
    }

    get stateOptions() {
        const stateOptions = [{ value: '', name: this.$t('common.select') }];

        const states = this.$tm('common.states') as Array<any>;

        states?.forEach((state) => {
            const value = state?.abbrev?.source?.toLowerCase();
            const name = state?.full?.source;

            if (name && value) {
                stateOptions.push({ value, name });
            }
        });

        return stateOptions;
    }

    get zipLabel(): string {
        return this.$t('common.zipCode');
    }

    get cvvLabel(): string {
        return 'CVV';
    }

    get expirationDateText(): string {
        return this.$t('payment.expirationDate');
    }

    get selectionText(): string {
        return this.$t('common.selection');
    }

    get userStore(): any {
        return this.$store.state.user;
    }

    get statesSelected(): Array<string> {
        return this.userStore.selectedPrivilegesToPurchase;
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

    get seletedStatePurchaseDsiplayDataList(): Array<object> {
        return this.selectedStatePurchaseDataList.map((state) => {
            const stateFeeText = `${state?.jurisdiction?.name()} ${this.compactPrivilegeStateFeeText}`;
            const stateMilitaryPurchaseText = `${state?.jurisdiction?.name()} ${this.militaryDiscountText}`;
            let stateFeeDisplay = '';
            let stateMilitaryDiscountAmountDisplay = '';

            if (state?.fee) {
                stateFeeDisplay = state.fee.toFixed(2);
            }

            if (state?.militaryDiscountAmount) {
                stateMilitaryDiscountAmountDisplay = state.militaryDiscountAmount.toFixed(2);
            }

            return {
                ...state,
                stateFeeDisplay,
                stateMilitaryDiscountAmountDisplay,
                stateFeeText,
                stateMilitaryPurchaseText
            };
        });
    }

    get currentCompact(): Compact | null {
        return this.userStore?.currentCompact || null;
    }

    get currentCompactType(): string | null {
        return this.currentCompact?.type || null;
    }

    get currentCompactCommissionFee(): number | null {
        return this.currentCompact?.compactCommissionFee || null;
    }

    get stateFeeText(): string {
        return this.$t('payment.expirationDate');
    }

    get arePurchaseAttestationsAccepted(): boolean {
        return this.userStore.arePurchaseAttestationsAccepted;
    }

    get purchaseDataList(): Array<PrivilegePurchaseOption> {
        return this.currentCompact?.privilegePurchaseOptions || [];
    }

    get compactPrivilegeStateFeeText(): string {
        return this.$t('payment.compactPrivilegeStateFee');
    }

    get compactCommissionFeeText(): string | null {
        return `${this.$t('payment.compactCommissionFee')} ($${this.currentCompactCommissionFee?.toFixed(2)} x ${this.privCount})`;
    }

    get privCount(): number {
        return this.selectedStatePurchaseDataList?.length || 0;
    }

    get totalTitle(): string {
        return this.$t('common.total');
    }

    get totalCompactCommissionFee(): number {
        let total = 0;

        if (this.currentCompactCommissionFee) {
            total = this.privCount * this.currentCompactCommissionFee;
        }

        return total;
    }

    get militaryDiscountText(): string {
        return this.$t('licensing.militaryDiscountText');
    }

    get formValidationErrorMessage(): string {
        return this.$t('common.formValidationErrorMessage');
    }

    get totalPurchasePrice(): number {
        let total = this.totalCompactCommissionFee;

        this.selectedStatePurchaseDataList.forEach((stateSelected) => {
            if (stateSelected?.fee) {
                total += stateSelected.fee;
            }

            if (stateSelected?.isMilitaryDiscountActive && stateSelected?.militaryDiscountAmount) {
                total -= stateSelected.militaryDiscountAmount;
            }
        });

        return total;
    }

    get isSubmitEnabled(): boolean {
        this.checkValidForAll();

        return this.isFormValid && this.formData.noRefunds.value && !this.isFormLoading;
    }

    get totalCompactCommissionFeeDisplay(): string {
        return this.totalCompactCommissionFee?.toFixed(2) || '';
    }

    get totalPurchasePriceDisplay(): string {
        return this.totalPurchasePrice?.toFixed(2) || '';
    }

    //
    // Methods
    //
    initFormInputs() {
        this.formData = reactive({
            firstName: new FormInput({
                id: 'first-name',
                name: 'first-name',
                label: this.firstNameInputLabel,
                shouldHideLabel: false,
                shouldHideMargin: true,
                autocomplete: 'given-name',
                placeholder: this.firstNamePlaceHolderText,
                validation: Joi.string().required().messages(this.joiMessages.string),
            }),
            lastName: new FormInput({
                id: 'last-name',
                name: 'last-name',
                label: this.lastNameInputLabel,
                shouldHideLabel: false,
                shouldHideMargin: true,
                autocomplete: 'family-name',
                placeholder: this.lastNamePlaceHolderText,
                validation: Joi.string().required().messages(this.joiMessages.string),
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
                label: this.cvvLabel,
                shouldHideLabel: false,
                shouldHideMargin: true,
                placeholder: '000',
                autocomplete: 'cc-csc',
                shouldHideErrorMessage: true,
                enforceMax: true,
                validation: Joi.string().required().regex(new RegExp('(^[0-9]{3,4}$)')).max(4),
            }),
            creditCard: new FormInput({
                id: 'card',
                name: 'card',
                label: this.cardNumberLabel,
                shouldHideLabel: false,
                shouldHideMargin: true,
                placeholder: '0000 0000 0000 0000',
                autocomplete: 'cc-number',
                validation: Joi.string().required().regex(new RegExp('(^[0-9]{4} [0-9]{4} [0-9]{4} [0-9]{4})')).messages(this.joiMessages.creditCard),
            }),
            streetAddress1: new FormInput({
                id: 'street-address-1',
                name: 'street-address-1',
                label: this.streetAddress1Label,
                shouldHideLabel: false,
                shouldHideMargin: true,
                autocomplete: 'address-line1',
                validation: Joi.string().required().messages(this.joiMessages.string),
                placeholder: this.streetAddress1PlaceHolderText,
            }),
            streetAddress2: new FormInput({
                id: 'street-address-2',
                name: 'street-address-2',
                label: this.streetAddress2Label,
                shouldHideLabel: false,
                shouldHideMargin: true,
                autocomplete: 'address-line2',
                placeholder: this.streetAddress2PlaceHolderText
            }),
            noRefunds: new FormInput({
                id: 'no-refunds-check',
                name: 'no-refunds-check',
                label: this.noRefundsAcknowledgement,
                validation: Joi.boolean().required(),
                value: false,
                isDisabled: false
            }),
            stateSelect: new FormInput({
                id: 'state-select',
                name: 'state-select',
                label: this.stateText,
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
                label: this.zipLabel,
                shouldHideLabel: false,
                shouldHideMargin: true,
                placeholder: '00000',
                autocomplete: 'postal-code',
                shouldHideErrorMessage: true,
                validation: Joi.string().required().regex(new RegExp('(^[0-9]{5}$)|(^[0-9]{5}-[0-9]{4}$)')),
            }),
            submit: new FormInput({
                isSubmitInput: true,
                id: 'submit',
            }),
        });
        this.watchFormInputs();
    }

    async handleSubmit() {
        this.validateAll({ asTouched: true });

        if (this.isFormValid) {
            this.startFormLoading();
            this.isFormError = false;
            this.formErrorMessage = '';

            const { formValues, statesSelected } = this;
            const serverData = LicenseeUserPurchaseSerializer.toServer({ formValues, statesSelected });
            const purchaseServerEvent = await this.$store.dispatch('user/postPrivilegePurchases', serverData);

            this.endFormLoading();

            if (purchaseServerEvent?.message === 'Successfully processed charge') {
                this.$router.push({
                    name: 'PurchaseSuccessful',
                    params: { compact: this.currentCompactType }
                });
            } else if (purchaseServerEvent?.message) {
                this.isFormError = true;
                this.formErrorMessage = purchaseServerEvent?.message;
            }
        } else {
            this.isFormError = true;
            this.formErrorMessage = this.formValidationErrorMessage;
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
                name: 'SelectPrivileges',
                params: { compact: this.currentCompactType }
            });
        }
    }

    handleExpYearRefEmitted(inputData) {
        this.expYearRef = inputData.ref;
    }

    handleCVVRefEmitted(inputData) {
        this.cvvRef = inputData.ref;
    }

    togglePaymentCollapsed() {
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

    handleExpMonthInput(formInput) {
        // Remove all non-numerals
        formInput.value = formInput.value.replace(/[^\d]/g, '');

        if (formInput.value && formInput.value.length > 1 && this.expYearRef) {
            this.expYearRef.focus();
        }
    }

    handleExpYearInput(formInput) {
        // Remove all non-numerals
        formInput.value = formInput.value.replace(/[^\d]/g, '');

        if (formInput.value && formInput.value.length > 1 && this.cvvRef) {
            this.cvvRef.focus();
        }
    }

    handleCVVInput(formInput) {
        // Remove all non-numerals
        formInput.value = formInput.value.replace(/[^\d]/g, '');
    }

    handleZipInput(formInput) {
        // Remove all non-numerals
        formInput.value = formInput.value.replace(/[^\d]/g, '');
    }
}
