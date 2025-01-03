//
//  user.mutations.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//
import { Compact } from '@models/Compact/Compact.model';
import { LicenseeUser } from '@/models/LicenseeUser/LicenseeUser.model';
import { StaffUser } from '@/models/StaffUser/StaffUser.model';
import { AuthTypes } from '@/app.config';

export enum MutationTypes {
    LOGIN_REQUEST = '[User] Login Request',
    LOGIN_FAILURE = '[User] Login Failure',
    LOGIN_SUCCESS = '[User] Login Success',
    LOGIN_RESET = '[User] Login Reset',
    LOGOUT_REQUEST = '[User] Logout Request',
    LOGOUT_FAILURE = '[User] Logout Failure',
    LOGOUT_SUCCESS = '[User] Logout Success',
    GET_ACCOUNT_REQUEST = '[User] Get Account Request',
    GET_ACCOUNT_FAILURE = '[User] Get Account Failure',
    GET_ACCOUNT_SUCCESS = '[User] Get Account Success',
    STORE_UPDATE_CURRENT_COMPACT = '[User] Updated current compact',
    STORE_UPDATE_USER = '[User] Updated user in store',
    STORE_RESET_USER = '[User] Reset user in store',
    UPDATE_ACCOUNT_REQUEST = '[User] Update Account Request',
    UPDATE_ACCOUNT_FAILURE = '[User] Update Account Failure',
    UPDATE_ACCOUNT_SUCCESS = '[User] Update Account Success',
    SET_REFRESH_TIMEOUT_ID = '[User] Set Refresh Timeout ID',
    GET_PRIVILEGE_PURCHASE_INFORMATION_REQUEST = '[User] Get Privilege Purchase Information Request',
    GET_PRIVILEGE_PURCHASE_INFORMATION_SUCCESS = '[User] Get Privilege Purchase Information Success',
    GET_PRIVILEGE_PURCHASE_INFORMATION_FAILURE = '[User] Get Privilege Purchase Information Failure',
    SAVE_SELECTED_PRIVILEGE_PURCHASES_TO_STORE = '[User] Save Selected Privilege Purchases To Store',
    SET_ATTESTATIONS_ACCEPTED = '[User] Set Attestations Accepted',
    POST_PRIVILEGE_PURCHASE_REQUEST = '[User] Post Privilege Purchase Request',
    POST_PRIVILEGE_PURCHASE_SUCCESS = '[User] Post Privilege Purchase Success',
    POST_PRIVILEGE_PURCHASE_FAILURE = '[User] Post Privilege Purchase Failure',
    END_MILITARY_AFFILIATION_REQUEST = '[User] Patch Military Affiliation Request',
    END_MILITARY_AFFILIATION_SUCCESS = '[User] Patch Military Affiliation Request',
    END_MILITARY_AFFILIATION_FAILURE = '[User] Patch Military Affiliation Request'
}

export default {
    [MutationTypes.LOGIN_REQUEST]: (state: any) => {
        state.isLoadingAccount = true;
        state.error = null;
    },
    [MutationTypes.LOGIN_FAILURE]: (state: any, error: Error) => {
        state.isLoadingAccount = false;
        state.error = error;
    },
    [MutationTypes.LOGIN_SUCCESS]: (state: any, authType: AuthTypes) => {
        state.isLoggedIn = true;
        state.isLoggedInAsLicensee = Boolean(authType === AuthTypes.LICENSEE);
        state.isLoggedInAsStaff = Boolean(authType === AuthTypes.STAFF);
        state.isLoadingAccount = false;
        state.error = null;
    },
    [MutationTypes.LOGIN_RESET]: (state: any) => {
        state.error = null;
    },
    [MutationTypes.LOGOUT_REQUEST]: (state: any) => {
        state.isLoadingAccount = true;
    },
    [MutationTypes.LOGOUT_FAILURE]: (state: any, error: Error) => {
        state.isLoadingAccount = false;
        state.error = error;
    },
    [MutationTypes.LOGOUT_SUCCESS]: (state: any) => {
        state.model = null;
        state.isLoggedIn = false;
        state.isLoadingAccount = false;
        state.error = null;
    },
    [MutationTypes.GET_ACCOUNT_REQUEST]: (state: any) => {
        state.isLoadingAccount = true;
        state.error = null;
    },
    [MutationTypes.GET_ACCOUNT_FAILURE]: (state: any, error: Error) => {
        state.isLoadingAccount = false;
        state.error = error;
    },
    [MutationTypes.GET_ACCOUNT_SUCCESS]: (state: any) => {
        state.isLoadingAccount = false;
        state.error = null;
    },
    [MutationTypes.STORE_UPDATE_CURRENT_COMPACT]: (state: any, compact: Compact | null) => {
        state.currentCompact = compact;
    },
    [MutationTypes.STORE_UPDATE_USER]: (state: any, user: LicenseeUser|StaffUser|null) => {
        state.model = user;
    },
    [MutationTypes.STORE_RESET_USER]: (state: any) => {
        state.model = null;
        state.isLoggedIn = false;
        state.isLoadingAccount = false;
        state.refreshTokenTimeoutId = null;
        state.userType = null;
        state.currentCompact = null;
        state.error = null;
    },
    [MutationTypes.UPDATE_ACCOUNT_REQUEST]: (state: any) => {
        state.isLoadingAccount = true;
        state.error = null;
    },
    [MutationTypes.UPDATE_ACCOUNT_FAILURE]: (state: any, error: Error) => {
        state.isLoadingAccount = false;
        state.error = error;
    },
    [MutationTypes.UPDATE_ACCOUNT_SUCCESS]: (state: any) => {
        state.isLoadingAccount = false;
        state.error = null;
    },
    [MutationTypes.SET_REFRESH_TIMEOUT_ID]: (state: any, timeoutId: number|null) => {
        state.refreshTokenTimeoutId = timeoutId;
    },
    [MutationTypes.GET_PRIVILEGE_PURCHASE_INFORMATION_REQUEST]: (state: any) => {
        state.isLoadingPrivilegePurchaseOptions = true;
        state.error = null;
    },
    [MutationTypes.GET_PRIVILEGE_PURCHASE_INFORMATION_SUCCESS]: (state: any) => {
        state.isLoadingPrivilegePurchaseOptions = false;
        state.error = null;
    },
    [MutationTypes.GET_PRIVILEGE_PURCHASE_INFORMATION_FAILURE]: (state: any, error: Error) => {
        state.isLoadingPrivilegePurchaseOptions = false;
        state.error = error;
    },
    [MutationTypes.SAVE_SELECTED_PRIVILEGE_PURCHASES_TO_STORE]: (
        state: any,
        privilegePurchaseChoices: Array<string>
    ) => {
        state.selectedPrivilegesToPurchase = privilegePurchaseChoices;
    },
    [MutationTypes.SET_ATTESTATIONS_ACCEPTED]: (state: any, areAttestationsAccepted: boolean) => {
        state.arePurchaseAttestationsAccepted = areAttestationsAccepted;
    },
    [MutationTypes.POST_PRIVILEGE_PURCHASE_REQUEST]: (state: any) => {
        state.isLoadingPrivilegePurchaseOptions = true;
        state.error = null;
    },
    [MutationTypes.POST_PRIVILEGE_PURCHASE_SUCCESS]: (state: any) => {
        state.isLoadingPrivilegePurchaseOptions = false;
        state.selectedPrivilegesToPurchase = null;
        state.arePurchaseAttestationsAccepted = false;
        state.error = null;
    },
    [MutationTypes.POST_PRIVILEGE_PURCHASE_FAILURE]: (state: any, error: Error) => {
        state.isLoadingPrivilegePurchaseOptions = false;
        state.error = error;
    },
    [MutationTypes.END_MILITARY_AFFILIATION_REQUEST]: (state: any) => {
        state.isLoadingAccount = true;
        state.error = null;
    },
    [MutationTypes.END_MILITARY_AFFILIATION_SUCCESS]: (state: any) => {
        state.isLoadingAccount = false;
        state.selectedPrivilegesToPurchase = null;
        state.arePurchaseAttestationsAccepted = false;
        state.error = null;
    },
    [MutationTypes.END_MILITARY_AFFILIATION_FAILURE]: (state: any, error: Error) => {
        state.isLoadingAccount = false;
        state.error = error;
    },
};
