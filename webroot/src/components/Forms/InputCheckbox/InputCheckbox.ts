//
//  InputCheckbox.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 1/22/2021.
//

import { Component, mixins, toNative } from 'vue-facing-decorator';
import MixinInput from '@components/Forms/_mixins/input.mixin';

@Component({
    name: 'InputCheckbox',
    emits: ['checked', 'unchecked']
})
class InputCheckbox extends mixins(MixinInput) {
    //
    // Computed
    //
    get isChecked(): boolean {
        return Boolean(this.formInput.value);
    }

    //
    // Methods
    //
    input(): void {
        if (this.isChecked) {
            this.$emit('checked');
        } else {
            this.$emit('unchecked');
        }
    }
}

export default toNative(InputCheckbox);

// export { InputCheckbox };
