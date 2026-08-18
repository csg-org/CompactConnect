//
//  apiUrls.ts
//  CompactConnect
//
//  Created by InspiringApps on 8/18/2026.
//

import { AppModes } from '@/app.config';
import { config as envConfig } from '@plugins/EnvConfig/envConfig.plugin';

export type ApiFamily = 'state' | 'license' | 'search' | 'user';

export const appModeApiUrls: Record<AppModes, Record<ApiFamily, string | undefined>> = {
    [AppModes.JCC]: {
        state: envConfig.apiUrlState,
        license: envConfig.apiUrlLicense,
        search: envConfig.apiUrlSearch,
        user: envConfig.apiUrlUser,
    },
    [AppModes.COSMETOLOGY]: {
        state: envConfig.apiUrlStateCosmo,
        license: envConfig.apiUrlLicenseCosmo,
        search: envConfig.apiUrlSearchCosmo,
        user: envConfig.apiUrlUserCosmo,
    },
    [AppModes.SOCIAL_WORK]: {
        state: envConfig.apiUrlStateSw,
        license: envConfig.apiUrlLicenseSw,
        search: envConfig.apiUrlSearchSw,
        user: envConfig.apiUrlUserSw,
    },
};

export const getApiBaseUrl = (
    appMode: AppModes | null | undefined,
    apiFamily: ApiFamily
): string | undefined =>
    appModeApiUrls[appMode as AppModes]?.[apiFamily]
    || appModeApiUrls[AppModes.JCC][apiFamily];
