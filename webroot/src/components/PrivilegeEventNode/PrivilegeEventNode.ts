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
        return this.event?.effectiveDateDisplay() || '';
    }

    get eventNameDisplay(): string {
        return this.event?.updateTypeDisplay() || '';
    }

    get isActivating(): boolean {
        return this.event?.isActivatingEvent() || false;
    }

    get isDeactivating(): boolean {
        return this.event?.isDeactivatingEvent() || false;
    }

    get detailDisplay(): string {
        return this.event?.noteDisplay() || '';
    }

    get updateType(): string {
        return this.event?.updateType || '';
    }

    get uploadOnDisplay(): string {
        return this.updateType === 'encumbrance' || this.updateType === 'lifting_encumbrance' ? `${this.$t('licensing.uploadedOn')}: ${this.event?.createDateDisplay()}` : '';
    }
}

export default toNative(PrivilegeEventNode);

// export default PrivilegeEventNode;
