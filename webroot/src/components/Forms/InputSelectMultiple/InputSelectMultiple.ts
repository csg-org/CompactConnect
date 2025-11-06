//
//  InputSelectMultiple.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/2/2025.
//

import {
    Component,
    mixins,
    toNative
} from 'vue-facing-decorator';
import { ComputedRef } from 'vue';
import MixinInput from '@components/Forms/_mixins/input.mixin';
import CloseXIcon from '@components/Icons/CloseX/CloseX.vue';

interface SelectOption {
    value: string | number;
    name: string | ComputedRef<string>;
}

@Component({
    name: 'InputSelectMultiple',
    components: {
        CloseXIcon,
    },
})
class InputSelectMultiple extends mixins(MixinInput) {
    //
    // Methods
    //
    getValueDisplay(value = ''): string | ComputedRef<string> {
        const selectedOption: SelectOption = this.formInput?.valueOptions?.find((option: SelectOption) =>
            option.value === value) || { value, name: '' };

        return selectedOption?.name || '';
    }

    removeSelectedValue(value): void {
        const { formInput } = this;

        if (Array.isArray(formInput.value)) {
            (formInput.value as Array<string>) = formInput.value.filter((selected) => selected !== value);
        }

        formInput.validate();
    }
}

export default toNative(InputSelectMultiple);

// export default InputSelectMultiple;
