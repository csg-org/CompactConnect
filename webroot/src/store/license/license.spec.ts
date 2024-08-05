//
//  license.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 7/2/24.
//

import mutations, { MutationTypes } from './license.mutations';
import actions from './license.actions';
import getters from './license.getters';

const chaiMatchPattern = require('chai-match-pattern');
const chai = require('chai').use(chaiMatchPattern);
const sinon = require('sinon');

const { expect } = chai;

describe('License Store Mutations', () => {
    it('should successfully get licensees request', () => {
        const state = {};

        mutations[MutationTypes.GET_LICENSEES_REQUEST](state);

        expect(state.isLoading).to.equal(true);
        expect(state.error).to.equal(null);
    });
    it('should successfully get licensees failure', () => {
        const state = {};
        const error = new Error();

        mutations[MutationTypes.GET_LICENSEES_FAILURE](state, error);

        expect(state.isLoading).to.equal(false);
        expect(state.error).to.equal(error);
    });
    it('should successfully get licensees success', () => {
        const state = {};

        mutations[MutationTypes.GET_LICENSEES_SUCCESS](state);

        expect(state.isLoading).to.equal(false);
        expect(state.error).to.equal(null);
    });
    it('should successfully update count', () => {
        const state = {};
        const count = 1;

        mutations[MutationTypes.STORE_UPDATE_COUNT](state, count);

        expect(state.total).to.equal(count);
    });
    it('should successfully set licensees', () => {
        const state = {};
        const licensees = [];

        mutations[MutationTypes.STORE_SET_LICENSEES](state, licensees);

        expect(state.model).to.equal(licensees);
    });
    it('should successfully update licensee (missing id)', () => {
        const state = {};
        const licensee = {};

        mutations[MutationTypes.STORE_UPDATE_LICENSEE](state, licensee);

        expect(state).to.equal(state);
    });
    it('should successfully update licensee (not already in store - empty store)', () => {
        const state = {};
        const licensee = { id: 1 };

        mutations[MutationTypes.STORE_UPDATE_LICENSEE](state, licensee);

        expect(state.model).to.matchPattern([licensee]);
    });
    it('should successfully update licensee (not already in store - non-empty store)', () => {
        const state = { model: [{ id: 2 }]};
        const licensee = { id: 1 };

        mutations[MutationTypes.STORE_UPDATE_LICENSEE](state, licensee);

        expect(state.model).to.matchPattern([ { id: 2 }, licensee]);
    });
    it('should successfully update licensee (already in store)', () => {
        const state = { model: [{ id: 1, name: 'test1' }]};
        const licensee = { id: 1, name: 'test2' };

        mutations[MutationTypes.STORE_UPDATE_LICENSEE](state, licensee);

        expect(state.model).to.matchPattern([licensee]);
    });
    it('should successfully remove licensee (id missing)', () => {
        const state = {};
        const licenseeId = '';

        mutations[MutationTypes.STORE_REMOVE_LICENSEE](state, licenseeId);

        expect(state).to.equal(state);
    });
    it('should successfully remove licensee (not already in store)', () => {
        const state = {};
        const licenseeId = 1;

        mutations[MutationTypes.STORE_REMOVE_LICENSEE](state, licenseeId);

        expect(state).to.equal(state);
    });
    it('should successfully remove licensee (already in store)', () => {
        const state = { model: [{ id: 1 }, { id: 2 }]};
        const licenseeId = 1;

        mutations[MutationTypes.STORE_REMOVE_LICENSEE](state, licenseeId);

        expect(state.model).to.matchPattern([{ id: 2 }]);
    });
    it('should successfully remove licensee (already in store - only record)', () => {
        const state = { model: [{ id: 1 }]};
        const licenseeId = 1;

        mutations[MutationTypes.STORE_REMOVE_LICENSEE](state, licenseeId);

        expect(state.model).to.matchPattern([]);
    });
    it('should successfully reset license store', () => {
        const state = {
            model: [{ id: 1 }],
            total: 1,
            isLoading: true,
            error: new Error(),
        };

        mutations[MutationTypes.STORE_RESET_LICENSE](state);

        expect(state).to.matchPattern({
            model: null,
            total: 0,
            isLoading: false,
            error: null,
        });
    });
});
describe('License Store Actions', async () => {
    it('should successfully start licensees request', async () => {
        const commit = sinon.spy();
        // const getters = sinon.spy();
        const dispatch = sinon.spy();
        const params = { getNextPage: true };

        await actions.getLicenseesRequest({ commit, getters, dispatch }, { params });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.GET_LICENSEES_REQUEST]);
        expect(dispatch.calledThrice).to.equal(true);
    });
    it('should successfully start licensees failure', () => {
        const commit = sinon.spy();
        const error = new Error();

        actions.getLicenseesFailure({ commit }, error);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.GET_LICENSEES_FAILURE, error]);
    });
    it('should successfully start licensees success', () => {
        const commit = sinon.spy();

        actions.getLicenseesSuccess({ commit });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.GET_LICENSEES_SUCCESS]);
    });
    it('should successfully start licensee request', async () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();
        const licenseeId = '1';
        const params = {};

        await actions.getLicenseeRequest({ commit, dispatch }, { licenseeId, params });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.GET_LICENSEE_REQUEST]);
        expect(dispatch.calledTwice).to.equal(true);
    });
    it('should successfully start licensee failure', () => {
        const commit = sinon.spy();
        const error = new Error();

        actions.getLicenseeFailure({ commit }, error);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.GET_LICENSEE_FAILURE, error]);
    });
    it('should successfully start licensee success', () => {
        const commit = sinon.spy();

        actions.getLicenseeSuccess({ commit });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.GET_LICENSEE_SUCCESS]);
    });
    it('should successfully set paging last key', () => {
        const commit = sinon.spy();
        const lastKey = 'abc';

        actions.setStoreLicenseeLastKey({ commit }, lastKey);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.STORE_UPDATE_LASTKEY, lastKey]);
    });
    it('should successfully set paging count', () => {
        const commit = sinon.spy();
        const count = 'abc';

        actions.setStoreLicenseeCount({ commit }, count);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.STORE_UPDATE_COUNT, count]);
    });
    it('should successfully set licensees', () => {
        const commit = sinon.spy();
        const licensees = [];

        actions.setStoreLicensees({ commit }, licensees);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.STORE_SET_LICENSEES, licensees]);
    });
    it('should successfully set licensee', () => {
        const commit = sinon.spy();
        const licensee = { id: '1' };

        actions.setStoreLicensee({ commit }, licensee);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.STORE_UPDATE_LICENSEE, licensee]);
    });
    it('should successfully reset store', () => {
        const commit = sinon.spy();

        actions.resetStoreLicense({ commit });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.STORE_RESET_LICENSE]);
    });
});
describe('License Store Getters', async () => {
    it('should successfully get paging last key', async () => {
        const state = { lastKey: 'abc' };
        const lastKey = getters.lastKey(state);

        expect(lastKey).to.equal(state.lastKey);
    });
    it('should successfully get licensee by id (not found)', async () => {
        const state = {};
        const licensee = getters.licenseeById(state)('1');

        expect(licensee).to.equal(undefined);
    });
    it('should successfully get licensee by id (found)', async () => {
        const record = { id: '1' };
        const state = { model: [record]};
        const licensee = getters.licenseeById(state)('1');

        expect(licensee).to.matchPattern(record);
    });
});
