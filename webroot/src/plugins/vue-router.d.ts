//
//  envConfig.d.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/11/24.
//

import VueRouter, { Route } from 'vue-router';

declare module '@vue/runtime-core' {
    interface ComponentCustomProperties {
        $router: VueRouter,
        $route: Route
    }
}
