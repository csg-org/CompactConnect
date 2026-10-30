//
//  _guards.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

import {
    // RouteLocationNormalized as Route,
    RouteLocationRaw as RouteConfig
} from 'vue-router';
import { config } from '@plugins/EnvConfig/envConfig.plugin';
import store from '@/store';

/**
 * Guard against entering auth-required route if not authenticated.
 */
const authGuard = (/* to: Route, from: Route */): void | boolean | RouteConfig => {
    const { isLoggedIn } = store.getters['user/state'];
    let action: any = false;

    if (isLoggedIn || config.isTest) {
        action = true;
    }

    return action;
};

/**
 * Guard against entering no-auth-required route if already authenticated.
 */
const noAuthGuard = (/* to: Route, from: Route */): Promise<void | boolean | RouteConfig> => {
    const { isLoggedIn } = store.getters['user/state'];
    const routeToIfAuthenticated: RouteConfig = { name: 'Home' };
    let action: any = true;

    if (isLoggedIn) {
        action = routeToIfAuthenticated;
    }

    return action;
};

/**
 * In-app login stays closed unless custom auth is enabled.
 * When it is enabled, logged-in visitors still follow the no-auth guard.
 */
const customAuthGuard = async (): Promise<void | boolean | RouteConfig> => {
    const dashboardRoute: RouteConfig = { name: 'DashboardPublic' };
    let action: void | boolean | RouteConfig = dashboardRoute;

    if (config.isCustomAuth) {
        action = await noAuthGuard();
    }

    return action;
};

export default {
    authGuard,
    noAuthGuard,
    customAuthGuard,
};
