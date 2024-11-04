//
//  PrivilegePurchaseAttestation.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/4/2024.
//

import { Component, Vue } from 'vue-facing-decorator';

@Component({
    name: 'PrivilegePurchaseAttestation',
    components: {}
})
export default class PrivilegePurchaseAttestation extends Vue {
    //
    // Data
    //

    //
    // Lifecycle
    //
    created() {
        this.$store.dispatch('user/setAttestationsAccepted', true);
    }

    //
    // Computed
    //

    //
    // Methods
    //
}
