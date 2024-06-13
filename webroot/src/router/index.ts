//
//  index.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

import { getCurrentInstance } from 'vue';
import { createRouter, createWebHistory, RouteLocationNormalized as Route } from 'vue-router';
import { config } from '@plugins/EnvConfig/envConfig.plugin';
import localStorage, { AUTH_TOKEN, AUTH_LOGIN_GOTO_PATH } from '@store/local.storage';
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
    const logout = () => {
        localStorage.setItem(AUTH_LOGIN_GOTO_PATH, to.fullPath); // Store the intended path; will be used to re-route the user after login.
        store.dispatch('user/logoutRequest');
        next({ path: '/Login' });
    };

    if (isAuthGuardedRoute) {
        if (config.isUsingMockApi) {
            if (!localStorage.getItem(AUTH_TOKEN)) {
                logout();
            } else {
                next();
            }
        } else if (!(await getCurrentInstance()?.appContext.app.config.globalProperties.$auth.isAuthenticated())) {
            logout();
        } else {
            next();
        }
    } else {
        next();
    }
});

export default router;
