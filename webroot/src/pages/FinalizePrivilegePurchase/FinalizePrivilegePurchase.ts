//
//  FinalizePrivilegePurchase.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/28/2024.
//

import { Component, mixins } from 'vue-facing-decorator';
import { reactive } from 'vue';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import InputText from '@components/Forms/InputText/InputText.vue';
import InputSelect from '@components/Forms/InputSelect/InputSelect.vue';
import InputCheckbox from '@components/Forms/InputCheckbox/InputCheckbox.vue';
// import InputDate from '@components/Forms/InputDate/InputDate.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import { FormInput } from '@models/FormInput/FormInput.model';

@Component({
    name: 'FinalizePrivilegePurchase',
    components: {
        InputText,
        InputSelect,
        InputCheckbox,
        InputSubmit,
        InputButton
    }
})
export default class FinalizePrivilegePurchase extends mixins(MixinForm) {
    //
    // Data
    //
    created() {
        this.initFormInputs();
    }

    //
    // Lifecycle
    //

    //
    // Computed
    //
    get nameInputLabel(): string {
        return this.$t('common.compact');
    }

    get namePlaceHolderText(): string {
        return this.$t('common.compact');
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

    //
    // Methods
    //
    handleSubmit() {
        console.log('submitted');
    }

    initFormInputs() {
        this.formData = reactive({
            compact: new FormInput({
                id: 'name',
                name: 'name',
                label: this.nameInputLabel,
                shouldHideLabel: false,
                shouldHideMargin: true,
                placeholder: this.namePlaceHolderText,
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
