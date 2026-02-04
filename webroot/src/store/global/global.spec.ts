//
//  global.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

import { AuthTypes, AppModes } from '@/app.config';
import mutations, { MutationTypes } from './global.mutations';
import actions from './global.actions';

const chaiMatchPattern = require('chai-match-pattern');
const chai = require('chai').use(chaiMatchPattern);
const sinon = require('sinon');

const { expect } = chai;

describe('Global Store Mutations', () => {
    it('should successfully begin loading', () => {
        const state = {};

        mutations[MutationTypes.BEGIN_LOADING](state);

        expect(state.isLoading).to.equal(true);
        expect(state.error).to.equal(null);
    });
    it('should successfully end loading', () => {
        const state = {};

        mutations[MutationTypes.END_LOADING](state);

        expect(state.isLoading).to.equal(false);
    });
    it('should successfully set error (Error)', () => {
        const state = {};
        const error = new Error();

        mutations[MutationTypes.SET_ERROR](state, error);

        expect(state.error).to.equal(error);
    });
    it('should successfully set error (null)', () => {
        const state = {};
        const error = '';

        mutations[MutationTypes.SET_ERROR](state, error);

        expect(state.error).to.equal(null);
    });
    it('should successfully push a message (no messages exist)', () => {
        const state = {};
        const message = 'message';

        mutations[MutationTypes.PUSH_MESSAGE](state, message);

        expect(state.messages).to.matchPattern([message]);
    });
    it('should successfully push a message (some messages exist)', () => {
        const state = { messages: [ 'existing' ] };
        const message = 'message';

        mutations[MutationTypes.PUSH_MESSAGE](state, message);

        expect(state.messages).to.matchPattern([ 'existing', message]);
    });
    it('should successfully clear messages', () => {
        const state = {};

        mutations[MutationTypes.CLEAR_MESSAGES](state);

        expect(state.messages).to.matchPattern([]);
    });
    it('should successfully reset store', () => {
        const state = {};

        mutations[MutationTypes.STORE_RESET_GLOBAL](state);

        expect(state).to.matchPattern({
            isLoading: false,
            error: null,
            messages: [],
            isModalOpen: false,
            isModalLogoutOnly: false,
        });
    });
    it('should successfully set modal open', () => {
        const state = {};
        const isModalOpen = true;

        mutations[MutationTypes.SET_MODAL_OPEN](state, isModalOpen);

        expect(state.isModalOpen).to.equal(isModalOpen);
    });
    it('should successfully set modal as logout-only', () => {
        const state = {};
        const isModalLogoutOnly = true;

        mutations[MutationTypes.SET_MODAL_LOGOUT_ONLY](state, isModalLogoutOnly);

        expect(state.isModalLogoutOnly).to.equal(isModalLogoutOnly);
    });
    it('should successfully set app mode', () => {
        const state = {};
        const appMode = AppModes.JCC;

        mutations[MutationTypes.SET_APP_MODE](state, appMode);

        expect(state.appMode).to.equal(appMode);
    });
    it('should successfully set auth type', () => {
        const state = {};
        const authType = AuthTypes.LICENSEE;

        mutations[MutationTypes.SET_AUTH_TYPE](state, authType);

        expect(state.authType).to.equal(authType);
    });
    it('should successfully set nav menu expand', () => {
        const state = {};

        mutations[MutationTypes.EXPAND_NAV_MENU](state);

        expect(state.isNavExpanded).to.equal(true);
    });
    it('should successfully set nav menu collapse', () => {
        const state = {};

        mutations[MutationTypes.COLLAPSE_NAV_MENU](state);

        expect(state.isNavExpanded).to.equal(false);
    });
});
describe('Global Store Actions', () => {
    it('should successfully start store loading', () => {
        const commit = sinon.spy();

        actions.startLoading({ commit });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.BEGIN_LOADING]);
    });
    it('should successfully end store loading', () => {
        const commit = sinon.spy();

        actions.endLoading({ commit });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.END_LOADING]);
    });
    it('should successfully reset store', () => {
        const commit = sinon.spy();

        actions.reset({ commit });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.STORE_RESET_GLOBAL]);
    });
    it('should successfully add message', () => {
        const commit = sinon.spy();
        const message = 'message';

        actions.addMessage({ commit }, message);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.PUSH_MESSAGE, message]);
    });
    it('should successfully clear messages', () => {
        const commit = sinon.spy();

        actions.clearMessages({ commit });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.CLEAR_MESSAGES]);
    });
    it('should successfully set modal to open', () => {
        const commit = sinon.spy();
        const isOpen = true;

        actions.setModalIsOpen({ commit }, isOpen);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.SET_MODAL_OPEN, isOpen]);
    });
    it('should successfully set modal to logout only', () => {
        const commit = sinon.spy();
        const isLogoutOnly = true;

        actions.setModalIsLogoutOnly({ commit }, isLogoutOnly);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.SET_MODAL_LOGOUT_ONLY, isLogoutOnly]);
    });
    it('should successfully set auth type', () => {
        const commit = sinon.spy();
        const authType = AuthTypes.LICENSEE;

        actions.setAuthType({ commit }, authType);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.SET_AUTH_TYPE, authType]);
    });
    it('should successfully set nav menu expand', () => {
        const commit = sinon.spy();

        actions.expandNavMenu({ commit });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.EXPAND_NAV_MENU]);
    });
    it('should successfully set nav menu collapse', () => {
        const commit = sinon.spy();

        actions.collapseNavMenu({ commit });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.COLLAPSE_NAV_MENU]);
    });
});
