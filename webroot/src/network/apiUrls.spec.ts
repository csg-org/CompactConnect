//
//  apiUrls.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 8/18/2026.
//

import chaiMatchPattern from 'chai-match-pattern';
import chai from 'chai';
import { AppModes } from '@/app.config';
import { config as envConfig } from '@plugins/EnvConfig/envConfig.plugin';
import { getApiBaseUrl } from '@network/apiUrls';

chai.use(chaiMatchPattern);

const { expect } = chai;

describe('apiUrls helpers', () => {
    it('should successfully resolve jcc api base urls', () => {
        expect(getApiBaseUrl(AppModes.JCC, 'state')).to.equal(envConfig.apiUrlState);
        expect(getApiBaseUrl(AppModes.JCC, 'license')).to.equal(envConfig.apiUrlLicense);
        expect(getApiBaseUrl(AppModes.JCC, 'search')).to.equal(envConfig.apiUrlSearch);
        expect(getApiBaseUrl(AppModes.JCC, 'user')).to.equal(envConfig.apiUrlUser);
    });

    it('should successfully resolve cosmetology api base urls', () => {
        expect(getApiBaseUrl(AppModes.COSMETOLOGY, 'state')).to.equal(envConfig.apiUrlStateCosmo);
        expect(getApiBaseUrl(AppModes.COSMETOLOGY, 'license')).to.equal(envConfig.apiUrlLicenseCosmo);
        expect(getApiBaseUrl(AppModes.COSMETOLOGY, 'search')).to.equal(envConfig.apiUrlSearchCosmo);
        expect(getApiBaseUrl(AppModes.COSMETOLOGY, 'user')).to.equal(envConfig.apiUrlUserCosmo);
    });

    it('should successfully resolve social work api base urls', () => {
        expect(getApiBaseUrl(AppModes.SOCIAL_WORK, 'state')).to.equal(envConfig.apiUrlStateSw);
        expect(getApiBaseUrl(AppModes.SOCIAL_WORK, 'license')).to.equal(envConfig.apiUrlLicenseSw);
        expect(getApiBaseUrl(AppModes.SOCIAL_WORK, 'search')).to.equal(envConfig.apiUrlSearchSw);
        expect(getApiBaseUrl(AppModes.SOCIAL_WORK, 'user')).to.equal(envConfig.apiUrlUserSw);
    });

    it('should successfully fall back to jcc for an unknown or missing app mode', () => {
        expect(getApiBaseUrl(null, 'license')).to.equal(envConfig.apiUrlLicense);
        expect(getApiBaseUrl(undefined, 'user')).to.equal(envConfig.apiUrlUser);
        expect(getApiBaseUrl('not-an-app-mode' as AppModes, 'search')).to.equal(envConfig.apiUrlSearch);
    });
});
