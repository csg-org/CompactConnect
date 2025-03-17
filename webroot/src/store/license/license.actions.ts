//
//  license.actions.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 7/2/24.
//

import { dataApi } from '@network/data.api';
import { PageExhaustError } from '@store/pagination';
import { MutationTypes } from './license.mutations';

export default {
    // GET LICENSEES
    getLicenseesRequest: async ({ commit, getters, dispatch }, { params }: any) => {
        commit(MutationTypes.GET_LICENSEES_REQUEST);

        const apiRequest = (params?.isPublic) ? dataApi.getLicenseesPublic : dataApi.getLicensees;

        if (params?.getNextPage) {
            params.lastKey = getters.lastKey;
        } else if (params?.getPrevPage) {
            params.lastKey = getters.prevLastKey;
        }

        await apiRequest(params).then(async ({ prevLastKey, lastKey, licensees }) => {
            // Support for limited server paging support
            if (!licensees.length && params?.getNextPage) {
                throw new PageExhaustError('end of list');
            } else {
                await dispatch('setStoreLicenseePrevLastKey', prevLastKey);
                await dispatch('setStoreLicenseeLastKey', lastKey);
                await dispatch('setStoreLicensees', licensees);
            }
            dispatch('getLicenseesSuccess', licensees);
        }).catch((error) => {
            dispatch('getLicenseesFailure', error);
        });
    },
    getLicenseesSuccess: ({ commit }) => {
        commit(MutationTypes.GET_LICENSEES_SUCCESS);
    },
    getLicenseesFailure: ({ commit }, error: Error) => {
        commit(MutationTypes.GET_LICENSEES_FAILURE, error);
    },
    // GET LICENSEE
    getLicenseeRequest: async ({ commit, dispatch }, { compact, licenseeId }: any) => {
        commit(MutationTypes.GET_LICENSEE_REQUEST);

        await dataApi.getLicensee(compact, licenseeId).then((licensee) => {
            dispatch('getLicenseeSuccess', licensee);
        }).catch((error) => {
            dispatch('getLicenseeFailure', error);
        });
    },
    getLicenseeSuccess: ({ commit, dispatch }, licensee) => {
        commit(MutationTypes.GET_LICENSEE_SUCCESS);

        if (licensee) {
            dispatch('setStoreLicensee', licensee);
        }
    },
    getLicenseeFailure: ({ commit }, error: Error) => {
        commit(MutationTypes.GET_LICENSEE_FAILURE, error);
    },
    // SET THE STORE STATE
    setStoreLicenseePrevLastKey: ({ commit }, prevLastKey) => {
        commit(MutationTypes.STORE_UPDATE_PREVLASTKEY, prevLastKey);
    },
    setStoreLicenseeLastKey: ({ commit }, lastKey) => {
        commit(MutationTypes.STORE_UPDATE_LASTKEY, lastKey);
    },
    setStoreLicenseeCount: ({ commit }, count) => {
        commit(MutationTypes.STORE_UPDATE_COUNT, count);
    },
    setStoreLicensees: ({ commit }, licensees) => {
        commit(MutationTypes.STORE_SET_LICENSEES, licensees);
    },
    setStoreLicensee: ({ commit }, licensee) => {
        commit(MutationTypes.STORE_UPDATE_LICENSEE, licensee);
    },
    setStoreSearch: ({ commit }, search) => {
        commit(MutationTypes.STORE_UPDATE_SEARCH, search);
    },
    resetStoreSearch: ({ commit }) => {
        commit(MutationTypes.STORE_RESET_SEARCH);
    },
    // RESET LICENSEES STORE STATE
    resetStoreLicense: ({ commit }) => {
        commit(MutationTypes.STORE_RESET_LICENSE);
    },
};
