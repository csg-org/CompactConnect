//
//  users.actions.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 9/4/24.
//

import { dataApi } from '@network/data.api';
import { PageExhaustError } from '@store/pagination';
import { MutationTypes } from './users.mutations';

export default {
    // GET USERS
    getUsersRequest: async ({ commit, getters, dispatch }, { params }: any) => {
        commit(MutationTypes.GET_USERS_REQUEST);

        if (params?.getNextPage) {
            params.lastKey = getters.lastKey;
        } else if (params?.getPrevPage) {
            params.lastKey = getters.prevLastKey;
        }

        await dataApi.getUsers(params).then(async ({ prevLastKey, lastKey, users }) => {
            // Support for limited server paging support
            if (!users.length && params?.getNextPage) {
                throw new PageExhaustError('end of list');
            } else {
                await dispatch('setStoreUsersPrevLastKey', prevLastKey);
                await dispatch('setStoreUsersLastKey', lastKey);
                await dispatch('setStoreUsers', users);
            }
            dispatch('getUsersSuccess', users);
        }).catch((error) => {
            dispatch('getUsersFailure', error);
        });
    },
    getUsersSuccess: ({ commit }) => {
        commit(MutationTypes.GET_USERS_SUCCESS);
    },
    getUsersFailure: ({ commit }, error: Error) => {
        commit(MutationTypes.GET_USERS_FAILURE, error);
    },
    // CREATE USER
    createUserRequest: async ({ commit, dispatch }, { compact, data }: any) => {
        commit(MutationTypes.CREATE_USER_REQUEST);
        await dataApi.createUser(compact, data).then(async (user) => {
            await dispatch('setStoreUser', user);
            dispatch('createUserSuccess', user);
        }).catch((error) => {
            dispatch('createUserFailure', error);
        });
    },
    createUserSuccess: ({ commit }) => {
        commit(MutationTypes.CREATE_USER_SUCCESS);
    },
    createUserFailure: ({ commit }, error: Error) => {
        commit(MutationTypes.CREATE_USER_FAILURE, error);
    },
    // GET USER
    getUserRequest: async ({ commit, dispatch }, { compact, userId }: any) => {
        commit(MutationTypes.GET_USER_REQUEST);
        await dataApi.getUser(compact, userId).then(async (user) => {
            await dispatch('setStoreUser', user);
            dispatch('getUserSuccess', user);
        }).catch((error) => {
            dispatch('getUserFailure', error);
        });
    },
    getUserSuccess: ({ commit }) => {
        commit(MutationTypes.GET_USER_SUCCESS);
    },
    getUserFailure: ({ commit }, error: Error) => {
        commit(MutationTypes.GET_USER_FAILURE, error);
    },
    // UPDATE USER
    updateUserRequest: async ({ commit, dispatch }, { compact, userId, data }: any) => {
        commit(MutationTypes.UPDATE_USER_REQUEST);
        await dataApi.updateUser(compact, userId, data).then(async (user) => {
            await dispatch('setStoreUser', user);
            dispatch('updateUserSuccess', user);
        }).catch((error) => {
            dispatch('updateUserFailure', error);
        });
    },
    updateUserSuccess: ({ commit }) => {
        commit(MutationTypes.UPDATE_USER_SUCCESS);
    },
    updateUserFailure: ({ commit }, error: Error) => {
        commit(MutationTypes.UPDATE_USER_FAILURE, error);
    },
    // SET THE STORE STATE
    setStoreUsersPrevLastKey: ({ commit }, prevLastKey) => {
        commit(MutationTypes.STORE_UPDATE_PREVLASTKEY, prevLastKey);
    },
    setStoreUsersLastKey: ({ commit }, lastKey) => {
        commit(MutationTypes.STORE_UPDATE_LASTKEY, lastKey);
    },
    setStoreUsersCount: ({ commit }, count) => {
        commit(MutationTypes.STORE_UPDATE_COUNT, count);
    },
    setStoreUsers: ({ commit }, users) => {
        commit(MutationTypes.STORE_SET_USERS, users);
    },
    setStoreUser: ({ commit }, user) => {
        commit(MutationTypes.STORE_UPDATE_USER, user);
    },
    // RESET USERS STORE STATE
    resetStoreUsers: ({ commit }) => {
        commit(MutationTypes.STORE_RESET_USERS);
    },
};
