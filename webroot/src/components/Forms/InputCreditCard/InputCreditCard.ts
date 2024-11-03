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

@Component({
    name: 'InputCreditCard',
})
class InputCreditCard extends mixins(MixinInput) {
}

export default toNative(InputCreditCard);
