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
const context = process.env;

export interface EnvConfig {
    name?: string;
    isProduction?: boolean;
    isTest?: boolean;
    isDevelopment?: boolean;
    baseUrl?: string;
    domain?: string;
    apiUrlState?: string;
    apiUrlLicense?: string;
    apiUrlUser?: string;
    apiUrlExample?: string;
    apiKeyExample?: string;
    cognitoRegion?: string;
    cognitoAuthDomainStaff?: string;
    cognitoClientIdStaff?: string;
    cognitoAuthDomainLicensee?: string;
    cognitoClientIdLicensee?: string;
    isUsingMockApi?: boolean;
}

// @NOTE: Any custom keys in .env have to start with VUE_APP_ to be accessible at runtime
export const config: EnvConfig = {
    name: context.NODE_ENV,
    isProduction: (context.NODE_ENV === ENV_PRODUCTION),
    isTest: (context.NODE_ENV === ENV_TEST),
    isDevelopment: (context.NODE_ENV === ENV_DEVELOPMENT),
    baseUrl: context.BASE_URL,
    domain: context.VUE_APP_DOMAIN,
    apiUrlState: context.VUE_APP_API_STATE_ROOT,
    apiUrlLicense: context.VUE_APP_API_LICENSE_ROOT,
    apiUrlUser: context.VUE_APP_API_USER_ROOT,
    apiUrlExample: '/api',
    apiKeyExample: 'example',
    cognitoRegion: context.VUE_APP_COGNITO_REGION,
    cognitoAuthDomainStaff: context.VUE_APP_COGNITO_AUTH_DOMAIN_STAFF,
    cognitoClientIdStaff: context.VUE_APP_COGNITO_CLIENT_ID_STAFF,
    cognitoAuthDomainLicensee: context.VUE_APP_COGNITO_AUTH_DOMAIN_LICENSEE,
    cognitoClientIdLicensee: context.VUE_APP_COGNITO_CLIENT_ID_LICENSEE,
    isUsingMockApi: (context.VUE_APP_MOCK_API === 'true'),
};

export default {
    install: (app) => {
        app.config.globalProperties.$envConfig = config;
    },
};
