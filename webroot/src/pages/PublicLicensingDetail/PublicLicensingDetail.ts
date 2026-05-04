//
//  PublicLicensingDetail.ts
//  CompactConnect
//
//  Created by InspiringApps on 3/17/2025.
//

import { Component, Vue } from 'vue-facing-decorator';
import LoadingSpinner from '@components/LoadingSpinner/LoadingSpinner.vue';
import LicenseCard from '@/components/LicenseCard/LicenseCard.vue';
import PrivilegeCard from '@/components/PrivilegeCard/PrivilegeCard.vue';
import CollapseCaretButton from '@components/CollapseCaretButton/CollapseCaretButton.vue';
import ExpirationExplanationIcon from '@components/Icons/ExpirationExplanationIcon/ExpirationExplanationIcon.vue';
import LicenseIcon from '@components/Icons/LicenseIcon/LicenseIcon.vue';
import { Licensee } from '@models/Licensee/Licensee.model';
import { License, LicenseStatus } from '@models/License/License.model';

@Component({
    name: 'PublicLicensingDetail',
    components: {
        LoadingSpinner,
        LicenseIcon,
        LicenseCard,
        PrivilegeCard,
        CollapseCaretButton,
        ExpirationExplanationIcon
    }
})
export default class PublicLicensingDetail extends Vue {
    //
    // Data
    //
    isLicensesCollapsed = false;
    isPrivsCollapsed = false;

    //
    // Lifecycle
    //
    async created() {
        if (!this.licenseePrivileges.length) {
            await this.fetchLicenseeData();
        }

        if (!this.licensee) {
            this.$router.push({ name: '404' });
        }
    }

    //
    // Computed
    //
    get userStore() {
        return this.$store.state.user;
    }

    get isAppModeJcc(): boolean {
        return this.$store.getters.isAppModeJcc;
    }

    get isAppModeCosmetology(): boolean {
        return this.$store.getters.isAppModeCosmetology;
    }

    get compact(): string {
        const defaultCompactType = this.userStore.currentCompact?.type;

        return this.$route.params.compact as string || defaultCompactType;
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
        return this.licensee?.homeJurisdictionDisplay() || '';
    }

    get isLoading(): boolean {
        return this.licenseStore?.isLoading || false;
    }

    get licenseeLicenses(): Array<License> {
        return (this.licensee?.licenses || []).slice().sort(this.sortLicenses);
    }

    get activeLicenses(): Array<License> {
        return this.licenseeLicenses.filter((license) => (license.status === LicenseStatus.ACTIVE));
    }

    get licenseePrivileges(): Array<License> {
        return (this.licensee?.privileges || []).slice().sort(this.sortPrivileges);
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

    get homeState(): string {
        return this.licensee?.homeJurisdiction?.name() || '';
    }

    //
    // Methods
    //
    async fetchLicenseeData(): Promise<void> {
        const { compact, licenseeId } = this;

        await this.$store.dispatch('license/getLicenseeRequest', {
            compact,
            licenseeId,
            isPublic: true,
        });
    }

    toggleLicensesCollapsed(): void {
        this.isLicensesCollapsed = !this.isLicensesCollapsed;
    }

    togglePrivsCollapsed(): void {
        this.isPrivsCollapsed = !this.isPrivsCollapsed;
    }

    sortLicenses(license1: License, license2: License): number {
        let sort = this.sortByIssueState(license1, license2);

        if (sort === 0) {
            sort = this.sortByLicenseType(license1, license2);
        }

        return sort;
    }

    sortPrivileges(privilege1: License, privilege2: License): number {
        let sort = this.sortByLicenseType(privilege1, privilege2);

        if (sort === 0) {
            sort = this.sortByIssueState(privilege1, privilege2);
        }

        return sort;
    }

    sortByLicenseType(license1: License, license2: License): number {
        const licenseType1 = license1.licenseTypeAbbreviation();
        const licenseType2 = license2.licenseTypeAbbreviation();
        let sort = 0;

        if (licenseType1 < licenseType2) {
            sort = -1;
        } else if (licenseType1 > licenseType2) {
            sort = 1;
        }

        return sort;
    }

    sortByIssueState(license1: License, license2: License): number {
        const state1 = license1.issueState?.name().toLowerCase() || '';
        const state2 = license2.issueState?.name().toLowerCase() || '';
        let sort = 0;

        if (state1 < state2) {
            sort = -1;
        } else if (state1 > state2) {
            sort = 1;
        }

        return sort;
    }
}
