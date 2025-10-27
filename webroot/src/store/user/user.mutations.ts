//
//  user.mutations.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//
import { Compact } from '@models/Compact/Compact.model';
import { LicenseeUser } from '@/models/LicenseeUser/LicenseeUser.model';
import { StaffUser } from '@/models/StaffUser/StaffUser.model';
import { PurchaseFlowStep } from '@/models/PurchaseFlowStep/PurchaseFlowStep.model';
import { AuthTypes } from '@/app.config';

export enum MutationTypes {
    LOGIN_REQUEST = '[User] Login Request',
    LOGIN_FAILURE = '[User] Login Failure',
    LOGIN_SUCCESS = '[User] Login Success',
    LOGIN_RESET = '[User] Login Reset',
    LOGOUT_REQUEST = '[User] Logout Request',
    LOGOUT_FAILURE = '[User] Logout Failure',
    LOGOUT_SUCCESS = '[User] Logout Success',
    CREATE_LICENSEE_ACCOUNT_REQUEST = '[User] Create Licensee Account Request',
    CREATE_LICENSEE_ACCOUNT_FAILURE = '[User] Create Licensee Account Failure',
    CREATE_LICENSEE_ACCOUNT_SUCCESS = '[User] Create Licensee Account Success',
    GET_ACCOUNT_REQUEST = '[User] Get Account Request',
    GET_ACCOUNT_FAILURE = '[User] Get Account Failure',
    GET_ACCOUNT_SUCCESS = '[User] Get Account Success',
    GET_COMPACT_STATES_REQUEST = '[User] Get Compact States Request',
    GET_COMPACT_STATES_FAILURE = '[User] Get Compact States Failure',
    GET_COMPACT_STATES_SUCCESS = '[User] Get Compact States Success',
    GET_COMPACT_STATES_FOR_REGISTRATION_REQUEST = '[User] Get Compact States for Registration Request',
    GET_COMPACT_STATES_FOR_REGISTRATION_FAILURE = '[User] Get Compact States for Registration Failure',
    GET_COMPACT_STATES_FOR_REGISTRATION_SUCCESS = '[User] Get Compact States for Registration Success',
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
    GET_PRIVILEGE_HISTORY_REQUEST = '[User] Get Privilege History Request',
    GET_PRIVILEGE_HISTORY_SUCCESS = '[User] Get Privilege History Success',
    GET_PRIVILEGE_HISTORY_FAILURE = '[User] Get Privilege History Failure',
    POST_PRIVILEGE_PURCHASE_REQUEST = '[User] Post Privilege Purchase Request',
    POST_PRIVILEGE_PURCHASE_SUCCESS = '[User] Post Privilege Purchase Success',
    POST_PRIVILEGE_PURCHASE_FAILURE = '[User] Post Privilege Purchase Failure',
    UPLOAD_MILITARY_AFFILIATION_REQUEST = '[User] Post Military Affiliation Request',
    UPLOAD_MILITARY_AFFILIATION_SUCCESS = '[User] Post Military Affiliation Success',
    UPLOAD_MILITARY_AFFILIATION_FAILURE = '[User] Post Military Affiliation Failure',
    END_MILITARY_AFFILIATION_REQUEST = '[User] Patch Military Affiliation Request',
    END_MILITARY_AFFILIATION_SUCCESS = '[User] Patch Military Affiliation Success',
    END_MILITARY_AFFILIATION_FAILURE = '[User] Patch Military Affiliation Failure',
    RESET_TO_PURCHASE_FLOW_STEP = '[User] Reset Purchase Flow State to input flow step',
    SAVE_PURCHASE_FLOW_STEP = '[User] Save a Purchase Flow Step to the Store',
    UPDATE_HOME_JURISDICTION_REQUEST = '[User] Update Home Jurisdiction Request',
    UPDATE_HOME_JURISDICTION_FAILURE = '[User] Update Home Jurisdiction Failure',
    UPDATE_HOME_JURISDICTION_SUCCESS = '[User] Update Home Jurisdiction Success',
    RESET_MFA_LICENSEE_ACCOUNT_REQUEST = '[User] Reset MFA Licensee Account Request',
    RESET_MFA_LICENSEE_ACCOUNT_FAILURE = '[User] Reset MFA Licensee Account Failure',
    RESET_MFA_LICENSEE_ACCOUNT_SUCCESS = '[User] Reset MFA Licensee Account Success',
    CONFIRM_MFA_LICENSEE_ACCOUNT_REQUEST = '[User] Confirm MFA Licensee Account Request',
    CONFIRM_MFA_LICENSEE_ACCOUNT_FAILURE = '[User] Confirm MFA Licensee Account Failure',
    CONFIRM_MFA_LICENSEE_ACCOUNT_SUCCESS = '[User] Confirm MFA Licensee Account Success',
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
    [MutationTypes.CREATE_LICENSEE_ACCOUNT_REQUEST]: (state: any) => {
        state.isLoadingAccount = true;
        state.error = null;
    },
    [MutationTypes.CREATE_LICENSEE_ACCOUNT_FAILURE]: (state: any, error: Error) => {
        state.isLoadingAccount = false;
        state.error = error;
    },
    [MutationTypes.CREATE_LICENSEE_ACCOUNT_SUCCESS]: (state: any) => {
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
    [MutationTypes.GET_COMPACT_STATES_REQUEST]: (state: any) => {
        state.isLoadingCompactStates = true;
        state.error = null;
    },
    [MutationTypes.GET_COMPACT_STATES_FAILURE]: (state: any, error: Error) => {
        state.isLoadingCompactStates = false;
        state.error = error;
    },
    [MutationTypes.GET_COMPACT_STATES_SUCCESS]: (state: any, compactStates: any) => {
        state.isLoadingCompactStates = false;
        state.error = null;

        if (state.currentCompact) {
            state.currentCompact.memberStates = compactStates;
        }
    },
    [MutationTypes.GET_COMPACT_STATES_FOR_REGISTRATION_REQUEST]: (state: any) => {
        state.isLoadingCompactStates = true;
        state.error = null;
    },
    [MutationTypes.GET_COMPACT_STATES_FOR_REGISTRATION_FAILURE]: (state: any, error: Error) => {
        state.isLoadingCompactStates = false;
        state.error = error;
    },
    [MutationTypes.GET_COMPACT_STATES_FOR_REGISTRATION_SUCCESS]: (state: any) => {
        state.isLoadingCompactStates = false;
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
    [MutationTypes.GET_PRIVILEGE_HISTORY_REQUEST]: (state: any) => {
        state.isLoadingPrivilegeHistory = true;
        state.error = null;
    },
    [MutationTypes.GET_PRIVILEGE_HISTORY_SUCCESS]: (state: any, { history }) => {
        const privilegeId = `${history.providerId}-${history.jurisdiction}-${history.licenseType}`;
        const foundPrivilege = (state.model?.licensee?.privileges?.find((privilege) =>
            (privilege.id === privilegeId)) || null);

        if (foundPrivilege) {
            foundPrivilege.history = history.events;
        }

        state.isLoadingPrivilegeHistory = false;
        state.error = null;
    },
    [MutationTypes.GET_PRIVILEGE_HISTORY_FAILURE]: (state: any, error: Error) => {
        state.isLoadingPrivilegeHistory = false;
        state.error = error;
    },
    [MutationTypes.POST_PRIVILEGE_PURCHASE_REQUEST]: (state: any) => {
        state.isLoadingPrivilegePurchaseOptions = true;
        state.error = null;
    },
    [MutationTypes.POST_PRIVILEGE_PURCHASE_SUCCESS]: (state: any) => {
        state.isLoadingPrivilegePurchaseOptions = false;
        state.selectedPrivilegesToPurchase = null;
        state.error = null;
    },
    [MutationTypes.POST_PRIVILEGE_PURCHASE_FAILURE]: (state: any, error: Error) => {
        state.isLoadingPrivilegePurchaseOptions = false;
        state.error = error;
    },
    [MutationTypes.UPLOAD_MILITARY_AFFILIATION_REQUEST]: (state: any) => {
        state.isLoadingAccount = true;
        state.error = null;
    },
    [MutationTypes.UPLOAD_MILITARY_AFFILIATION_SUCCESS]: (state: any) => {
        state.isLoadingAccount = false;
        state.error = null;
    },
    [MutationTypes.UPLOAD_MILITARY_AFFILIATION_FAILURE]: (state: any, error: Error) => {
        state.isLoadingAccount = false;
        state.error = error;
    },
    [MutationTypes.END_MILITARY_AFFILIATION_REQUEST]: (state: any) => {
        state.isLoadingAccount = true;
        state.error = null;
    },
    [MutationTypes.END_MILITARY_AFFILIATION_SUCCESS]: (state: any) => {
        state.isLoadingAccount = false;
        state.error = null;
    },
    [MutationTypes.END_MILITARY_AFFILIATION_FAILURE]: (state: any, error: Error) => {
        state.isLoadingAccount = false;
        state.error = error;
    },
    [MutationTypes.RESET_TO_PURCHASE_FLOW_STEP]: (state: any, flowStepNum: number) => {
        state.purchase.steps = state.purchase.steps.filter((step) => (step.stepNum < flowStepNum));
    },
    [MutationTypes.SAVE_PURCHASE_FLOW_STEP]: (state: any, flowStep: PurchaseFlowStep) => {
        state.purchase.steps = [
            ...state.purchase.steps,
            flowStep
        ];
    },
    [MutationTypes.UPDATE_HOME_JURISDICTION_REQUEST]: (state: any) => {
        state.isLoadingAccount = true;
        state.error = null;
    },
    [MutationTypes.UPDATE_HOME_JURISDICTION_FAILURE]: (state: any, error: Error) => {
        state.isLoadingAccount = false;
        state.error = error;
    },
    [MutationTypes.UPDATE_HOME_JURISDICTION_SUCCESS]: (state: any) => {
        state.isLoadingAccount = false;
        state.error = null;
    },
    [MutationTypes.RESET_MFA_LICENSEE_ACCOUNT_REQUEST]: (state: any) => {
        state.isLoadingAccount = true;
        state.error = null;
    },
    [MutationTypes.RESET_MFA_LICENSEE_ACCOUNT_FAILURE]: (state: any, error: Error) => {
        state.isLoadingAccount = false;
        state.error = error;
    },
    [MutationTypes.RESET_MFA_LICENSEE_ACCOUNT_SUCCESS]: (state: any) => {
        state.isLoadingAccount = false;
        state.error = null;
    },
    [MutationTypes.CONFIRM_MFA_LICENSEE_ACCOUNT_REQUEST]: (state: any) => {
        state.isLoadingAccount = false;
        state.error = null;
    },
    [MutationTypes.CONFIRM_MFA_LICENSEE_ACCOUNT_FAILURE]: (state: any, error: Error) => {
        state.isLoadingAccount = false;
        state.error = error;
    },
    [MutationTypes.CONFIRM_MFA_LICENSEE_ACCOUNT_SUCCESS]: (state: any) => {
        state.isLoadingAccount = false;
        state.error = null;
    },
};
