//
//  user.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 6/12/24.
//

import mutations, { MutationTypes } from './user.mutations';
import actions from './user.actions';

const chaiMatchPattern = require('chai-match-pattern');
const chai = require('chai').use(chaiMatchPattern);
const sinon = require('sinon');

const { expect } = chai;

describe('Use Store Mutations', () => {
    it('should successfully get login request', () => {
        const state = {};

        mutations[MutationTypes.LOGIN_REQUEST](state);

        expect(state.isLoading).to.equal(true);
        expect(state.error).to.equal(null);
    });
    it('should successfully get login failure', () => {
        const state = {};
        const error = new Error();

        mutations[MutationTypes.LOGIN_FAILURE](state, error);

        expect(state.isLoading).to.equal(false);
        expect(state.error).to.equal(error);
    });
    it('should successfully get login success', () => {
        const state = {};

        mutations[MutationTypes.LOGIN_SUCCESS](state);

        expect(state.isLoading).to.equal(false);
        expect(state.isLoggedIn).to.equal(true);
        expect(state.error).to.equal(null);
    });
    it('should successfully get login reset', () => {
        const state = {};

        mutations[MutationTypes.LOGIN_RESET](state);

        expect(state.error).to.equal(null);
    });
    it('should successfully get logout request', () => {
        const state = {};

        mutations[MutationTypes.LOGOUT_REQUEST](state);

        expect(state.isLoading).to.equal(true);
    });
    it('should successfully get logout failure', () => {
        const state = {};
        const error = new Error();

        mutations[MutationTypes.LOGOUT_FAILURE](state, error);

        expect(state.isLoading).to.equal(false);
        expect(state.error).to.equal(error);
    });
    it('should successfully get logout success', () => {
        const state = {};

        mutations[MutationTypes.LOGOUT_SUCCESS](state);

        expect(state.model).to.equal(null);
        expect(state.isLoading).to.equal(false);
        expect(state.isLoggedIn).to.equal(false);
        expect(state.error).to.equal(null);
    });
    it('should successfully get account request', () => {
        const state = {};

        mutations[MutationTypes.GET_ACCOUNT_REQUEST](state);

        expect(state.isLoading).to.equal(true);
        expect(state.error).to.equal(null);
    });
    it('should successfully get account failure', () => {
        const state = {};
        const error = new Error();

        mutations[MutationTypes.GET_ACCOUNT_FAILURE](state, error);

        expect(state.isLoading).to.equal(false);
        expect(state.error).to.equal(error);
    });
    it('should successfully get account success', () => {
        const state = {};

        mutations[MutationTypes.GET_ACCOUNT_SUCCESS](state);

        expect(state.isLoading).to.equal(false);
        expect(state.error).to.equal(null);
    });
    it('should successfully update user', () => {
        const state = {};
        const user = { id: 1 };

        mutations[MutationTypes.STORE_UPDATE_USER](state, user);

        expect(state.model).to.equal(user);
    });
    it('should successfully reset user', () => {
        const state = {};

        mutations[MutationTypes.STORE_RESET_USER](state);

        expect(state.model).to.equal(null);
        expect(state.isLoading).to.equal(false);
        expect(state.error).to.equal(null);
    });
    it('should successfully update account request', () => {
        const state = {};

        mutations[MutationTypes.UPDATE_ACCOUNT_REQUEST](state);

        expect(state.isLoading).to.equal(true);
        expect(state.error).to.equal(null);
    });
    it('should successfully update account failure', () => {
        const state = {};
        const error = new Error();

        mutations[MutationTypes.UPDATE_ACCOUNT_FAILURE](state, error);

        expect(state.isLoading).to.equal(false);
        expect(state.error).to.equal(error);
    });
    it('should successfully update account success', () => {
        const state = {};

        mutations[MutationTypes.UPDATE_ACCOUNT_SUCCESS](state);

        expect(state.isLoading).to.equal(false);
        expect(state.error).to.equal(null);
    });
});
describe('User Store Actions', async () => {
    it('should successfully start login request', () => {
        const commit = sinon.spy();

        actions.loginRequest({ commit });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.LOGIN_REQUEST]);
    });
    it('should successfully start login success', async () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();

        await actions.loginSuccess({ commit, dispatch });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.LOGIN_SUCCESS]);
        expect(dispatch.calledOnce).to.equal(true);
    });
    it('should successfully start login failure', () => {
        const commit = sinon.spy();
        const error = new Error();

        actions.loginFailure({ commit }, error);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.LOGIN_FAILURE, error]);
    });
    it('should successfully start logout request', () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();

        actions.logoutRequest({ commit, dispatch });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.LOGOUT_REQUEST]);
        expect(dispatch.callCount).to.equal(4);
    });
    it('should successfully start logout success', () => {
        const commit = sinon.spy();

        actions.logoutSuccess({ commit });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.LOGOUT_SUCCESS]);
    });
    it('should successfully start logout failure', () => {
        const commit = sinon.spy();
        const error = new Error();

        actions.logoutFailure({ commit }, error);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.LOGOUT_FAILURE, error]);
    });
    it('should successfully start account request', async () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();

        await actions.getAccountRequest({ commit, dispatch });

        expect(commit.calledOnce, 'commit').to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.GET_ACCOUNT_REQUEST]);
        expect(dispatch.calledOnce, 'dispatch').to.equal(true);
    });
    it('should successfully start account success', () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();
        const account = {};

        actions.getAccountSuccess({ commit, dispatch }, account);

        expect(commit.calledOnce, 'commit').to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.GET_ACCOUNT_SUCCESS, account]);
        expect(dispatch.calledOnce, 'dispatch').to.equal(true);
    });
    it('should successfully start account failure', () => {
        const commit = sinon.spy();
        const error = new Error();

        actions.getAccountFailure({ commit }, error);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.GET_ACCOUNT_FAILURE, error]);
    });
    it('should successfully set user', () => {
        const commit = sinon.spy();
        const user = {};

        actions.setStoreUser({ commit }, user);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.STORE_UPDATE_USER, user]);
    });
    it('should successfully reset user', () => {
        const commit = sinon.spy();

        actions.resetStoreUser({ commit });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.STORE_RESET_USER]);
    });
    it('should successfully clear session stores', () => {
        const dispatch = sinon.spy();

        actions.clearSessionStores({ dispatch });

        expect(dispatch.callCount).to.equal(4);
    });
});
