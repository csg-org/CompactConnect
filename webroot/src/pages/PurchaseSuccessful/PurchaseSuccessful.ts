//
//  PurchaseSuccessful.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/5/2024.
//

import { Component, Vue } from 'vue-facing-decorator';

@Component({
    name: 'PurchaseSuccessful',
    components: {}
})
export default class PurchaseSuccessful extends Vue {
    //
    // Computed
    //
    get purchaseSuccessfulTitle(): string {
        return this.$t('payment.purchaseSuccessful');
    }

    get purchaseSuccessfulMessage(): string {
        return this.$t('payment.purchaseSuccessfulMessage');
    }
}
