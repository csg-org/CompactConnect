//
//  envConfig.d.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

import { API } from './api.plugin';

declare module '@vue/runtime-core' {
    interface ComponentCustomProperties {
        $api: API
    }
}
