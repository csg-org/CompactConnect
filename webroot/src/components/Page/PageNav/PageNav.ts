//
//  PageNav.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/4/2020.
//

import { Component, Vue, toNative } from 'vue-facing-decorator';
import PageMainNav from '@components/Page/PageMainNav/PageMainNav.vue';

@Component({
    name: 'PageNav',
    components: {
        PageMainNav,
    }
})
class PageNav extends Vue {
}

export default toNative(PageNav);

// export { PageNav };
