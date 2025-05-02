//
//  LicenseeProof.ts
//  CompactConnect
//
//  Created by InspiringApps on 5/2/2025.
//

import { Component, Vue } from 'vue-facing-decorator';
import LicenseHomeIcon from '@components/Icons/LicenseHome/LicenseHome.vue';
import PrivilegesIcon from '@components/Icons/LicenseeUser/LicenseeUser.vue';
import { Compact } from '@models/Compact/Compact.model';
import { License } from '@models/License/License.model';
import { Licensee } from '@models/Licensee/Licensee.model';
import { State } from '@models/State/State.model';
import { LicenseeUser } from '@/models/LicenseeUser/LicenseeUser.model';

@Component({
    name: 'LicenseeProof',
    components: {
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

    get licensee(): Licensee {
        return this.user?.licensee || new Licensee();
    }

    get licenseeLicenses(): Array<License> {
        return this.licensee.licenses || [];
    }

    get licenseePrivileges(): Array<License> {
        return this.licensee.privileges || [];
    }

    get homeJurisdiction(): State | null {
        return this.licensee?.homeJurisdiction || null;
    }

    get userFullName(): string {
        return this.user?.getFullName() || '';
    }
}
