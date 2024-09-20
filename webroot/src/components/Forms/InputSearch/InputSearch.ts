//
//  InputSearch.ts
//  CompactConnect
//
//  Created by InspiringApps on 9/11/2024.
//

import { Component, mixins, toNative } from 'vue-facing-decorator';
import MixinInput from '@components/Forms/_mixins/input.mixin';
import SearchIcon from '@components/Icons/Search/Search.vue';

@Component({
    name: 'InputSearch',
    components: {
        SearchIcon,
    },
})
class InputSearch extends mixins(MixinInput) {
}

export default toNative(InputSearch);

// export default InputSearch;
