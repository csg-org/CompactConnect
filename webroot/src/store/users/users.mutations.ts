//
//  users.mutations.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 9/4/24.
//

export enum MutationTypes {
    GET_USERS_REQUEST = '[Users] Get Users Request',
    GET_USERS_FAILURE = '[Users] Get Users Failure',
    GET_USERS_SUCCESS = '[Users] Get Users Success',
    STORE_UPDATE_PREVLASTKEY = '[Users] Updated previous last paging key in store',
    STORE_UPDATE_LASTKEY = '[Users] Updated last paging key in store',
    STORE_UPDATE_COUNT = '[Users] Updated total count in store',
    STORE_SET_USERS = '[Users] Set Users in store',
    CREATE_USER_REQUEST = '[Users] Create User Request',
    CREATE_USER_FAILURE = '[Users] Create User Failure',
    CREATE_USER_SUCCESS = '[Users] Create User Success',
    GET_USER_REQUEST = '[Users] Get User Request',
    GET_USER_FAILURE = '[Users] Get User Failure',
    GET_USER_SUCCESS = '[Users] Get User Success',
    UPDATE_USER_REQUEST = '[Users] Update User Request',
    UPDATE_USER_FAILURE = '[Users] Update User Failure',
    UPDATE_USER_SUCCESS = '[Users] Update User Success',
    REINVITE_USER_REQUEST = '[Users] Reinvite User Request',
    REINVITE_USER_FAILURE = '[Users] Reinvite User Failure',
    REINVITE_USER_SUCCESS = '[Users] Reinvite User Success',
    DELETE_USER_REQUEST = '[Users] Delete User Request',
    DELETE_USER_FAILURE = '[Users] Delete User Failure',
    DELETE_USER_SUCCESS = '[Users] Delete User Success',
    ENCUMBER_LICENSE_REQUEST = '[Users] Encumber License Request',
    ENCUMBER_LICENSE_FAILURE = '[Users] Encumber License Failure',
    ENCUMBER_LICENSE_SUCCESS = '[Users] Encumber License Success',
    UNENCUMBER_LICENSE_REQUEST = '[Users] Unencumber License Request',
    UNENCUMBER_LICENSE_FAILURE = '[Users] Unencumber License Failure',
    UNENCUMBER_LICENSE_SUCCESS = '[Users] Unencumber License Success',
    CREATE_INVESTIGATION_LICENSE_REQUEST = '[Users] Create Investigation License Request',
    CREATE_INVESTIGATION_LICENSE_FAILURE = '[Users] Create Investigation License Failure',
    CREATE_INVESTIGATION_LICENSE_SUCCESS = '[Users] Create Investigation License Success',
    UPDATE_INVESTIGATION_LICENSE_REQUEST = '[Users] Update Investigation License Request',
    UPDATE_INVESTIGATION_LICENSE_FAILURE = '[Users] Update Investigation License Failure',
    UPDATE_INVESTIGATION_LICENSE_SUCCESS = '[Users] Update Investigation License Success',
    DELETE_PRIVILEGE_REQUEST = '[Users] Delete Privilege Request',
    DELETE_PRIVILEGE_FAILURE = '[Users] Delete Privilege Failure',
    DELETE_PRIVILEGE_SUCCESS = '[Users] Delete Privilege Success',
    ENCUMBER_PRIVILEGE_REQUEST = '[Users] Encumber Privilege Request',
    ENCUMBER_PRIVILEGE_FAILURE = '[Users] Encumber Privilege Failure',
    ENCUMBER_PRIVILEGE_SUCCESS = '[Users] Encumber Privilege Success',
    UNENCUMBER_PRIVILEGE_REQUEST = '[Users] Unencumber Privilege Request',
    UNENCUMBER_PRIVILEGE_FAILURE = '[Users] Unencumber Privilege Failure',
    UNENCUMBER_PRIVILEGE_SUCCESS = '[Users] Unencumber Privilege Success',
    CREATE_INVESTIGATION_PRIVILEGE_REQUEST = '[Users] Create Investigation Privilege Request',
    CREATE_INVESTIGATION_PRIVILEGE_FAILURE = '[Users] Create Investigation Privilege Failure',
    CREATE_INVESTIGATION_PRIVILEGE_SUCCESS = '[Users] Create Investigation Privilege Success',
    UPDATE_INVESTIGATION_PRIVILEGE_REQUEST = '[Users] Update Investigation Privilege Request',
    UPDATE_INVESTIGATION_PRIVILEGE_FAILURE = '[Users] Update Investigation Privilege Failure',
    UPDATE_INVESTIGATION_PRIVILEGE_SUCCESS = '[Users] Update Investigation Privilege Success',
    STORE_UPDATE_USER = '[Users] Updated User in store',
    STORE_REMOVE_USER = '[Users] Remove User from store',
    STORE_RESET_USERS = '[Users] Reset users store',
}

export default {
    [MutationTypes.GET_USERS_REQUEST]: (state: any) => {
        state.isLoading = true;
        state.error = null;
    },
    [MutationTypes.GET_USERS_FAILURE]: (state: any, error: Error) => {
        state.isLoading = false;
        state.error = error;
    },
    [MutationTypes.GET_USERS_SUCCESS]: (state: any) => {
        state.isLoading = false;
        state.error = null;
    },
    [MutationTypes.STORE_UPDATE_PREVLASTKEY]: (state: any, prevLastKey: string | null) => {
        state.prevLastKey = prevLastKey;
    },
    [MutationTypes.STORE_UPDATE_LASTKEY]: (state: any, lastKey: string | null) => {
        state.lastKey = lastKey;
    },
    [MutationTypes.STORE_UPDATE_COUNT]: (state: any, count: number) => {
        state.total = count;
    },
    [MutationTypes.STORE_SET_USERS]: (state: any, users: Array<any>) => {
        state.model = users;
    },
    [MutationTypes.CREATE_USER_REQUEST]: (state: any) => {
        state.isLoading = true;
        state.error = null;
    },
    [MutationTypes.CREATE_USER_FAILURE]: (state: any, error: Error) => {
        state.isLoading = false;
        state.error = error;
    },
    [MutationTypes.CREATE_USER_SUCCESS]: (state: any) => {
        state.isLoading = false;
        state.error = null;
    },
    [MutationTypes.GET_USER_REQUEST]: (state: any) => {
        state.isLoading = true;
        state.error = null;
    },
    [MutationTypes.GET_USER_FAILURE]: (state: any, error: Error) => {
        state.isLoading = false;
        state.error = error;
    },
    [MutationTypes.GET_USER_SUCCESS]: (state: any) => {
        state.isLoading = false;
        state.error = null;
    },
    [MutationTypes.UPDATE_USER_REQUEST]: (state: any) => {
        state.isLoading = true;
        state.error = null;
    },
    [MutationTypes.UPDATE_USER_FAILURE]: (state: any, error: Error) => {
        state.isLoading = false;
        state.error = error;
    },
    [MutationTypes.UPDATE_USER_SUCCESS]: (state: any) => {
        state.isLoading = false;
        state.error = null;
    },
    [MutationTypes.REINVITE_USER_REQUEST]: (state: any) => {
        state.isLoading = false; // State is handled locally for this to avoid triggering unwanted actions
        state.error = null;
    },
    [MutationTypes.REINVITE_USER_FAILURE]: (state: any) => {
        state.isLoading = false;
        state.error = null; // State is handled locally for this to avoid triggering unwanted actions
    },
    [MutationTypes.REINVITE_USER_SUCCESS]: (state: any) => {
        state.isLoading = false;
        state.error = null;
    },
    [MutationTypes.DELETE_USER_REQUEST]: (state: any) => {
        state.isLoading = false; // State is handled locally for this to avoid triggering unwanted actions
        state.error = null;
    },
    [MutationTypes.DELETE_USER_FAILURE]: (state: any) => {
        state.isLoading = false;
        state.error = null; // State is handled locally for this to avoid triggering unwanted actions
    },
    [MutationTypes.DELETE_USER_SUCCESS]: (state: any) => {
        state.isLoading = false;
        state.error = null;
    },
    [MutationTypes.ENCUMBER_LICENSE_REQUEST]: (state: any) => {
        state.isLoading = true;
        state.error = null;
    },
    [MutationTypes.ENCUMBER_LICENSE_FAILURE]: (state: any, error: Error) => {
        state.isLoading = false;
        state.error = error;
    },
    [MutationTypes.ENCUMBER_LICENSE_SUCCESS]: (state: any) => {
        state.isLoading = false;
        state.error = null;
    },
    [MutationTypes.UNENCUMBER_LICENSE_REQUEST]: (state: any) => {
        state.isLoading = true;
        state.error = null;
    },
    [MutationTypes.UNENCUMBER_LICENSE_FAILURE]: (state: any, error: Error) => {
        state.isLoading = false;
        state.error = error;
    },
    [MutationTypes.UNENCUMBER_LICENSE_SUCCESS]: (state: any) => {
        state.isLoading = false;
        state.error = null;
    },
    [MutationTypes.CREATE_INVESTIGATION_LICENSE_REQUEST]: (state: any) => {
        state.isLoading = true;
        state.error = null;
    },
    [MutationTypes.CREATE_INVESTIGATION_LICENSE_FAILURE]: (state: any, error: Error) => {
        state.isLoading = false;
        state.error = error;
    },
    [MutationTypes.CREATE_INVESTIGATION_LICENSE_SUCCESS]: (state: any) => {
        state.isLoading = false;
        state.error = null;
    },
    [MutationTypes.UPDATE_INVESTIGATION_LICENSE_REQUEST]: (state: any) => {
        state.isLoading = true;
        state.error = null;
    },
    [MutationTypes.UPDATE_INVESTIGATION_LICENSE_FAILURE]: (state: any, error: Error) => {
        state.isLoading = false;
        state.error = error;
    },
    [MutationTypes.UPDATE_INVESTIGATION_LICENSE_SUCCESS]: (state: any) => {
        state.isLoading = false;
        state.error = null;
    },
    [MutationTypes.DELETE_PRIVILEGE_REQUEST]: (state: any) => {
        state.isLoading = true;
        state.error = null;
    },
    [MutationTypes.DELETE_PRIVILEGE_FAILURE]: (state: any, error: Error) => {
        state.isLoading = false;
        state.error = error;
    },
    [MutationTypes.DELETE_PRIVILEGE_SUCCESS]: (state: any) => {
        state.isLoading = false;
        state.error = null;
    },
    [MutationTypes.ENCUMBER_PRIVILEGE_REQUEST]: (state: any) => {
        state.isLoading = true;
        state.error = null;
    },
    [MutationTypes.ENCUMBER_PRIVILEGE_FAILURE]: (state: any, error: Error) => {
        state.isLoading = false;
        state.error = error;
    },
    [MutationTypes.ENCUMBER_PRIVILEGE_SUCCESS]: (state: any) => {
        state.isLoading = false;
        state.error = null;
    },
    [MutationTypes.UNENCUMBER_PRIVILEGE_REQUEST]: (state: any) => {
        state.isLoading = true;
        state.error = null;
    },
    [MutationTypes.UNENCUMBER_PRIVILEGE_FAILURE]: (state: any, error: Error) => {
        state.isLoading = false;
        state.error = error;
    },
    [MutationTypes.UNENCUMBER_PRIVILEGE_SUCCESS]: (state: any) => {
        state.isLoading = false;
        state.error = null;
    },
    [MutationTypes.CREATE_INVESTIGATION_PRIVILEGE_REQUEST]: (state: any) => {
        state.isLoading = true;
        state.error = null;
    },
    [MutationTypes.CREATE_INVESTIGATION_PRIVILEGE_FAILURE]: (state: any, error: Error) => {
        state.isLoading = false;
        state.error = error;
    },
    [MutationTypes.CREATE_INVESTIGATION_PRIVILEGE_SUCCESS]: (state: any) => {
        state.isLoading = false;
        state.error = null;
    },
    [MutationTypes.UPDATE_INVESTIGATION_PRIVILEGE_REQUEST]: (state: any) => {
        state.isLoading = true;
        state.error = null;
    },
    [MutationTypes.UPDATE_INVESTIGATION_PRIVILEGE_FAILURE]: (state: any, error: Error) => {
        state.isLoading = false;
        state.error = error;
    },
    [MutationTypes.UPDATE_INVESTIGATION_PRIVILEGE_SUCCESS]: (state: any) => {
        state.isLoading = false;
        state.error = null;
    },
    [MutationTypes.STORE_UPDATE_USER]: (state: any, user: any) => {
        if (user.id) { // Don't put objects with NULL IDs in the store
            if (state.model && state.model.length) {
                const userToUpdateIndex = state.model
                    .findIndex((p: any) => p.id === user.id);

                if (userToUpdateIndex !== -1) {
                    state.model[userToUpdateIndex] = user;
                } else {
                    state.model.push(user);
                }
            } else {
                state.model = [user];
            }
        } else {
            console.warn('Cannot put User with null ID in the store:');
            console.warn(JSON.stringify(user, null, 2));
        }
    },
    [MutationTypes.STORE_REMOVE_USER]: (state: any, userId: string | number) => {
        if (userId) { // Can't remove user with NULL IDs from the store
            if (state.model && state.model.length) {
                const userToRemoveIndex = state.model
                    .findIndex((p: any) => p.id === userId);

                if (userToRemoveIndex !== -1) {
                    state.model.splice(userToRemoveIndex, 1);
                }
            }
        } else {
            console.warn('Cannot remove User with null ID from the store:');
        }
    },
    [MutationTypes.STORE_RESET_USERS]: (state: any) => {
        state.model = null;
        state.total = 0;
        state.isLoading = false;
        state.error = null;
    },
};
