//
//  app.config.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/27/21.
//
import { AppModes } from '@/app.config';
import { config as envConfig } from '@plugins/EnvConfig/envConfig.plugin';
import localStorage from '@store/local.storage';
import moment from 'moment';

// ====================
// =   Auth storage   =
// ====================
export const authStorage = localStorage;
export const tokens = {
    staff: {
        AUTH_TOKEN: 'auth_token_staff',
        AUTH_TOKEN_TYPE: 'auth_token_type_staff',
        AUTH_TOKEN_EXPIRY: 'auth_token_expiry_staff',
        ID_TOKEN: 'id_token_staff',
        REFRESH_TOKEN: 'refresh_token_staff',
    },
    licensee: {
        AUTH_TOKEN: 'auth_token_licensee',
        AUTH_TOKEN_TYPE: 'auth_token_type_licensee',
        AUTH_TOKEN_EXPIRY: 'auth_token_expiry_licensee',
        ID_TOKEN: 'id_token_licensee',
        REFRESH_TOKEN: 'refresh_token_licensee',
    },
};
export const AUTH_TYPE = 'auth_type';
export const AUTH_LOGIN_GOTO_PATH = 'login_goto';
export const AUTH_LOGIN_GOTO_PATH_AUTH_TYPE = 'login_goto_auth_type';
export const AUTH_LOGIN_GOTO_COMPACT = 'login_goto_compact';

// =========================
// =  Authorization Types  =
// =========================
export enum AuthTypes {
    STAFF = 'staff',
    LICENSEE = 'licensee',
    PUBLIC = 'public',
}

// ===========================
// =  Cognito Configuration  =
// ===========================
export type CognitoConfig = {
    scopes?: string;
    clientId?: string;
    authDomain?: string;
    state?: string;
};

export enum CognitoStateTypes {
    STAFF_JCC = 'staff',
    STAFF_COSMETOLOGY = 'staff-cosmo',
    STAFF_SOCIAL_WORK = 'staff-social-work',
    LICENSEE_JCC = 'licensee',
}

export const staffLoginScopes = 'email openid phone profile aws.cognito.signin.user.admin';
export const licenseeLoginScopes = 'email openid phone profile aws.cognito.signin.user.admin';
export const getCognitoConfig = (appMode: AppModes, authType: AuthTypes): CognitoConfig => {
    const config: CognitoConfig = {
        scopes: '',
        clientId: '',
        authDomain: '',
        state: '',
    };

    switch (authType) {
    case AuthTypes.STAFF:
        config.scopes = staffLoginScopes;

        if (appMode === AppModes.JCC) {
            config.state = CognitoStateTypes.STAFF_JCC;
            config.clientId = envConfig.cognitoClientIdStaff;
            config.authDomain = envConfig.cognitoAuthDomainStaff;
        } else if (appMode === AppModes.COSMETOLOGY) {
            config.state = CognitoStateTypes.STAFF_COSMETOLOGY;
            config.clientId = envConfig.cognitoClientIdStaffCosmo;
            config.authDomain = envConfig.cognitoAuthDomainStaffCosmo;
        } else if (appMode === AppModes.SOCIAL_WORK) {
            config.state = CognitoStateTypes.STAFF_SOCIAL_WORK;
            config.clientId = envConfig.cognitoClientIdStaffSw;
            config.authDomain = envConfig.cognitoAuthDomainStaffSw;
        }

        break;
    case AuthTypes.LICENSEE:
        config.scopes = licenseeLoginScopes;
        config.state = CognitoStateTypes.LICENSEE_JCC;
        config.clientId = envConfig.cognitoClientIdLicensee;
        config.authDomain = envConfig.cognitoAuthDomainLicensee;
        break;
    default:
        break;
    }

    return config;
};

export const getHostedLoginUri = (appMode: AppModes, authType: AuthTypes, hostedIdpPath = '/login'): string => {
    const { domain } = envConfig;
    const {
        scopes,
        clientId,
        authDomain,
        state
    } = getCognitoConfig(appMode, authType);
    const loginUriQuery = [
        `?client_id=${clientId}`,
        `&response_type=code`,
        `&scope=${encodeURIComponent(scopes || '')}`,
        `&state=${state}`,
        `&redirect_uri=${encodeURIComponent(`${domain}/auth/callback`)}`,
    ].join('');
    const loginUri = `${authDomain}${hostedIdpPath}${loginUriQuery}`;

    return loginUri;
};

// ====================
// =    Auto logout   =
// ====================
export const autoLogoutConfig = {
    INACTIVITY_TIMER_DEFAULT_MS: moment.duration(10, 'minutes').asMilliseconds(),
    INACTIVITY_TIMER_STAFF_MS: moment.duration(10, 'minutes').asMilliseconds(),
    INACTIVITY_TIMER_LICENSEE_MS: moment.duration(10, 'minutes').asMilliseconds(),
    GRACE_PERIOD_MS: moment.duration(30, 'seconds').asMilliseconds(),
    LOG: (message = '') => {
        const isEnabled = false; // Helper logging for auto-logout testing

        if (isEnabled) {
            console.log(`auto-logout: ${message}`);
        }
    },
};

export default {
    authStorage,
    tokens,
    AUTH_TYPE,
    AUTH_LOGIN_GOTO_PATH,
    AUTH_LOGIN_GOTO_PATH_AUTH_TYPE,
    AUTH_LOGIN_GOTO_COMPACT,
    AuthTypes,
    CognitoStateTypes,
    staffLoginScopes,
    licenseeLoginScopes,
    getCognitoConfig,
    getHostedLoginUri,
    autoLogoutConfig,
};
