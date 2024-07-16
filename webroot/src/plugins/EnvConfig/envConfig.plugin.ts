//
//  envConfig.plugin.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

// https://vuejs.org/v2/guide/plugins.html

//
// @NOTE: Any custom keys in .env have to start with VUE_APP.... to be recognized at runtime
//

const ENV_PRODUCTION = 'production';
const ENV_TEST = 'test';
const ENV_DEVELOPMENT = 'development';

export interface EnvConfig {
    name?: string;
    isProduction?: boolean;
    isTest?: boolean;
    isDevelopment?: boolean;
    baseUrl?: string;
    domain?: string;
    apiUrlState?: string;
    apiUrlExample?: string;
    apiKeyExample?: string;
    isUsingMockApi?: boolean;
}

// @NOTE: Any custom keys in .env have to start with VUE_APP_ to be accessible at runtime
export const config: EnvConfig = {
    name: process.env.NODE_ENV,
    isProduction: (process.env.NODE_ENV === ENV_PRODUCTION),
    isTest: (process.env.NODE_ENV === ENV_TEST),
    isDevelopment: (process.env.NODE_ENV === ENV_DEVELOPMENT),
    baseUrl: process.env.BASE_URL,
    domain: process.env.VUE_APP_DOMAIN,
    apiUrlState: process.env.VUE_APP_API_STATE_ROOT,
    apiUrlExample: '/api',
    apiKeyExample: 'example',
    isUsingMockApi: (process.env.VUE_APP_MOCK_API === 'true'),
};

export default {
    install: (app) => {
        app.config.globalProperties.$envConfig = config;
    },
};
