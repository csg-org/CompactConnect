//
//  app.config.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/27/21.
//
import { AppModes } from '@/app.config';
import { config as envConfig } from '@plugins/EnvConfig/envConfig.plugin';
import sessionStorage from '@store/session.storage';
import localStorage from '@store/local.storage';
import { v4 as uuidv4 } from 'uuid';
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
export const AUTH_CSRF_STATE = 'auth_csrf_state';
export const AUTH_PKCE_CODE_VERIFIER = 'auth_pkce_code_verifier';

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
};

// ===========================
// =       CSRF Tokens       =
// ===========================
export const createAuthCsrfState = (): string => {
    const state = uuidv4();

    sessionStorage.setItem(AUTH_CSRF_STATE, state); // Specifically using sessionStorage for CSRF tokens

    return state;
};

export const consumeAuthCsrfState = (): string | null => {
    const state = sessionStorage.getItem(AUTH_CSRF_STATE);

    sessionStorage.removeItem(AUTH_CSRF_STATE);

    return state;
};

// ============================
// =           PKCE           =
// ============================
const base64UrlEncode = (bytes: Uint8Array): string => {
    let binary = '';

    bytes.forEach((byte) => { binary += String.fromCharCode(byte); });

    return btoa(binary)
        .replace(/\+/g, '-')
        .replace(/\//g, '_')
        .replace(/=+$/, '');
};

const generatePkceCodeVerifier = (): string => {
    const randomBytes = new Uint8Array(32);

    crypto.getRandomValues(randomBytes);

    return base64UrlEncode(randomBytes);
};

const generatePkceCodeChallenge = async (codeVerifier: string): Promise<string> => {
    const data = new TextEncoder().encode(codeVerifier);
    const digest = await crypto.subtle.digest('SHA-256', data);

    return base64UrlEncode(new Uint8Array(digest));
};

export const createPkceChallenge = async (): Promise<string> => {
    const codeVerifier = generatePkceCodeVerifier();
    const codeChallenge = await generatePkceCodeChallenge(codeVerifier);

    sessionStorage.setItem(AUTH_PKCE_CODE_VERIFIER, codeVerifier); // Specifically using sessionStorage for PKCE

    return codeChallenge;
};

export const consumePkceCodeVerifier = (): string | null => {
    const codeVerifier = sessionStorage.getItem(AUTH_PKCE_CODE_VERIFIER);

    sessionStorage.removeItem(AUTH_PKCE_CODE_VERIFIER);

    return codeVerifier;
};

// ===========================
// =      OAuth Scopes       =
// ===========================
export const staffLoginScopes = 'email openid phone profile aws.cognito.signin.user.admin';
export const licenseeLoginScopes = 'email openid phone profile aws.cognito.signin.user.admin';

// ===========================
// =      Login URI Setup    =
// ===========================
export const getCognitoConfig = (appMode: AppModes, authType: AuthTypes): CognitoConfig => {
    const config: CognitoConfig = {
        scopes: '',
        clientId: '',
        authDomain: '',
    };

    switch (authType) {
    case AuthTypes.STAFF:
        config.scopes = staffLoginScopes;

        if (appMode === AppModes.JCC) {
            config.clientId = envConfig.cognitoClientIdStaff;
            config.authDomain = envConfig.cognitoAuthDomainStaff;
        } else if (appMode === AppModes.COSMETOLOGY) {
            config.clientId = envConfig.cognitoClientIdStaffCosmo;
            config.authDomain = envConfig.cognitoAuthDomainStaffCosmo;
        } else if (appMode === AppModes.SOCIAL_WORK) {
            config.clientId = envConfig.cognitoClientIdStaffSw;
            config.authDomain = envConfig.cognitoAuthDomainStaffSw;
        }

        break;
    case AuthTypes.LICENSEE:
        config.scopes = licenseeLoginScopes;
        config.clientId = envConfig.cognitoClientIdLicensee;
        config.authDomain = envConfig.cognitoAuthDomainLicensee;
        break;
    default:
        break;
    }

    return config;
};

export const getHostedLoginUri = (appMode: AppModes, authType: AuthTypes, hostedIdpPath = '/login', state = '', codeChallenge = ''): string => {
    const { domain } = envConfig;
    const {
        scopes,
        clientId,
        authDomain
    } = getCognitoConfig(appMode, authType);
    const getCallbackPath = () => {
        let userScopePath = ``;
        let compactScopePath = ``;

        switch (authType) {
        case AuthTypes.STAFF:
            userScopePath += `/staff`;
            break;
        case AuthTypes.LICENSEE:
            userScopePath += `/licensee`;
            break;
        default:
            break;
        }

        switch (appMode) {
        case AppModes.JCC:
            compactScopePath += `/jcc`;
            break;
        case AppModes.COSMETOLOGY:
            compactScopePath += `/cosmo`;
            break;
        case AppModes.SOCIAL_WORK:
            compactScopePath += `/socialwork`;
            break;
        default:
            break;
        }

        return `/auth/callback${userScopePath}${compactScopePath}`;
    };
    const loginUriQuery = [
        `?client_id=${clientId}`,
        `&response_type=code`,
        `&scope=${encodeURIComponent(scopes || '')}`,
        `&state=${encodeURIComponent(state)}`,
        `&code_challenge=${encodeURIComponent(codeChallenge)}`,
        `&code_challenge_method=S256`,
        `&redirect_uri=${encodeURIComponent(`${domain}${getCallbackPath()}`)}`,
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
    AUTH_CSRF_STATE,
    AUTH_PKCE_CODE_VERIFIER,
    AuthTypes,
    staffLoginScopes,
    licenseeLoginScopes,
    getCognitoConfig,
    getHostedLoginUri,
    createAuthCsrfState,
    consumeAuthCsrfState,
    createPkceChallenge,
    consumePkceCodeVerifier,
    autoLogoutConfig,
};
