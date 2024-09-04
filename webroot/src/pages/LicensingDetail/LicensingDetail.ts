//
//  LicensingDetail.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/1/2024.
//

import { Component, Vue } from 'vue-facing-decorator';
import { Licensee } from '@models/Licensee/Licensee.model';
import { License } from '@models/License/License.model';

@Component({
    name: 'LicensingDetail',
    components: {}
})
export default class LicensingDetail extends Vue {
    //
    // Data
    //

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
        return this.licensee?.licenseStatesDisplay() || '';
    }

    get licenseePrivilegeStatesDisplay(): string {
        return this.licensee?.privilegeStatesAllDisplay() || '';
    }

    get licenseeLicenses(): Array<License> {
        return this.licensee?.licenses || [];
    }

    //
    // Methods
    //
    async fetchLicenseeData(): Promise<void> {
        const { licenseeId } = this;

        await this.$store.dispatch('license/getLicenseeRequest', { compact: this.compact, licenseeId });
    }
}
