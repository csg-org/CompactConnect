//
//  SelectedStatePurchaseInformation.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/12/2024.
//

import { Component, Vue, toNative } from 'vue-facing-decorator';

@Component({
    name: 'SelectedStatePurchaseInformation',
})
class SelectedStatePurchaseInformation extends Vue {
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
    get activeLicense(): License | null {
        return this.licenseList?.find((license) => license.statusState === LicenseStatus.ACTIVE) || null;
    }

    get activeLicenseExpirationDate(): string {
        let date = '';

        if (this.activeLicense) {
            const { expireDate } = this.activeLicense;

            if (expireDate) {
                date = moment(expireDate).format(displayDateFormat);
            }
        }

        return date;
    }

    //
    // Methods
    //
}

export default toNative(SelectedStatePurchaseInformation);

// export default SelectedStatePurchaseInformation;
