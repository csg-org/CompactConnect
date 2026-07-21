//
//  global.state.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//
import { AppModes, AppGroupModes } from '@/app.config';
import { AuthTypes } from '@utils/auth';
import { AppMessage } from '@/models/AppMessage/AppMessage.model';

export interface State {
    isLoading: boolean;
    error: any | null;
    messages: Array<AppMessage>;
    isModalOpen: boolean;
    isModalLogoutOnly: boolean;
    appMode: AppModes;
    isAppModeDisplayed: boolean;
    appGroupMode: AppGroupModes;
    authType: AuthTypes;
    isNavExpanded: boolean;
}

export const state: State = {
    isLoading: false,
    error: null,
    messages: [],
    isModalOpen: false,
    isModalLogoutOnly: false,
    appMode: AppModes.JCC,
    isAppModeDisplayed: false,
    appGroupMode: AppGroupModes.PRIVILEGE_PURCHASE,
    authType: AuthTypes.PUBLIC,
    isNavExpanded: false,
};
