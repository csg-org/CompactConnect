//
//  LicenseeJcc.ts
//  CompactConnect
//
//  Created by InspiringApps on 6/24/2026.
//

import { AppModes } from '@/app.config';
import { AuthTypes } from '@utils/auth';
import { config as envConfig } from '@plugins/EnvConfig/envConfig.plugin';
import { Component, mixins } from 'vue-facing-decorator';
import MixinAuthCallbackHandler from '@pages/AuthCallback/_mixins/handler.mixin';

@Component({
    name: 'AuthCallbackLicenseeJcc',
})
export default class AuthCallbackLicenseeJcc extends mixins(MixinAuthCallbackHandler) {
    //
    // Data
    //
    appMode: AppModes = AppModes.JCC;
    authType: AuthTypes = AuthTypes.LICENSEE;
    cognitoAuthDomain = envConfig.cognitoAuthDomainLicensee || '';
    cognitoClientId = envConfig.cognitoClientIdLicensee || '';
}
