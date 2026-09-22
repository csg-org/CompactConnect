//
//  App.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

import chaiMatchPattern from 'chai-match-pattern';
import { use, expect } from 'chai';
import { nextTick } from 'vue';
import { flushPromises } from '@vue/test-utils';
import sinon from 'sinon';
import { AuthTypes } from '@utils/auth';
import { mountShallow } from '@tests/helpers/setup';
import App from '@components/App/App.vue';
import store from '@/store';
import { AppModes } from '@/app.config';
import { Compact, CompactType } from '@models/Compact/Compact.model';
import { MutationTypes } from '@/store/user/user.mutations';
import { MessageTypes, AppMessage } from '@/models/AppMessage/AppMessage.model';

use(chaiMatchPattern);

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
    it('should successfully clear the search stores when the app mode changes', async () => {
        const wrapper = await mountShallow(App);

        await flushPromises(); // Let created() settle before changing the mode under test
        await store.dispatch('setAppMode', AppModes.JCC);
        await store.dispatch('license/setStoreSearch', { compact: 'aslp', firstName: 'Test' });
        await store.dispatch('pagination/updatePaginationPage', { paginationId: 'licensees', newPage: 3 });
        await store.dispatch('sorting/updateSortOption', { sortingId: 'licensees', newOption: 'lastName' });
        await store.dispatch('setAppMode', AppModes.PSYPACT);
        await nextTick();
        await flushPromises();

        expect(wrapper.vm.$appMode).to.equal(AppModes.PSYPACT);
        expect(store.state.license.search).to.matchPattern({
            compact: '',
            firstName: '',
            lastName: '',
            state: '',
            licenseNumber: '',
        });
        expect(store.state.pagination.paginationMap).to.matchPattern({});
        expect(store.state.sorting.sortingMap).to.matchPattern({});
    });
    it('should successfully set the page title for the app mode', async () => {
        await mountShallow(App);

        await flushPromises();
        await store.dispatch('setAppMode', AppModes.JCC);
        await nextTick();

        expect(document.title).to.equal('CompactConnect');

        await store.dispatch('setAppMode', AppModes.PSYPACT);
        await nextTick();

        expect(document.title).to.equal('PSYPACT');
    });
    it('should fetch compact member states when a seeded compact has none', async () => {
        // Seed via mutation so setCurrentCompact's side-effect fetch does not run first
        store.commit(`user/${MutationTypes.STORE_UPDATE_CURRENT_COMPACT}`, new Compact({ type: CompactType.PSYPACT }));

        const dispatchSpy = sinon.spy(store, 'dispatch');

        await mountShallow(App);
        await flushPromises();

        expect(dispatchSpy.calledWith('user/getCompactStatesRequest', { compact: CompactType.PSYPACT })).to.equal(true);
    });
});
