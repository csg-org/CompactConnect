//
//  AppTypeSelector.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 9/22/2026.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import AppTypeSelector from '@components/AppTypeSelector/AppTypeSelector.vue';
import store from '@store/index';
import { AppModes } from '@/app.config';
import {
    authStorage,
    AUTH_LOGIN_GOTO_PATH,
    AUTH_LOGIN_GOTO_PATH_AUTH_TYPE,
    AUTH_LOGIN_GOTO_COMPACT,
    AuthTypes
} from '@utils/auth';

const seedStash = (path: string, compact: string) => {
    authStorage.setItem(AUTH_LOGIN_GOTO_PATH, path);
    authStorage.setItem(AUTH_LOGIN_GOTO_PATH_AUTH_TYPE, AuthTypes.STAFF);
    authStorage.setItem(AUTH_LOGIN_GOTO_COMPACT, compact);
};

const clearStash = () => {
    authStorage.removeItem(AUTH_LOGIN_GOTO_PATH);
    authStorage.removeItem(AUTH_LOGIN_GOTO_PATH_AUTH_TYPE);
    authStorage.removeItem(AUTH_LOGIN_GOTO_COMPACT);
};

describe('AppTypeSelector component', async () => {
    afterEach(async () => {
        clearStash();
        await store.dispatch('setAppMode', AppModes.JCC);
        await store.dispatch('user/setCurrentCompact', null);
    });
    it('should mount the component', async () => {
        const wrapper = await mountShallow(AppTypeSelector);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(AppTypeSelector).exists()).to.equal(true);
    });
    it('should successfully clear an incompatible stash on created', async () => {
        await store.dispatch('setAppMode', AppModes.PSYPACT);
        seedStash('/socw/Licensing', 'socw');

        await mountShallow(AppTypeSelector);

        expect(authStorage.getItem(AUTH_LOGIN_GOTO_PATH)).to.equal(null);
        expect(authStorage.getItem(AUTH_LOGIN_GOTO_COMPACT)).to.equal(null);
    });
    it('should successfully keep a compatible stash on created', async () => {
        await store.dispatch('setAppMode', AppModes.JCC);
        seedStash('/aslp/Licensing', 'aslp');

        await mountShallow(AppTypeSelector);

        expect(authStorage.getItem(AUTH_LOGIN_GOTO_PATH)).to.equal('/aslp/Licensing');
        expect(authStorage.getItem(AUTH_LOGIN_GOTO_COMPACT)).to.equal('aslp');
    });
    it('should successfully clear an incompatible stash when switching host mode', async () => {
        const wrapper = await mountShallow(AppTypeSelector);
        const component = wrapper.vm;

        seedStash('/aslp/Licensing', 'aslp');
        component.formData.appType.value = 'psypact';
        await component.handleAppTypeSelect();

        expect(authStorage.getItem(AUTH_LOGIN_GOTO_PATH)).to.equal(null);
        expect(authStorage.getItem(AUTH_LOGIN_GOTO_COMPACT)).to.equal(null);
        expect(store.state.appMode).to.equal(AppModes.PSYPACT);
    });
    it('should successfully keep a compatible stash when switching host mode', async () => {
        const wrapper = await mountShallow(AppTypeSelector);
        const component = wrapper.vm;

        await store.dispatch('setAppMode', AppModes.PSYPACT);
        seedStash('/aslp/Licensing', 'aslp');
        component.formData.appType.value = 'compactconnect';
        await component.handleAppTypeSelect();

        expect(authStorage.getItem(AUTH_LOGIN_GOTO_PATH)).to.equal('/aslp/Licensing');
        expect(authStorage.getItem(AUTH_LOGIN_GOTO_COMPACT)).to.equal('aslp');
        expect(store.state.appMode).to.equal(AppModes.JCC);
    });
});
