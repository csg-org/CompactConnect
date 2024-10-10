//
//  LicenseCard.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/8/2024.
//
import {
    Component,
    Vue,
    toNative,
    Prop
} from 'vue-facing-decorator';
import { License, LicenseStatus } from '@/models/License/License.model';
import { State } from '@/models/State/State.model';
import moment from 'moment';

@Component({
    name: 'LicenseCard',
})
class LicenseCard extends Vue {
    @Prop({ required: true }) license?: License;

    //
    // Data
    //

    //
    // Lifecycle
    //

    //
    // Computed
    //
    get statusDisplay():string {
        let licenseStatus = this.$t('licensing.statusOptions.inactive');

        if (this.isActive) {
            licenseStatus = this.$t('licensing.statusOptions.active');
        }

        return licenseStatus;
    }

    get isActive(): boolean {
        return Boolean(this.license && this.license.statusState === LicenseStatus.ACTIVE);
    }

    get stateTitle():string {
        return this.$t('licensing.state');
    }

    get state(): State | null {
        return this.license?.issueState || null;
    }

    get stateContent():string {
        return this.state?.name() || '';
    }

    get issuedTitle():string {
        return this.$t('licensing.issued');
    }

    get issuedContent():string {
        return this.license?.issueDateDisplay() || '';
    }

    get expiresTitle():string {
        return this.$t('licensing.expires');
    }

    get expiresContent():string {
        return this.license?.expireDateDisplay() || '';
    }

    get disciplineTitle():string {
        return this.$t('licensing.disciplineStatus');
    }

    get disciplineContent():string {
        return this.$t('licensing.noDiscipline');
    }

    get licenseTitle():string {
        return this.$t('licensing.license');
    }

    get isPastExiprationDate():boolean {
        let isPastDate = false;

        const expireDate = this.license?.expireDate;

        if (expireDate) {
            const now = moment();
            const expirationDate = moment(expireDate);

            if (!expirationDate.isAfter(now)) {
                isPastDate = true;
            }
        }

        return isPastDate;
    }

    //
    // Methods
    //
}

export default toNative(LicenseCard);

// export default LicenseCard;
