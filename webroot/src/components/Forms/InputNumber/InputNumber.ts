//
//  InputNumber.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/31/2024.
//

import {
    Component,
    mixins,
    toNative
} from 'vue-facing-decorator';
import MixinInput from '@components/Forms/_mixins/input.mixin';

@Component({
    name: 'InputNumber',
})
class InputNumber extends mixins(MixinInput) {
    //
    // LifeCycle
    //
    mounted() {
        this.$emit('emitInputRef', { ref: this.$refs.numberInput, inputId: this.formInput.id });
    }
}

export default toNative(InputNumber);

// export default InputNumber;
