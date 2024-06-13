//
//  ExampleMobileLinks.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/5/2021.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

import { Component, Vue, toNative } from 'vue-facing-decorator';
import Section from '@components/Section/Section.vue';
import MobileStoreLinks from '@components/MobileStoreLinks/MobileStoreLinks.vue';

@Component({
    name: 'ExampleMobileLinks',
    components: {
        Section,
        MobileStoreLinks,
    }
})
class ExampleMobileLinks extends Vue {
}

export default toNative(ExampleMobileLinks);

// export { ExampleMobileLinks };
