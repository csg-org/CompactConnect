//
//  PublicDashboard.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 8/12/2024.
//

import { mountShallow } from '@tests/helpers/setup';
import PublicDashboard from '@pages/PublicDashboard/PublicDashboard.vue';
import { AuthTypes, getCognitoConfig, getHostedLoginUri } from '@/app.config';
import { config as envConfig } from '@plugins/EnvConfig/envConfig.plugin';

const chaiMatchPattern = require('chai-match-pattern');
const chai = require('chai').use(chaiMatchPattern);

const { expect } = chai;

describe('PublicDashboard page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(PublicDashboard);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(PublicDashboard).exists()).to.equal(true);
    });
    it('should use staff cognito config in app.config', async () => {
        const cognitoConfig = getCognitoConfig(AuthTypes.STAFF);

        expect(cognitoConfig.scopes).to.equal('email openid phone profile aws.cognito.signin.user.admin');
        expect(cognitoConfig.clientId).to.equal(envConfig.cognitoClientIdStaff);
        expect(cognitoConfig.authDomain).to.equal(envConfig.cognitoAuthDomainStaff);
    });
    it('should use licensee cognito config in app.config', async () => {
        const cognitoConfig = getCognitoConfig(AuthTypes.LICENSEE);

        expect(cognitoConfig.scopes).to.equal('email openid phone profile aws.cognito.signin.user.admin');
        expect(cognitoConfig.clientId).to.equal(envConfig.cognitoClientIdLicensee);
        expect(cognitoConfig.authDomain).to.equal(envConfig.cognitoAuthDomainLicensee);
    });
    it('should use fallback cognito config in app.config', async () => {
        expect(getCognitoConfig()).to.matchPattern({
            scopes: '',
            clientId: '',
            authDomain: '',
        });
    });
    it('should use fallback idp path in app.config', async () => {
        expect(getHostedLoginUri(AuthTypes.LICENSEE)).to.contain('/login');
    });
    it('should get correct hosted login uri config for staff', async () => {
        const wrapper = await mountShallow(PublicDashboard);
        const component = wrapper.vm;

        expect(component.hostedLoginUriStaff).to.contain('/login');
        expect(component.hostedLoginUriStaff).to.contain('scope=email%20openid%20phone%20profile%20aws.cognito.signin.user.admin');
        expect(component.hostedLoginUriStaff).to.contain('&state=staff');
        expect(component.hostedLoginUriStaff).to.contain('&response_type=code');
        expect(component.hostedLoginUriStaff).to.contain('%2Fauth%2Fcallback');
    });
    it('should get correct hosted login uri config for licensee', async () => {
        const wrapper = await mountShallow(PublicDashboard);
        const component = wrapper.vm;

        expect(component.hostedLoginUriLicensee).to.contain('/login');
        expect(component.hostedLoginUriLicensee).to.contain('scope=email%20openid%20phone%20profile%20aws.cognito.signin.user.admin');
        expect(component.hostedLoginUriLicensee).to.contain('&state=licensee');
        expect(component.hostedLoginUriLicensee).to.contain('&response_type=code');
        expect(component.hostedLoginUriLicensee).to.contain('%2Fauth%2Fcallback');
    });
});
