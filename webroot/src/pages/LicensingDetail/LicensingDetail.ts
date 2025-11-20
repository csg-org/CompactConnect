//
//  LicensingDetail.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/1/2024.
//

import { Component, Vue } from 'vue-facing-decorator';
import { Permission } from '@/app.config';
import LoadingSpinner from '@components/LoadingSpinner/LoadingSpinner.vue';
import LicenseCard from '@/components/LicenseCard/LicenseCard.vue';
import PrivilegeCard from '@/components/PrivilegeCard/PrivilegeCard.vue';
import MilitaryAffiliationInfoBlock from '@components/MilitaryAffiliationInfoBlock/MilitaryAffiliationInfoBlock.vue';
import CollapseCaretButton from '@components/CollapseCaretButton/CollapseCaretButton.vue';
import AlertIcon from '@components/Icons/AlertTriangle/AlertTriangle.vue';
import LicenseIcon from '@components/Icons/LicenseIcon/LicenseIcon.vue';
import ExpirationExplanationIcon from '@components/Icons/ExpirationExplanationIcon/ExpirationExplanationIcon.vue';
import { CompactType } from '@models/Compact/Compact.model';
import { StaffUser } from '@models/StaffUser/StaffUser.model';
import { Licensee } from '@models/Licensee/Licensee.model';
import { License, LicenseStatus } from '@models/License/License.model';
import { State } from '@models/State/State.model';
import { dataApi } from '@network/data.api';

@Component({
    name: 'LicensingDetail',
    components: {
        LoadingSpinner,
        LicenseCard,
        PrivilegeCard,
        CollapseCaretButton,
        AlertIcon,
        LicenseIcon,
        MilitaryAffiliationInfoBlock,
        ExpirationExplanationIcon
    }
})
export default class LicensingDetail extends Vue {
    //
    // Data
    //
    isPersonalInfoCollapsed = false;
    isLicensesCollapsed = false;
    isPrivsCollapsed = false;
    licenseeFullSsnLoading = false;
    licenseeFullSsn = '';
    licenseeFullSsnError = '';

    //
    // Lifecycle
    //
    async created() {
        await this.fetchLicenseeData();

        if (!this.licensee) {
            this.$router.push({ name: '404' });
        }
    }

    //
    // Computed
    //
    get compact(): string {
        const defaultCompactType = this.$store.state.user.currentCompact?.type;

        return this.$route.params.compact as string || defaultCompactType;
    }

    get userStore() {
        return this.$store.state.user;
    }

    get loggedInUser(): StaffUser {
        return this.userStore.model;
    }

    get hasLoggedInReadSsnAccessForLicensee(): boolean {
        const { compact, loggedInUser, licenseeStates } = this;
        let hasLoggedInReadSsnAccess = false;

        if (compact && loggedInUser) {
            hasLoggedInReadSsnAccess = licenseeStates.some((state) => loggedInUser.hasPermission(
                Permission.READ_SSN,
                this.compact as CompactType,
                state
            ));
        }

        return hasLoggedInReadSsnAccess;
    }

    get licenseeId(): string {
        return this.$route.params.licenseeId as string || '';
    }

    get licenseStore(): any {
        return this.$store.state.license;
    }

    get licensee(): Licensee | null {
        const { licenseeId } = this;
        let storeRecord: Licensee | null = null;

        if (licenseeId && this.licenseStore.model) {
            storeRecord = this.$store.getters['license/licenseeById'](licenseeId);
        }

        return storeRecord;
    }

    get isLicenseeUnderInvestigation(): boolean {
        return this.licensee?.isUnderInvestigation() || false;
    }

    get licenseeInvestigationAlertContent(): string {
        const investigationStates = this.licensee?.underInvestigationStates() || [];
        const statesContent = (investigationStates.length === 1)
            ? investigationStates[0].name()
            : this.$t('licensing.underInvestigationAlertMultipleLocations');
        let alertContent = '';

        if (investigationStates.length) {
            alertContent += `${this.$t('licensing.underInvestigationAlertLocation', { locations: statesContent })}
            ${this.$t('licensing.underInvestigationAlertStatus')}`;
        }

        return alertContent;
    }

    get licenseeNameDisplay(): string {
        return this.licensee?.nameDisplay() || '';
    }

    get licenseeHomeStateDisplay(): string {
        return this.licensee?.homeJurisdictionDisplay() || '';
    }

    get licenseeLicenses(): Array<License> {
        return this.licensee?.licenses || [];
    }

    get isLoading(): boolean {
        return this.licenseStore?.isLoading || false;
    }

    get activeLicenses(): Array<License> {
        return this.licenseeLicenses.filter((license) => (license.status === LicenseStatus.ACTIVE));
    }

    get licenseePrivileges(): Array<License> {
        return this.licensee?.privileges || [];
    }

    get licenseeStates(): Array<string> {
        const licenseStates = this.activeLicenses
            .map((license) => license.issueState?.abbrev || '')
            .filter((state) => !!state);
        const privilegeStates = this.licenseePrivileges
            .map((privilege) => privilege.issueState?.abbrev || '')
            .filter((state) => !!state);

        return licenseStates.concat(privilegeStates);
    }

    get dob(): string {
        return this.licensee?.dobDisplay() || '';
    }

    get ssn(): string {
        return this.licensee?.ssnDisplay() || '';
    }

    get birthMonthDay(): string {
        return this.licensee?.birthMonthDay || '';
    }

    get addressLine1(): string {
        return this.licensee?.bestLicenseMailingAddress()?.street1 || '';
    }

    get addressLine2(): string {
        return this.licensee?.bestLicenseMailingAddress()?.street2 || '';
    }

    get addressLine3(): string {
        const bestLicenseAddress = this.licensee?.bestLicenseMailingAddress() || {};
        const { city = '', state = null, zip = '' } = bestLicenseAddress;
        const stateAbbrev = state?.abbrev?.toUpperCase();
        const delim = (city && stateAbbrev) ? ', ' : '';

        return `${city}${delim}${stateAbbrev} ${zip}`.trim();
    }

    get privilegesTitle(): string {
        return this.$t('licensing.privileges');
    }

    get licenseDetails(): string {
        return this.$t('licensing.licenseDetails');
    }

    get personalInformationTitle(): string {
        return this.$t('licensing.personalInformation');
    }

    get licenseExpiredMessage(): string {
        return this.$t('licensing.licenseExpired');
    }

    get homeState(): State | null {
        return this.licensee?.homeJurisdiction || null;
    }

    get homeStateName(): string {
        return this.homeState?.name() || '';
    }

    //
    // Methods
    //
    async fetchLicenseeData(): Promise<void> {
        const { licenseeId } = this;

        await this.$store.dispatch('license/getLicenseeRequest', { compact: this.compact, licenseeId });
    }

    isLicenseActive(license: License): boolean {
        return license?.status === LicenseStatus.ACTIVE;
    }

    isLicenseExpired(license: License): boolean {
        return license?.isExpired() || false;
    }

    togglePersonalInfoCollapsed(): void {
        this.isPersonalInfoCollapsed = !this.isPersonalInfoCollapsed;
    }

    toggleLicensesCollapsed(): void {
        this.isLicensesCollapsed = !this.isLicensesCollapsed;
    }

    togglePrivsCollapsed(): void {
        this.isPrivsCollapsed = !this.isPrivsCollapsed;
    }

    sortingChange(): boolean {
        // Sorting not API supported
        return false;
    }

    paginationChange(): boolean {
        // Pagination not API supported
        return false;
    }

    async revealFullSsn(): Promise<void> {
        this.licenseeFullSsnLoading = true;
        this.licenseeFullSsn = '';
        this.licenseeFullSsnError = '';

        const { compact, licenseeId } = this;
        let isError = false;
        const ssnFullResponse = await dataApi.getLicenseeSsn(compact, licenseeId).catch((error) => {
            isError = true;
            this.licenseeFullSsnError = error?.response?.data?.message || this.$t('serverErrors.networkError');
        });

        if (!isError && ssnFullResponse?.ssn) {
            this.licenseeFullSsn = ssnFullResponse.ssn;
        }

        this.licenseeFullSsnLoading = false;
    }
}
