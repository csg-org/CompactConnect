//
//  PrivilegePurchase.ts
//  CompactConnect
//
//  Created by InspiringApps on 1/31/2025.
//

import { Component, Vue } from 'vue-facing-decorator';
import PrivilegePurchaseSelect from '@components/PrivilegePurchaseSelect/PrivilegePurchaseSelect.vue';
import PrivilegePurchaseAttestation from '@components/PrivilegePurchaseAttestation/PrivilegePurchaseAttestation.vue';
import PrivilegePurchaseFinalize from '@components/PrivilegePurchaseFinalize/PrivilegePurchaseFinalize.vue';
import PrivilegePurchaseSuccessful from '@components/PrivilegePurchaseSuccessful/PrivilegePurchaseSuccessful.vue';

@Component({
    name: 'PrivilegePurchase',
    components: {
        PrivilegePurchaseSelect,
        PrivilegePurchaseAttestation,
        PrivilegePurchaseFinalize,
        PrivilegePurchaseSuccessful
    }
})
export default class PrivilegePurchase extends Vue {
    //
    // Data
    //

    //
    // Lifecycle
    //

    //
    // Computed
    //
    get routeName(): string {
        return this.$route?.name?.toString() || '';
    }

    get isSelectPrivilegesRoute(): boolean {
        return Boolean(this.routeName === 'PrivilegePurchaseSelect');
    }

    get isAttestationRoute(): boolean {
        return Boolean(this.routeName === 'PrivilegePurchaseAttestation');
    }

    get isFinalizeRoute(): boolean {
        return Boolean(this.routeName === 'PrivilegePurchaseFinalize');
    }

    get isPurchaseSuccessfulRoute(): boolean {
        return Boolean(this.routeName === 'PrivilegePurchaseSuccessful');
    }

    //
    // Methods
    //
}
