//
//  StaffJcc.ts
//  CompactConnect
//
//  Created by InspiringApps on 6/24/2026.
//

import { AppModes } from '@/app.config';
import { AuthTypes } from '@utils/auth';
import { Component, mixins } from 'vue-facing-decorator';
import MixinAuthCallbackHandler from '@pages/AuthCallback/_mixins/handler.mixin';

@Component({
    name: 'AuthCallbackStaffJcc',
})
export default class AuthCallbackStaffJcc extends mixins(MixinAuthCallbackHandler) {
    //
    // Data
    //
    appMode: AppModes = AppModes.JCC;
    authType: AuthTypes = AuthTypes.STAFF;
}
