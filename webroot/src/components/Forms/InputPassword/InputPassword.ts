//
//  InputPassword.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/22/2020.
//

import {
    Component,
    mixins,
    Prop,
    toNative
} from 'vue-facing-decorator';
import MixinInput from '@components/Forms/_mixins/input.mixin';
import ShowPasswordEye from '@components/Icons/ShowPasswordEye/ShowPasswordEye.vue';
import HidePasswordEye from '@components/Icons/HidePasswordEye/HidePasswordEye.vue';

@Component({
    name: 'InputPassword',
    components: {
        ShowPasswordEye,
        HidePasswordEye
    }
})
class InputPassword extends mixins(MixinInput) {
    @Prop({ required: true }) joiMessages!: any;
    @Prop({ default: false }) showEyeIcon?: boolean;
    @Prop({ default: true }) showRequirements?: boolean;

    //
    // Data
    //
    inputType = 'password';
    shouldHidePassword = true;

    //
    // Computed
    //
    get passwordRequirements(): Array<any> {
        // @NOTE: This is dipping into Joi private API - here be dragons. If this becomes a hassle, we can just manually add the "*" to the labels for now.
        const { validation } = this.formInput;
        const inputValue = this.formInput.value;
        const requirements: any = [];

        if (validation) {
            const { _rules: rules } = validation;
            const validationResults = (validation as any).validate(inputValue, { abortEarly: false });
            const validationErrors = validationResults?.error?.details || [];

            if (Array.isArray(rules)) {
                (rules as any).forEach((rule) => {
                    const { name, args } = rule;
                    const { limit = 0, min = 0 } = args || {};
                    let ruleDesc = this.joiMessages.string[`string.${name}`] || this.joiMessages.password[`password.${name}`];
                    let ruleEval = false;

                    ruleDesc = ruleDesc
                        .replace(/{#limit}/g, limit)
                        .replace(/{#min}/g, min);

                    if (inputValue) {
                        const matchValidationError = validationErrors.find((error) => error.message === ruleDesc);

                        if (!matchValidationError) {
                            ruleEval = true;
                        }
                    }

                    if (limit === 1 || min === 1) {
                        ruleDesc = ruleDesc
                            .replace(/characters$/, 'character')
                            .replace(/numbers$/, 'number');
                    }

                    requirements.push({
                        description: ruleDesc,
                        isValid: ruleEval,
                    });
                });
            }
        }

        return requirements;
    }

    //
    // Methods
    //
    togglePassword() {
        this.shouldHidePassword = !this.shouldHidePassword;
        this.inputType = (this.inputType === 'password') ? 'text' : 'password';
    }
}

export default toNative(InputPassword);

// export { InputPassword };
