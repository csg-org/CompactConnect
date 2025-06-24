//
//  index.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

import { createRouter, createWebHistory, RouteLocationNormalized as Route } from 'vue-router';
import routes from '@router/routes';
import store from '@/store';
import { authStorage, AUTH_TYPE, AuthTypes } from '@/app.config';
import { CompactSerializer } from '@models/Compact/Compact.model';

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

    // If the store does not have the requested compact, set it from the route (e.g. page refreshes)
    if (routeParamCompactType) {
        const { currentCompact } = store.getters['user/state'];

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
    if (window.innerWidth < 770) {
        store.dispatch('collapseNavMenu');
    }
});

export default router;
