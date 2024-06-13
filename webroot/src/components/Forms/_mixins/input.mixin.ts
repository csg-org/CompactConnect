//
//  input.mixin.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/21/2020.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

import {
    Component,
    Vue,
    Prop
} from 'vue-facing-decorator';
import { FormInput } from '@models/FormInput/FormInput.model';

@Component({
    name: 'MixinInput',
    emits: ['blur', 'input'],
})
class MixinInput extends Vue {
    @Prop({ required: true, default: new FormInput() }) formInput!: FormInput;

    //
    // Computed
    //
    get isRequired(): boolean {
        // @NOTE: This is dipping into Joi private API - here be dragons. If this becomes a hassle, we can just manually add the "*" to the labels for now.
        const { validation } = this.formInput;
        let isInputRequired = false;

        if (validation) {
            const { _rules: rules, _flags: flags } = validation;

            if ((flags as any)?.presence === 'required') {
                isInputRequired = true;
            } else if (Array.isArray(rules)) {
                (rules as any).forEach((rule) => {
                    switch (rule.name) {
                    case 'min':
                        isInputRequired = Boolean(rule.args?.limit);
                        break;
                    default:
                        break;
                    }
                });
            }
        }

        return isInputRequired;
    }

    get remainingCharacters(): number {
        const { value } = this.formInput;
        const valueLength = value?.length || 0;
        const maxLength = this.formInput.maxLength();
        let remaining = 0;

        if (maxLength >= 0 && valueLength < maxLength) {
            remaining = maxLength - valueLength;
        }

        return remaining;
    }

    //
    // Methods
    //
    blur(formInput: FormInput): void {
        this.formInput.blur();
        this.$emit('blur', formInput);
    }

    input(formInput: FormInput): void {
        this.formInput.input();
        this.$emit('input', formInput);
    }
}

// export default toNative(MixinInput);

export default MixinInput;
