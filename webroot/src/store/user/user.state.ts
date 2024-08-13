//
//  user.state.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

import { User } from '@models/User/User.model';
import localStorage, { tokens } from '@store/local.storage';

export interface State {
    model: User | null;
    isLoggedIn: boolean;
    isLoading: boolean;
    error: any | null;
}

export const state: State = {
    model: null,
    isLoggedIn: (localStorage.getItem(tokens.staff.AUTH_TOKEN) !== null),
    isLoading: false,
    error: null,
};
