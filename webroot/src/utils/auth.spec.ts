//
//  auth.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/29/2026.
//

import chaiMatchPattern from 'chai-match-pattern';
import { use, expect } from 'chai';
import sinon from 'sinon';
import axios from 'axios';
import { AppModes } from '@/app.config';
import {
    authStorage,
    tokens,
    AuthTypes,
    AUTH_LOGIN_GOTO_PATH,
    AUTH_LOGIN_GOTO_PATH_AUTH_TYPE,
    AUTH_LOGIN_GOTO_COMPACT,
    revokeCognitoRefreshToken,
    getCompactFromGotoPath,
    clearStashIfIncompatibleWithAppMode
} from '@utils/auth';
import { config as envConfig } from '@plugins/EnvConfig/envConfig.plugin';

use(chaiMatchPattern);

describe('auth utils', () => {
    let axiosPostStub;
    let originalCognitoConfig;

    beforeEach(() => {
        axiosPostStub = sinon.stub(axios, 'post').resolves({ data: {}});

        // Preserve real env values, then seed stable doubles so tests do not depend on .env / CI secrets
        originalCognitoConfig = {
            cognitoClientIdStaff: envConfig.cognitoClientIdStaff,
            cognitoAuthDomainStaff: envConfig.cognitoAuthDomainStaff,
            cognitoClientIdLicensee: envConfig.cognitoClientIdLicensee,
            cognitoAuthDomainLicensee: envConfig.cognitoAuthDomainLicensee,
            cognitoClientIdStaffCosmo: envConfig.cognitoClientIdStaffCosmo,
            cognitoAuthDomainStaffCosmo: envConfig.cognitoAuthDomainStaffCosmo,
        };
        envConfig.cognitoClientIdStaff = 'test-staff-client-id';
        envConfig.cognitoAuthDomainStaff = 'https://staff-auth.test.example.com';
        envConfig.cognitoClientIdLicensee = 'test-licensee-client-id';
        envConfig.cognitoAuthDomainLicensee = 'https://licensee-auth.test.example.com';
        envConfig.cognitoClientIdStaffCosmo = 'test-cosmo-client-id';
        envConfig.cognitoAuthDomainStaffCosmo = 'https://cosmo-auth.test.example.com';

        authStorage.removeItem(tokens.staff.REFRESH_TOKEN);
        authStorage.removeItem(tokens.licensee.REFRESH_TOKEN);
        authStorage.removeItem(AUTH_LOGIN_GOTO_PATH);
        authStorage.removeItem(AUTH_LOGIN_GOTO_PATH_AUTH_TYPE);
        authStorage.removeItem(AUTH_LOGIN_GOTO_COMPACT);
    });

    afterEach(() => {
        axiosPostStub.restore();

        envConfig.cognitoClientIdStaff = originalCognitoConfig.cognitoClientIdStaff;
        envConfig.cognitoAuthDomainStaff = originalCognitoConfig.cognitoAuthDomainStaff;
        envConfig.cognitoClientIdLicensee = originalCognitoConfig.cognitoClientIdLicensee;
        envConfig.cognitoAuthDomainLicensee = originalCognitoConfig.cognitoAuthDomainLicensee;
        envConfig.cognitoClientIdStaffCosmo = originalCognitoConfig.cognitoClientIdStaffCosmo;
        envConfig.cognitoAuthDomainStaffCosmo = originalCognitoConfig.cognitoAuthDomainStaffCosmo;

        authStorage.removeItem(tokens.staff.REFRESH_TOKEN);
        authStorage.removeItem(tokens.licensee.REFRESH_TOKEN);
        authStorage.removeItem(AUTH_LOGIN_GOTO_PATH);
        authStorage.removeItem(AUTH_LOGIN_GOTO_PATH_AUTH_TYPE);
        authStorage.removeItem(AUTH_LOGIN_GOTO_COMPACT);
    });

    it('should successfully parse a compact type from a goto path', () => {
        expect(getCompactFromGotoPath('/socw/Licensing')).to.equal('socw');
        expect(getCompactFromGotoPath('psyp/Licensing')).to.equal('psyp');
        expect(getCompactFromGotoPath('/Dashboard')).to.equal(null);
        expect(getCompactFromGotoPath('')).to.equal(null);
    });
    it('should successfully clear an incompatible login stash for the app mode', () => {
        authStorage.setItem(AUTH_LOGIN_GOTO_PATH, '/socw/Licensing');
        authStorage.setItem(AUTH_LOGIN_GOTO_PATH_AUTH_TYPE, AuthTypes.STAFF);
        authStorage.setItem(AUTH_LOGIN_GOTO_COMPACT, 'socw');

        clearStashIfIncompatibleWithAppMode(AppModes.PSYPACT);

        expect(authStorage.getItem(AUTH_LOGIN_GOTO_PATH)).to.equal(null);
        expect(authStorage.getItem(AUTH_LOGIN_GOTO_PATH_AUTH_TYPE)).to.equal(null);
        expect(authStorage.getItem(AUTH_LOGIN_GOTO_COMPACT)).to.equal(null);
    });
    it('should successfully keep a compatible login stash for the app mode', () => {
        authStorage.setItem(AUTH_LOGIN_GOTO_PATH, '/aslp/Licensing');
        authStorage.setItem(AUTH_LOGIN_GOTO_PATH_AUTH_TYPE, AuthTypes.STAFF);
        authStorage.setItem(AUTH_LOGIN_GOTO_COMPACT, 'aslp');

        clearStashIfIncompatibleWithAppMode(AppModes.JCC);

        expect(authStorage.getItem(AUTH_LOGIN_GOTO_PATH)).to.equal('/aslp/Licensing');
        expect(authStorage.getItem(AUTH_LOGIN_GOTO_PATH_AUTH_TYPE)).to.equal(AuthTypes.STAFF);
        expect(authStorage.getItem(AUTH_LOGIN_GOTO_COMPACT)).to.equal('aslp');
    });
    it('should successfully clear an incompatible stash inferred from the goto path', () => {
        authStorage.setItem(AUTH_LOGIN_GOTO_PATH, '/psyp/Licensing');

        clearStashIfIncompatibleWithAppMode(AppModes.JCC);

        expect(authStorage.getItem(AUTH_LOGIN_GOTO_PATH)).to.equal(null);
    });
    it('should successfully post refresh token to Cognito /oauth2/revoke for staff', async () => {
        const refreshToken = 'staff-refresh-token';

        authStorage.setItem(tokens.staff.REFRESH_TOKEN, refreshToken);

        await revokeCognitoRefreshToken(AppModes.JCC, AuthTypes.STAFF);

        expect(axiosPostStub.calledOnce).to.equal(true);
        expect(axiosPostStub.firstCall.args[0]).to.equal(`${envConfig.cognitoAuthDomainStaff}/oauth2/revoke`);
        expect(axiosPostStub.firstCall.args[1].toString()).to.equal(
            `token=${refreshToken}&client_id=${envConfig.cognitoClientIdStaff}`
        );
        expect(axiosPostStub.firstCall.args[2]).to.matchPattern({
            timeout: 30000,
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                Accept: 'application/json',
            },
        });
    });

    it('should successfully post refresh token to Cognito /oauth2/revoke for licensee', async () => {
        const refreshToken = 'licensee-refresh-token';

        authStorage.setItem(tokens.licensee.REFRESH_TOKEN, refreshToken);

        await revokeCognitoRefreshToken(AppModes.JCC, AuthTypes.LICENSEE);

        expect(axiosPostStub.calledOnce).to.equal(true);
        expect(axiosPostStub.firstCall.args[0]).to.equal(`${envConfig.cognitoAuthDomainLicensee}/oauth2/revoke`);
        expect(axiosPostStub.firstCall.args[1].toString()).to.equal(
            `token=${refreshToken}&client_id=${envConfig.cognitoClientIdLicensee}`
        );
    });

    it('should successfully use cosmetology staff cognito config when app mode is cosmetology', async () => {
        authStorage.setItem(tokens.staff.REFRESH_TOKEN, 'cosmo-refresh-token');

        await revokeCognitoRefreshToken(AppModes.COSMETOLOGY, AuthTypes.STAFF);

        expect(axiosPostStub.calledOnce).to.equal(true);
        expect(axiosPostStub.firstCall.args[0]).to.equal(`${envConfig.cognitoAuthDomainStaffCosmo}/oauth2/revoke`);
        expect(axiosPostStub.firstCall.args[1].toString()).to.contain(
            `client_id=${envConfig.cognitoClientIdStaffCosmo}`
        );
    });

    it('should successfully no-op when refresh token is missing', async () => {
        await revokeCognitoRefreshToken(AppModes.JCC, AuthTypes.STAFF);

        expect(axiosPostStub.called).to.equal(false);
    });

    it('should successfully retry retryable revoke failures then succeed', async () => {
        const networkError = new Error('network');

        axiosPostStub.onCall(0).rejects(networkError);
        axiosPostStub.onCall(1).rejects(networkError);
        axiosPostStub.onCall(2).resolves({ data: {}});

        authStorage.setItem(tokens.staff.REFRESH_TOKEN, 'staff-refresh-token');

        await revokeCognitoRefreshToken(AppModes.JCC, AuthTypes.STAFF);

        expect(axiosPostStub.callCount).to.equal(3);
    });

    it('should successfully throw after exhausting retryable revoke attempts', async () => {
        const networkError = new Error('network');
        let didThrow = false;

        axiosPostStub.rejects(networkError);
        authStorage.setItem(tokens.staff.REFRESH_TOKEN, 'staff-refresh-token');

        await revokeCognitoRefreshToken(AppModes.JCC, AuthTypes.STAFF).catch(() => {
            didThrow = true;
        });

        expect(didThrow).to.equal(true);
        expect(axiosPostStub.callCount).to.equal(3);
    });

    it('should successfully not retry non-retryable revoke failures', async () => {
        const clientError = Object.assign(new Error('bad request'), { response: { status: 400 }});
        let didThrow = false;

        axiosPostStub.rejects(clientError);
        authStorage.setItem(tokens.staff.REFRESH_TOKEN, 'staff-refresh-token');

        await revokeCognitoRefreshToken(AppModes.JCC, AuthTypes.STAFF).catch(() => {
            didThrow = true;
        });

        expect(didThrow).to.equal(true);
        expect(axiosPostStub.callCount).to.equal(1);
    });
});
