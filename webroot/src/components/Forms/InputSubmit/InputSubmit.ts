//
//  InputSubmit.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/22/2020.
//

import {
    Component,
    Prop,
    mixins,
    toNative
} from 'vue-facing-decorator';
import MixinInput from '@components/Forms/_mixins/input.mixin';

@Component({
    name: 'InputSubmit',
})
class InputSubmit extends mixins(MixinInput) {
    @Prop({ default: '' }) private label?: string;
    @Prop({ default: true }) private isEnabled?: boolean;
}

export default toNative(InputSubmit);

// export { InputSubmit };
