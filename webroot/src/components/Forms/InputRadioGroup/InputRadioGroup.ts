//
//  InputRadioGroup.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/12/2024.
//

import {
    Component,
    mixins,
    Prop,
    toNative
} from 'vue-facing-decorator';
import MixinInput from '@components/Forms/_mixins/input.mixin';

@Component({
    name: 'InputRadioGroup',
})
class InputRadioGroup extends mixins(MixinInput) {
    @Prop({ default: false }) isGroupHorizontal?: boolean;

    //
    // Methods
    //
    isButtonChecked(value: string): boolean {
        let checked = false;

        if (this.formInput.value === value) {
            checked = true;
        }

        return checked;
    }
}

export default toNative(InputRadioGroup);

// export { InputRadioGroup };
