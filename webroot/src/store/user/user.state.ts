//
//  user.state.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

import { LicenseeUser } from '@models/LicenseeUser/LicenseeUser.model';
import { StaffUser } from '@models/StaffUser/StaffUser.model';
import { Compact } from '@models/Compact/Compact.model';
import {
    authStorage,
    tokens,
    AuthTypes,
    AUTH_TYPE
} from '@/app.config';

export interface State {
    model: StaffUser | LicenseeUser | null;
    isLoggedIn: boolean;
    isLoggedInAsLicensee: boolean;
    isLoggedInAsStaff: boolean;
    isLoadingAccount: boolean;
    isLoadingPrivilegePurchaseOptions: boolean;
    refreshTokenTimeoutId: number | null;
    currentCompact: Compact | null;
    purchase: any; // @TODO: Migration to this prop, including typing, will be in #302.
    error: any | null;
}

export const state: State = {
    model: null,
    isLoggedIn: (!!authStorage.getItem(tokens.staff.AUTH_TOKEN) || !!authStorage.getItem(tokens.licensee.AUTH_TOKEN)),
    isLoggedInAsLicensee: Boolean(authStorage.getItem(AUTH_TYPE) === AuthTypes.LICENSEE),
    isLoggedInAsStaff: Boolean(authStorage.getItem(AUTH_TYPE) === AuthTypes.STAFF),
    isLoadingAccount: false,
    isLoadingPrivilegePurchaseOptions: false,
    refreshTokenTimeoutId: null,
    currentCompact: null,
    purchase: {},
    error: null,
};
