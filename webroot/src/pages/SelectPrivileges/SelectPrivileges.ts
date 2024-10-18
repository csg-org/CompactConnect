//
//  SelectPrivileges.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/15/2024.
//

import { Component, Vue } from 'vue-facing-decorator';

@Component({
    name: 'SelectPrivileges',
    components: {}
})
export default class SelectPrivileges extends Vue {
    //
    // Data
    //

    //
    // Lifecycle
    //
    mounted() {
        this.$store.dispatch('user/getPrivilegePurchaseInformationRequest');
    }

    //
    // Computed
    //

    //
    // Methods
    //
}
