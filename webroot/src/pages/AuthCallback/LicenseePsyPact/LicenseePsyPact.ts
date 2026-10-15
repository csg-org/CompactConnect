//
//  LicenseePsyPact.ts
//  CompactConnect
//
//  Created by InspiringApps on 9/16/2026.
//

import { AppModes } from '@/app.config';
import { AuthTypes } from '@utils/auth';
import { Component, mixins } from 'vue-facing-decorator';
import MixinAuthCallbackHandler from '@pages/AuthCallback/_mixins/handler.mixin';

@Component({
    name: 'AuthCallbackLicenseePsyPact',
})
export default class AuthCallbackLicenseePsyPact extends mixins(MixinAuthCallbackHandler) {
    //
    // Data
    //
    appMode: AppModes = AppModes.PSYPACT;
    authType: AuthTypes = AuthTypes.LICENSEE;
}
