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
    // Methods
    //
    add(): void {
        const { formInput, $refs } = this;
        const emailInput = $refs.email as HTMLInputElement;
        const emailValue = emailInput.value.toLowerCase();
        const validation = Joi.string().email({ tlds: false }).messages({
            'string.empty': this.$t('inputErrors.email'),
            'string.email': this.$t('inputErrors.email'),
        }).validate(emailValue);

        if (validation.error) {
            formInput.errorMessage = validation.error.message;
            formInput.isValid = false;
        } else if (Array.isArray(formInput.value)) {
            if (!formInput.value.includes(emailValue)) {
                formInput.value.push(emailValue);
            }
            emailInput.value = '';
        }

        formInput.isTouched = true;
        formInput.validate();
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
    }
}

export default toNative(InputEmailList);

// export default InputEmailList;
