//
//  LicensingDetail.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/1/2024.
//

import { Component, Vue } from 'vue-facing-decorator';
import LoadingSpinner from '@components/LoadingSpinner/LoadingSpinner.vue';
import LicenseCard from '@/components/LicenseCard/LicenseCard.vue';
import PrivilegeCard from '@/components/PrivilegeCard/PrivilegeCard.vue';
import ListContainer from '@components/Lists/ListContainer/ListContainer.vue';
import MilitaryDocumentRow from '@components/MilitaryDocumentRow/MilitaryDocumentRow.vue';
import CollapseCaretButton from '@components/CollapseCaretButton/CollapseCaretButton.vue';
import LicenseIcon from '@components/Icons/LicenseIcon/LicenseIcon.vue';
import { Licensee } from '@models/Licensee/Licensee.model';
import { License, LicenseStatus } from '@models/License/License.model';
import { MilitaryAffiliation } from '@/models/MilitaryAffiliation/MilitaryAffiliation.model';

@Component({
    name: 'LicensingDetail',
    components: {
        LoadingSpinner,
        LicenseCard,
        PrivilegeCard,
        CollapseCaretButton,
        ListContainer,
        MilitaryDocumentRow,
        LicenseIcon
    }
})
export default class LicensingDetail extends Vue {
    //
    // Data
    //
    isPersonalInfoCollapsed = false;
    isLicensesCollapsed = false;
    isRecentPrivsCollapsed = false;
    isPastPrivsCollapsed = false;

    //
    // Lifecycle
    //
    async mounted() {
        await this.fetchLicenseeData();

        if (!this.licensee) {
            this.$router.push({ name: '404' });
        }
    }

    //
    // Computed
    //
    get compact(): string {
        const defaultCompact = this.$store.state.user.currentCompact;

        return this.$route.params.compact as string || defaultCompact;
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

    get licenseeNameDisplay(): string {
        return this.licensee?.nameDisplay() || '';
    }

    get licenseeHomeStateDisplay(): string {
        return this.licensee?.address?.state?.name() || '';
    }

    get licenseePrivilegeStatesDisplay(): string {
        return this.licensee?.privilegeStatesAllDisplay() || '';
    }

    get licenseeLicenses(): Array<License> {
        return this.licensee?.licenses || [];
    }

    get isLoading(): boolean {
        return this.licenseStore?.isLoading || false;
    }

    get activeLicenses(): Array<License> {
        return this.licenseeLicenses.filter((license) => (license.statusState === LicenseStatus.ACTIVE));
    }

    get licenseePrivileges(): Array<License> {
        return this.licensee?.privileges || [];
    }

    get dob(): string {
        return this.licensee?.dobDisplay() || '';
    }

    get ssn(): string {
        // Task stubbed off here, later ticket will get this value
        return '';
    }

    get licenseNumber(): string {
        // Task stubbed off here, later ticket will get this value
        return '';
    }

    get birthMonthDay(): string {
        return this.licensee?.birthMonthDay || '';
    }

    get addressLine1(): string {
        return this.licensee?.address?.street1 || '';
    }

    get addressLine2(): string {
        return this.licensee?.address?.street2 || '';
    }

    get addressLine3(): string {
        const { address = {}} = this.licensee || {};
        const { city = '', state = null, zip = '' } = address;
        const stateAbbrev = state?.abbrev?.toUpperCase();
        const delim = (city && stateAbbrev) ? ', ' : '';

        return `${city}${delim}${stateAbbrev} ${zip}`.trim();
    }

    get recentPrivilegesTitle(): string {
        return this.$t('licensing.recentPrivilegesTitle');
    }

    get pastPrivilegesTitle(): string {
        return this.$t('licensing.pastPrivilegesTitle');
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

    get militaryStatusTitleText(): string {
        return this.$t('licensing.status').toUpperCase();
    }

    get militaryStatus(): string {
        let status = '';

        if (this.licensee) {
            status = this.licensee.isMilitary() ? this.$t('licensing.statusOptions.active') : this.$t('licensing.statusOptions.inactive');
        }

        return status;
    }

    get affiliationTypeTitle(): string {
        return this.$t('military.affiliationType').toUpperCase();
    }

    get affiliationType(): string {
        let affiliationType = '';

        if (this.licensee) {
            const activeAffiliation = this.licensee.aciveMilitaryAffiliation() as any;
            const isMilitary = this.licensee.isMilitary();

            if (isMilitary && activeAffiliation?.affiliationType === 'militaryMember') {
                affiliationType = this.$tm('military.affiliationTypes.militaryMember');
            } else if (isMilitary && activeAffiliation?.affiliationType === 'militaryMemberSpouse') {
                affiliationType = this.$tm('military.affiliationTypes.militaryMemberSpouse');
            } else {
                affiliationType = this.$tm('military.affiliationTypes.none');
            }
        }

        return affiliationType;
    }

    get militaryAffilitionDocs(): string {
        return this.$t('licensing.militaryAffilitionDocs').toUpperCase();
    }

    get militaryDocumentHeader(): any {
        return { name: this.$t('military.fileName'), date: this.$t('military.dateUploaded') };
    }

    get sortOptions(): Array<any> {
        // Sorting not API supported
        return [];
    }

    get affiliations(): Array<any> {
        let affiliations: any = [];

        if (this.licensee && this.licensee?.militaryAffiliations) {
            affiliations = (this.licensee.militaryAffiliations)
                .map((militaryAffiliation: MilitaryAffiliation) => {
                    const affiliationDisplay = { name: '', date: '' };

                    if (militaryAffiliation.fileNames && (militaryAffiliation.fileNames as Array<string>).length) {
                        affiliationDisplay.name = militaryAffiliation.fileNames[0] || '';
                        affiliationDisplay.date = militaryAffiliation.dateOfUploadDisplay();
                    }

                    return affiliationDisplay;
                });
        }

        return affiliations;
    }

    get homeState(): string {
        return this.licensee?.address?.state?.name() || '';
    }

    get pastPrivilegeList(): Array<License> {
        const privilegeList: Array<License> = [];

        this.licenseePrivileges.forEach((privilege) => {
            privilege.history?.forEach((historyItem: any) => {
                privilegeList.push(new License({
                    ...privilege,
                    expireDate: historyItem.previousValues?.dateOfExpiration || null,
                    issueDate: historyItem.previousValues?.dateOfIssuance || null,
                    statusState: LicenseStatus.INACTIVE
                }));
            });
        });

        return privilegeList;
    }

    //
    // Methods
    //
    async fetchLicenseeData(): Promise<void> {
        const { licenseeId } = this;

        await this.$store.dispatch('license/getLicenseeRequest', { compact: this.compact, licenseeId });
    }

    isLicenseActive(license: License): boolean {
        return license && license.statusState === LicenseStatus.ACTIVE;
    }

    togglePersonalInfoCollapsed() {
        this.isPersonalInfoCollapsed = !this.isPersonalInfoCollapsed;
    }

    toggleLicensesCollapsed() {
        this.isLicensesCollapsed = !this.isLicensesCollapsed;
    }

    toggleRecentPrivsCollapsed() {
        this.isRecentPrivsCollapsed = !this.isRecentPrivsCollapsed;
    }

    togglePastPrivsCollapsed() {
        this.isPastPrivsCollapsed = !this.isPastPrivsCollapsed;
    }

    sortingChange() {
        // Sorting not API supported
        return false;
    }

    paginationChange() {
        // Pagination not API supported
        return false;
    }
}
