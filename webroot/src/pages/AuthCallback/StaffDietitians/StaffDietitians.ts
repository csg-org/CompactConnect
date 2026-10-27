//
//  StaffDietitians.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/14/2026.
//

import { AppModes } from '@/app.config';
import { AuthTypes } from '@utils/auth';
import { Component, mixins } from 'vue-facing-decorator';
import MixinAuthCallbackHandler from '@pages/AuthCallback/_mixins/handler.mixin';

@Component({
    name: 'AuthCallbackStaffDietitians',
})
export default class AuthCallbackStaffDietitians extends mixins(MixinAuthCallbackHandler) {
    //
    // Data
    //
    appMode: AppModes = AppModes.DIETITIANS;
    authType: AuthTypes = AuthTypes.STAFF;
}
