//
//  routes.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

import { RouteRecordRaw as RouteConfig } from 'vue-router';

// The route array
const routes: Array<RouteConfig> = [
    // {
    //     path: '/',
    //     redirect: '/'
    // },
    {
        path: '/',
        name: 'Home',
        component: () => import(/* webpackChunkName: "home" */ '@pages/Home/Home.vue'),
    },
    {
        path: '/Licensing',
        name: 'Licensing',
        component: () => import(/* webpackChunkName: "licensing" */ '@pages/LicensingList/LicensingList.vue'),
    },
    {
        path: '/styleguide',
        name: 'StyleGuide',
        component: () => import(/* webpackChunkName: "styleGuide" */ '@pages/StyleGuide/StyleGuide.vue'),
    },
    //
    // KEEP "*" path AT THE BOTTOM OF THIS ARRAY
    //
    {
        path: '/:pathMatch(.*)*',
        name: '404',
        component: () => import(/* webpackChunkName: "login" */ '@pages/404/404.vue'),
    },
];

export default routes;
