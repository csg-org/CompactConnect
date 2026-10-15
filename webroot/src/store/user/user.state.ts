//
//  user.state.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

import { getHostAppMode, getImpliedCompactForAppMode } from '@utils/compactConfig';
import { LicenseeUser } from '@models/LicenseeUser/LicenseeUser.model';
import { StaffUser } from '@models/StaffUser/StaffUser.model';
import { Compact } from '@models/Compact/Compact.model';
import {
    authStorage,
    tokens,
    AuthTypes,
    AUTH_TYPE
} from '@utils/auth';
import { PurchaseFlowState } from '@/models/PurchaseFlowState/PurchaseFlowState.model';

export const getImpliedCompactForHost = (): Compact | null => {
    const impliedCompactType = getImpliedCompactForAppMode(getHostAppMode());

    return (impliedCompactType) ? new Compact({ type: impliedCompactType }) : null;
};

export interface State {
    model: StaffUser | LicenseeUser | null;
    isLoggedIn: boolean;
    isLoggedInAsLicensee: boolean;
    isLoggedInAsStaff: boolean;
    isLoadingAccount: boolean;
    isLoadingPrivilegeHistory: boolean;
    isLoadingCompactStates: boolean;
    isLoadingPrivilegePurchaseOptions: boolean;
    refreshTokenTimeoutId: number | null;
    isAutoLogoutWarning: boolean;
    autoLogoutTimeoutId: number | null;
    currentCompact: Compact | null;
    purchase: PurchaseFlowState;
    error: any | null;
}

export const state: State = {
    model: null,
    isLoggedIn: (!!authStorage.getItem(tokens.staff.AUTH_TOKEN) || !!authStorage.getItem(tokens.licensee.AUTH_TOKEN)),
    isLoggedInAsLicensee: Boolean(authStorage.getItem(AUTH_TYPE) === AuthTypes.LICENSEE),
    isLoggedInAsStaff: Boolean(authStorage.getItem(AUTH_TYPE) === AuthTypes.STAFF),
    isLoadingAccount: false,
    isLoadingPrivilegeHistory: false,
    isLoadingCompactStates: false,
    isLoadingPrivilegePurchaseOptions: false,
    refreshTokenTimeoutId: null,
    isAutoLogoutWarning: false,
    autoLogoutTimeoutId: null,
    currentCompact: getImpliedCompactForHost(),
    purchase: new PurchaseFlowState(),
    error: null,
};
