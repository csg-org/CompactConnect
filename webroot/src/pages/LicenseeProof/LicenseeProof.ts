//
//  LicenseeProof.ts
//  CompactConnect
//
//  Created by InspiringApps on 5/2/2025.
//

import { Component, Vue } from 'vue-facing-decorator';
import LicenseHomeIcon from '@components/Icons/LicenseHome/LicenseHome.vue';
import PrivilegesIcon from '@components/Icons/LicenseeUser/LicenseeUser.vue';
import UserIcon from '@components/Icons/User/User.vue';
import { Compact } from '@models/Compact/Compact.model';
import { License, LicenseStatus } from '@models/License/License.model';
import { Licensee } from '@models/Licensee/Licensee.model';
import { State } from '@models/State/State.model';
import { LicenseeUser } from '@/models/LicenseeUser/LicenseeUser.model';
import moment from 'moment';

@Component({
    name: 'LicenseeProof',
    components: {
        UserIcon,
        LicenseHomeIcon,
        PrivilegesIcon,
    }
})
export default class LicenseeProof extends Vue {
    //
    // Computed
    //
    get userStore(): any {
        return this.$store.state.user;
    }

    get user(): LicenseeUser | null {
        return this.userStore.model;
    }

    get currentCompact(): Compact | null {
        return this.userStore?.currentCompact || null;
    }

    get currentCompactType(): string | null {
        return this.currentCompact?.type || null;
    }

    get currentDateDisplay(): string {
        return moment().format('MMM D, YYYY');
    }

    get licensee(): Licensee {
        return this.user?.licensee || new Licensee();
    }

    get homeJurisdiction(): State | null {
        return this.licensee?.homeJurisdiction || null;
    }

    get homeJurisdictionName(): string {
        return this.homeJurisdiction?.name() || '';
    }

    get userFullName(): string {
        return this.user?.getFullName() || '';
    }

    get licenseeLicenses(): Array<License> {
        return this.licensee.activeHomeJurisdictionLicenses() || [];
    }

    get licenseePrivileges(): Array<License> {
        return this.licensee.privileges?.filter((privilege: License) =>
            privilege.status === LicenseStatus.ACTIVE)
            .sort((a: License, b: License) => {
                const dateA = moment(a.issueDate);
                const dateB = moment(b.issueDate);

                return dateB.valueOf() - dateA.valueOf(); // Most recent first
            }) || [];
    }

    //
    // Methods
    //
    printHandler(): void {
        window.print();
    }
}
