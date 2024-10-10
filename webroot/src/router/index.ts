//
//  index.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

import { createRouter, createWebHistory, RouteLocationNormalized as Route } from 'vue-router';
import routes from '@router/routes';
import store from '@/store';
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
    const routeParamCompactType = to.params?.compact;

    // If the store does not have the requested compact, set it from the route (e.g. page refreshes)
    if (routeParamCompactType) {
        const { currentCompact } = store.getters['user/state'];

        if (!currentCompact || currentCompact.type !== routeParamCompactType) {
            store.dispatch('user/setCurrentCompact', CompactSerializer.fromServer({ type: routeParamCompactType }));
        }
    }

    // If the route requires auth, check first
    if (isAuthGuardedRoute) {
        const { isLoggedIn } = store.getters['user/state'];

        if (!isLoggedIn) {
            next({ name: 'Logout' });
        } else {
            next();
        }
    } else {
        next();
    }
});

export default router;
