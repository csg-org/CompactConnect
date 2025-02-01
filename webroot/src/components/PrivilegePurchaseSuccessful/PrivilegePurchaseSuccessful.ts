//
//  PrivilegePurchaseSuccessful.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/5/2024.
//

import { Component, Vue } from 'vue-facing-decorator';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import { CompactType } from '@models/Compact/Compact.model';

@Component({
    name: 'PrivilegePurchaseSuccessful',
    components: {
        InputButton
    }
})
export default class PrivilegePurchaseSuccessful extends Vue {
    //
    // Computed
    //
    get purchaseSuccessfulTitle(): string {
        return this.$t('payment.purchaseSuccessful');
    }

    get purchaseSuccessfulMessage(): string {
        return this.$t('payment.purchaseSuccessfulMessage');
    }

    get finishText(): string {
        return this.$t('common.finish');
    }

    get userStore() {
        return this.$store.state.user;
    }

    get compactType(): CompactType | null {
        return this.userStore.currentCompact?.type;
    }

    //
    // Methods
    //
    handleFinishClicked() {
        this.$store.dispatch('user/getLicenseeAccountRequest');

        this.$router.push({
            name: 'LicenseeDashboard',
            params: { compact: this.compactType }
        });
    }
}
