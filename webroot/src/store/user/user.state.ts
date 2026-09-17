//
//  user.state.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

import { psypactHostnames } from '@/app.config';
import { LicenseeUser } from '@models/LicenseeUser/LicenseeUser.model';
import { StaffUser } from '@models/StaffUser/StaffUser.model';
import { Compact, CompactType } from '@models/Compact/Compact.model';
import {
    authStorage,
    tokens,
    AuthTypes,
    AUTH_TYPE
} from '@utils/auth';
import { PurchaseFlowState } from '@/models/PurchaseFlowState/PurchaseFlowState.model';

export const getDefaultCurrentCompact = (): Compact | null => {
    const { hostname } = window.location;
    let defaultCurrentCompact: Compact | null = null;

    if (psypactHostnames.includes(hostname)) {
        defaultCurrentCompact = new Compact({ type: CompactType.PSYPACT });
    }

    return defaultCurrentCompact;
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
    currentCompact: getDefaultCurrentCompact(),
    purchase: new PurchaseFlowState(),
    error: null,
};
