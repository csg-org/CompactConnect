//
//  mixins.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 6/24/2026.
//

import { mountShallow } from '@tests/helpers/setup';
import AuthCallbackHandlerMixin from '@pages/AuthCallback/_mixins/handler.mixin';
import { AppModes } from '@/app.config';
import { AuthTypes } from '@utils/auth';

const chaiMatchPattern = require('chai-match-pattern');
const chai = require('chai').use(chaiMatchPattern);

const { expect } = chai;

describe('AuthCallbackHandler mixin', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(AuthCallbackHandlerMixin);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(AuthCallbackHandlerMixin).exists()).to.equal(true);
    });
    it('should successfully get default query param values', async () => {
        const wrapper = await mountShallow(AuthCallbackHandlerMixin);
        const component = wrapper.vm;

        expect(component.authorizationCode).to.equal('');
        expect(component.stateParam).to.equal('');
    });
    it('should successfully get custom query param values', async () => {
        const wrapper = await mountShallow(AuthCallbackHandlerMixin);
        const component = wrapper.vm;

        component.$route.query.code = 'abc';
        component.$route.query.state = 'def';

        expect(component.authorizationCode).to.equal('abc');
        expect(component.stateParam).to.equal('def');
    });
    it('should successfully get tokens', async () => {
        const wrapper = await mountShallow(AuthCallbackHandlerMixin);
        const component = wrapper.vm;

        await component.getTokens(AppModes.JCC, AuthTypes.STAFF, 'http://localhost', 'abc');

        expect(component.$router.options.history.state.replaced).to.equal(true);
    });
});
