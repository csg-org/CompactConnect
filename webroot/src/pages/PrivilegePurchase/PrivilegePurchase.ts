//
//  PrivilegePurchase.ts
//  CompactConnect
//
//  Created by InspiringApps on 1/31/2025.
//

import { Component, Vue } from 'vue-facing-decorator';
import PrivilegePurchaseInformationConfirmation from '@components/PrivilegePurchaseInformationConfirmation/PrivilegePurchaseInformationConfirmation.vue';
import PrivilegePurchaseSelect from '@components/PrivilegePurchaseSelect/PrivilegePurchaseSelect.vue';
import PrivilegePurchaseAttestation from '@components/PrivilegePurchaseAttestation/PrivilegePurchaseAttestation.vue';
import PrivilegePurchaseFinalize from '@components/PrivilegePurchaseFinalize/PrivilegePurchaseFinalize.vue';
import PrivilegePurchaseSuccessful from '@components/PrivilegePurchaseSuccessful/PrivilegePurchaseSuccessful.vue';
import { Compact } from '@models/Compact/Compact.model';

@Component({
    name: 'PrivilegePurchase',
    components: {
        PrivilegePurchaseInformationConfirmation,
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
    created() {
        if (this.currentCompactType) {
            this.$router.push({
                name: 'PrivilegePurchaseInformationConfirmation',
                params: { compact: this.currentCompactType }
            });
        }
    }

    //
    // Computed
    //
    get userStore(): any {
        return this.$store.state.user;
    }

    get currentCompact(): Compact | null {
        return this.userStore?.currentCompact || null;
    }

    get currentCompactType(): string | null {
        return this.currentCompact?.type || null;
    }

    get routeName(): string {
        return this.$route?.name?.toString() || '';
    }

    get isConfirmInfoRoute(): boolean {
        return Boolean(this.routeName === 'PrivilegePurchaseInformationConfirmation');
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
