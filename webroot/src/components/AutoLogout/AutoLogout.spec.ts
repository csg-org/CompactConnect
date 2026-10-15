//
//  AutoLogout.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/13/2025.
//

import { expect } from 'chai';
import sinon from 'sinon';
import { mountShallow } from '@tests/helpers/setup';
import AutoLogout from '@components/AutoLogout/AutoLogout.vue';

describe('AutoLogout component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(AutoLogout);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(AutoLogout).exists()).to.equal(true);
    });
    it('should successfully clear auto logout state when the user is no longer logged in', async () => {
        const wrapper = await mountShallow(AutoLogout);
        const component = wrapper.vm;

        if (component.userStore.isLoggedIn) {
            await component.$store.dispatch('user/logoutSuccess');
        }

        const dispatchSpy = sinon.spy(component.$store, 'dispatch');
        const eventsStub = sinon.stub(component, 'removeAutoLogoutEvents');
        const graceStub = sinon.stub(component, 'clearAutoLogoutGracePeriodTimer');

        await component.handleLoginUpdate();

        expect(eventsStub.calledOnce).to.equal(true);
        expect(graceStub.calledOnce).to.equal(true);
        expect(dispatchSpy.calledWith('user/clearAutoLogoutTimeout')).to.equal(true);
        expect(dispatchSpy.calledWith('user/updateAutoLogoutWarning', false)).to.equal(true);

        eventsStub.restore();
        graceStub.restore();
        dispatchSpy.restore();
    });
});
