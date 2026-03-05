//
//  global.getters.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

import { AppModes } from '@/app.config';
import { State } from './global.state';

export default {
    // isLoading: (state: State) => state.isLoading,
    // error: (state: State) => state.error,
    // isModalOpen: (state: State) => state.isModalOpen,
    isAppModeJcc: (state: State) => state.appMode === AppModes.JCC,
    isAppModeCosmetology: (state: State) => state.appMode === AppModes.COSMETOLOGY,
};
