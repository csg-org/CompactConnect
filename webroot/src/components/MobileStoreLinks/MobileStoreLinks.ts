//
//  MobileStoreLinks.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 9/4/2020.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

import { Component, Vue, toNative } from 'vue-facing-decorator';
import { mobileStoreLinks } from '@/app.config';

@Component
class MobileStoreLinks extends Vue {
    //
    // Computed
    //
    get appleStoreLink() {
        return mobileStoreLinks.APPLE_STORE_LINK;
    }

    get googleStoreLink() {
        return mobileStoreLinks.GOOGLE_STORE_LINK;
    }
}

export default toNative(MobileStoreLinks);

// export { MobileStoreLinks };
