//
//  AuthHelper.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/28/2026.
//

import {
    Component,
    Prop,
    Vue,
    toNative
} from 'vue-facing-decorator';
import { CognitoAuthStep } from '@utils/cognitoAuth';

@Component({
    name: 'AuthHelper',
})
class AuthHelper extends Vue {
    @Prop({ default: '' }) screen!: string;

    //
    // Computed
    //
    get isMfaSetup(): boolean {
        return this.screen === CognitoAuthStep.MFA_SETUP;
    }

    get instructions(): string {
        let instructions = '';

        if (this.screen === CognitoAuthStep.NEW_PASSWORD) {
            instructions = this.$t('auth.newPasswordInstructions');
        } else if (this.screen === CognitoAuthStep.MFA_CODE) {
            instructions = this.$t('auth.mfaCodeInstructions');
        } else if (this.screen === CognitoAuthStep.FORGOT_PASSWORD) {
            instructions = this.$t('auth.forgotPasswordInstructions');
        } else if (this.screen === CognitoAuthStep.FORGOT_PASSWORD_CONFIRM) {
            instructions = this.$t('auth.confirmForgotPasswordInstructions');
        }

        return instructions;
    }
}

export default toNative(AuthHelper);
