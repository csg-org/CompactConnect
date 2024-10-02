//
//  PageHeader.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/4/2020.
//

import { AuthTypes } from '@/app.config';
import { Component, Vue, toNative } from 'vue-facing-decorator';
import CompactSelector from '@components/CompactSelector/CompactSelector.vue';
import PageNav from '@components/Page/PageNav/PageNav.vue';
import PageMainNav from '@components/Page/PageMainNav/PageMainNav.vue';

@Component({
    name: 'PageHeader',
    components: {
        CompactSelector,
        PageNav,
        PageMainNav,
    }
})
class PageHeader extends Vue {
    //
    // Computed
    //
    get isStaffUser(): boolean {
        return this.$store.state.authType === AuthTypes.STAFF;
    }
}

export default toNative(PageHeader);

// export { PageHeader };
