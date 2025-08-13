//
//  shims-vue-responsiveness.d.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 8/8/25.
//

import 'vue-responsiveness';

declare module '@vue/runtime-core' {
    interface ComponentCustomProperties {
        $matches: (typeof import('vue-responsiveness'))['matches'],
    }
}
