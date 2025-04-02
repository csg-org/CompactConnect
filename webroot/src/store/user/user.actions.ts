//
//  user.actions.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

import { dataApi } from '@network/data.api';
import { config } from '@plugins/EnvConfig/envConfig.plugin';
import {
    authStorage,
    AuthTypes,
    tokens,
    AUTH_TYPE
} from '@/app.config';
import localStorage from '@store/local.storage';
import { Compact } from '@models/Compact/Compact.model';
import { PurchaseFlowStep } from '@/models/PurchaseFlowStep/PurchaseFlowStep.model';
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
    loginSuccess: async ({ commit }, authType) => {
        commit(MutationTypes.LOGIN_SUCCESS, authType);
    },
    loginFailure: async ({ commit }, error: Error) => {
        commit(MutationTypes.LOGIN_FAILURE, error);
    },
    // LOGOUT
    logoutRequest: ({ commit, dispatch }, authType) => {
        dispatch('clearSessionStores');
        dispatch('startLoading', null, { root: true });
        let tokenType = AuthTypes.STAFF;

        if (authType === AuthTypes.LICENSEE) {
            tokenType = authType;
        }
        dispatch('clearAuthToken', tokenType);
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
    // CREATE LICENSEE ACCOUNT
    createLicenseeAccountRequest: async ({ commit, dispatch }, { compact, data }: any) => {
        commit(MutationTypes.CREATE_LICENSEE_ACCOUNT_REQUEST);
        return dataApi.createLicenseeAccount(compact, data).then((response) => {
            dispatch('createLicenseeAccountSuccess');

            return response;
        }).catch((error) => {
            dispatch('createLicenseeAccountFailure', error);

            throw error;
        });
    },
    createLicenseeAccountSuccess: ({ commit }) => {
        commit(MutationTypes.CREATE_LICENSEE_ACCOUNT_SUCCESS);
    },
    createLicenseeAccountFailure: ({ commit }, error: Error) => {
        commit(MutationTypes.CREATE_LICENSEE_ACCOUNT_FAILURE, error);
    },
    // GET STAFF ACCOUNT
    getStaffAccountRequest: async ({ commit, dispatch }) => {
        commit(MutationTypes.GET_ACCOUNT_REQUEST);
        return dataApi.getAuthenticatedStaffUser().then((account) => {
            dispatch('getAccountSuccess', account);

            return account;
        }).catch((error) => {
            dispatch('getAccountFailure', error);
        });
    },
    // GET LICENSEE ACCOUNT
    getLicenseeAccountRequest: async ({ commit, dispatch }) => {
        commit(MutationTypes.GET_ACCOUNT_REQUEST);
        return dataApi.getAuthenticatedLicenseeUser().then((account) => {
            dispatch('getAccountSuccess', account);

            return account;
        }).catch((error) => {
            dispatch('getAccountFailure', error);
        });
    },
    // GET ACCOUNT SUCCESS / FAIL HANDLERS
    getAccountSuccess: ({ commit, dispatch }, account) => {
        commit(MutationTypes.GET_ACCOUNT_SUCCESS, account);
        if (account) {
            dispatch('setStoreUser', account);
        }
    },
    getAccountFailure: ({ commit }, error: Error) => {
        commit(MutationTypes.GET_ACCOUNT_FAILURE, error);
    },
    // GET COMPACT STATES FOR USER
    getCompactStatesRequest: async ({ commit, dispatch }, { compact }) => {
        commit(MutationTypes.GET_COMPACT_STATES_REQUEST);
        return dataApi.getCompactStates(compact).then((states) => {
            dispatch('getCompactStatesSuccess', states);

            return states;
        }).catch((error) => {
            dispatch('getCompactStatesFailure', error);
        });
    },
    getCompactStatesSuccess: ({ commit }, states) => {
        commit(MutationTypes.GET_COMPACT_STATES_SUCCESS, states);
    },
    getCompactStatesFailure: ({ commit }, error: Error) => {
        commit(MutationTypes.GET_COMPACT_STATES_FAILURE, error);
    },
    // SET THE STORE STATE
    setCurrentCompact: async ({ commit, dispatch }, compact: Compact | null) => {
        commit(MutationTypes.STORE_UPDATE_CURRENT_COMPACT, compact);

        if (compact?.type) {
            await dispatch('getCompactStatesRequest', { compact: compact.type });
        }
    },
    setStoreUser: ({ commit }, user) => {
        commit(MutationTypes.STORE_UPDATE_USER, user);
    },
    resetStoreUser: ({ commit }) => {
        commit(MutationTypes.STORE_RESET_USER);
    },
    updateAuthTokens: ({ dispatch }, { tokenResponse, authType }) => {
        dispatch('clearAllNonAccessTokens');
        dispatch('storeAuthTokens', { tokenResponse, authType });
    },
    storeAuthTokens: ({ dispatch }, { tokenResponse, authType }) => {
        const {
            access_token: accessToken,
            token_type: tokenType,
            expires_in: expiresIn,
            id_token: idToken,
            refresh_token: refreshToken,
        } = tokenResponse || {};

        authStorage.setItem(AUTH_TYPE, authType);

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

        dispatch('startRefreshTokenTimer', authType);
    },
    startRefreshTokenTimer: ({ dispatch }, authType) => {
        const expiry = authStorage.getItem(tokens[authType]?.AUTH_TOKEN_EXPIRY);
        const refreshToken = authStorage.getItem(tokens[authType]?.REFRESH_TOKEN);

        if (expiry && refreshToken) {
            const expiresIn = moment(expiry, 'YYYY-MM-DD:HH:mm:ss').diff(moment(), 'seconds');

            dispatch('setRefreshTokenTimeout', { refreshToken, expiresIn, authType });
        }
    },
    setRefreshTokenTimeout: async ({ commit, dispatch }, { refreshToken, expiresIn, authType }) => {
        let cognitoClientId;
        let cognitoAuthDomain;

        if (authType === AuthTypes.STAFF) {
            cognitoClientId = config.cognitoClientIdStaff;
            cognitoAuthDomain = config.cognitoAuthDomainStaff;
        } else if (authType === AuthTypes.LICENSEE) {
            cognitoClientId = config.cognitoClientIdLicensee;
            cognitoAuthDomain = config.cognitoAuthDomainLicensee;
        }

        const params = new URLSearchParams();
        const refreshInMs = moment().add(expiresIn, 'seconds').subtract(5, 'minutes').diff(moment(), 'milliseconds');
        const refreshTokens = async () => {
            let isError = false;

            params.append('grant_type', 'refresh_token');
            params.append('client_id', cognitoClientId || '');
            params.append('refresh_token', refreshToken);

            const { data } = await axios.post(`${cognitoAuthDomain}/oauth2/token`, params).catch(() => {
                isError = true;

                return { data: {}};
            });

            if (!isError) {
                dispatch('storeAuthTokens', { tokenResponse: data, authType });
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
    clearAllNonAccessTokens: () => {
        authStorage.removeItem(AUTH_TYPE);

        /* istanbul ignore next */
        Object.keys(tokens[AuthTypes.STAFF]).forEach((key) => {
            if (key !== 'AUTH_TOKEN') {
                authStorage.removeItem(tokens[AuthTypes.STAFF][key]);
            }
        });

        /* istanbul ignore next */
        Object.keys(tokens[AuthTypes.LICENSEE]).forEach((key) => {
            if (key !== 'AUTH_TOKEN') {
                authStorage.removeItem(tokens[AuthTypes.LICENSEE][key]);
            }
        });
    },
    clearAuthToken: (def, authType) => {
        authStorage.removeItem(AUTH_TYPE);

        /* istanbul ignore next */
        Object.keys(tokens[authType]).forEach((key) => {
            authStorage.removeItem(tokens[authType][key]);
            localStorage.removeItem(tokens[authType][key]); // Always remove localStorage to reduce edge cache states; e.g. from switching auth storage
        });
    },
    getPrivilegePurchaseInformationRequest: ({ commit, dispatch }) => {
        commit(MutationTypes.GET_PRIVILEGE_PURCHASE_INFORMATION_REQUEST);
        return dataApi.getPrivilegePurchaseInformation().then((privilegePurchaseData) => {
            dispatch('getPrivilegePurchaseInformationSuccess', privilegePurchaseData);
            return privilegePurchaseData;
        }).catch((error) => {
            dispatch('getPrivilegePurchaseInformationFailure', error);
        });
    },
    getPrivilegePurchaseInformationSuccess: ({ dispatch, commit, state }, privilegePurchaseData) => {
        if (privilegePurchaseData?.compactCommissionFee?.compactType === state?.currentCompact?.type) {
            const newCompact = new Compact({
                ...state.currentCompact,
                privilegePurchaseOptions: privilegePurchaseData.privilegePurchaseOptions,
                fees: privilegePurchaseData.compactCommissionFee
            });

            dispatch('setCurrentCompact', newCompact);
            commit(MutationTypes.GET_PRIVILEGE_PURCHASE_INFORMATION_SUCCESS);
        } else {
            dispatch('getPrivilegePurchaseInformationFailure', new Error('Compact mismatch'));
        }
    },
    getPrivilegePurchaseInformationFailure: ({ commit }, error: Error) => {
        commit(MutationTypes.GET_PRIVILEGE_PURCHASE_INFORMATION_FAILURE, error);
    },
    postPrivilegePurchases: ({ commit, dispatch }, privilegePurchases) => {
        commit(MutationTypes.POST_PRIVILEGE_PURCHASE_REQUEST);
        return dataApi.postPrivilegePurchases(privilegePurchases).then((serverResponse) => {
            dispatch('postPrivilegePurchasesSuccess');
            return serverResponse;
        }).catch((error) => {
            dispatch('postPrivilegePurchasesFailure', error);
            return error;
        });
    },
    postPrivilegePurchasesSuccess: ({ commit }) => {
        commit(MutationTypes.POST_PRIVILEGE_PURCHASE_SUCCESS);
    },
    postPrivilegePurchasesFailure: ({ commit }, error: Error) => {
        commit(MutationTypes.POST_PRIVILEGE_PURCHASE_FAILURE, error);
    },
    uploadMilitaryAffiliationRequest: ({ commit, dispatch }, documentData) => {
        commit(MutationTypes.UPLOAD_MILITARY_AFFILIATION_REQUEST);

        const documentIntentData = { ...documentData };

        delete documentIntentData.document;
        return dataApi.postUploadMilitaryDocumentIntent(documentIntentData).then((intentServerResponse) => {
            const postUrl = intentServerResponse.documentUploadFields[0].url;
            const uploadFields = intentServerResponse.documentUploadFields[0].fields;

            if (postUrl && uploadFields && documentData.document) {
                const documentUploadData = { ...uploadFields };

                return dataApi.postUploadMilitaryAffiliationDocument(postUrl, documentUploadData, documentData.document)
                    .then((uploadServerResponse) => {
                        if (uploadServerResponse?.status === 204) {
                            dispatch('uploadMilitaryAffiliationSuccess');

                            return uploadServerResponse;
                        }

                        throw new Error('Document Upload Failed');
                    });
            }

            throw new Error('Missing fields for Document upload');
        }).catch((error) => {
            dispatch('uploadMilitaryAffiliationFailure', error);
            return error;
        });
    },
    uploadMilitaryAffiliationSuccess: async ({ commit }) => {
        commit(MutationTypes.UPLOAD_MILITARY_AFFILIATION_SUCCESS);
    },
    uploadMilitaryAffiliationFailure: async ({ commit }, error: Error) => {
        commit(MutationTypes.UPLOAD_MILITARY_AFFILIATION_FAILURE, error);
    },
    endMilitaryAffiliationRequest: ({ commit, dispatch }) => {
        commit(MutationTypes.END_MILITARY_AFFILIATION_REQUEST);
        return dataApi.endMilitaryAffiliation().then((serverResponse) => {
            dispatch('endMilitaryAffiliationSuccess');
            return serverResponse;
        }).catch((error) => {
            dispatch('endMilitaryAffiliationFailure', error);
            return error;
        });
    },
    endMilitaryAffiliationSuccess: async ({ commit }) => {
        commit(MutationTypes.END_MILITARY_AFFILIATION_SUCCESS);
    },
    endMilitaryAffiliationFailure: async ({ commit }, error: Error) => {
        commit(MutationTypes.END_MILITARY_AFFILIATION_FAILURE, error);
    },
    resetToPurchaseFlowStep: ({ commit }, flowStepNum: number) => {
        commit(MutationTypes.RESET_TO_PURCHASE_FLOW_STEP, flowStepNum);
    },
    saveFlowStep: ({ commit }, flowStep: PurchaseFlowStep) => {
        commit(MutationTypes.SAVE_PURCHASE_FLOW_STEP, flowStep);
    },
};
