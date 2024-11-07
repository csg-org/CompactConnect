//
//  InputCreditCard.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/1/2024.
//
import {
    Component,
    mixins,
    toNative
} from 'vue-facing-decorator';
import MixinInput from '@components/Forms/_mixins/input.mixin';
import ShowPasswordEye from '@components/Icons/ShowPasswordEye/ShowPasswordEye.vue';
import HidePasswordEye from '@components/Icons/HidePasswordEye/HidePasswordEye.vue';

@Component({
    name: 'InputCreditCard',
    components: {
        ShowPasswordEye,
        HidePasswordEye
    }
})
class InputCreditCard extends mixins(MixinInput) {
    inputType = 'password';
    shouldMask = true;

    //
    // Methods
    //
    toggleMasking() {
        this.shouldMask = !this.shouldMask;
        this.inputType = (this.inputType === 'password') ? 'text' : 'password';
    }
}

export default toNative(InputCreditCard);
