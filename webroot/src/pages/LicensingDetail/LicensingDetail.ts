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
    get licenseStore(): any {
        return this.$store.state.license;
    }

    get licenseeId(): string {
        const routeId: string = this.$route.params.licenseeId as string || '';

        return routeId;
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
        const { licensee } = this;
        let nameDisplay = '';

        if (licensee) {
            nameDisplay = licensee.nameDisplay() || '';
        }

        return nameDisplay;
    }

    get licenseeLicenses(): Array<License> {
        const { licensee } = this;
        let licenses: Array<License> = [];

        if (licensee) {
            licenses = licensee.licenses || [];
        }

        return licenses;
    }

    //
    // Methods
    //
    async fetchLicenseeData(): Promise<void> {
        const { licenseeId } = this;

        await this.$store.dispatch('license/getLicenseeRequest', { licenseeId });
    }
}
