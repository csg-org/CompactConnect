//
//  auth.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/29/2026.
//

import sinon from 'sinon';
import axios from 'axios';
import { AppModes } from '@/app.config';
import {
    authStorage,
    tokens,
    AuthTypes,
    revokeCognitoRefreshToken
} from '@utils/auth';
import { config as envConfig } from '@plugins/EnvConfig/envConfig.plugin';

const chaiMatchPattern = require('chai-match-pattern');
const chai = require('chai').use(chaiMatchPattern);

const { expect } = chai;

describe('auth utils', () => {
    let axiosPostStub;

    beforeEach(() => {
        axiosPostStub = sinon.stub(axios, 'post').resolves({ data: {}});
        authStorage.removeItem(tokens.staff.REFRESH_TOKEN);
        authStorage.removeItem(tokens.licensee.REFRESH_TOKEN);
    });

    afterEach(() => {
        axiosPostStub.restore();
        authStorage.removeItem(tokens.staff.REFRESH_TOKEN);
        authStorage.removeItem(tokens.licensee.REFRESH_TOKEN);
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

        expect(axiosPostStub.firstCall.args[0]).to.equal(`${envConfig.cognitoAuthDomainStaffCosmo}/oauth2/revoke`);
        expect(axiosPostStub.firstCall.args[1].toString()).to.contain(
            `client_id=${envConfig.cognitoClientIdStaffCosmo}`
        );
    });
    it('should successfully no-op when refresh token is missing', async () => {
        await revokeCognitoRefreshToken(AppModes.JCC, AuthTypes.STAFF);

        expect(axiosPostStub.called).to.equal(false);
    });
});
