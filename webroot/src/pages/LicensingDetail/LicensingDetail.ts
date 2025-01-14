//
//  LicensingDetail.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/1/2024.
//

import { Component, Vue } from 'vue-facing-decorator';
import LicenseCard from '@/components/LicenseCard/LicenseCard.vue';
import PrivilegeCard from '@/components/PrivilegeCard/PrivilegeCard.vue';
import ListContainer from '@components/Lists/ListContainer/ListContainer.vue';
import MilitaryDocumentRow from '@components/MilitaryDocumentRow/MilitaryDocumentRow.vue';
import CollapseCaretButton from '@components/CollapseCaretButton/CollapseCaretButton.vue';
import { Licensee } from '@models/Licensee/Licensee.model';
import { License, LicenseStatus } from '@models/License/License.model';
import { MilitaryAffiliation } from '@/models/MilitaryAffiliation/MilitaryAffiliation.model';
import moment from 'moment';

@Component({
    name: 'LicensingDetail',
    components: {
        LicenseCard,
        PrivilegeCard,
        CollapseCaretButton,
        ListContainer,
        MilitaryDocumentRow
    }
})
export default class LicensingDetail extends Vue {
    //
    //
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

        console.log('storeRecord', storeRecord);

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
        return `${this.licensee?.address?.city}, ${this.licensee?.address?.state?.abbrev} ${this.licensee?.address?.zip}`;
    }

    get privilegeList(): Array<License> {
        // From list of all privileges associated with user (independent of status),
        // returns only most recent privilege fetched associated with each state
        // to positively and most clearly display user's status in each state
        const privilegeList: Array<License> = [];

        this.licenseePrivileges.forEach((privilege) => {
            const previousEntryOfStateIndex = privilegeList.findIndex((state) =>
                state?.issueState?.abbrev === privilege?.issueState?.abbrev);
            const previousEntryOfState = privilegeList[previousEntryOfStateIndex];

            // If no existing entry of state add to array
            if (previousEntryOfStateIndex === -1) {
                privilegeList.push(privilege);
            // If currently observed privilege is newer than saved entry replace existing entry
            } else if (
                privilege.renewalDate
                && previousEntryOfState.renewalDate
                && moment(privilege.renewalDate).isAfter(moment(previousEntryOfState.renewalDate))
            ) {
                privilegeList[previousEntryOfStateIndex] = privilege;
            }
        });

        return privilegeList;
    }

    get licenseList(): Array<License> {
        // From list of all licenses associated with user (independent of status),
        // returns only most recent license fetched associated with each state
        // to positively and most clearly display user's status in each state
        const licenseList: Array<License> = [];

        this.licenseeLicenses.forEach((license) => {
            const previousEntryOfStateIndex = licenseList.findIndex((state) =>
                state?.issueState?.abbrev === license?.issueState?.abbrev);
            const previousEntryOfState = licenseList[previousEntryOfStateIndex];

            // If no existing entry of state add to array
            if (previousEntryOfStateIndex === -1) {
                licenseList.push(license);
            // If currently observed license is newer than saved entry replace existing entry
            } else if (
                license.renewalDate
                && previousEntryOfState.renewalDate
                && moment(license.renewalDate).isAfter(moment(previousEntryOfState.renewalDate))
            ) {
                licenseList[previousEntryOfStateIndex] = license;
            }
        });

        return licenseList;
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

    get statusTitleText(): string {
        return this.$t('licensing.status').toUpperCase();
    }

    get status(): string {
        let militaryStatus = '';

        if (this.licensee) {
            militaryStatus = this.licensee.isMilitary() ? this.$t('licensing.statusOptions.active') : this.$t('licensing.statusOptions.inactive');
        }

        return militaryStatus;
    }

    get affiliationTypeTitle(): string {
        return this.$t('military.affiliationType').toUpperCase();
    }

    get affiliationType(): string {
        let militaryStatus = '';

        if (this.licensee) {
            const activeAffiliation = this.licensee.aciveMilitaryAffiliation() as any;
            const isMilitary = this.licensee.isMilitary();

            if (isMilitary && activeAffiliation?.affiliationType === 'militaryMember') {
                militaryStatus = this.$tm('military.affiliationTypes.militaryMember');
            } else if (isMilitary && activeAffiliation?.affiliationType === 'militaryMemberSpouse') {
                militaryStatus = this.$tm('military.affiliationTypes.militaryMemberSpouse');
            } else {
                militaryStatus = this.$tm('military.affiliationTypes.none');
            }
        }

        return militaryStatus;
    }

    get militaryAffilitionDocs(): string {
        return this.$t('licensing.militaryAffilitionDocs').toUpperCase();
    }

    get militaryDocumentHeader(): any {
        return { name: this.$t('military.fileName'), date: this.$t('military.dateUploaded') };
    }

    get listId(): string {
        return 'military-affiliations';
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
        console.log('this.licensee', this.licensee);
        return this.licensee?.address?.state?.name() || '';
    }

    //
    // Methods
    //
    async fetchLicenseeData(): Promise<void> {
        const { licenseeId } = this;

        await this.$store.dispatch('license/getLicenseeRequest', { compact: this.compact, licenseeId });
    }

    checkIfLicenseActive(license: License) {
        let isLicenseActive = false;

        if (license && license.statusState === LicenseStatus.ACTIVE) {
            isLicenseActive = true;
        }

        return isLicenseActive;
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
