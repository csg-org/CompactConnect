//
//  index.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

import { createRouter, createWebHistory, RouteLocationNormalized as Route } from 'vue-router';
import routes from '@router/routes';
import store from '@/store';

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
