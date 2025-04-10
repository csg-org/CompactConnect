//
//  StatusTimeBlock.ts
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
    name: 'StatusTimeBlock',
})
class StatusTimeBlock extends Vue {
    // PROPS
    @Prop({ required: true }) isStartOfVisualBlock!: boolean;
    @Prop({ required: true }) isEndOfVisualBlock!: boolean;
    @Prop({ required: true }) isLastEvent!: boolean;
    @Prop({ required: true }) event!: LicenseHistoryItem;

    //
    // Computed
    //
    get isActivating(): boolean {
        return this.event?.isActivatingEvent() || false;
    }

    get isDeactivating(): boolean {
        return this.event?.isDeactivatingEvent() || false;
    }

    get status(): string {
        let status = '';

        if (this.isActivating) {
            status = this.$t('licensing.statusOptions.active');
        } else if (this.isDeactivating) {
            status = this.$t('licensing.statusOptions.inactive');
        }

        return status;
    }
}

export default toNative(StatusTimeBlock);

// export default StatusTimeBlock;
