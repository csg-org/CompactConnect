//
//  LicenseePrivilegeList.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/3/2024.
//

import { License } from '@models/License/License.model';
import {
    Component,
    Vue,
    toNative,
    Prop
} from 'vue-facing-decorator';

@Component({
    name: 'LicenseePrivilegeList',
})
class LicenseePrivilegeList extends Vue {
    @Prop({ required: true }) privilegeList!: Array<License>;
    //
    // Computed
    //
    get privStateList(): Array <string> {
        return this.privilegeList.map((priv) => (priv.issueState?.name() || 'State missing'));
    }

    get privExpirationList(): Array <string> {
        return this.privilegeList.map((priv) => (priv.expireDate) || 'Expiry missing');
    }
}

export default toNative(LicenseePrivilegeList);

// export default LicenseePrivilegeList;
