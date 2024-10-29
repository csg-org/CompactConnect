//
//  App.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

import { AuthTypes } from '@/app.config';
import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import App from '@components/App/App.vue';
import store from '@/store';
import { MessageTypes, AppMessage } from '@/models/AppMessage/AppMessage.model';

global.requestAnimationFrame = () => {}; // eslint-disable-line @typescript-eslint/no-empty-function

describe('App component', async () => {
    before(async () => {
        await store.dispatch('user/resetStoreUser');
    });
    it('should mount the component', async () => {
        const wrapper = await mountShallow(App);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(App).exists()).to.equal(true);
    });
    it('should render the app container', async () => {
        const wrapper = await mountShallow(App);

        expect(wrapper.html()).to.include('<div id="app">');
    });
    it('should display an error modal', async () => {
        const wrapper = await mountShallow(App);
        const instance: any = wrapper.vm;

        instance.$store.dispatch('clearMessages');
        instance.$store.dispatch('addMessage', new AppMessage({
            type: MessageTypes.error,
            message: 'Test error',
        }));
        expect(instance.messages.length).to.equal(1);
        expect(instance.showMessageModal).to.equal(true);
        expect(instance.isErrorModal).to.equal(true);

        instance.$store.dispatch('clearMessages');
    });
    it('should display an info modal', async () => {
        const wrapper = await mountShallow(App);
        const instance: any = wrapper.vm;

        instance.$store.dispatch('clearMessages');
        instance.$store.dispatch('addMessage', new AppMessage({
            type: MessageTypes.info,
            message: 'Test info',
        }));
        expect(instance.messages.length).to.equal(1);
        expect(instance.showMessageModal).to.equal(true);
        expect(instance.isErrorModal).to.equal(false);

        instance.$store.dispatch('clearMessages');
    });
    it('should successfully set auth type', async () => {
        const wrapper = await mountShallow(App);
        const component = wrapper.vm;
        const authType = await component.setAuthType();

        expect(authType).to.equal(AuthTypes.PUBLIC);
    });
});
