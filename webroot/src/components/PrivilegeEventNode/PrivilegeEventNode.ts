//
//  PrivilegeEventNode.ts
//  CompactConnect
//
//  Created by InspiringApps on 3/21/2025.
//

import {
    Component,
    Vue,
    toNative,
    Prop
} from 'vue-facing-decorator';
import { LicenseHistoryItem } from '@models/LicenseHistoryItem/LicenseHistoryItem.model';

@Component({
    name: 'PrivilegeEventNode'
})
class PrivilegeEventNode extends Vue {
    // PROPS
    @Prop({ required: true }) event!: LicenseHistoryItem;
    @Prop({ default: 'short' }) eventLengthBucket?: string;

    //
    // Computed
    //
    get eventDate(): string {
        return this.event?.dateOfUpdateDisplay() || '';
    }

    get eventNameDisplay(): string {
        return this.event?.updateTypeDisplay() || '';
    }

    get isActivating() {
        return this.event?.isActivatingEvent();
    }

    get isDeactivating() {
        return this.event?.isDeactivatingEvent();
    }
}

export default toNative(PrivilegeEventNode);

// export default PrivilegeEventNode;
