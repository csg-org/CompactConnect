//
//  PageHeader.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/4/2020.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

import { Component, Vue, toNative } from 'vue-facing-decorator';
import PageNav from '@components/Page/PageNav/PageNav.vue';
import PageMainNav from '@components/Page/PageMainNav/PageMainNav.vue';

@Component({
    name: 'PageHeader',
    components: {
        PageNav,
        PageMainNav,
    }
})
class PageHeader extends Vue {
}

export default toNative(PageHeader);

// export { PageHeader };
