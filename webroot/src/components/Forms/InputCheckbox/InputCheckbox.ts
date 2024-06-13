//
//  InputCheckbox.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 1/22/2021.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

import { Component, mixins, toNative } from 'vue-facing-decorator';
import MixinInput from '@components/Forms/_mixins/input.mixin';

@Component({
    name: 'InputCheckbox',
})
class InputCheckbox extends mixins(MixinInput) {
    //
    // Computed
    //
    get isChecked(): boolean {
        return Boolean(this.formInput.value);
    }
}

export default toNative(InputCheckbox);

// export { InputCheckbox };
