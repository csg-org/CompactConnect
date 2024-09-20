//
//  user.actions.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

import { dataApi } from '@network/data.api';
import { config } from '@plugins/EnvConfig/envConfig.plugin';
import { authStorage, tokens } from '@/app.config';
import localStorage from '@store/local.storage';
import { Compact } from '@models/Compact/Compact.model';
import moment from 'moment';
import axios from 'axios';
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
    loginSuccess: async ({ commit }) => {
        commit(MutationTypes.LOGIN_SUCCESS);
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

        /* istanbul ignore next */
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
    setCurrentCompact: ({ commit }, compact: Compact | null) => {
        commit(MutationTypes.STORE_UPDATE_CURRENT_COMPACT, compact);
    },
    setStoreUser: ({ commit }, user) => {
        commit(MutationTypes.STORE_UPDATE_USER, user);
    },
    resetStoreUser: ({ commit }) => {
        commit(MutationTypes.STORE_RESET_USER);
    },
    // storeAuthTokensStaff: ({ dispatch }, tokenResponse) => {
    //     const {
    //         access_token: accessToken,
    //         token_type: tokenType,
    //         expires_in: expiresIn,
    //         id_token: idToken,
    //         refresh_token: refreshToken,
    //     } = tokenResponse || {};

    //     authStorage.setItem(tokens.staff.AUTH_TYPE, 'staff');

    //     if (accessToken) {
    //         authStorage.setItem(tokens.staff.AUTH_TOKEN, accessToken);
    //     }

    //     if (tokenType) {
    //         authStorage.setItem(tokens.staff.AUTH_TOKEN_TYPE, tokenType);
    //     }

    //     if (refreshToken) {
    //         authStorage.setItem(tokens.staff.REFRESH_TOKEN, refreshToken);
    //     }

    //     if (expiresIn) {
    //         const expiry = moment().add(expiresIn, 'seconds').format('YYYY-MM-DD:HH:mm:ss');

    //         authStorage.setItem(tokens.staff.AUTH_TOKEN_EXPIRY, expiry);
    //     }

    //     if (idToken) {
    //         authStorage.setItem(tokens.staff.ID_TOKEN, idToken);
    //     }

    //     dispatch('startRefreshTokenTimer');
    // },
    storeAuthTokens: ({ dispatch }, { tokenResponse, authType }) => {
        const {
            access_token: accessToken,
            token_type: tokenType,
            expires_in: expiresIn,
            id_token: idToken,
            refresh_token: refreshToken,
        } = tokenResponse || {};

        authStorage.setItem(tokens[authType].AUTH_TYPE, authType);

        if (accessToken) {
            authStorage.setItem(tokens[authType].AUTH_TOKEN, accessToken);
        }

        if (tokenType) {
            authStorage.setItem(tokens[authType].AUTH_TOKEN_TYPE, tokenType);
        }

        if (refreshToken) {
            authStorage.setItem(tokens[authType].REFRESH_TOKEN, refreshToken);
        }

        if (expiresIn) {
            const expiry = moment().add(expiresIn, 'seconds').format('YYYY-MM-DD:HH:mm:ss');

            authStorage.setItem(tokens[authType].AUTH_TOKEN_EXPIRY, expiry);
        }

        if (idToken) {
            authStorage.setItem(tokens[authType].ID_TOKEN, idToken);
        }

        dispatch('startRefreshTokenTimer');
    },
    startRefreshTokenTimer: ({ dispatch }) => {
        const expiry = authStorage.getItem(tokens.staff.AUTH_TOKEN_EXPIRY);
        const refreshToken = authStorage.getItem(tokens.staff.REFRESH_TOKEN);

        if (expiry && refreshToken) {
            const expiresIn = moment(expiry, 'YYYY-MM-DD:HH:mm:ss').diff(moment(), 'seconds');

            dispatch('setRefreshTokenTimeout', { refreshToken, expiresIn });
        }
    },
    setRefreshTokenTimeout: async ({ commit, dispatch }, { refreshToken, expiresIn }) => {
        const { cognitoAuthDomainStaff, cognitoClientIdStaff } = config;
        const params = new URLSearchParams();
        const refreshInMs = moment().add(expiresIn, 'seconds').subtract(5, 'minutes').diff(moment(), 'milliseconds');
        const refreshTokens = async () => {
            let isError = false;

            params.append('grant_type', 'refresh_token');
            params.append('client_id', cognitoClientIdStaff || '');
            params.append('refresh_token', refreshToken);

            const { data } = await axios.post(`${cognitoAuthDomainStaff}/oauth2/token`, params).catch(() => {
                isError = true;

                return { data: {}};
            });

            if (!isError) {
                dispatch('storeAuthTokensStaff', data);
            }
        };
        const timeoutId = setTimeout(refreshTokens, refreshInMs);

        commit(MutationTypes.SET_REFRESH_TIMEOUT_ID, timeoutId);
    },
    clearRefreshTokenTimeout: ({ commit, state }) => {
        const { refreshTokenTimeoutId } = state;

        clearTimeout(refreshTokenTimeoutId);
        commit(MutationTypes.SET_REFRESH_TIMEOUT_ID, null);
    },
    clearSessionStores: ({ dispatch }) => {
        dispatch('resetStoreUser');
        dispatch('license/resetStoreLicense', null, { root: true });
        dispatch('pagination/resetStorePagination', null, { root: true });
        dispatch('sorting/resetStoreSorting', null, { root: true });
        dispatch('reset', null, { root: true });
    },
    clearAuthTokens: () => {
        /* istanbul ignore next */
        Object.keys(tokens.staff).forEach((key) => {
            authStorage.removeItem(tokens.staff[key]);
            localStorage.removeItem(tokens.staff[key]); // Always remove localStorage to reduce edge cache states; e.g. from switching auth storage
        });
    },
};
