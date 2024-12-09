//
//  shims-vue-i18n.d.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 12/05/24.
//

import 'vue-i18n';

declare module '@vue/runtime-core' {
    interface ComponentCustomProperties {
        $t: (typeof import('vue-i18n'))['t'],
        $tm: (typeof import('vue-i18n'))['tm'],
        $i18n: (typeof import('vue-i18n'))['i18n'],
    }
}
