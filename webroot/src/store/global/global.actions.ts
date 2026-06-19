//
//  global.actions.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

import { AppModes, AppGroupModes } from '@/app.config';
import { MutationTypes } from './global.mutations';

export default {
    startLoading: ({ commit }) => {
        commit(MutationTypes.BEGIN_LOADING);
    },
    endLoading: ({ commit }) => {
        commit(MutationTypes.END_LOADING);
    },
    reset: (context) => {
        context.commit(MutationTypes.STORE_RESET_GLOBAL);
        // context.reset(); // vuex-extensions
    },
    addMessage: ({ commit }, message: object | string) => {
        commit(MutationTypes.PUSH_MESSAGE, message);
    },
    clearMessages: ({ commit }) => {
        commit(MutationTypes.CLEAR_MESSAGES);
    },
    setModalIsOpen: ({ commit }, isOpen) => {
        commit(MutationTypes.SET_MODAL_OPEN, isOpen);
    },
    setModalIsLogoutOnly: ({ commit }, isLogoutOnly) => {
        commit(MutationTypes.SET_MODAL_LOGOUT_ONLY, isLogoutOnly);
    },
    setAppMode: ({ commit }, mode) => {
        commit(MutationTypes.SET_APP_MODE, mode);

        switch (mode) {
        case AppModes.JCC:
            // Intentional fall through for all privilege-purchase compacts
            commit(MutationTypes.SET_APP_GROUP_MODE, AppGroupModes.PRIVILEGE_PURCHASE);
            break;
        case AppModes.COSMETOLOGY:
        case AppModes.SOCIAL_WORK:
            // Intentional fall through for all multi-state compacts
            commit(MutationTypes.SET_APP_GROUP_MODE, AppGroupModes.MULTI_STATE);
            break;
        default:
            break;
        }
    },
    setAppModeDisplay: ({ commit }, isDisplayed) => {
        commit(MutationTypes.SET_APP_MODE_DISPLAY, isDisplayed);
    },
    setAppGroupMode: ({ commit }, groupMode) => {
        commit(MutationTypes.SET_APP_GROUP_MODE, groupMode);
    },
    setAuthType: ({ commit }, type) => {
        commit(MutationTypes.SET_AUTH_TYPE, type);
    },
    expandNavMenu: ({ commit }) => {
        commit(MutationTypes.EXPAND_NAV_MENU);
    },
    collapseNavMenu: ({ commit }) => {
        commit(MutationTypes.COLLAPSE_NAV_MENU);
    },
};
