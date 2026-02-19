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

// Build environments (Node)
const ENV_PRODUCTION = 'production';
const ENV_TEST = 'test';
const ENV_DEVELOPMENT = 'development';

// App environments
export const appEnvironments = {
    APP_PRODUCTION: 'production',
    APP_BETA: 'beta',
    APP_TEST_IA: 'ia-test',
    APP_TEST_CSG: 'csg-test',
    APP_LOCAL: 'local',
};

const context = process.env;

export interface EnvConfig {
    name?: string;
    isProduction?: boolean;
    isTest?: boolean;
    isDevelopment?: boolean;
    appEnv?: string;
    isAppProduction?: boolean;
    isAppBeta?: boolean;
    isAppTest?: boolean;
    isAppTestIa?: boolean;
    isAppTestCsg?: boolean;
    isAppLocal?: boolean;
    baseUrl?: string;
    domain?: string;
    apiUrlState?: string;
    apiUrlLicense?: string;
    apiUrlSearch?: string;
    apiUrlUser?: string;
    apiUrlStateCosmo?: string;
    apiUrlLicenseCosmo?: string;
    apiUrlSearchCosmo?: string;
    apiUrlUserCosmo?: string;
    apiUrlExample?: string;
    apiKeyExample?: string;
    cognitoRegion?: string;
    cognitoAuthDomainStaff?: string;
    cognitoClientIdStaff?: string;
    cognitoAuthDomainLicensee?: string;
    cognitoClientIdLicensee?: string;
    cognitoAuthDomainStaffCosmo?: string;
    cognitoClientIdStaffCosmo?: string;
    recaptchaKey?: string;
    statsigKey?: string;
    isStatsigDisabled?: boolean;
    isUsingMockApi?: boolean;
}

// @NOTE: Any custom keys in .env have to start with VUE_APP_ to be accessible at runtime
export const config: EnvConfig = {
    name: context.NODE_ENV,
    isProduction: (context.NODE_ENV === ENV_PRODUCTION),
    isTest: (context.NODE_ENV === ENV_TEST),
    isDevelopment: (context.NODE_ENV === ENV_DEVELOPMENT),
    appEnv: context.VUE_APP_ENV,
    isAppProduction: (context.VUE_APP_ENV === appEnvironments.APP_PRODUCTION),
    isAppBeta: (context.VUE_APP_ENV === appEnvironments.APP_BETA),
    isAppTest: (context.VUE_APP_ENV === appEnvironments.APP_TEST_IA
        || context.VUE_APP_ENV === appEnvironments.APP_TEST_CSG),
    isAppTestIa: (context.VUE_APP_ENV === appEnvironments.APP_TEST_IA),
    isAppTestCsg: (context.VUE_APP_ENV === appEnvironments.APP_TEST_CSG),
    isAppLocal: (context.VUE_APP_ENV === appEnvironments.APP_LOCAL),
    baseUrl: context.BASE_URL,
    domain: context.VUE_APP_DOMAIN,
    apiUrlState: context.VUE_APP_API_STATE_ROOT,
    apiUrlLicense: context.VUE_APP_API_LICENSE_ROOT,
    apiUrlSearch: context.VUE_APP_API_SEARCH_ROOT,
    apiUrlUser: context.VUE_APP_API_USER_ROOT,
    apiUrlStateCosmo: context.VUE_APP_API_STATE_ROOT_COSMO,
    apiUrlLicenseCosmo: context.VUE_APP_API_LICENSE_ROOT_COSMO,
    apiUrlSearchCosmo: context.VUE_APP_API_SEARCH_ROOT_COSMO,
    apiUrlUserCosmo: context.VUE_APP_API_USER_ROOT_COSMO,
    apiUrlExample: '/api',
    apiKeyExample: 'example',
    cognitoRegion: context.VUE_APP_COGNITO_REGION,
    cognitoAuthDomainStaff: context.VUE_APP_COGNITO_AUTH_DOMAIN_STAFF,
    cognitoClientIdStaff: context.VUE_APP_COGNITO_CLIENT_ID_STAFF,
    cognitoAuthDomainLicensee: context.VUE_APP_COGNITO_AUTH_DOMAIN_LICENSEE,
    cognitoClientIdLicensee: context.VUE_APP_COGNITO_CLIENT_ID_LICENSEE,
    cognitoAuthDomainStaffCosmo: context.VUE_APP_COGNITO_AUTH_DOMAIN_STAFF_COSMO,
    cognitoClientIdStaffCosmo: context.VUE_APP_COGNITO_CLIENT_ID_STAFF_COSMO,
    recaptchaKey: context.VUE_APP_RECAPTCHA_KEY,
    statsigKey: context.VUE_APP_STATSIG_KEY,
    isStatsigDisabled: (context.VUE_APP_STATSIG_DISABLED === 'true'),
    isUsingMockApi: (context.VUE_APP_MOCK_API === 'true'),
};

export default {
    install: (app) => {
        app.config.globalProperties.$envConfig = config;
    },
};
