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
import LicenseActionsModal from '@components/LicenseActionsModal/LicenseActionsModal.vue';
import LicenseIcon from '@components/Icons/LicenseIcon/LicenseIcon.vue';
import LicenseHomeIcon from '@components/Icons/LicenseHome/LicenseHome.vue';
import MapPinIcon from '@components/Icons/MapPin/MapPin.vue';
import GlobeIcon from '@components/Icons/Globe/Globe.vue';
import CheckCircleIcon from '@components/Icons/CheckCircle/CheckCircle.vue';
import CloseXIcon from '@components/Icons/CloseX/CloseX.vue';
import { License, LicenseStatus, LicenseScope } from '@/models/License/License.model';
import { Licensee } from '@/models/Licensee/Licensee.model';
import { State } from '@/models/State/State.model';

@Component({
    name: 'LicenseCard',
    components: {
        LicenseActionsModal,
        LicenseIcon,
        LicenseHomeIcon,
        MapPinIcon,
        GlobeIcon,
        CheckCircleIcon,
        CloseXIcon,
    }
})
class LicenseCard extends Vue {
    @Prop({ required: true }) license!: License;
    @Prop({ required: true }) licensee!: Licensee;
    @Prop({ default: null }) homeState?: State | null;
    @Prop({ default: false }) shouldIncludeLogo?: boolean;
    @Prop({ default: false }) isPublicSearch!: boolean;

    //
    // Lifecycle
    //
    mounted(): void {
        this.addStatusDescriptionExpansion();
    }

    beforeUnmount(): void {
        this.removeStatusDescriptionExpansion();
    }

    //
    // Computed
    //
    get licenseNumber(): string {
        return this.license?.licenseNumber || '';
    }

    get licenseTypeDisplay(): string {
        return this.license?.licenseTypeDisplay() || '';
    }

    get licenseTypeAbbrev(): string {
        return this.license?.licenseTypeAbbreviation() || '';
    }

    get licenseScope(): string {
        return this.license?.licenseScope || '';
    }

    get licenseScopeDisplay(): string {
        return this.license?.licenseScopeDisplay() || '';
    }

    get isLicenseScopeSingleState(): boolean {
        return this.licenseScope === LicenseScope.SINGLE_STATE;
    }

    get isLicenseScopeMultiState(): boolean {
        return this.licenseScope === LicenseScope.MULTI_STATE;
    }

    get isActive(): boolean {
        return this.license?.status === LicenseStatus.ACTIVE;
    }

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

    get isCompactEligible(): boolean {
        return Boolean(this.license?.isCompactEligible());
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

    get isExpired(): boolean {
        return Boolean(this.license?.isExpired());
    }

    get expiresTitle(): string {
        return (this.isExpired) ? this.$t('licensing.expired') : this.$t('licensing.expires');
    }

    get expiresContent(): string {
        return this.license?.expireDateDisplay() || '';
    }

    get isEncumbered(): boolean {
        return this.license?.isEncumbered() || false;
    }

    get isUnderInvestigation(): boolean {
        return this.license?.isUnderInvestigation() || false;
    }

    get disciplineContent(): string {
        let content = this.$t('licensing.noDiscipline');

        if (this.isEncumbered) {
            content = this.$t('licensing.encumbered');
        } else if (this.isUnderInvestigation) {
            content = this.$t('licensing.underInvestigationStatus');
        }

        return content;
    }

    get shouldShowDiscipline(): boolean {
        return !this.isPublicSearch || this.$isAppModeSocialWork;
    }

    //
    // Methods
    //
    addStatusDescriptionExpansion(): void {
        const statusDescriptionElement = this.$refs.statusDescription as HTMLElement;

        if (statusDescriptionElement) {
            statusDescriptionElement.addEventListener('mouseenter', this.statusDescriptionExpansionEvent);
        }
    }

    removeStatusDescriptionExpansion(): void {
        const statusDescriptionElement = this.$refs.statusDescription as HTMLElement;

        if (statusDescriptionElement) {
            statusDescriptionElement.removeEventListener('mouseenter', this.statusDescriptionExpansionEvent);
        }
    }

    statusDescriptionExpansionEvent(event: Event): void {
        // Simple desktop hover for overflowed status descriptions; mvp while we test how states will use this field.
        const element = event.target as HTMLElement;

        if (!element.title && element.scrollWidth > element.clientWidth) {
            element.title = element.innerText;
        }
    }
}

export default toNative(LicenseCard);
