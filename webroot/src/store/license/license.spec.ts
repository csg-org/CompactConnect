//
//  license.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 7/2/24.
//
import { License } from '@/models/License/License.model';
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
        const state = { model: [{ id: 2 }] };
        const licensee = { id: 1 };

        mutations[MutationTypes.STORE_UPDATE_LICENSEE](state, licensee);

        expect(state.model).to.matchPattern([ { id: 2 }, licensee]);
    });
    it('should successfully update licensee (already in store)', () => {
        const state = { model: [{ id: 1, name: 'test1' }] };
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
        const state = { model: [{ id: 1 }, { id: 2 }] };
        const licenseeId = 1;

        mutations[MutationTypes.STORE_REMOVE_LICENSEE](state, licenseeId);

        expect(state.model).to.matchPattern([{ id: 2 }]);
    });
    it('should successfully remove licensee (already in store - only record)', () => {
        const state = { model: [{ id: 1 }] };
        const licenseeId = 1;

        mutations[MutationTypes.STORE_REMOVE_LICENSEE](state, licenseeId);

        expect(state.model).to.matchPattern([]);
    });
    it('should successfully update license search values', () => {
        const state = {};
        const search = {
            compact: 'test',
            firstName: 'test',
            lastName: 'test',
            state: 'test',
        };

        mutations[MutationTypes.STORE_UPDATE_SEARCH](state, search);

        expect(state.search).to.matchPattern(search);
    });
    it('should successfully reset license search values', () => {
        const state = {
            search: {
                compact: 'test',
                firstName: 'test',
                lastName: 'test',
                state: 'test',
            },
        };

        mutations[MutationTypes.STORE_RESET_SEARCH](state);

        expect(state.search).to.matchPattern({
            compact: '',
            firstName: '',
            lastName: '',
            state: '',
        });
    });
    it('should successfully reset license store', () => {
        const state = {
            model: [{ id: 1 }],
            total: 1,
            isLoading: true,
            error: new Error(),
            search: {
                compact: 'test',
                firstName: 'test',
                lastName: 'test',
                state: 'test',
            },
        };

        mutations[MutationTypes.STORE_RESET_LICENSE](state);

        expect(state).to.matchPattern({
            model: null,
            total: 0,
            isLoading: false,
            error: null,
            search: {
                compact: '',
                firstName: '',
                lastName: '',
                state: '',
            },
        });
    });
    it('should successfully get licensee request', () => {
        const state = {};

        mutations[MutationTypes.GET_LICENSEE_REQUEST](state);

        expect(state.isLoading).to.equal(true);
        expect(state.error).to.equal(null);
    });
    it('should successfully get licensee failure', () => {
        const state = {};
        const error = new Error();

        mutations[MutationTypes.GET_LICENSEE_FAILURE](state, error);

        expect(state.isLoading).to.equal(false);
        expect(state.error).to.equal(error);
    });
    it('should successfully get licensee success', () => {
        const state = {};

        mutations[MutationTypes.GET_LICENSEE_SUCCESS](state);

        expect(state.isLoading).to.equal(false);
        expect(state.error).to.equal(null);
    });
});
describe('License Store Actions', async () => {
    it('should successfully start licensees request with next page', async () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();
        const params = { getNextPage: true };

        await actions.getLicenseesRequest({ commit, getters, dispatch }, { params });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.GET_LICENSEES_REQUEST]);
        expect(dispatch.callCount).to.equal(4);
    });
    it('should successfully start licensees request with previous page', async () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();
        const params = { getPrevPage: true };

        await actions.getLicenseesRequest({ commit, getters, dispatch }, { params });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.GET_LICENSEES_REQUEST]);
        expect(dispatch.callCount).to.equal(4);
    });
    it('should successfully start licensees request as public request', async () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();
        const params = { isPublic: true };

        await actions.getLicenseesRequest({ commit, getters, dispatch }, { params });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.GET_LICENSEES_REQUEST]);
        expect(dispatch.callCount).to.equal(4);
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
        const compact = 'aslp';
        const licenseeId = '1';

        await actions.getLicenseeRequest({ commit, dispatch }, { compact, licenseeId });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.GET_LICENSEE_REQUEST]);
        expect(dispatch.calledOnce).to.equal(true);
    });
    it('should successfully start licensee request as public request', async () => {
        const commit = sinon.spy();
        const dispatch = sinon.spy();
        const compact = 'aslp';
        const licenseeId = '1';
        const isPublic = true;

        await actions.getLicenseeRequest({ commit, dispatch }, { compact, licenseeId, isPublic });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.GET_LICENSEE_REQUEST]);
        expect(dispatch.calledOnce).to.equal(true);
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
    it('should successfully set paging previous last key', () => {
        const commit = sinon.spy();
        const prevLastKey = 'abc';

        actions.setStoreLicenseePrevLastKey({ commit }, prevLastKey);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.STORE_UPDATE_PREVLASTKEY, prevLastKey]);
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
    it('should successfully update search', () => {
        const commit = sinon.spy();
        const search = { firstName: 'test' };

        actions.setStoreSearch({ commit }, search);

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.STORE_UPDATE_SEARCH, search]);
    });
    it('should successfully reset search', () => {
        const commit = sinon.spy();

        actions.resetStoreSearch({ commit });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.STORE_RESET_SEARCH]);
    });
    it('should successfully reset store', () => {
        const commit = sinon.spy();

        actions.resetStoreLicense({ commit });

        expect(commit.calledOnce).to.equal(true);
        expect(commit.firstCall.args).to.matchPattern([MutationTypes.STORE_RESET_LICENSE]);
    });
});
describe('License Store Getters', async () => {
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
    it('should successfully get licensee by id (not found)', async () => {
        const state = {};
        const licensee = getters.licenseeById(state)('1');

        expect(licensee).to.equal(undefined);
    });
    it('should successfully get licensee by id (found)', async () => {
        const record = { id: '1' };
        const state = { model: [record] };
        const licensee = getters.licenseeById(state)('1');

        expect(licensee).to.matchPattern(record);
    });
    it('should successfully get privilege by LicenseeId And PrivilegeId', async () => {
        const licensee1 = {
            id: '1',
            privileges: [
                new License({ id: '1' }),
                new License({ id: '2' }),
            ]
        };

        const licensee2 = {
            id: '2',
            privileges: [
                new License({ id: '12' }),
                new License({ id: '22' }),
            ]
        };
        const state = { model: [ licensee1, licensee2 ] };
        const privilege = getters.getPrivilegeByLicenseeIdAndId(state)({ licenseeId: '2', privilegeId: '12' });

        expect(privilege.id).to.equal('12');
    });
    it('should successfully not get privilege by LicenseeId And PrivilegeId (no licensee)', async () => {
        const licensee1 = {
            id: '1',
            privileges: [
                new License({ id: '1' }),
                new License({ id: '2' }),
            ]
        };

        const licensee2 = {
            id: '2',
            privileges: [
                new License({ id: '12' }),
                new License({ id: '22' }),
            ]
        };
        const state = { model: [ licensee1, licensee2 ] };
        const privilege = getters.getPrivilegeByLicenseeIdAndId(state)({ licenseeId: '3', privilegeId: '12' });

        expect(privilege).to.equal(null);
    });
    it('should successfully not get privilege by LicenseeId And PrivilegeId (no privilege)', async () => {
        const licensee1 = {
            id: '1',
            privileges: [
                new License({ id: '1' }),
                new License({ id: '2' }),
            ]
        };

        const licensee2 = {
            id: '2',
            privileges: [
                new License({ id: '12' }),
                new License({ id: '22' }),
            ]
        };
        const state = { model: [ licensee1, licensee2 ] };
        const privilege = getters.getPrivilegeByLicenseeIdAndId(state)({ licenseeId: '2', privilegeId: '1' });

        expect(privilege).to.equal(null);
    });
});
