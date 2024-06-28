//
//  user.actions.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

import { dataApi } from '@network/data.api';
import { config } from '@plugins/EnvConfig/envConfig.plugin';
import localStorage, { AUTH_TOKEN } from '@store/local.storage';
import { MutationTypes } from './user.mutations';

export default {
    // ========================================================================
    // =                       GENERAL USER ACTIONS                           =
    // =                                                                      =
    // = These are higher-level actions that commit the store mutations.      =
    // = These actions might dispatch more specific actions.                  =
    // ========================================================================
    // LOGIN
    loginRequest: ({ commit }) => {
        commit(MutationTypes.LOGIN_REQUEST);
    },
    loginSuccess: async ({ commit, dispatch }) => {
        commit(MutationTypes.LOGIN_SUCCESS);
        await dispatch('getAccountRequest');
    },
    loginFailure: async ({ commit }, error: Error) => {
        commit(MutationTypes.LOGIN_FAILURE, error);
    },
    // LOGOUT
    logoutRequest: ({ commit, dispatch }) => {
        dispatch('clearSessionStores');
        dispatch('startLoading', null, { root: true });
        dispatch('clearAuthTokens');
        commit(MutationTypes.LOGOUT_REQUEST);

        /* istanbul ignore if */
        if (config.isUsingMockApi) {
            setTimeout(() => dispatch('endLoading', null, { root: true }), 1000);
            dispatch('logoutSuccess');
        } else {
            dispatch('logoutSuccess');
        }
    },
    logoutSuccess: ({ commit }) => {
        commit(MutationTypes.LOGOUT_SUCCESS);
    },
    logoutFailure: ({ commit }, error: Error) => {
        commit(MutationTypes.LOGOUT_FAILURE, error);
    },
    // GET ACCOUNT
    getAccountRequest: async ({ commit, dispatch }) => {
        commit(MutationTypes.GET_ACCOUNT_REQUEST);
        await dataApi.getAccount().then((account) => {
            dispatch('getAccountSuccess', account);
        }).catch((error) => {
            dispatch('getAccountFailure', error);
        });
    },
    getAccountSuccess: ({ commit, dispatch }, account) => {
        commit(MutationTypes.GET_ACCOUNT_SUCCESS, account);
        if (account) {
            dispatch('setStoreUser', account);
        }
    },
    getAccountFailure: ({ commit }, error: Error) => {
        commit(MutationTypes.GET_ACCOUNT_FAILURE, error);
    },
    // SET THE STORE STATE
    setStoreUser: ({ commit }, user) => {
        commit(MutationTypes.STORE_UPDATE_USER, user);
    },
    resetStoreUser: ({ commit }) => {
        commit(MutationTypes.STORE_RESET_USER);
    },
    clearSessionStores: ({ dispatch }) => {
        dispatch('resetStoreUser');
        dispatch('pagination/resetStorePagination', null, { root: true });
        dispatch('sorting/resetStoreSorting', null, { root: true });
        dispatch('reset', null, { root: true });
    },
    clearAuthTokens: () => {
        localStorage.removeItem(AUTH_TOKEN); // Used by the mock or custom auth API
    },
};
