//
//  index.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

import { createRouter, createWebHistory, RouteLocationNormalized as Route } from 'vue-router';
import routes from '@router/routes';
import store from '@/store';
import {
    AppModes,
    authStorage,
    AUTH_TYPE,
    AuthTypes
} from '@/app.config';
import { CompactType, CompactSerializer } from '@models/Compact/Compact.model';

const router = createRouter({
    history: createWebHistory(process.env.BASE_URL || '/'),
    routes,
    scrollBehavior: (to: Route, from: Route, savedPosition: any): any => new Promise((resolve) => {
        let whereTo: any = savedPosition || { top: 0 };

        if (to.hash) {
            whereTo = {
                el: to.hash,
                behavior: 'smooth',
            };
        }

        resolve(whereTo);
    }),
});

router.beforeEach(async (to, from, next) => {
    const isAuthGuardedRoute = to.matched.some((route) => route.meta.requiresAuth);
    const isLicenseeRoute = to.matched.some((route) => route.meta.licenseeAccess);
    const isStaffRoute = to.matched.some((route) => route.meta.staffAccess);
    const routeParamCompactType = to.params?.compact;

    if (routeParamCompactType) {
        const { appMode } = store.state;
        let expectedAppMode = AppModes.JCC;
        const { currentCompact } = store.getters['user/state'];

        // Update the app mode based on attempted compact route, if needed
        if (routeParamCompactType === CompactType.COSMETOLOGY) {
            expectedAppMode = AppModes.COSMETOLOGY;
        }

        if (!appMode || appMode !== expectedAppMode) {
            store.dispatch('setAppMode', expectedAppMode);
        }

        // If the store does not have the requested compact, set it from the route (e.g. page refreshes)
        if (!currentCompact || currentCompact.type !== routeParamCompactType) {
            await store.dispatch('user/setCurrentCompact', CompactSerializer.fromServer({ type: routeParamCompactType }));
        }
    }

    // If the route requires auth, check first
    if (isAuthGuardedRoute) {
        const { isLoggedIn } = store.getters['user/state'];

        if (!isLoggedIn) {
            if (to?.path) {
                next({ name: 'Logout', query: { goto: to.path }});
            } else {
                next({ name: 'Logout' });
            }
        } else if ((isLicenseeRoute && isStaffRoute)
        || (isLicenseeRoute && authStorage.getItem(AUTH_TYPE) === AuthTypes.LICENSEE)
        || (isStaffRoute && authStorage.getItem(AUTH_TYPE) === AuthTypes.STAFF)) {
            next();
        } else {
            next({ name: 'Home' });
        }
    } else {
        next();
    }
});

router.afterEach(() => {
    if (window.innerWidth < 770 || window.matchMedia('(hover: hover) and (pointer: fine)').matches) {
        store.dispatch('collapseNavMenu');
    }
});

export default router;
