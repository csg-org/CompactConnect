//
//  shims-vuex.d.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/08/24.
//

import { Store } from 'vuex';

declare module '@vue/runtime-core' {
    interface ComponentCustomProperties {
        $store: Store<any> // @TODO: <any> might be able to use globalStore.state?
    }
}
