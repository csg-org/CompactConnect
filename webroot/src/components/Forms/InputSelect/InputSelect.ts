//
//  InputSelect.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/28/2020.
//

import {
    Component,
    mixins,
    toNative
} from 'vue-facing-decorator';
import MixinInput from '@components/Forms/_mixins/input.mixin';
import InputLabel from '@components/Forms/InputLabel/InputLabel.vue';

@Component({
    name: 'InputSelect',
    components: {
        InputLabel,
    },
})
class InputSelect extends mixins(MixinInput) {
}

export default toNative(InputSelect);

// export { InputSelect };
