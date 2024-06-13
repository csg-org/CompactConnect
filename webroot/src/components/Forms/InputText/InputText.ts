//
//  InputText.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 6/15/2020.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

import {
    Component,
    mixins,
    toNative
} from 'vue-facing-decorator';
import MixinInput from '@components/Forms/_mixins/input.mixin';

@Component({
    name: 'InputText',
})
class InputText extends mixins(MixinInput) {
}

export default toNative(InputText);

// export { InputText };
