//
//  user.state.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

import { LicenseeUser } from '@models/LicenseeUser/LicenseeUser.model';
import { StaffUser } from '@models/StaffUser/StaffUser.model';
import { Compact } from '@models/Compact/Compact.model';
import { authStorage, tokens } from '@/app.config';

export interface State {
    model: StaffUser | LicenseeUser | null;
    isLoggedIn: boolean;
    isLoadingAccount: boolean;
    isLoadingPrivilegePurchaseOptions: boolean;
    refreshTokenTimeoutId: number | null;
    currentCompact: Compact | null;
    selectedPrivilegesToPurchase: Array<string> | null;
    arePurchaseAttestationsAccepted: boolean;
    error: any | null;
}

export const state: State = {
    model: null,
    isLoggedIn: (!!authStorage.getItem(tokens.staff.AUTH_TOKEN) || !!authStorage.getItem(tokens.licensee.AUTH_TOKEN)),
    isLoadingAccount: false,
    isLoadingPrivilegePurchaseOptions: false,
    arePurchaseAttestationsAccepted: false,
    selectedPrivilegesToPurchase: null,
    refreshTokenTimeoutId: null,
    currentCompact: null,
    error: null,
};
