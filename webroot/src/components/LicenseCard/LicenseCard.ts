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
import LicenseIcon from '@components/Icons/LicenseIcon/LicenseIcon.vue';
import { License, LicenseStatus } from '@/models/License/License.model';
import { State } from '@/models/State/State.model';
import moment from 'moment';

@Component({
    name: 'LicenseCard',
    components: {
        LicenseIcon
    }
})
class LicenseCard extends Vue {
    @Prop({ required: true }) license?: License;
    @Prop({ default: false }) shouldIncludeLogo?: boolean;

    //
    // Computed
    //
    get statusDisplay(): string {
        let licenseStatus = this.$t('licensing.statusOptions.inactive');

        if (this.isActive) {
            licenseStatus = this.$t('licensing.statusOptions.active');
        }

        return licenseStatus;
    }

    get isActive(): boolean {
        return Boolean(this.license && this.license.status === LicenseStatus.ACTIVE);
    }

    get state(): State | null {
        return this.license?.issueState || null;
    }

    get stateContent(): string {
        return this.state?.name() || '';
    }

    get issuedTitle(): string {
        return this.$t('licensing.issued');
    }

    get issuedContent(): string {
        return this.license?.issueDateDisplay() || '';
    }

    get expiresTitle(): string {
        return this.$t('licensing.expires');
    }

    get expiresContent(): string {
        return this.license?.expireDateDisplay() || '';
    }

    get disciplineTitle(): string {
        return this.$t('licensing.disciplineStatus');
    }

    get disciplineContent(): string {
        return this.$t('licensing.noDiscipline');
    }

    get licenseTitleDisplay(): string {
        return this.$t('licensing.license').toUpperCase();
    }

    get licenseNumber(): string {
        return this.license?.licenseNumber || '';
    }

    get isPastExiprationDate(): boolean {
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

    get licenseTypeDisplay(): string {
        return this.license?.licenseTypeAbbreviation() || '';
    }
}

export default toNative(LicenseCard);

// export default LicenseCard;
