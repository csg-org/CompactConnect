//
//  LicenseeDashboard.ts
//  CompactConnect
//
//  Created by InspiringApps on 9/23/2024.
//

import { Component, Vue } from 'vue-facing-decorator';
import AdverseActionList from '@/components/AdverseActionList/AdverseActionList.vue';
import HomeStateBlock from '@/components/HomeStateBlock/HomeStateBlock.vue';
import LicenseCard from '@/components/LicenseCard/LicenseCard.vue';
import PrivilegeCard from '@/components/PrivilegeCard/PrivilegeCard.vue';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import LicenseePrivilegeList from '@/components/LicenseePrivilegeList/LicenseePrivilegeList.vue';
import { License } from '@models/License/License.model';
import { Licensee } from '@models/Licensee/Licensee.model';
import { State } from '@models/State/State.model';
import { User } from '@models/User/User.model';

@Component({
    name: 'LicenseeDashboard',
    components: {
        AdverseActionList,
        HomeStateBlock,
        LicenseCard,
        PrivilegeCard,
        InputButton,
        LicenseePrivilegeList
    }
})
export default class LicenseeDashboard extends Vue {
    //
    // Computed
    //
    get userStore(): any {
        return this.$store.state.user;
    }

    get user(): User | null {
        return this.userStore.model;
    }

    get licensee(): Licensee | null {
        return this.user?.licensee || null;
    }

    get userFullName(): string {
        let name = '';

        if (this.user) {
            name = this.user.getFullName();
        }

        return name;
    }

    get homeStateList(): Array<State> {
        return this.licensee?.licenseStates || [];
    }

    get privilegeList(): Array<License> {
        return this.licensee?.privileges || [];
    }

    get licenseList(): Array<License> {
        return this.licensee?.licenses || [];
    }

    get obtainPrivButtonLabel():string {
        return '+ Obtain Privileges';
    }

    get privilegeTitle():string {
        return this.$t('licensing.privileges');
    }

    //
    // Methods
    //
    startPrivPurchaseFlow() {
        console.log('Starting Privilege Purchase Flow!');
    }
}
