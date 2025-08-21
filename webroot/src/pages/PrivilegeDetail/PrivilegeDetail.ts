//
//  PrivilegeDetail.ts
//  CompactConnect
//
//  Created by InspiringApps on 3/18/2025.
//

import {
    Component,
    Vue,
    Watch
} from 'vue-facing-decorator';
import { AuthTypes } from '@/app.config';
import LoadingSpinner from '@components/LoadingSpinner/LoadingSpinner.vue';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import PrivilegeDetailBlock from '@components/PrivilegeDetailBlock/PrivilegeDetailBlock.vue';
import { License } from '@models/License/License.model';
import { Licensee } from '@models/Licensee/Licensee.model';

@Component({
    name: 'PrivilegeDetail',
    components: {
        InputButton,
        PrivilegeDetailBlock,
        LoadingSpinner
    }
})
export default class PrivilegeDetail extends Vue {
    //
    // Lifecycle
    //
    async created() {
        await this.populateData();
    }

    //
    // Computed
    //
    get globalStore() {
        return this.$store.state;
    }

    get authType(): string {
        return this.globalStore.authType;
    }

    get userStore() {
        return this.$store.state.user;
    }

    get user() {
        return this.userStore.model;
    }

    get licenseStore(): any {
        return this.$store.state.license;
    }

    get isLoggedIn(): boolean {
        return this.userStore.isLoggedIn;
    }

    get isLoggedInAsStaff(): boolean {
        return this.authType === AuthTypes.STAFF;
    }

    get isLoggedInAsLicensee(): boolean {
        return this.authType === AuthTypes.LICENSEE;
    }

    get privilegeId(): string {
        return (this.$route.params.privilegeId as string || '');
    }

    get licenseeId(): string {
        return (this.$route.params.licenseeId as string || '');
    }

    get isLoading(): boolean {
        return this.licenseStore?.isLoading || this.userStore?.isLoadingPrivilegeHistory || false;
    }

    get compact(): string {
        const defaultCompactType = this.$store.state.user.currentCompact?.type;

        return this.$route.params.compact as string || defaultCompactType;
    }

    get licenseeRecord(): Licensee | null {
        const { licenseeId } = this;
        let storeRecord: Licensee | null = null;

        if (licenseeId && this.licenseStore.model) {
            storeRecord = this.$store.getters['license/licenseeById'](licenseeId);
        }

        return storeRecord;
    }

    get privilege(): License {
        let foundPrivilege = new License();

        if (this.isLoggedInAsLicensee) {
            foundPrivilege = this.$store.getters['user/getUserPrivilegeById'](this.privilegeId) || new License();
        } else if (this.isLoggedInAsStaff && this.licenseeRecord) {
            foundPrivilege = this.licenseeRecord.privileges?.find((privilege) =>
                ((privilege as any).id === this.privilegeId)) || new License();
        }

        return foundPrivilege;
    }

    get privilegeLicenseTypeAbbrev(): string {
        return this.privilege?.licenseTypeAbbreviation() || '';
    }

    get privilegeTitle(): string {
        return `${this.privilegeLicenseTypeAbbrev} - ${this.privilege?.issueState?.name() || ''}`;
    }

    get isPrivilegeLoaded(): boolean {
        return !!this.privilege.id;
    }

    get isPrivilegeHistoryLoaded(): boolean {
        return Boolean(this.privilege.history?.length);
    }

    //
    // Methods
    //
    goBack() {
        this.$router.back();
    }

    async fetchLicenseeData(): Promise<void> {
        const { licenseeId } = this;

        await this.$store.dispatch('license/getLicenseeRequest', { compact: this.compact, licenseeId });
    }

    async fetchPrivilegeHistoryStaff(): Promise<void> {
        const issueStateAbbrev = this.privilege.issueState?.abbrev;

        if (issueStateAbbrev && this.privilegeLicenseTypeAbbrev) {
            await this.$store.dispatch('license/getPrivilegeHistoryRequest', {
                compact: this.compact,
                providerId: this.licenseeId,
                jurisdiction: issueStateAbbrev,
                licenseTypeAbbrev: this.privilegeLicenseTypeAbbrev,
                isPublic: false
            });
        }
    }

    async fetchPrivilegeHistoryLicensee(): Promise<void> {
        const issueStateAbbrev = this.privilege.issueState?.abbrev;

        if (issueStateAbbrev && this.privilegeLicenseTypeAbbrev) {
            await this.$store.dispatch('user/getPrivilegeHistoryRequestLicensee', {
                jurisdiction: issueStateAbbrev,
                licenseTypeAbbrev: this.privilegeLicenseTypeAbbrev
            });
        }
    }

    async populateData(): Promise<void> {
        if (this.isLoggedInAsStaff) {
            if (!this.licenseeRecord) {
                await this.fetchLicenseeData();
            }

            if (!this.isPrivilegeHistoryLoaded) {
                await this.fetchPrivilegeHistoryStaff();
            }
        } else if (
            this.isLoggedInAsLicensee
            && this.isPrivilegeLoaded
            && !this.isPrivilegeHistoryLoaded
        ) {
            await this.fetchPrivilegeHistoryLicensee();
        }
    }

    //
    // Watch
    //
    @Watch('isPrivilegeLoaded') async loadPrivilegeHistory() {
        if (this.isLoggedInAsLicensee
            && !this.isPrivilegeHistoryLoaded
            && this.isPrivilegeLoaded
        ) {
            await this.fetchPrivilegeHistoryLicensee();
        }
    }
}
