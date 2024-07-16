//
//  license.actions.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 7/2/24.
//

import { dataApi } from '@network/data.api';
import { MutationTypes } from './license.mutations';

export default {
    // GET LICENSEES
    getLicenseesRequest: async ({ commit, getters, dispatch }, { params }: any) => {
        commit(MutationTypes.GET_LICENSEES_REQUEST);

        // Temp for limited server paging support
        if (params?.getNextPage) {
            params.lastKey = getters.lastKey;
        }

        await dataApi.getLicensees(params).then(async ({ lastKey, licensees }) => {
            // Temp for limited server paging support
            if (!licensees.length && params?.getNextPage) {
                throw new Error('end of list');
            } else {
                await dispatch('setStoreLicenseeLastKey', lastKey);
                // await dispatch('setStoreLicenseeCount', totalCount);
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
    getLicenseeRequest: async ({ commit, dispatch }, { licenseeId, params }: any) => {
        commit(MutationTypes.GET_LICENSEE_REQUEST);
        await dataApi.getLicensee(licenseeId, params).then(async ({ licensee }) => {
            await dispatch('setStoreLicensee', licensee);
            dispatch('getLicenseeSuccess', licensee);
        }).catch((error) => {
            dispatch('getLicenseeFailure', error);
        });
    },
    getLicenseeSuccess: ({ commit }) => {
        commit(MutationTypes.GET_LICENSEE_SUCCESS);
    },
    getLicenseeFailure: ({ commit }, error: Error) => {
        commit(MutationTypes.GET_LICENSEE_FAILURE, error);
    },
    // SET THE STORE STATE
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
    // RESET LICENSEES STORE STATE
    resetStoreLicense: ({ commit }) => {
        commit(MutationTypes.STORE_RESET_LICENSE);
    },
};
