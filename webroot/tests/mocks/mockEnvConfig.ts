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
    apiUrlStateDiet: '/',
    apiUrlLicenseDiet: '/',
    apiUrlSearchDiet: '/',
    apiUrlUserDiet: '/',
    apiUrlExample: '/api',
    apiKeyExample: 'example',
    cognitoRegion: 'us-east-1',
    cognitoAuthDomainStaff: '',
    cognitoClientIdStaff: '',
    cognitoUserPoolIdStaff: '',
    cognitoAuthDomainLicensee: '',
    cognitoClientIdLicensee: '',
    cognitoUserPoolIdLicensee: '',
    cognitoAuthDomainStaffCosmo: '',
    cognitoClientIdStaffCosmo: '',
    cognitoUserPoolIdStaffCosmo: '',
    cognitoAuthDomainStaffSw: '',
    cognitoClientIdStaffSw: '',
    cognitoUserPoolIdStaffSw: '',
    cognitoAuthDomainStaffPsypact: '',
    cognitoClientIdStaffPsypact: '',
    cognitoUserPoolIdStaffPsypact: '',
    cognitoAuthDomainLicenseePsypact: '',
    cognitoClientIdLicenseePsypact: '',
    cognitoUserPoolIdLicenseePsypact: '',
    cognitoAuthDomainStaffDiet: '',
    cognitoClientIdStaffDiet: '',
    cognitoAuthDomainLicenseeDiet: '',
    cognitoClientIdLicenseeDiet: '',
    recaptchaKey: '',
    statsigKey: '',
    isStatsigDisabled: true,
    isUsingMockApi: true,
    isCustomAuth: false,
};

export default mockEnvConfig;
