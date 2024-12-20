//
//  global.state.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//
import { AuthTypes } from '@/app.config';
import { AppMessage } from '@/models/AppMessage/AppMessage.model';

export interface State {
    isLoading: boolean;
    error: any | null;
    messages: Array<AppMessage>;
    isModalOpen: boolean;
    isModalLogoutOnly: boolean;
    authType: AuthTypes;
    isNavExpanded: boolean;
}

export const state: State = {
    isLoading: false,
    error: null,
    messages: [],
    isModalOpen: false,
    isModalLogoutOnly: false,
    authType: AuthTypes.PUBLIC,
    isNavExpanded: false,
};
