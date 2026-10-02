//
//  global.state.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//
import { AppModes, AppGroupModes } from '@/app.config';
import { getAppGroupModeForAppMode, getHostAppMode } from '@utils/compactConfig';
import { AuthTypes } from '@utils/auth';
import { AppMessage } from '@/models/AppMessage/AppMessage.model';

export const getDefaultAppMode = (): AppModes => getHostAppMode() || AppModes.JCC;

export const getDefaultAppGroupMode = (): AppGroupModes =>
    getAppGroupModeForAppMode(getDefaultAppMode()) || AppGroupModes.PRIVILEGE_PURCHASE;

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
    appMode: getDefaultAppMode(),
    isAppModeDisplayed: false,
    appGroupMode: getDefaultAppGroupMode(),
    authType: AuthTypes.PUBLIC,
    isNavExpanded: false,
};
