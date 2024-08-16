//
//  user.state.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

import { User } from '@models/User/User.model';
import { authStorage, tokens } from '@/app.config';

export interface State {
    model: User | null;
    isLoggedIn: boolean;
    isLoading: boolean;
    refreshTokenTimeoutId: number | null;
    error: any | null;
}

export const state: State = {
    model: null,
    isLoggedIn: (authStorage.getItem(tokens.staff.AUTH_TOKEN) !== null),
    isLoading: false,
    refreshTokenTimeoutId: null,
    error: null,
};
