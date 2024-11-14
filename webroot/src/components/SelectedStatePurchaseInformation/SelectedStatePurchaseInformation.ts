//
//  SelectedStatePurchaseInformation.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/12/2024.
//

import { Component, Vue, toNative } from 'vue-facing-decorator';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import Modal from '@components/Modal/Modal.vue';
import { Compact } from '@models/Compact/Compact.model';
import { FormInput } from '@/models/FormInput/FormInput.model';
import { License, LicenseStatus } from '@/models/License/License.model';
import { Licensee } from '@models/Licensee/Licensee.model';
import { LicenseeUser } from '@/models/LicenseeUser/LicenseeUser.model';
import { PrivilegePurchaseOption } from '@models/PrivilegePurchaseOption/PrivilegePurchaseOption.model';
import { State } from '@/models/State/State.model';
import moment from 'moment';

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

    get licenseList(): Array<License> {
        return this.licensee?.licenses || [];
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
