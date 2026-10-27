//
//  cognitoAuth.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/22/2026.
//

import { expect } from 'chai';
import sinon from 'sinon';
import axios from 'axios';
import { Amplify } from 'aws-amplify';
import { cognitoUserPoolsTokenProvider } from 'aws-amplify/auth/cognito';
import { AppModes } from '@/app.config';
import { config as envConfig } from '@plugins/EnvConfig/envConfig.plugin';
import { AuthTypes } from '@utils/auth';
import cognitoAuth, {
    amplifyAuthClient,
    AUTH_SESSION_MINUTES,
    AUTH_SESSION_MS,
    CognitoAuthStep,
    formatAuthCountdown,
    getTotpIssuer,
    mapCognitoAuthError,
    mfaSetupDeadline,
    parseUserPoolId,
    resetCognitoAuthState,
    toOAuthTokenResponse
} from '@utils/cognitoAuth';

const staffUsername = 'person@example.com';
const staffPassword = 'Password1';
const openIdIssuer = 'https://cognito-idp.us-east-1.amazonaws.com/us-east-1_PoolFromDoc';

const signInStaff = (username = staffUsername) => cognitoAuth.signInWithPassword(
    AppModes.JCC,
    AuthTypes.STAFF,
    username,
    staffPassword,
    'CompactConnect'
);

const doneStep = () => ({
    isSignedIn: true,
    nextStep: { signInStep: 'DONE' },
});

describe('cognitoAuth utils', () => {
    it('should keep the MFA setup window at Cognito maximum of 15 minutes', () => {
        const deadline = mfaSetupDeadline();

        expect(AUTH_SESSION_MINUTES).to.equal(15);
        expect(mfaSetupDeadline(1_000)).to.equal(1_000 + AUTH_SESSION_MS);
        expect(deadline).to.be.greaterThan(Date.now());
        expect(AUTH_SESSION_MS).to.equal(15 * 60 * 1000);
        expect(formatAuthCountdown(AUTH_SESSION_MS)).to.equal('15:00');
        expect(formatAuthCountdown(90_000)).to.equal('1:30');
        expect(formatAuthCountdown(0)).to.equal('0:00');
        expect(formatAuthCountdown(-1_000)).to.equal('0:00');
    });
    it('should parse a user pool id from the Cognito issuer', () => {
        expect(parseUserPoolId('https://cognito-idp.us-east-1.amazonaws.com/us-east-1_Ab12Cd')).to.equal('us-east-1_Ab12Cd');
        expect(parseUserPoolId('us-east-1_Ab12Cd')).to.equal('us-east-1_Ab12Cd');
        expect(parseUserPoolId('https://example.com/not-a-pool')).to.equal('');
        expect(parseUserPoolId('')).to.equal('');
        expect(parseUserPoolId('///')).to.equal('');
    });
    it('should use the PsyPact issuer only for that app mode', () => {
        expect(getTotpIssuer(AppModes.PSYPACT)).to.equal('PSYPACT');
        expect(getTotpIssuer(AppModes.JCC)).to.equal('CompactConnect');
        expect(getTotpIssuer(AppModes.COSMETOLOGY)).to.equal('CompactConnect');
        expect(getTotpIssuer(AppModes.SOCIAL_WORK)).to.equal('CompactConnect');
    });
    it('should map Cognito auth errors onto login steps', () => {
        const reset = mapCognitoAuthError({ name: 'PasswordResetRequiredException', message: '' });
        const expired = mapCognitoAuthError({ name: 'NotAuthorizedException', message: 'Invalid session for the user' });
        const code = mapCognitoAuthError({ name: 'CodeMismatchException', message: '' });

        expect(reset.messageKey).to.equal('auth.passwordResetRequired');
        expect(reset.step).to.equal(CognitoAuthStep.FORGOT_PASSWORD);
        expect(expired.messageKey).to.equal('auth.sessionExpired');
        expect(expired.step).to.equal(CognitoAuthStep.LOGIN);
        expect(code.messageKey).to.equal('auth.invalidCode');
        expect(code.step).to.equal(undefined);
    });
    it('should map the remaining Cognito error names', () => {
        const missing = mapCognitoAuthError(null);
        const unnamed = mapCognitoAuthError({ message: 'nope' });
        const credentials = mapCognitoAuthError({
            name: 'NotAuthorizedException',
            message: 'Incorrect username or password.',
        });
        const unknownUser = mapCognitoAuthError({ name: 'UserNotFoundException', message: 'missing' });
        const softwareToken = mapCognitoAuthError({ name: 'EnableSoftwareTokenMFAException', message: 'Code mismatch' });
        const expiredCode = mapCognitoAuthError({ name: 'ExpiredCodeException', message: 'expired' });
        const limited = mapCognitoAuthError({ name: 'LimitExceededException', message: 'limited' });
        const tooMany = mapCognitoAuthError({ name: 'TooManyRequestsException', message: 'slow down' });
        const invalidPassword = mapCognitoAuthError({ name: 'InvalidPasswordException', message: 'weak' });

        expect(missing.messageKey).to.equal('auth.genericError');
        expect(missing.step).to.equal(undefined);
        expect(unnamed.messageKey).to.equal('auth.genericError');
        expect(credentials.messageKey).to.equal('auth.invalidCredentials');
        expect(credentials.step).to.equal(undefined);
        expect(unknownUser.messageKey).to.equal('auth.invalidCredentials');
        expect(softwareToken.messageKey).to.equal('auth.invalidCode');
        expect(softwareToken.step).to.equal(undefined);
        expect(expiredCode.messageKey).to.equal('auth.expiredCode');
        expect(limited.messageKey).to.equal('auth.tooManyAttempts');
        expect(tooMany.messageKey).to.equal('auth.tooManyAttempts');
        expect(invalidPassword.messageKey).to.equal('auth.invalidPassword');
    });
    it('should shape Amplify tokens like the OAuth token response', () => {
        const nowSeconds = Math.floor(Date.now() / 1000);
        const response = toOAuthTokenResponse('access', 'id', 'refresh', nowSeconds + 120);
        const fallback = toOAuthTokenResponse('access', 'id', 'refresh');

        expect(response.access_token).to.equal('access');
        expect(response.id_token).to.equal('id');
        expect(response.refresh_token).to.equal('refresh');
        expect(response.token_type).to.equal('Bearer');
        expect(response.expires_in).to.be.within(119, 120);
        expect(fallback.expires_in).to.equal(300);
    });
});
describe('cognitoAuth flows', () => {
    const originalClientId = envConfig.cognitoClientIdStaff;
    const originalAuthDomain = envConfig.cognitoAuthDomainStaff;
    const originalPoolId = envConfig.cognitoUserPoolIdStaff;
    let signInStub;
    let confirmSignInStub;
    let resetPasswordStub;
    let confirmResetPasswordStub;
    let configureStub;
    let loadTokensStub;
    let clearDeviceMetadataStub;
    let clearTokensStub;
    let axiosGetStub;

    beforeEach(() => {
        resetCognitoAuthState();
        envConfig.cognitoClientIdStaff = 'staff-client';
        envConfig.cognitoAuthDomainStaff = 'https://staff.example.com';
        envConfig.cognitoUserPoolIdStaff = 'us-east-1_Ab12Cd';
        signInStub = sinon.stub(amplifyAuthClient, 'signIn');
        confirmSignInStub = sinon.stub(amplifyAuthClient, 'confirmSignIn');
        resetPasswordStub = sinon.stub(amplifyAuthClient, 'resetPassword');
        confirmResetPasswordStub = sinon.stub(amplifyAuthClient, 'confirmResetPassword');
        configureStub = sinon.stub(Amplify, 'configure');
        loadTokensStub = sinon.stub(cognitoUserPoolsTokenProvider.authTokenStore, 'loadTokens').resolves({
            accessToken: {
                toString: () => 'access-token',
                payload: { exp: Math.floor(Date.now() / 1000) + 120 },
            },
            idToken: { toString: () => 'id-token' },
            refreshToken: 'refresh-token',
            username: staffUsername,
        });
        clearDeviceMetadataStub = sinon.stub(
            cognitoUserPoolsTokenProvider.authTokenStore,
            'clearDeviceMetadata'
        ).resolves();
        clearTokensStub = sinon.stub(cognitoUserPoolsTokenProvider.authTokenStore, 'clearTokens').resolves();
        axiosGetStub = sinon.stub(axios, 'get');
    });
    afterEach(() => {
        resetCognitoAuthState();
        envConfig.cognitoClientIdStaff = originalClientId;
        envConfig.cognitoAuthDomainStaff = originalAuthDomain;
        envConfig.cognitoUserPoolIdStaff = originalPoolId;
        sinon.restore();
    });
    it('should return tokens when sign-in is complete', async () => {
        signInStub.resolves(doneStep());

        const result = await signInStaff();

        expect(result.step).to.equal(CognitoAuthStep.DONE);
        expect(result.tokenResponse.access_token).to.equal('access-token');
        expect(result.tokenResponse.id_token).to.equal('id-token');
        expect(result.tokenResponse.refresh_token).to.equal('refresh-token');
        expect(result.tokenResponse.token_type).to.equal('Bearer');
        expect(result.tokenResponse.expires_in).to.be.within(119, 120);
        expect(signInStub.firstCall.args[0].options).to.deep.equal({ authFlowType: 'USER_SRP_AUTH' });
        expect(configureStub.calledOnce).to.equal(true);
        expect(configureStub.firstCall.args[0].Auth.Cognito.userPoolId).to.equal('us-east-1_Ab12Cd');
        expect(configureStub.firstCall.args[0].Auth.Cognito.userPoolClientId).to.equal('staff-client');
        expect(clearDeviceMetadataStub.calledOnceWith(staffUsername)).to.equal(true);
        expect(clearTokensStub.calledOnce).to.equal(true);
        expect(axiosGetStub.called).to.equal(false);
    });
    it('should configure Amplify once for the same client', async () => {
        signInStub.resolves(doneStep());

        await signInStaff();
        await signInStaff();

        expect(configureStub.calledOnce).to.equal(true);
    });
    it('should confirm TOTP when Cognito asks which MFA to use', async () => {
        signInStub.resolves({
            isSignedIn: false,
            nextStep: { signInStep: 'CONTINUE_SIGN_IN_WITH_MFA_SELECTION' },
        });
        confirmSignInStub.resolves(doneStep());

        const result = await signInStaff();

        expect(result.step).to.equal(CognitoAuthStep.DONE);
        expect(confirmSignInStub.firstCall.args[0]).to.deep.equal({ challengeResponse: 'TOTP' });
    });
    it('should confirm TOTP when Cognito asks which MFA to set up', async () => {
        signInStub.resolves({
            isSignedIn: false,
            nextStep: { signInStep: 'CONTINUE_SIGN_IN_WITH_MFA_SETUP_SELECTION' },
        });
        confirmSignInStub.resolves({
            isSignedIn: false,
            nextStep: { signInStep: 'CONFIRM_SIGN_IN_WITH_TOTP_CODE' },
        });

        const result = await signInStaff();

        expect(result.step).to.equal(CognitoAuthStep.MFA_CODE);
        expect(confirmSignInStub.firstCall.args[0]).to.deep.equal({ challengeResponse: 'TOTP' });
    });
    it('should continue to a new password and submit the email attribute', async () => {
        signInStub.resolves({
            isSignedIn: false,
            nextStep: {
                signInStep: 'CONFIRM_SIGN_IN_WITH_NEW_PASSWORD_REQUIRED',
                missingAttributes: ['email'],
            },
        });
        confirmSignInStub.resolves({
            isSignedIn: false,
            nextStep: { signInStep: 'CONFIRM_SIGN_IN_WITH_TOTP_CODE' },
        });

        const started = await signInStaff();
        const confirmed = await cognitoAuth.confirmChallenge('NewPassword1', 'CompactConnect');

        expect(started.step).to.equal(CognitoAuthStep.NEW_PASSWORD);
        expect(confirmed.step).to.equal(CognitoAuthStep.MFA_CODE);
        expect(confirmSignInStub.firstCall.args[0].challengeResponse).to.equal('NewPassword1');
        expect(confirmSignInStub.firstCall.args[0].options.userAttributes.email).to.equal(staffUsername);
    });
    it('should continue when Cognito does not list missing attributes', async () => {
        signInStub.resolves({
            isSignedIn: false,
            nextStep: { signInStep: 'CONFIRM_SIGN_IN_WITH_NEW_PASSWORD_REQUIRED' },
        });
        confirmSignInStub.resolves(doneStep());

        const started = await signInStaff();
        const confirmed = await cognitoAuth.confirmChallenge('NewPassword1', 'CompactConnect');

        expect(started.step).to.equal(CognitoAuthStep.NEW_PASSWORD);
        expect(confirmed.step).to.equal(CognitoAuthStep.DONE);
        expect(confirmSignInStub.firstCall.args[0].options).to.equal(undefined);
    });
    it('should treat a missing attribute list as empty', async () => {
        signInStub.resolves({
            isSignedIn: false,
            nextStep: {
                signInStep: 'CONFIRM_SIGN_IN_WITH_NEW_PASSWORD_REQUIRED',
                missingAttributes: undefined,
            },
        });

        const result = await signInStaff();

        expect(result.step).to.equal(CognitoAuthStep.NEW_PASSWORD);
    });
    it('should stop when a required attribute is not the email', async () => {
        signInStub.resolves({
            isSignedIn: false,
            nextStep: {
                signInStep: 'CONFIRM_SIGN_IN_WITH_NEW_PASSWORD_REQUIRED',
                missingAttributes: ['phone_number'],
            },
        });

        const started = await signInStaff();
        const confirmed = await cognitoAuth.confirmChallenge('NewPassword1', 'CompactConnect');

        expect(started.step).to.equal(CognitoAuthStep.NEW_PASSWORD);
        expect(confirmed.messageKey).to.equal('auth.genericError');
        expect(confirmed.step).to.equal(undefined);
        expect(confirmSignInStub.called).to.equal(false);
    });
    it('should stop when the email attribute has no username', async () => {
        signInStub.resolves({
            isSignedIn: false,
            nextStep: {
                signInStep: 'CONFIRM_SIGN_IN_WITH_NEW_PASSWORD_REQUIRED',
                missingAttributes: ['email'],
            },
        });

        await signInStaff('');

        const confirmed = await cognitoAuth.confirmChallenge('NewPassword1', 'CompactConnect');

        expect(confirmed.messageKey).to.equal('auth.genericError');
        expect(confirmSignInStub.called).to.equal(false);
    });
    it('should return MFA setup details', async () => {
        signInStub.resolves({
            isSignedIn: false,
            nextStep: {
                signInStep: 'CONTINUE_SIGN_IN_WITH_TOTP_SETUP',
                totpSetupDetails: {
                    sharedSecret: 'SECRETKEY',
                    getSetupUri: () => new URL('otpauth://totp/CompactConnect:person@example.com?secret=SECRETKEY'),
                },
            },
        });

        const result = await signInStaff();

        expect(result.step).to.equal(CognitoAuthStep.MFA_SETUP);
        expect(result.totpSecret).to.equal('SECRETKEY');
        expect(result.totpSetupUri).to.equal('otpauth://totp/CompactConnect:person@example.com?secret=SECRETKEY');
        expect(result.mfaSetupExpiresAt).to.be.greaterThan(Date.now());
    });
    it('should ignore a TOTP setup step without details', async () => {
        signInStub.resolves({
            isSignedIn: false,
            nextStep: { signInStep: 'CONTINUE_SIGN_IN_WITH_TOTP_SETUP' },
        });

        const result = await signInStaff();

        expect(result.messageKey).to.equal('auth.genericError');
        expect(result.step).to.equal(undefined);
    });
    it('should send the user to forgot password when Cognito requires a reset', async () => {
        signInStub.resolves({
            isSignedIn: false,
            nextStep: { signInStep: 'RESET_PASSWORD' },
        });

        const result = await signInStaff();

        expect(result.step).to.equal(CognitoAuthStep.FORGOT_PASSWORD);
        expect(result.messageKey).to.equal('auth.passwordResetRequired');
    });
    it('should return a generic error for an unsupported sign-in step', async () => {
        signInStub.resolves({
            isSignedIn: false,
            nextStep: { signInStep: 'CONFIRM_SIGN_IN_WITH_SMS_CODE' },
        });

        const result = await signInStaff();

        expect(result.messageKey).to.equal('auth.genericError');
        expect(result.step).to.equal(undefined);
    });
    it('should return a generic error when the session has no tokens', async () => {
        signInStub.resolves(doneStep());
        loadTokensStub.resolves(undefined);

        const missingSession = await signInStaff();

        loadTokensStub.resolves({
            accessToken: {
                toString: () => 'access-token',
                payload: { exp: 1 },
            },
            idToken: { toString: () => 'id-token' },
            refreshToken: '',
            username: staffUsername,
        });

        const missingRefresh = await signInStaff();

        expect(missingSession.messageKey).to.equal('auth.genericError');
        expect(missingSession.step).to.equal(undefined);
        expect(missingRefresh.messageKey).to.equal('auth.genericError');
        expect(clearTokensStub.called).to.equal(false);
    });
    it('should keep a login that has no id token or expiry', async () => {
        signInStub.resolves(doneStep());
        loadTokensStub.resolves({
            accessToken: {
                toString: () => 'access-token',
                payload: {},
            },
            refreshToken: 'refresh-token',
        });

        const result = await signInStaff();

        expect(result.step).to.equal(CognitoAuthStep.DONE);
        expect(result.tokenResponse.id_token).to.equal('');
        expect(result.tokenResponse.expires_in).to.equal(300);
        expect(clearDeviceMetadataStub.calledOnceWith(undefined)).to.equal(true);
    });
    it('should return a generic error when the Cognito client is not configured', async () => {
        envConfig.cognitoClientIdStaff = '';

        const result = await signInStaff();

        expect(result.messageKey).to.equal('auth.genericError');
        expect(result.step).to.equal(undefined);
        expect(configureStub.called).to.equal(false);
    });
    it('should return a generic error when the Cognito domain is not configured', async () => {
        envConfig.cognitoAuthDomainStaff = '';

        const result = await signInStaff();

        expect(result.messageKey).to.equal('auth.genericError');
        expect(configureStub.called).to.equal(false);
    });
    it('should read the user pool id from the OpenID document and reuse it', async () => {
        envConfig.cognitoUserPoolIdStaff = '';
        axiosGetStub.resolves({ data: { issuer: openIdIssuer }});
        signInStub.resolves(doneStep());

        const first = await signInStaff();

        envConfig.cognitoClientIdStaff = 'other-client';

        const second = await signInStaff();

        expect(first.step).to.equal(CognitoAuthStep.DONE);
        expect(second.step).to.equal(CognitoAuthStep.DONE);
        expect(axiosGetStub.calledOnce).to.equal(true);
        expect(axiosGetStub.firstCall.args[0]).to.equal(
            'https://staff.example.com/.well-known/openid-configuration'
        );
        expect(configureStub.firstCall.args[0].Auth.Cognito.userPoolId).to.equal('us-east-1_PoolFromDoc');
        expect(configureStub.secondCall.args[0].Auth.Cognito.userPoolClientId).to.equal('other-client');
    });
    it('should return a generic error when the pool id cannot be discovered', async () => {
        envConfig.cognitoUserPoolIdStaff = '';
        axiosGetStub.onFirstCall().resolves({ data: {}});
        axiosGetStub.onSecondCall().resolves({ data: { issuer: 'https://example.com/not-a-pool' }});

        const missingIssuer = await signInStaff();
        const badIssuer = await signInStaff();

        expect(missingIssuer.messageKey).to.equal('auth.genericError');
        expect(badIssuer.messageKey).to.equal('auth.genericError');
        expect(configureStub.called).to.equal(false);
    });
    it('should fall back to the OpenID document when the configured pool id is invalid', async () => {
        envConfig.cognitoUserPoolIdStaff = 'not-a-pool';
        axiosGetStub.resolves({ data: { issuer: openIdIssuer }});
        signInStub.resolves(doneStep());

        const result = await signInStaff();

        expect(result.step).to.equal(CognitoAuthStep.DONE);
        expect(configureStub.firstCall.args[0].Auth.Cognito.userPoolId).to.equal('us-east-1_PoolFromDoc');
    });
    it('should map a password-reset exception onto the forgot-password step', async () => {
        signInStub.rejects({ name: 'PasswordResetRequiredException', message: '' });

        const result = await signInStaff();

        expect(result.step).to.equal(CognitoAuthStep.FORGOT_PASSWORD);
        expect(result.messageKey).to.equal('auth.passwordResetRequired');
    });
    it('should map a challenge failure', async () => {
        signInStub.resolves({
            isSignedIn: false,
            nextStep: { signInStep: 'CONFIRM_SIGN_IN_WITH_TOTP_CODE' },
        });
        confirmSignInStub.rejects({ name: 'CodeMismatchException', message: 'bad code' });

        const started = await signInStaff();
        const result = await cognitoAuth.confirmChallenge('123456', 'CompactConnect');

        expect(started.step).to.equal(CognitoAuthStep.MFA_CODE);
        expect(result.messageKey).to.equal('auth.invalidCode');
        expect(result.step).to.equal(undefined);
    });
    it('should send a reset code', async () => {
        resetPasswordStub.resolves({});

        const result = await cognitoAuth.requestPasswordReset(
            AppModes.JCC,
            AuthTypes.STAFF,
            staffUsername
        );

        expect(result.step).to.equal(CognitoAuthStep.FORGOT_PASSWORD_CONFIRM);
        expect(result.messageKey).to.equal('auth.codeSent');
        expect(resetPasswordStub.firstCall.args[0]).to.deep.equal({ username: staffUsername });
    });
    it('should send the same reset response when the account does not exist', async () => {
        resetPasswordStub.rejects({ name: 'UserNotFoundException', message: 'missing' });

        const result = await cognitoAuth.requestPasswordReset(
            AppModes.JCC,
            AuthTypes.STAFF,
            staffUsername
        );

        expect(result.step).to.equal(CognitoAuthStep.FORGOT_PASSWORD_CONFIRM);
        expect(result.messageKey).to.equal('auth.codeSent');
    });
    it('should map a reset-password failure', async () => {
        resetPasswordStub.rejects({ name: 'TooManyRequestsException', message: 'slow down' });

        const result = await cognitoAuth.requestPasswordReset(
            AppModes.JCC,
            AuthTypes.STAFF,
            staffUsername
        );

        expect(result.messageKey).to.equal('auth.tooManyAttempts');
        expect(result.step).to.equal(undefined);
    });
    it('should confirm a password reset', async () => {
        confirmResetPasswordStub.resolves();

        const result = await cognitoAuth.confirmPasswordReset(staffUsername, '123456', 'NewPassword1');

        expect(result.step).to.equal(CognitoAuthStep.LOGIN);
        expect(result.messageKey).to.equal('auth.passwordUpdated');
        expect(confirmResetPasswordStub.firstCall.args[0]).to.deep.equal({
            username: staffUsername,
            confirmationCode: '123456',
            newPassword: 'NewPassword1',
        });
    });
    it('should confirm a password reset with the username from the request', async () => {
        resetPasswordStub.resolves({});
        confirmResetPasswordStub.resolves();
        await cognitoAuth.requestPasswordReset(AppModes.JCC, AuthTypes.STAFF, staffUsername);

        const result = await cognitoAuth.confirmPasswordReset('', '123456', 'NewPassword1');

        expect(result.messageKey).to.equal('auth.passwordUpdated');
        expect(confirmResetPasswordStub.firstCall.args[0].username).to.equal(staffUsername);
    });
    it('should map a password-reset confirmation failure', async () => {
        confirmResetPasswordStub.rejects({ name: 'ExpiredCodeException', message: 'expired' });

        const result = await cognitoAuth.confirmPasswordReset(staffUsername, '000000', 'NewPassword1');

        expect(result.messageKey).to.equal('auth.expiredCode');
        expect(result.step).to.equal(undefined);
    });
});
