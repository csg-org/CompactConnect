//
//  mockEnvConfig.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

import { EnvConfig } from '@plugins/EnvConfig/envConfig.plugin';

// ========================================================
// =                     ENV CONFIG                       =
// ========================================================
const mockEnvConfig: EnvConfig = {
    name: 'test',
    isProduction: false,
    isTest: true,
    isDevelopment: false,
    appEnv: 'local',
    isAppProduction: false,
    isAppBeta: false,
    isAppTest: false,
    isAppTestIa: false,
    isAppTestCsg: false,
    isAppLocal: true,
    baseUrl: '/',
    domain: 'localhost',
    origin: 'http://localhost',
    apiUrlState: '/',
    apiUrlLicense: '/',
    apiUrlSearch: '/',
    apiUrlUser: '/',
    apiUrlStateCosmo: '/',
    apiUrlLicenseCosmo: '/',
    apiUrlSearchCosmo: '/',
    apiUrlUserCosmo: '/',
    apiUrlStateSw: '/',
    apiUrlLicenseSw: '/',
    apiUrlSearchSw: '/',
    apiUrlUserSw: '/',
    apiUrlStatePsypact: '/',
    apiUrlLicensePsypact: '/',
    apiUrlSearchPsypact: '/',
    apiUrlUserPsypact: '/',
    apiUrlExample: '/api',
    apiKeyExample: 'example',
    cognitoRegion: 'us-east-1',
    cognitoAuthDomainStaff: '',
    cognitoClientIdStaff: '',
    cognitoAuthDomainLicensee: '',
    cognitoClientIdLicensee: '',
    cognitoAuthDomainStaffCosmo: '',
    cognitoClientIdStaffCosmo: '',
    cognitoAuthDomainStaffSw: '',
    cognitoClientIdStaffSw: '',
    cognitoAuthDomainStaffPsypact: '',
    cognitoClientIdStaffPsypact: '',
    cognitoAuthDomainLicenseePsypact: '',
    cognitoClientIdLicenseePsypact: '',
    recaptchaKey: '',
    statsigKey: '',
    isStatsigDisabled: true,
    isUsingMockApi: true,
};

export default mockEnvConfig;
