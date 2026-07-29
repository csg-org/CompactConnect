//
//  Logout.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/29/2026.
//

import sinon from 'sinon';
import axios from 'axios';
import { mountShallow } from '@tests/helpers/setup';
import Logout from '@pages/Logout/Logout.vue';
import { authStorage, tokens, AuthTypes } from '@utils/auth';

const chaiMatchPattern = require('chai-match-pattern');
const chai = require('chai').use(chaiMatchPattern);

const { expect } = chai;

describe('Logout page', async () => {
    let logoutStub;

    beforeEach(() => {
        // Prevent created() from running real logout (clears shared store / redirects)
        logoutStub = sinon.stub(Logout.methods, 'logout').resolves();
    });

    afterEach(() => {
        logoutStub.restore();
    });

    it('should mount the page component', async () => {
        const wrapper = await mountShallow(Logout);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(Logout).exists()).to.equal(true);
        expect(logoutStub.calledOnce).to.equal(true);
    });

    it('should successfully revoke tokens before logoutRequest in logoutChecklist', async () => {
        const wrapper = await mountShallow(Logout);
        const component = wrapper.vm;
        const revokeStub = sinon.stub(component, 'revokeTokens').resolves();
        const dispatchSpy = sinon.spy(component.$store, 'dispatch');

        await component.logoutChecklist(false);

        expect(revokeStub.calledOnce).to.equal(true);
        expect(revokeStub.firstCall.args[0]).to.equal(AuthTypes.STAFF);
        expect(dispatchSpy.calledWith('user/logoutRequest', AuthTypes.STAFF)).to.equal(true);
        expect(revokeStub.calledBefore(
            dispatchSpy.withArgs('user/logoutRequest', AuthTypes.STAFF)
        )).to.equal(true);

        revokeStub.restore();
        dispatchSpy.restore();
    });

    it('should successfully revoke licensee tokens when logged in as licensee only', async () => {
        const wrapper = await mountShallow(Logout);
        const component = wrapper.vm;
        const revokeStub = sinon.stub(component, 'revokeTokens').resolves();

        await component.logoutChecklist(true);

        expect(revokeStub.firstCall.args[0]).to.equal(AuthTypes.LICENSEE);

        revokeStub.restore();
    });

    it('should successfully swallow errors inside revokeTokens', async () => {
        const wrapper = await mountShallow(Logout);
        const component = wrapper.vm;
        const axiosPostStub = sinon.stub(axios, 'post').rejects(new Error('network'));
        let didThrow = false;

        authStorage.setItem(tokens.staff.REFRESH_TOKEN, 'staff-refresh-token');

        try {
            await component.revokeTokens(AuthTypes.STAFF);
        } catch (err) {
            didThrow = true;
        }

        expect(didThrow).to.equal(false);

        axiosPostStub.restore();
        authStorage.removeItem(tokens.staff.REFRESH_TOKEN);
    });
});
