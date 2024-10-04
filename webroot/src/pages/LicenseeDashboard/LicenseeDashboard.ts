//
//  LicenseeDashboard.ts
//  CompactConnect
//
//  Created by InspiringApps on 9/23/2024.
//

import { Component, Vue } from 'vue-facing-decorator';
import AdverseActionList from '@/components/AdverseActionList/AdverseActionList.vue';
import HomeStateBlock from '@/components/HomeStateBlock/HomeStateBlock.vue';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import LicenseePrivilegeList from '@/components/LicenseePrivilegeList/LicenseePrivilegeList.vue';
import { User } from '@models/User/User.model';

@Component({
    name: 'LicenseeDashboard',
    components: {
        AdverseActionList,
        HomeStateBlock,
        InputButton,
        LicenseePrivilegeList
    }
})
export default class LicenseeDashboard extends Vue {
    //
    // Computed
    //
    get userStore() {
        return this.$store.state.user;
    }

    get user(): User | null {
        return this.userStore.model;
    }

    get userFullName() {
        let name = '';

        if (this.user) {
            name = this.user.getFullName();
        }

        return name;
    }

    get homeStateList() {
        return ['', ''];
    }
}
