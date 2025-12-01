//
//  license.mutations.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 7/2/24.
//
import { LicenseSearchLegacy } from '@components/Licensee/LicenseeSearchLegacy/LicenseeSearchLegacy.vue';

export enum MutationTypes {
    GET_LICENSEES_REQUEST = '[License] Get Licensees Request',
    GET_LICENSEES_FAILURE = '[License] Get Licensees Failure',
    GET_LICENSEES_SUCCESS = '[License] Get Licensees Success',
    STORE_UPDATE_PREVLASTKEY = '[License] Updated previous last paging key in store',
    STORE_UPDATE_LASTKEY = '[License] Updated last paging key in store',
    STORE_UPDATE_COUNT = '[License] Updated total count in store',
    STORE_SET_LICENSEES = '[License] Set Licensees in store',
    GET_LICENSEE_REQUEST = '[License] Get Licensee Request',
    GET_LICENSEE_FAILURE = '[License] Get Licensee Failure',
    GET_LICENSEE_SUCCESS = '[License] Get Licensee Success',
    GET_PRIVILEGE_HISTORY_REQUEST = '[User] Get Privilege History Request',
    GET_PRIVILEGE_HISTORY_SUCCESS = '[User] Get Privilege History Success',
    GET_PRIVILEGE_HISTORY_FAILURE = '[User] Get Privilege History Failure',
    STORE_UPDATE_LICENSEE = '[License] Updated Licensee in store',
    STORE_REMOVE_LICENSEE = '[License] Remove Licensee from store',
    STORE_UPDATE_SEARCH = '[License] Update search params',
    STORE_RESET_SEARCH = '[License] Reset search params',
    STORE_RESET_LICENSE = '[License] Reset license store',
}

export default {
    [MutationTypes.GET_LICENSEES_REQUEST]: (state: any) => {
        state.isLoading = true;
        state.error = null;
    },
    [MutationTypes.GET_LICENSEES_FAILURE]: (state: any, error: Error) => {
        state.isLoading = false;
        state.error = error;
    },
    [MutationTypes.GET_LICENSEES_SUCCESS]: (state: any) => {
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
    [MutationTypes.STORE_SET_LICENSEES]: (state: any, licensees: Array<any>) => {
        state.model = licensees;
    },
    [MutationTypes.GET_LICENSEE_REQUEST]: (state: any) => {
        state.isLoading = true;
        state.error = null;
    },
    [MutationTypes.GET_LICENSEE_FAILURE]: (state: any, error: Error) => {
        state.isLoading = false;
        state.error = error;
    },
    [MutationTypes.GET_LICENSEE_SUCCESS]: (state: any) => {
        state.isLoading = false;
        state.error = null;
    },
    [MutationTypes.STORE_UPDATE_LICENSEE]: (state: any, licensee: any) => {
        if (licensee.id) { // Don't put objects with NULL IDs in the store
            if (state.model && state.model.length) {
                const licenseeToUpdateIndex = state.model
                    .findIndex((p: any) => p.id === licensee.id);

                if (licenseeToUpdateIndex !== -1) {
                    state.model.splice(licenseeToUpdateIndex, 1, licensee);
                } else {
                    state.model.push(licensee);
                }
            } else {
                state.model = [licensee];
            }
        } else {
            console.warn('Cannot put Licensee with null ID in the store:');
            console.warn(JSON.stringify(licensee, null, 2));
        }
    },
    [MutationTypes.STORE_REMOVE_LICENSEE]: (state: any, licenseeId: string | number) => {
        if (licenseeId) { // Can't remove licensee with NULL IDs from the store
            if (state.model && state.model.length) {
                const licenseeToRemoveIndex = state.model
                    .findIndex((p: any) => Number(p.id) === Number(licenseeId));

                if (licenseeToRemoveIndex !== -1) {
                    state.model.splice(licenseeToRemoveIndex, 1);
                }
            }
        } else {
            console.warn('Cannot remove Licensee with null ID from the store:');
        }
    },
    [MutationTypes.STORE_UPDATE_SEARCH]: (state: any, search: LicenseSearchLegacy) => {
        state.search = search;
    },
    [MutationTypes.STORE_RESET_SEARCH]: (state: any) => {
        state.search = {
            compact: '',
            firstName: '',
            lastName: '',
            state: '',
        };
    },
    [MutationTypes.STORE_RESET_LICENSE]: (state: any) => {
        state.model = null;
        state.total = 0;
        state.isLoading = false;
        state.error = null;
        state.search = {
            compact: '',
            firstName: '',
            lastName: '',
            state: '',
        };
    },
    [MutationTypes.GET_PRIVILEGE_HISTORY_REQUEST]: (state: any) => {
        state.isLoading = true;
        state.error = null;
    },
    [MutationTypes.GET_PRIVILEGE_HISTORY_SUCCESS]: (state: any, { history }) => {
        const privilegeId = `${history.providerId}-${history.jurisdiction}-${history.licenseType}`;
        const licenseeId = history.providerId;
        const licensees = state.model || [];
        const foundLicensee = licensees.find((licensee) => licensee.id === licenseeId);
        const foundPrivilege = foundLicensee?.privileges?.find((privilege) => (privilege.id === privilegeId)) || null;

        if (foundPrivilege) {
            foundPrivilege.history = history.events;
        }

        state.isLoading = false;
        state.error = null;
    },
    [MutationTypes.GET_PRIVILEGE_HISTORY_FAILURE]: (state: any, error: Error) => {
        state.isLoading = false;
        state.error = error;
    },
};
