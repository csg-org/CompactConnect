//
//  SelectPrivileges.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/15/2024.
//

import { Component, Vue } from 'vue-facing-decorator';
import { Compact } from '@models/Compact/Compact.model';
import { PrivilegePurchaseOption } from '@models/PrivilegePurchaseOption/PrivilegePurchaseOption.model';

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
    get unfilteredPuchaseList(): Array<PrivilegePurchaseOption> | null {
        return this.currentCompact?.privilegePurchaseOptions || null;
    }

    get currentCompact(): Compact | null {
        return this.userStore?.currentCompact || null;
    }

    get userStore(): any {
        return this.$store.state.user || null;
    }

    //
    // Methods
    //
}
