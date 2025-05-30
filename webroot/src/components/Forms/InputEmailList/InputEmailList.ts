//
//  InputEmailList.ts
//  CompactConnect
//
//  Created by InspiringApps on 5/13/2025.
//

import { Component, mixins, toNative } from 'vue-facing-decorator';
import MixinInput from '@components/Forms/_mixins/input.mixin';
import CloseXIcon from '@components/Icons/CloseX/CloseX.vue';
import Joi from 'joi';

@Component({
    name: 'InputEmailList',
    components: {
        CloseXIcon,
    },
})
class InputEmailList extends mixins(MixinInput) {
    //
    // Data
    //
    inputValue = '';

    //
    // Computed
    //
    get shouldDisplayAddEmailHelp(): boolean {
        return this.inputValue.length > 0;
    }

    //
    // Methods
    //
    validateInputValue(): void {
        const { formInput, inputValue } = this;

        if (formInput.isTouched) {
            const emailValue = inputValue.toLowerCase();
            const validation = Joi.string().email({ tlds: false }).messages({
                'string.empty': this.$t('inputErrors.email'),
                'string.email': this.$t('inputErrors.email'),
            }).validate(emailValue);

            if (validation.error) {
                formInput.errorMessage = validation.error.message;
            } else {
                formInput.errorMessage = '';
            }
        }
    }

    input(): void {
        this.validateInputValue();
    }

    add(): void {
        const { formInput, inputValue, $refs } = this;
        const emailInput = $refs.email as HTMLInputElement;
        const emailValue = inputValue.toLowerCase();

        formInput.isTouched = true;
        this.validateInputValue();

        if (!formInput.errorMessage && Array.isArray(formInput.value)) {
            if (!formInput.value.includes(emailValue)) {
                formInput.value.push(emailValue);
            }
            this.inputValue = '';
            formInput.validate();
            formInput.isTouched = false;
        }

        emailInput.focus();
    }

    remove(emailToRemove): void {
        const { formInput, $refs } = this;
        const emailInput = $refs.email as HTMLInputElement;

        if (Array.isArray(formInput.value)) {
            (formInput.value as Array<string>) = formInput.value.filter((email) => email !== emailToRemove);
        }

        formInput.isTouched = true;
        formInput.validate();
        emailInput.focus();
        formInput.isTouched = false;
    }
}

export default toNative(InputEmailList);

// export default InputEmailList;
