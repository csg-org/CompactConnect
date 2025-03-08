//
//  SelectedLicenseInfo.ts
//  CompactConnect
//
//  Created by InspiringApps on 3/7/2025.
//

import { Component, Vue, toNative } from 'vue-facing-decorator';
import { License } from '@/models/License/License.model';

@Component({
    name: 'SelectedLicenseInfo',
})
class SelectedLicenseInfo extends Vue {
    // PROPS

    //
    // Data
    //

    //
    // Lifecycle
    //

    //
    // Computed
    //
    get license(): License | null {
        return this.$store.getters['user/getLicenseSelected']();
    }

    get expirationDisplay(): string {
        return `Exp ${this.license?.expireDateDisplay()}`;
    }

    //
    // Methods
    //
}

export default toNative(SelectedLicenseInfo);

// export default SelectedLicenseInfo;
