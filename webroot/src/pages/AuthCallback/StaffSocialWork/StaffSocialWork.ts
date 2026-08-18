//
//  StaffSocialWork.ts
//  CompactConnect
//
//  Created by InspiringApps on 6/24/2026.
//

import { AppModes } from '@/app.config';
import { AuthTypes } from '@utils/auth';
import { Component, mixins } from 'vue-facing-decorator';
import MixinAuthCallbackHandler from '@pages/AuthCallback/_mixins/handler.mixin';

@Component({
    name: 'AuthCallbackStaffSocialWork',
})
export default class AuthCallbackStaffSocialWork extends mixins(MixinAuthCallbackHandler) {
    //
    // Data
    //
    appMode: AppModes = AppModes.SOCIAL_WORK;
    authType: AuthTypes = AuthTypes.STAFF;
}
