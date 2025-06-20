//
//  users.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 9/4/24.
//

import mutations, { MutationTypes } from './users.mutations';
import actions from './users.actions';
import getters from './users.getters';

const chaiMatchPattern = require('chai-match-pattern');
const chai = require('chai').use(chaiMatchPattern);
const sinon = require('sinon');

const { expect } = chai;

describe('Users Store Mutations', () => {
    it('should successfully get users request', () => {
        const state = {};

        mutations[MutationTypes.GET_USERS_REQUEST](state);

        expect(state.isLoading).to.equal(true);
        expect(state.error).to.equal(null);
    });
    it('should successfully get users failure', () => {
        const state = {};
        const error = new Error();

        mutations[MutationTypes.GET_USERS_FAILURE](state, error);

        expect(state.isLoading).to.equal(false);
        expect(state.error).to.equal(error);
    });
    it('should successfully get users success', () => {
        const state = {};

        mutations[MutationTypes.GET_USERS_SUCCESS](state);

        expect(state.isLoading).to.equal(false);
        expect(state.error).to.equal(null);
    });
    it('should successfully update previous last key', () => {
        const state = {};
        const prevLastKey = 'abc';

        mutations[MutationTypes.STORE_UPDATE_PREVLASTKEY](state, prevLastKey);

        expect(state.prevLastKey).to.equal(prevLastKey);
    });
    it('should successfully update last key', () => {
        const state = {};
        const lastKey = 'abc';

        mutations[MutationTypes.STORE_UPDATE_LASTKEY](state, lastKey);

        expect(state.lastKey).to.equal(lastKey);
    });
    it('should successfully update count', () => {
        const state = {};
        const count = 1;

        mutations[MutationTypes.STORE_UPDATE_COUNT](state, count);

        expect(state.total).to.equal(count);
    });
    it('should successfully set users', () => {
        const state = {};
        const users = [];

        mutations[MutationTypes.STORE_SET_USERS](state, users);

        expect(state.model).to.equal(users);
    });
    it('should successfully create user request', () => {
        const state = {};

        mutations[MutationTypes.CREATE_USER_REQUEST](state);

        expect(state.isLoading).to.equal(true);
        expect(state.error).to.equal(null);
    });
    it('should successfully create user failure', () => {
        const state = {};
        const error = new Error();

        mutations[MutationTypes.CREATE_USER_FAILURE](state, error);

        expect(state.isLoading).to.equal(false);
        expect(state.error).to.equal(error);
    });
    it('should successfully create user success', () => {
        const state = {};

        mutations[MutationTypes.CREATE_USER_SUCCESS](state);

        expect(state.isLoading).to.equal(false);
        expect(state.error).to.equal(null);
    });
    it('should successfully get user request', () => {
        const state = {};

        mutations[MutationTypes.GET_USER_REQUEST](state);

        expect(state.isLoading).to.equal(true);
        expect(state.error).to.equal(null);
    });
    it('should successfully get user failure', () => {
        const state = {};
        const error = new Error();

        mutations[MutationTypes.GET_USER_FAILURE](state, error);

        expect(state.isLoading).to.equal(false);
        expect(state.error).to.equal(error);
    });
    it('should successfully get user success', () => {
        const state = {};

        mutations[MutationTypes.GET_USER_SUCCESS](state);

        expect(state.isLoading).to.equal(false);
        expect(state.error).to.equal(null);
    });
    it('should successfully update user request', () => {
        const state = {};

        mutations[MutationTypes.UPDATE_USER_REQUEST](state);

        expect(state.isLoading).to.equal(true);
        expect(state.error).to.equal(null);
    });
    it('should successfully update user failure', () => {
        const state = {};
        const error = new Error();

        mutations[MutationTypes.UPDATE_USER_FAILURE](state, error);

        expect(state.isLoading).to.equal(false);
        expect(state.error).to.equal(error);
    });
    it('should successfully update user success', () => {
        const state = {};

        mutations[MutationTypes.UPDATE_USER_SUCCESS](state);

        expect(state.isLoading).to.equal(false);
        expect(state.error).to.equal(null);
    });
    it('should successfully reinvite user request', () => {
        const state = {};

        mutations[MutationTypes.REINVITE_USER_REQUEST](state);

        expect(state.isLoading).to.equal(false);
        expect(state.error).to.equal(null);
    });
    it('should successfully reinvite user failure', () => {
        const state = {};

        mutations[MutationTypes.REINVITE_USER_FAILURE](state);

        expect(state.isLoading).to.equal(false);
        expect(state.error).to.equal(null);
    });
    it('should successfully reinvite user success', () => {
        const state = {};

        mutations[MutationTypes.REINVITE_USER_SUCCESS](state);

        expect(state.isLoading).to.equal(false);
        expect(state.error).to.equal(null);
    });
    it('should successfully delete user request', () => {
        const state = {};

        mutations[MutationTypes.DELETE_USER_REQUEST](state);

        expect(state.isLoading).to.equal(false);
        expect(state.error).to.equal(null);
    });
    it('should successfully delete user failure', () => {
        const state = {};

        mutations[MutationTypes.DELETE_USER_FAILURE](state);

        expect(state.isLoading).to.equal(false);
        expect(state.error).to.equal(null);
    });
    it('should successfully delete user success', () => {
        const state = {};

        mutations[MutationTypes.DELETE_USER_SUCCESS](state);

        expect(state.isLoading).to.equal(false);
        expect(state.error).to.equal(null);
    });
    it('should successfully encumber license request', () => {
        const state = {};

        mutations[MutationTypes.ENCUMBER_LICENSE_REQUEST](state);

        expect(state.isLoading).to.equal(true);
        expect(state.error).to.equal(null);
    });
    it('should successfully encumber license failure', () => {
        const state = {};
        const error = new Error();

        mutations[MutationTypes.ENCUMBER_LICENSE_FAILURE](state, error);

        expect(state.isLoading).to.equal(false);
        expect(state.error).to.equal(error);
    });
    it('should successfully encumber license success', () => {
        const state = {};

        mutations[MutationTypes.ENCUMBER_LICENSE_SUCCESS](state);

        expect(state.isLoading).to.equal(false);
        expect(state.error).to.equal(null);
    });
    it('should successfully unencumber license request', () => {
        const state = {};

        mutations[MutationTypes.UNENCUMBER_LICENSE_REQUEST](state);

        expect(state.isLoading).to.equal(true);
        expect(state.error).to.equal(null);
    });
    it('should successfully unencumber license failure', () => {
        const state = {};
        const error = new Error();

        mutations[MutationTypes.UNENCUMBER_LICENSE_FAILURE](state, error);

        expect(state.isLoading).to.equal(false);
        expect(state.error).to.equal(error);
    });
    it('should successfully unencumber license success', () => {
        const state = {};

        mutations[MutationTypes.UNENCUMBER_LICENSE_SUCCESS](state);

        expect(state.isLoading).to.equal(false);
        expect(state.error).to.equal(null);
    });
    it('should successfully delete privilege request', () => {
        const state = {};

        mutations[MutationTypes.DELETE_PRIVILEGE_REQUEST](state);

        expect(state.isLoading).to.equal(true);
        expect(state.error).to.equal(null);
    });
    it('should successfully delete privilege failure', () => {
        const state = {};
        const error = new Error();

        mutations[MutationTypes.DELETE_PRIVILEGE_FAILURE](state, error);

        expect(state.isLoading).to.equal(false);
        expect(state.error).to.equal(error);
    });
    it('should successfully delete privilege success', () => {
        const state = {};

        mutations[MutationTypes.DELETE_PRIVILEGE_SUCCESS](state);

        expect(state.isLoading).to.equal(false);
        expect(state.error).to.equal(null);
    });
    it('should successfully encumber privilege request', () => {
        const state = {};

        mutations[MutationTypes.ENCUMBER_PRIVILEGE_REQUEST](state);

        expect(state.isLoading).to.equal(true);
        expect(state.error).to.equal(null);
    });
    it('should successfully encumber privilege failure', () => {
        const state = {};
        const error = new Error();

        mutations[MutationTypes.ENCUMBER_PRIVILEGE_FAILURE](state, error);

        expect(state.isLoading).to.equal(false);
        expect(state.error).to.equal(error);
    });
    it('should successfully encumber privilege success', () => {
        const state = {};

        mutations[MutationTypes.ENCUMBER_PRIVILEGE_SUCCESS](state);

        expect(state.isLoading).to.equal(false);
        expect(state.error).to.equal(null);
    });
    it('should successfully unencumber privilege request', () => {
        const state = {};

        mutations[MutationTypes.UNENCUMBER_PRIVILEGE_REQUEST](state);

        expect(state.isLoading).to.equal(true);
        expect(state.error).to.equal(null);
    });
    it('should successfully unencumber privilege failure', () => {
        const state = {};
        const error = new Error();

        mutations[MutationTypes.UNENCUMBER_PRIVILEGE_FAILURE](state, error);

        expect(state.isLoading).to.equal(false);
        expect(state.error).to.equal(error);
    });
    it('should successfully unencumber privilege success', () => {
        const state = {};

        mutations[MutationTypes.UNENCUMBER_PRIVILEGE_SUCCESS](state);

        expect(state.isLoading).to.equal(false);
        expect(state.error).to.equal(null);
    });
    it('should successfully update user (missing id)', () => {
        const state = {};
        const user = {};

        mutations[MutationTypes.STORE_UPDATE_USER](state, user);

        expect(state).to.equal(state);
    });
    it('should successfully update user (not already in store - empty store)', () => {
        const state = {};
        const user = { id: 1 };

        mutations[MutationTypes.STORE_UPDATE_USER](state, user);

        expect(state.model).to.matchPattern([user]);
    });
    it('should successfully update user (not already in store - non-empty store)', () => {
        const state = { model: [{ id: 2 }] };
        const user = { id: 1 };

        mutations[MutationTypes.STORE_UPDATE_USER](state, user);

        expect(state.model).to.matchPattern([ { id: 2 }, user]);
    });
    it('should successfully update user (already in store)', () => {
        const state = { model: [{ id: 1, name: 'test1' }] };
        const user = { id: 1, name: 'test2' };

        mutations[MutationTypes.STORE_UPDATE_USER](state, user);

        expect(state.model).to.matchPattern([user]);
    });
    it('should successfully remove user (id missing)', () => {
        const state = {};
        const userId = '';

        mutations[MutationTypes.STORE_REMOVE_USER](state, userId);

        expect(state).to.equal(state);
    });
    it('should successfully remove user (not already in store)', () => {
        const state = {};
        const userId = 1;

        mutations[MutationTypes.STORE_REMOVE_USER](state, userId);

        expect(state).to.equal(state);
    });
    it('should successfully remove user (already in store)', () => {
        const state = { model: [{ id: 1 }, { id: 2 }] };
        const userId = 1;

        mutations[MutationTypes.STORE_REMOVE_USER](state, userId);

        expect(state.model).to.matchPattern([{ id: 2 }]);
    });
    it('should successfully remove user (already in store - only record)', () => {
        const state = { model: [{ id: 1 }] };
        const userId = 1;

        mutations[MutationTypes.STORE_REMOVE_USER](state, userId);

        expect(state.model).to.matchPattern([]);
    });
    it('should successfully reset users store', () => {
        const state = {
            model: [{ id: 1 }],
            total: 1,
            isLoading: true,
            error: new Error(),
        };

        mutations[MutationTypes.STORE_RESET_USERS](state);

        expect(state).to.matchPattern({
            model: null,
            total: 0,
            isLoading: false,
            error: null,
        });
    });
});
describe('Users Store Actions', async () => {
    it('should successfully start get-users request with next page', async () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();
        const params = { getNextPage: true };

        await actions.getUsersRequest({ commit, getters, dispatch }, { params });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.GET_USERS_REQUEST]);
        expect(dispatch.callCount).to.equal(4);
    });
    it('should successfully start get-users request with previous page', async () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();
        const params = { getPrevPage: true };

        await actions.getUsersRequest({ commit, getters, dispatch }, { params });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.GET_USERS_REQUEST]);
        expect(dispatch.callCount).to.equal(4);
    });
    it('should successfully start get-users failure', () => {
        const commit = sinon.spy();
        const error = new Error();

        actions.getUsersFailure({ commit }, error);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.GET_USERS_FAILURE, error]);
    });
    it('should successfully start get-users success', () => {
        const commit = sinon.spy();

        actions.getUsersSuccess({ commit });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.GET_USERS_SUCCESS]);
    });
    it('should successfully set paging previous last key', () => {
        const commit = sinon.spy();
        const prevLastKey = 'abc';

        actions.setStoreUsersPrevLastKey({ commit }, prevLastKey);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.STORE_UPDATE_PREVLASTKEY, prevLastKey]);
    });
    it('should successfully set paging last key', () => {
        const commit = sinon.spy();
        const lastKey = 'abc';

        actions.setStoreUsersLastKey({ commit }, lastKey);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.STORE_UPDATE_LASTKEY, lastKey]);
    });
    it('should successfully set paging count', () => {
        const commit = sinon.spy();
        const count = 'abc';

        actions.setStoreUsersCount({ commit }, count);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.STORE_UPDATE_COUNT, count]);
    });
    it('should successfully set users', () => {
        const commit = sinon.spy();
        const users = [];

        actions.setStoreUsers({ commit }, users);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.STORE_SET_USERS, users]);
    });
    it('should successfully start create-user request', async () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();
        const compact = 'aslp';
        const data = {};

        await actions.createUserRequest({ commit, dispatch }, { compact, data });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.CREATE_USER_REQUEST]);
        expect(dispatch.calledTwice).to.equal(true);
    });
    it('should successfully start create-user failure', () => {
        const commit = sinon.spy();
        const error = new Error();

        actions.createUserFailure({ commit }, error);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.CREATE_USER_FAILURE, error]);
    });
    it('should successfully start create-user success', () => {
        const commit = sinon.spy();

        actions.createUserSuccess({ commit });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.CREATE_USER_SUCCESS]);
    });
    it('should successfully start get-user request', async () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();
        const compact = 'aslp';
        const userId = '1';

        await actions.getUserRequest({ commit, dispatch }, { compact, userId });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.GET_USER_REQUEST]);
        expect(dispatch.calledTwice).to.equal(true);
    });
    it('should successfully start get-user failure', () => {
        const commit = sinon.spy();
        const error = new Error();

        actions.getUserFailure({ commit }, error);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.GET_USER_FAILURE, error]);
    });
    it('should successfully start get-user success', () => {
        const commit = sinon.spy();

        actions.getUserSuccess({ commit });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.GET_USER_SUCCESS]);
    });
    it('should successfully start update-user request', async () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();
        const compact = 'aslp';
        const data = {};

        await actions.updateUserRequest({ commit, dispatch }, { compact, data });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.UPDATE_USER_REQUEST]);
        expect(dispatch.calledTwice).to.equal(true);
    });
    it('should successfully start update-user failure', () => {
        const commit = sinon.spy();
        const error = new Error();

        actions.updateUserFailure({ commit }, error);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.UPDATE_USER_FAILURE, error]);
    });
    it('should successfully start update-user success', () => {
        const commit = sinon.spy();

        actions.updateUserSuccess({ commit });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.UPDATE_USER_SUCCESS]);
    });
    it('should successfully start reinvite-user request', async () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();
        const compact = 'aslp';
        const userId = '1';

        await actions.reinviteUserRequest({ commit, dispatch }, { compact, userId });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.REINVITE_USER_REQUEST]);
        expect(dispatch.calledOnce).to.equal(true);
    });
    it('should successfully start reinvite-user failure', () => {
        const commit = sinon.spy();
        const error = new Error();

        actions.reinviteUserFailure({ commit }, error);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.REINVITE_USER_FAILURE, error]);
    });
    it('should successfully start reinvite-user success', () => {
        const commit = sinon.spy();

        actions.reinviteUserSuccess({ commit });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.REINVITE_USER_SUCCESS]);
    });
    it('should successfully start delete-user request', async () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();
        const compact = 'aslp';
        const userId = '1';

        await actions.deleteUserRequest({ commit, dispatch }, { compact, userId });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.DELETE_USER_REQUEST]);
        expect(dispatch.calledOnce).to.equal(true);
    });
    it('should successfully start delete-user failure', () => {
        const commit = sinon.spy();
        const error = new Error();

        actions.deleteUserFailure({ commit }, error);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.DELETE_USER_FAILURE, error]);
    });
    it('should successfully start delete-user success', () => {
        const commit = sinon.spy();

        actions.deleteUserSuccess({ commit });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.DELETE_USER_SUCCESS]);
    });
    it('should successfully start encumber-license request', async () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();
        const compact = 'aslp';
        const licenseeId = '1';
        const licenseState = 'co';
        const licenseType = 'test';
        const npdbCategory = 'test';
        const startDate = 'test';

        await actions.encumberLicenseRequest({ commit, dispatch }, {
            compact, licenseeId, licenseState, licenseType, npdbCategory, startDate
        });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.ENCUMBER_LICENSE_REQUEST]);
        expect(dispatch.calledOnce).to.equal(true);
    });
    it('should successfully start encumber-license request (intentional error)', async () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();

        await actions.encumberLicenseRequest({ commit, dispatch }, {}).catch((error) => {
            expect(error).to.be.an('error').with.property('message', 'failed license encumber');
        });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.ENCUMBER_LICENSE_REQUEST]);
        expect(dispatch.calledOnce).to.equal(true);
        expect(dispatch.firstCall.args[0]).to.equal('encumberLicenseFailure');
    });
    it('should successfully start encumber-license failure', () => {
        const commit = sinon.spy();
        const error = new Error();

        actions.encumberLicenseFailure({ commit }, error);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.ENCUMBER_LICENSE_FAILURE, error]);
    });
    it('should successfully start encumber-license success', () => {
        const commit = sinon.spy();

        actions.encumberLicenseSuccess({ commit });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.ENCUMBER_LICENSE_SUCCESS]);
    });
    it('should successfully start unencumber-license request', async () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();
        const compact = 'aslp';
        const licenseeId = '1';
        const licenseState = 'co';
        const licenseType = 'test';
        const encumbranceId = 'test';
        const endDate = 'test';

        await actions.unencumberLicenseRequest({ commit, dispatch }, {
            compact, licenseeId, licenseState, licenseType, encumbranceId, endDate
        });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.UNENCUMBER_LICENSE_REQUEST]);
        expect(dispatch.calledOnce).to.equal(true);
    });
    it('should successfully start unencumber-license request (intentional error)', async () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();

        await actions.unencumberLicenseRequest({ commit, dispatch }, {}).catch((error) => {
            expect(error).to.be.an('error').with.property('message', 'failed license unencumber');
        });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.UNENCUMBER_LICENSE_REQUEST]);
        expect(dispatch.calledOnce).to.equal(true);
        expect(dispatch.firstCall.args[0]).to.equal('unencumberLicenseFailure');
    });
    it('should successfully start unencumber-license failure', () => {
        const commit = sinon.spy();
        const error = new Error();

        actions.unencumberLicenseFailure({ commit }, error);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.UNENCUMBER_LICENSE_FAILURE, error]);
    });
    it('should successfully start unencumber-license success', () => {
        const commit = sinon.spy();

        actions.unencumberLicenseSuccess({ commit });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.UNENCUMBER_LICENSE_SUCCESS]);
    });
    it('should successfully start delete-privilege request', async () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();
        const compact = 'aslp';
        const licenseeId = '1';
        const privilegeState = 'co';
        const licenseType = 'test';
        const notes = 'test';

        await actions.deletePrivilegeRequest({ commit, dispatch }, {
            compact, licenseeId, privilegeState, licenseType, notes
        });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.DELETE_PRIVILEGE_REQUEST]);
        expect(dispatch.calledOnce).to.equal(true);
    });
    it('should successfully start delete-privilege request (intentional error)', async () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();

        await actions.deletePrivilegeRequest({ commit, dispatch }, {}).catch((error) => {
            expect(error).to.be.an('error').with.property('message', 'failed privilege delete');
        });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.DELETE_PRIVILEGE_REQUEST]);
        expect(dispatch.calledOnce).to.equal(true);
        expect(dispatch.firstCall.args[0]).to.equal('deletePrivilegeFailure');
    });
    it('should successfully start delete-privilege failure', () => {
        const commit = sinon.spy();
        const error = new Error();

        actions.deletePrivilegeFailure({ commit }, error);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.DELETE_PRIVILEGE_FAILURE, error]);
    });
    it('should successfully start delete-privilege success', () => {
        const commit = sinon.spy();

        actions.deletePrivilegeSuccess({ commit });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.DELETE_PRIVILEGE_SUCCESS]);
    });
    it('should successfully start encumber-privilege request', async () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();
        const compact = 'aslp';
        const licenseeId = '1';
        const privilegeState = 'co';
        const licenseType = 'test';
        const npdbCategory = 'test';
        const startDate = 'test';

        await actions.encumberPrivilegeRequest({ commit, dispatch }, {
            compact, licenseeId, privilegeState, licenseType, npdbCategory, startDate
        });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.ENCUMBER_PRIVILEGE_REQUEST]);
        expect(dispatch.calledOnce).to.equal(true);
    });
    it('should successfully start encumber-privilege request (intentional error)', async () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();

        await actions.encumberPrivilegeRequest({ commit, dispatch }, {}).catch((error) => {
            expect(error).to.be.an('error').with.property('message', 'failed privilege encumber');
        });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.ENCUMBER_PRIVILEGE_REQUEST]);
        expect(dispatch.calledOnce).to.equal(true);
        expect(dispatch.firstCall.args[0]).to.equal('encumberPrivilegeFailure');
    });
    it('should successfully start encumber-privilege failure', () => {
        const commit = sinon.spy();
        const error = new Error();

        actions.encumberPrivilegeFailure({ commit }, error);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.ENCUMBER_PRIVILEGE_FAILURE, error]);
    });
    it('should successfully start encumber-privilege success', () => {
        const commit = sinon.spy();

        actions.encumberPrivilegeSuccess({ commit });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.ENCUMBER_PRIVILEGE_SUCCESS]);
    });
    it('should successfully start unencumber-privilege request', async () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();
        const compact = 'aslp';
        const licenseeId = '1';
        const privilegeState = 'co';
        const licenseType = 'test';
        const encumbranceId = 'test';
        const endDate = 'test';

        await actions.unencumberPrivilegeRequest({ commit, dispatch }, {
            compact, licenseeId, privilegeState, licenseType, encumbranceId, endDate
        });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.UNENCUMBER_PRIVILEGE_REQUEST]);
        expect(dispatch.calledOnce).to.equal(true);
    });
    it('should successfully start unencumber-privilege request (intentional error)', async () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();

        await actions.unencumberPrivilegeRequest({ commit, dispatch }, {}).catch((error) => {
            expect(error).to.be.an('error').with.property('message', 'failed privilege unencumber');
        });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.UNENCUMBER_PRIVILEGE_REQUEST]);
        expect(dispatch.calledOnce).to.equal(true);
        expect(dispatch.firstCall.args[0]).to.equal('unencumberPrivilegeFailure');
    });
    it('should successfully start unencumber-privilege failure', () => {
        const commit = sinon.spy();
        const error = new Error();

        actions.unencumberPrivilegeFailure({ commit }, error);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.UNENCUMBER_PRIVILEGE_FAILURE, error]);
    });
    it('should successfully start unencumber-privilege success', () => {
        const commit = sinon.spy();

        actions.unencumberPrivilegeSuccess({ commit });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.UNENCUMBER_PRIVILEGE_SUCCESS]);
    });
    it('should successfully set user', () => {
        const commit = sinon.spy();
        const user = { id: '1' };

        actions.setStoreUser({ commit }, user);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.STORE_UPDATE_USER, user]);
    });
    it('should successfully reset store', () => {
        const commit = sinon.spy();

        actions.resetStoreUsers({ commit });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.STORE_RESET_USERS]);
    });
});
describe('Users Store Getters', async () => {
    it('should successfully get paging previous last key', async () => {
        const state = { lastKey: 'abc' };
        const prevLastKey = getters.prevLastKey(state);

        expect(prevLastKey).to.equal(state.prevLastKey);
    });
    it('should successfully get paging last key', async () => {
        const state = { lastKey: 'abc' };
        const lastKey = getters.lastKey(state);

        expect(lastKey).to.equal(state.lastKey);
    });
    it('should successfully get user by id (not found)', async () => {
        const state = {};
        const user = getters.userById(state)('1');

        expect(user).to.equal(undefined);
    });
    it('should successfully get user by id (found)', async () => {
        const record = { id: '1' };
        const state = { model: [record] };
        const user = getters.userById(state)('1');

        expect(user).to.matchPattern(record);
    });
});
