//
//  compacts.d.ts
//  CompactConnect
//
//  Created by InspiringApps on 8/17/2026.
//

import { AppModes, AppGroupModes } from '@/app.config';
import { CompactConfig } from './compacts.plugin';

declare module '@vue/runtime-core' {
    interface ComponentCustomProperties {
        $compactsAll: Array<CompactConfig>, // Includes compacts disabled for the current environment; prefer $compactsEnabled for anything user-selectable
        $compactsEnabled: Array<CompactConfig>,
        $appMode: AppModes,
        $appGroupMode: AppGroupModes,
        $isAppModeJcc: boolean,
        $isAppModeCosmetology: boolean,
        $isAppModeSocialWork: boolean,
        $isAppGroupModePrivilegePurchase: boolean,
        $isAppGroupModeMultiState: boolean,
    }
}
