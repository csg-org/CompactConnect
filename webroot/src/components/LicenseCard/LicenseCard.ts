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
import LicenseHomeIcon from '@components/Icons/LicenseHome/LicenseHome.vue';
import CheckCircleIcon from '@components/Icons/CheckCircle/CheckCircle.vue';
import CloseXIcon from '@components/Icons/CloseX/CloseX.vue';
import { License, LicenseStatus } from '@/models/License/License.model';
import { State } from '@/models/State/State.model';

@Component({
    name: 'LicenseCard',
    components: {
        LicenseIcon,
        LicenseHomeIcon,
        CheckCircleIcon,
        CloseXIcon,
    }
})
class LicenseCard extends Vue {
    @Prop({ required: true }) license!: License;
    @Prop({ default: null }) homeState?: State | null;
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

    get statusDescriptionDisplay(): string {
        return this.license?.statusDescription || '';
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

    get isHomeState(): boolean {
        return this.license?.issueState?.abbrev === this.homeState?.abbrev;
    }

    get issuedTitle(): string {
        return this.$t('licensing.issued');
    }

    get issuedContent(): string {
        return this.license?.issueDateDisplay() || '';
    }

    get expiresTitle(): string {
        return this.isExpired ? this.$t('licensing.expired') : this.$t('licensing.expires');
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

    get licenseNumber(): string {
        return this.license?.licenseNumber || '';
    }

    get isExpired(): boolean {
        return Boolean(this.license?.isExpired());
    }

    get licenseTypeDisplay(): string {
        return this.license?.licenseTypeAbbreviation() || '';
    }

    get isCompactEligible(): boolean {
        return Boolean(this.license?.isCompactEligible());
    }
}

export default toNative(LicenseCard);

// export default LicenseCard;
