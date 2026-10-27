//
//  cognitoAuth.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/22/2026.
//

import { Amplify } from 'aws-amplify';
import {
    confirmResetPassword,
    confirmSignIn,
    resetPassword,
    signIn,
    type SignInOutput
} from 'aws-amplify/auth';
import { cognitoUserPoolsTokenProvider } from 'aws-amplify/auth/cognito';
import { AppModes } from '@/app.config';
import { AuthTypes, getCognitoConfig } from '@utils/auth';
import axios from 'axios';

// Cognito's maximum authentication-flow session. Managed login ignores this and
// uses 3 minutes for MFA. User-pool API auth (SRP) honors AuthSessionValidity.
export const AUTH_SESSION_MINUTES = 15;
export const AUTH_SESSION_MS = AUTH_SESSION_MINUTES * 60 * 1000;

export enum CognitoAuthStep {
    LOGIN = 'login',
    NEW_PASSWORD = 'new-password',
    MFA_SETUP = 'mfa-setup',
    MFA_CODE = 'mfa-code',
    FORGOT_PASSWORD = 'forgot-password',
    FORGOT_PASSWORD_CONFIRM = 'forgot-password-confirm',
    DONE = 'done',
}

export type OAuthTokenResponse = {
    access_token: string; // eslint-disable-line camelcase
    id_token: string; // eslint-disable-line camelcase
    refresh_token: string; // eslint-disable-line camelcase
    token_type: string; // eslint-disable-line camelcase
    expires_in: number; // eslint-disable-line camelcase
};

export type CognitoAuthResult = {
    step?: CognitoAuthStep;
    messageKey?: string;
    totpSecret?: string;
    totpSetupUri?: string;
    mfaSetupExpiresAt?: number;
    tokenResponse?: OAuthTokenResponse;
};

export type MappedAuthError = {
    messageKey: string;
    step?: CognitoAuthStep;
};

type CognitoErrorShape = {
    name?: string;
    message?: string;
};

// Grouped so tests can stub these Amplify client methods.
export const amplifyAuthClient = {
    signIn,
    confirmSignIn,
    resetPassword,
    confirmResetPassword,
};

const poolIdCache: Record<string, string> = {};
let pendingUsername = '';
let pendingMissingAttributes: string[] = [];
let configuredKey = '';

export const mfaSetupDeadline = (fromMs = Date.now()): number => fromMs + AUTH_SESSION_MS;

export const formatAuthCountdown = (remainingMs: number): string => {
    const safeMs = Math.max(remainingMs, 0);
    const totalSeconds = Math.floor(safeMs / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    const paddedSeconds = String(seconds).padStart(2, '0');

    return `${minutes}:${paddedSeconds}`;
};

export const getTotpIssuer = (appMode: AppModes): string => {
    let issuer = 'CompactConnect';

    if (appMode === AppModes.PSYPACT) {
        issuer = 'PSYPACT';
    }

    return issuer;
};

export const parseUserPoolId = (issuer: string): string => {
    const parts = (issuer || '').split('/').filter((part) => part);
    const poolId = parts[parts.length - 1] || '';
    const isPoolId = /^[a-z]{2}-[a-z]+-\d_[A-Za-z0-9]+$/.test(poolId);
    let result = '';

    if (isPoolId) {
        result = poolId;
    }

    return result;
};

export const toOAuthTokenResponse = (
    accessToken: string,
    idToken: string,
    refreshToken: string,
    expiresAtSeconds?: number
): OAuthTokenResponse => {
    const nowSeconds = Math.floor(Date.now() / 1000);
    let expiresIn = 300;

    if (typeof expiresAtSeconds === 'number') {
        expiresIn = Math.max(expiresAtSeconds - nowSeconds, 0);
    }

    return {
        access_token: accessToken,
        id_token: idToken,
        refresh_token: refreshToken,
        token_type: 'Bearer',
        expires_in: expiresIn,
    };
};

const readError = (error: unknown): CognitoErrorShape => {
    const err = (error || {}) as CognitoErrorShape;

    return {
        name: err.name || '',
        message: err.message || '',
    };
};

export const mapCognitoAuthError = (error: unknown): MappedAuthError => {
    const { name, message } = readError(error);
    const errorName = name || '';
    const errorMessage = message || '';
    const isSessionExpired = errorName === 'NotAuthorizedException' && /session/i.test(errorMessage);
    let messageKey = 'auth.genericError';
    let step: CognitoAuthStep | undefined;

    if (errorName === 'PasswordResetRequiredException') {
        messageKey = 'auth.passwordResetRequired';
        step = CognitoAuthStep.FORGOT_PASSWORD;
    } else if (isSessionExpired) {
        messageKey = 'auth.sessionExpired';
        step = CognitoAuthStep.LOGIN;
    } else if (errorName === 'NotAuthorizedException' || errorName === 'UserNotFoundException') {
        messageKey = 'auth.invalidCredentials';
    } else if (errorName === 'CodeMismatchException' || errorName === 'EnableSoftwareTokenMFAException') {
        messageKey = 'auth.invalidCode';
    } else if (errorName === 'ExpiredCodeException') {
        messageKey = 'auth.expiredCode';
    } else if (errorName === 'LimitExceededException' || errorName === 'TooManyRequestsException') {
        messageKey = 'auth.tooManyAttempts';
    } else if (errorName === 'InvalidPasswordException') {
        messageKey = 'auth.invalidPassword';
    }

    return { messageKey, step };
};

export const resetCognitoAuthState = (): void => {
    pendingUsername = '';
    pendingMissingAttributes = [];
    configuredKey = '';
    Object.keys(poolIdCache).forEach((key) => {
        delete poolIdCache[key];
    });
};

const resolveUserPoolId = async (authDomain: string): Promise<string> => {
    let poolId = poolIdCache[authDomain] || '';

    if (!poolId) {
        const { data } = await axios.get(`${authDomain}/.well-known/openid-configuration`);

        poolId = parseUserPoolId(data?.issuer || '');

        if (poolId) {
            poolIdCache[authDomain] = poolId;
        }
    }

    return poolId;
};

const configureFor = async (appMode: AppModes, authType: AuthTypes): Promise<void> => {
    const { clientId, authDomain, userPoolId } = getCognitoConfig(appMode, authType);
    const configKey = `${authType}:${appMode}:${clientId || ''}`;
    let poolId = '';

    if (!clientId || !authDomain) {
        throw Object.assign(new Error('Missing Cognito client'), { name: 'AuthConfigException' });
    }

    if (configuredKey !== configKey) {
        // The custom auth domain does not serve the OpenID document, and the
        // browser cannot read the pool id from any other response on that host
        poolId = parseUserPoolId(userPoolId || '');

        if (!poolId) {
            poolId = await resolveUserPoolId(authDomain);
        }

        if (!poolId) {
            throw Object.assign(new Error('Missing user pool id'), { name: 'AuthConfigException' });
        }

        Amplify.configure({
            Auth: {
                Cognito: {
                    userPoolId: poolId,
                    userPoolClientId: clientId,
                    loginWith: { email: true },
                },
            },
        });
        configuredKey = configKey;
    }
};

const takeTokenResponse = async (): Promise<OAuthTokenResponse> => {
    const stored = await cognitoUserPoolsTokenProvider.authTokenStore.loadTokens();
    const accessToken = stored?.accessToken?.toString() || '';
    const idToken = stored?.idToken?.toString() || '';
    const refreshToken = stored?.refreshToken || '';
    const expiresAt = stored?.accessToken?.payload?.exp;

    if (!accessToken || !refreshToken) {
        throw Object.assign(new Error('Missing tokens'), { name: 'AuthConfigException' });
    }

    const response = toOAuthTokenResponse(
        accessToken,
        idToken,
        refreshToken,
        (typeof expiresAt === 'number') ? expiresAt : undefined
    );

    await cognitoUserPoolsTokenProvider.authTokenStore.clearDeviceMetadata(stored?.username);
    await cognitoUserPoolsTokenProvider.authTokenStore.clearTokens();

    return response;
};

const applySignInOutput = async (
    output: SignInOutput,
    issuer: string,
    username: string
): Promise<CognitoAuthResult> => {
    let resolved = output;
    let result: CognitoAuthResult = { messageKey: 'auth.genericError' };
    const stepName = resolved.nextStep.signInStep;
    let finalStep = stepName;

    if (stepName === 'CONTINUE_SIGN_IN_WITH_MFA_SELECTION'
        || stepName === 'CONTINUE_SIGN_IN_WITH_MFA_SETUP_SELECTION') {
        resolved = await amplifyAuthClient.confirmSignIn({ challengeResponse: 'TOTP' });
        finalStep = resolved.nextStep.signInStep;
    }

    if (finalStep === 'DONE') {
        result = {
            step: CognitoAuthStep.DONE,
            tokenResponse: await takeTokenResponse(),
        };
    } else if (finalStep === 'CONFIRM_SIGN_IN_WITH_NEW_PASSWORD_REQUIRED') {
        pendingMissingAttributes = ('missingAttributes' in resolved.nextStep)
            ? (resolved.nextStep.missingAttributes || [])
            : [];
        result = { step: CognitoAuthStep.NEW_PASSWORD };
    } else if (finalStep === 'CONTINUE_SIGN_IN_WITH_TOTP_SETUP' && 'totpSetupDetails' in resolved.nextStep) {
        const setupUri = resolved.nextStep.totpSetupDetails.getSetupUri(issuer, username);

        result = {
            step: CognitoAuthStep.MFA_SETUP,
            totpSecret: resolved.nextStep.totpSetupDetails.sharedSecret,
            totpSetupUri: setupUri.toString(),
            mfaSetupExpiresAt: mfaSetupDeadline(),
        };
    } else if (finalStep === 'CONFIRM_SIGN_IN_WITH_TOTP_CODE') {
        result = { step: CognitoAuthStep.MFA_CODE };
    } else if (finalStep === 'RESET_PASSWORD') {
        result = {
            step: CognitoAuthStep.FORGOT_PASSWORD,
            messageKey: 'auth.passwordResetRequired',
        };
    }

    return result;
};

const failureResult = (error: unknown): CognitoAuthResult => {
    const mapped = mapCognitoAuthError(error);
    const result: CognitoAuthResult = { messageKey: mapped.messageKey };

    if (mapped.step) {
        result.step = mapped.step;
    }

    return result;
};

const signInWithPassword = async (
    appMode: AppModes,
    authType: AuthTypes,
    username: string,
    password: string,
    issuer: string
): Promise<CognitoAuthResult> => {
    let result: CognitoAuthResult;

    pendingUsername = username;
    pendingMissingAttributes = [];

    try {
        await configureFor(appMode, authType);
        const output = await amplifyAuthClient.signIn({
            username,
            password,
            options: { authFlowType: 'USER_SRP_AUTH' },
        });

        result = await applySignInOutput(output, issuer, username);
    } catch (error) {
        result = failureResult(error);
    }

    return result;
};

const confirmChallenge = async (challengeResponse: string, issuer: string): Promise<CognitoAuthResult> => {
    const userAttributes: Record<string, string> = {};
    let canConfirm = true;
    let result: CognitoAuthResult = { messageKey: 'auth.genericError' };

    pendingMissingAttributes.forEach((attribute) => {
        if (attribute === 'email' && pendingUsername) {
            userAttributes.email = pendingUsername;
        } else {
            canConfirm = false;
        }
    });

    if (canConfirm) {
        try {
            const output = await amplifyAuthClient.confirmSignIn({
                challengeResponse,
                options: (Object.keys(userAttributes).length) ? { userAttributes } : undefined,
            });

            pendingMissingAttributes = [];
            result = await applySignInOutput(output, issuer, pendingUsername);
        } catch (error) {
            result = failureResult(error);
        }
    }

    return result;
};

const requestPasswordReset = async (
    appMode: AppModes,
    authType: AuthTypes,
    username: string
): Promise<CognitoAuthResult> => {
    let result: CognitoAuthResult = {
        step: CognitoAuthStep.FORGOT_PASSWORD_CONFIRM,
        messageKey: 'auth.codeSent',
    };

    pendingUsername = username;

    try {
        await configureFor(appMode, authType);
        await amplifyAuthClient.resetPassword({ username });
    } catch (error) {
        const { name } = readError(error);

        // Same response whether or not the account exists.
        if (name !== 'UserNotFoundException') {
            result = failureResult(error);
        }
    }

    return result;
};

const confirmPasswordReset = async (
    username: string,
    confirmationCode: string,
    newPassword: string
): Promise<CognitoAuthResult> => {
    const account = username || pendingUsername;
    let result: CognitoAuthResult = {
        step: CognitoAuthStep.LOGIN,
        messageKey: 'auth.passwordUpdated',
    };

    try {
        await amplifyAuthClient.confirmResetPassword({ username: account, confirmationCode, newPassword });
    } catch (error) {
        result = failureResult(error);
    }

    return result;
};

const cognitoAuth = {
    signInWithPassword,
    confirmChallenge,
    requestPasswordReset,
    confirmPasswordReset,
};

export default cognitoAuth;
