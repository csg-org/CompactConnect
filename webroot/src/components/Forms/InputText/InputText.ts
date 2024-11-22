//
//  InputText.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 6/15/2020.
//

import {
    Component,
    mixins,
    toNative
} from 'vue-facing-decorator';
import MixinInput from '@components/Forms/_mixins/input.mixin';

@Component({
    name: 'InputText',
    emits: [ 'emitInputRef' ]
})
class InputText extends mixins(MixinInput) {
    //
    // LifeCycle
    //
    mounted() {
        this.$emit('emitInputRef', { ref: this.$refs.input, inputId: this.formInput.id });
    }
}

export default toNative(InputText);

// export { InputText };
