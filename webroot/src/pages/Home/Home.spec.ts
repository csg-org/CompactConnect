//
//  Home.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/30/2021.
//

import { expect } from 'chai';
import sinon from 'sinon';
import { mountShallow } from '@tests/helpers/setup';
import store from '@store/index';
import Home from '@pages/Home/Home.vue';
import { Compact, CompactType } from '@models/Compact/Compact.model';
import {
    authStorage,
    AUTH_TYPE,
    AUTH_LOGIN_GOTO_COMPACT,
    AuthTypes
} from '@utils/auth';

describe('Home page', async () => {
    afterEach(async () => {
        authStorage.removeItem(AUTH_TYPE);
        authStorage.removeItem(AUTH_LOGIN_GOTO_COMPACT);
        await store.dispatch('user/setCurrentCompact', null);
    });
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(Home);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(Home).exists()).to.equal(true);
    });
    it('should successfully prefer the login-intent compact over a leftover currentCompact', async () => {
        const wrapper = await mountShallow(Home);
        const component = wrapper.vm;
        const pushStub = sinon.stub(component.$router, 'push').resolves();

        await store.dispatch('user/setCurrentCompact', new Compact({ type: CompactType.PSYPACT }));
        authStorage.setItem(AUTH_LOGIN_GOTO_COMPACT, CompactType.ASLP);
        authStorage.setItem(AUTH_TYPE, AuthTypes.STAFF);

        component.goToCompactHome();

        expect(pushStub.calledOnce).to.equal(true);
        expect(pushStub.firstCall.args[0]).to.eql({
            name: 'Licensing',
            params: { compact: CompactType.ASLP },
        });
        expect(authStorage.getItem(AUTH_LOGIN_GOTO_COMPACT)).to.equal(CompactType.ASLP);

        pushStub.restore();
    });
    it('should successfully fall back to currentCompact when no login-intent compact is stashed', async () => {
        const wrapper = await mountShallow(Home);
        const component = wrapper.vm;
        const pushStub = sinon.stub(component.$router, 'push').resolves();

        await store.dispatch('user/setCurrentCompact', new Compact({ type: CompactType.ASLP }));
        authStorage.setItem(AUTH_TYPE, AuthTypes.STAFF);

        component.goToCompactHome();

        expect(pushStub.calledOnce).to.equal(true);
        expect(pushStub.firstCall.args[0]).to.eql({
            name: 'Licensing',
            params: { compact: CompactType.ASLP },
        });

        pushStub.restore();
    });
    it('should successfully send a licensee to LicenseeDashboard for the login-intent compact', async () => {
        const wrapper = await mountShallow(Home);
        const component = wrapper.vm;
        const pushStub = sinon.stub(component.$router, 'push').resolves();

        authStorage.setItem(AUTH_LOGIN_GOTO_COMPACT, CompactType.ASLP);
        authStorage.setItem(AUTH_TYPE, AuthTypes.LICENSEE);

        component.goToCompactHome();

        expect(pushStub.calledOnce).to.equal(true);
        expect(pushStub.firstCall.args[0]).to.eql({
            name: 'LicenseeDashboard',
            params: { compact: CompactType.ASLP },
        });
        expect(authStorage.getItem(AUTH_LOGIN_GOTO_COMPACT)).to.equal(CompactType.ASLP);

        pushStub.restore();
    });
    it('should successfully stay on Home when no compact is available', async () => {
        const wrapper = await mountShallow(Home);
        const component = wrapper.vm;
        const pushStub = sinon.stub(component.$router, 'push').resolves();

        await store.dispatch('user/setCurrentCompact', null);
        authStorage.setItem(AUTH_TYPE, AuthTypes.STAFF);

        component.goToCompactHome();

        expect(pushStub.called).to.equal(false);

        pushStub.restore();
    });
});
