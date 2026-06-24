//
//  global.getters.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

import { AppModes, AppGroupModes } from '@/app.config';
import { State } from './global.state';

export default {
    // isLoading: (state: State) => state.isLoading,
    // error: (state: State) => state.error,
    // isModalOpen: (state: State) => state.isModalOpen,
    isAppModeJcc: (state: State) => state.appMode === AppModes.JCC,
    isAppModeCosmetology: (state: State) => state.appMode === AppModes.COSMETOLOGY,
    isAppModeSocialWork: (state: State) => state.appMode === AppModes.SOCIAL_WORK,
    isAppGroupModePrivilegePurchase: (state: State) => state.appGroupMode === AppGroupModes.PRIVILEGE_PURCHASE,
    isAppGroupModeMultiState: (state: State) => state.appGroupMode === AppGroupModes.MULTI_STATE,
};
