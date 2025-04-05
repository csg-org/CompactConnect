//
//  PublicPrivilegeDetail.ts
//  CompactConnect
//
//  Created by InspiringApps on 3/18/2025.
//

import { Component, Vue } from 'vue-facing-decorator';
import LoadingSpinner from '@components/LoadingSpinner/LoadingSpinner.vue';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import PrivilegeDetailBlock from '@components/PrivilegeDetailBlock/PrivilegeDetailBlock.vue';
import { License } from '@models/License/License.model';
import { Licensee } from '@models/Licensee/Licensee.model';

@Component({
    name: 'PublicPrivilegeDetail',
    components: {
        InputButton,
        PrivilegeDetailBlock,
        LoadingSpinner
    }
})
export default class PublicPrivilegeDetail extends Vue {
    //
    // Lifecycle
    //
    mounted() {
        if (!this.licenseeRecord) {
            this.fetchLicenseePublicData();
        }
    }

    //
    // Computed
    //
    get globalStore() {
        return this.$store.state;
    }

    get licenseStore(): any {
        return this.$store.state.license;
    }

    get isLoading(): boolean {
        return this.licenseStore?.isLoading || false;
    }

    get privilegeId(): string | null {
        return (this.$route.params.privilegeId as string || null);
    }

    get licenseeId(): string {
        return (this.$route.params.licenseeId as string || '');
    }

    get compact(): string {
        return this.$route.params.compact as string || '';
    }

    get licenseeRecord(): Licensee | null {
        const { licenseeId } = this;
        let storeRecord: Licensee | null = null;

        if (licenseeId && this.licenseStore.model) {
            storeRecord = this.$store.getters['license/licenseeById'](licenseeId);
        }

        return storeRecord;
    }

    get privilege(): License | null {
        let foundPrivilege: Licensee | null = null;

        if (this.licenseeRecord) {
            foundPrivilege = this.licenseeRecord.privileges?.find((privilege: License) =>
                (privilege.id === this.privilegeId)) || null;
        }

        return foundPrivilege;
    }

    get privilegeTitle(): string {
        return `${this.privilege?.licenseTypeAbbreviation() || ''} - ${this.privilege?.issueState?.name() || ''}`;
    }

    //
    // Methods
    //
    goBack() {
        this.$router.back();
    }

    async fetchLicenseePublicData(): Promise<void> {
        const { compact, licenseeId } = this;

        await this.$store.dispatch('license/getLicenseeRequest', {
            compact,
            licenseeId,
            isPublic: true,
        });
    }
}
