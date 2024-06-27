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
import localStorage, { AUTH_TOKEN } from '@store/local.storage';

/**
 * Guard against entering auth-required route if not authenticated.
 */
const authGuard = (/* to: Route, from: Route */): void | boolean | RouteConfig => {
    let action: any = false;

    //
    // @TODO: Create app-specific auth rules
    //
    if (config.isUsingMockApi) {
        if (localStorage.getItem(AUTH_TOKEN) || config.isTest) {
            action = true;
        }
    } else {
        action = true;
    }

    return action;
};

/**
 * Guard against entering no-auth-required route if already authenticated.
 */
const noAuthGuard = async (/* to: Route, from: Route */): Promise<void | boolean | RouteConfig> => {
    //
    // @TODO: Create app-specific no-auth rules
    //
    const routeToIfAuthenticated: RouteConfig = { name: 'Home' };
    let action: any = true;

    if (config.isUsingMockApi && (localStorage.getItem(AUTH_TOKEN))) {
        action = routeToIfAuthenticated;
    }

    return action;
};

export default {
    authGuard,
    noAuthGuard,
};
