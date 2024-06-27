//
//  Search.mixin.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 6/18/2020.
//

import {
    Component,
    Vue,
    Watch,
    toNative
} from 'vue-facing-decorator';
import { FormInput } from '@/models/FormInput/FormInput.model';

@Component({
    name: 'Search'
})
class MixinSearch extends Vue {
    //
    // Data
    //
    searchTerm = '';
    search = new FormInput();

    //
    // Watch
    //
    @Watch('search.value') updateSearchTerm() {
        this.searchTerm = this.search.value;
    }
}

export default toNative(MixinSearch);

// export { MixinSearch };
