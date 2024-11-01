//
//  FinalizePrivilegePurchase.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/28/2024.
//

import { Component, mixins } from 'vue-facing-decorator';
import { reactive, computed } from 'vue';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import InputText from '@components/Forms/InputText/InputText.vue';
import InputNumber from '@components/Forms/InputNumber/InputNumber.vue';
import InputSelect from '@components/Forms/InputSelect/InputSelect.vue';
import InputCheckbox from '@components/Forms/InputCheckbox/InputCheckbox.vue';
// import InputDate from '@components/Forms/InputDate/InputDate.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import { FormInput } from '@models/FormInput/FormInput.model';
import Joi from 'joi';

@Component({
    name: 'FinalizePrivilegePurchase',
    components: {
        InputText,
        InputSelect,
        InputCheckbox,
        InputSubmit,
        InputNumber,
        InputButton
    }
})
export default class FinalizePrivilegePurchase extends mixins(MixinForm) {
    //
    // Lifecycle
    //
    created() {
        this.initFormInputs();
    }

    //
    // Computed
    //
    get firstNameInputLabel(): string {
        return this.$t('common.firstname');
    }

    get firstNamePlaceHolderText(): string {
        return this.$t('licensing.firstNameOnCard');
    }

    get lastNameInputLabel(): string {
        return this.$t('common.lastname');
    }

    get lastNamePlaceHolderText(): string {
        return this.$t('licensing.lastNameOnCard');
    }

    get isDesktop(): boolean {
        return this.$matches.desktop.min;
    }

    get isMobile(): boolean {
        return !this.isDesktop;
    }

    get cancelText(): string {
        return this.$t('common.cancel');
    }

    get backText(): string {
        return this.$t('common.back');
    }

    get submitLabel(): string {
        return this.$t('licensing.completePurchase');
    }

    get paymentTitleText(): string {
        return this.$t('licensing.payment');
    }

    get noRefundsAcknowledgement(): string {
        return this.$t('licensing.noRefundsMessage');
    }

    get cardNumberText(): string {
        return this.$t('licensing.noRefundsMessage');
    }

    get streetAddress1Label(): string {
        return this.$t('licensing.streetAddress');
    }

    get streetAddress1PlaceHolderText(): string {
        return this.$t('licensing.enterStreetAddress');
    }

    get streetAddress2Label(): string {
        return this.$t('licensing.streetAddress2');
    }

    get streetAddress2PlaceHolderText(): string {
        return this.$t('licensing.apptUnitNumber');
    }

    get creditCardTitleText(): string {
        return this.$t('licensing.creditCardTitle');
    }

    get billingAddressTitleText(): string {
        return this.$t('licensing.billingAddressTitle');
    }

    get stateText(): string {
        return this.$t('common.state');
    }

    get stateOptions() {
        const stateOptions = [{ value: '', name: 'select' }];

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

    //
    // Methods
    //
    handleSubmit() {
        console.log('submitted');
    }

    initFormInputs() {
        this.formData = reactive({
            firstName: new FormInput({
                id: 'first-name',
                name: 'first-name',
                label: this.firstNameInputLabel,
                shouldHideLabel: false,
                shouldHideMargin: true,
                placeholder: this.firstNamePlaceHolderText,
                value: '',
            }),
            lastName: new FormInput({
                id: 'last-name',
                name: 'last-name',
                label: this.lastNameInputLabel,
                shouldHideLabel: false,
                shouldHideMargin: true,
                placeholder: this.lastNamePlaceHolderText,
                value: '',
            }),
            streetAddress1: new FormInput({
                id: 'street-address-1',
                name: 'street-address-1',
                label: this.streetAddress1Label,
                shouldHideLabel: false,
                shouldHideMargin: true,
                placeholder: this.streetAddress1PlaceHolderText,
                value: '',
            }),
            streetAddress2: new FormInput({
                id: 'street-address-2',
                name: 'street-address-2',
                label: this.streetAddress2Label,
                shouldHideLabel: false,
                shouldHideMargin: true,
                placeholder: this.streetAddress2PlaceHolderText,
                value: '',
            }),
            noRefunds: new FormInput({
                id: 'no-refunds-check',
                name: 'no-refunds-check',
                label: this.noRefundsAcknowledgement,
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
                validation: Joi.string().regex(new RegExp('(^[0-9]{5}$)|(^[0-9]{5}-[0-9]{4}$)')),
                value: '',
            }),
            submit: new FormInput({
                isSubmitInput: true,
                id: 'submit',
            }),
        });
    }

    handleCancelClicked() {
        console.log('cancel');
    }

    handleBackClicked() {
        console.log('back');
    }
}
