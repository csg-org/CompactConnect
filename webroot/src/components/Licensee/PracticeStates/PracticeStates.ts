//
//  PracticeStates.ts
//  CompactConnect
//
//  Created by InspiringApps on 9/24/2026.
//

import {
    Component,
    Vue,
    Prop,
    toNative
} from 'vue-facing-decorator';
import LicenseActionsModal from '@components/LicenseActionsModal/LicenseActionsModal.vue';
import { Licensee } from '@models/Licensee/Licensee.model';
import { License, LicenseStatus } from '@models/License/License.model';

@Component({
    name: 'PracticeStates',
    components: {
        LicenseActionsModal,
    },
})
class PracticeStates extends Vue {
    @Prop({ required: true }) licensee!: Licensee;
    @Prop({ default: false }) isPublicSearch!: boolean;

    //
    // Computed
    //
    get licenseeLicenses(): Array<License> {
        return this.licensee?.licenses || [];
    }

    get licenseePrivileges(): Array<License> {
        return this.licensee?.privileges || [];
    }

    get licenseeAllCredentials(): Array<License> {
        return this.licenseeLicenses.concat(this.licenseePrivileges).sort(this.sortByIssueState);
    }

    //
    // Methods
    //
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

    getStatusDisplay(license: License): string {
        let statusDisplay = this.$t('licensing.statusOptions.inactive');

        if (license.status === LicenseStatus.ACTIVE) {
            statusDisplay = this.$t('licensing.statusOptions.active');
        }

        return statusDisplay;
    }

    getDisciplineContent(license: License): string {
        let disciplineContent = this.$t('licensing.noDiscipline');

        if (license.isEncumbered()) {
            disciplineContent = this.$t('licensing.encumbered');
        } else if (license.isUnderInvestigation()) {
            disciplineContent = this.$t('licensing.underInvestigationStatus');
        }

        return disciplineContent;
    }
}

export default toNative(PracticeStates);

// export default PracticeStates;
