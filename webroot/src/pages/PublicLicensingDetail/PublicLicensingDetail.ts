//
//  PublicLicensingDetail.ts
//  CompactConnect
//
//  Created by InspiringApps on 3/17/2025.
//

import { Component, Vue } from 'vue-facing-decorator';
import LoadingSpinner from '@components/LoadingSpinner/LoadingSpinner.vue';
import PrivilegeCard from '@/components/PrivilegeCard/PrivilegeCard.vue';
import CollapseCaretButton from '@components/CollapseCaretButton/CollapseCaretButton.vue';
import { Licensee } from '@models/Licensee/Licensee.model';
import { License, LicenseStatus } from '@models/License/License.model';

@Component({
    name: 'PublicLicensingDetail',
    components: {
        LoadingSpinner,
        PrivilegeCard,
        CollapseCaretButton,
    }
})
export default class PublicLicensingDetail extends Vue {
    //
    // Data
    //
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
    get userStore() {
        return this.$store.state.user;
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

    get licenseePrivileges(): Array<License> {
        return this.licensee?.privileges || [];
    }

    get licenseeStates(): Array<string> {
        return this.licenseePrivileges
            .map((privilege) => privilege.issueState?.abbrev || '')
            .filter((state) => !!state);
    }

    get homeState(): string {
        return this.licensee?.homeJurisdiction?.name() || '';
    }

    get pastPrivilegeList(): Array<License> {
        const privilegeList: Array<License> = [];

        this.licenseePrivileges.forEach((privilege) => {
            privilege.history?.forEach((historyItem: any) => {
                privilegeList.push(new License({
                    ...privilege,
                    expireDate: historyItem.previousValues?.dateOfExpiration || null,
                    issueDate: historyItem.previousValues?.dateOfIssuance || null,
                    status: LicenseStatus.INACTIVE
                }));
            });
        });

        return privilegeList;
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

    toggleRecentPrivsCollapsed(): void {
        this.isRecentPrivsCollapsed = !this.isRecentPrivsCollapsed;
    }

    togglePastPrivsCollapsed(): void {
        this.isPastPrivsCollapsed = !this.isPastPrivsCollapsed;
    }
}
