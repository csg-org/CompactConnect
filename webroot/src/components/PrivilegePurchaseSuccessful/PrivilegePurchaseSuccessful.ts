//
//  PrivilegePurchaseSuccessful.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/5/2024.
//

import { Component, Vue, Prop } from 'vue-facing-decorator';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import ProgressBar from '@components/ProgressBar/ProgressBar.vue';
import { CompactType } from '@models/Compact/Compact.model';

@Component({
    name: 'PrivilegePurchaseSuccessful',
    components: {
        InputButton,
        ProgressBar
    }
})
export default class PrivilegePurchaseSuccessful extends Vue {
    @Prop({ default: 0 }) flowStep!: number;
    @Prop({ default: 0 }) progressPercent!: number;
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
        const { $store, $router } = this;

        $store.dispatch('user/cleanPurchaseFlowState', 0);

        $store.dispatch('user/getLicenseeAccountRequest');

        $router.push({
            name: 'LicenseeDashboard',
            params: { compact: this.compactType }
        });
    }
}
