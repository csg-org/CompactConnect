//
//  EventNode.ts
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
    name: 'EventNode'
})
class EventNode extends Vue {
    // PROPS
    @Prop({ required: true }) event?: LicenseHistoryItem;

    //
    // Data
    //

    //
    // Lifecycle
    //

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

    //
    // Methods
    //
}

export default toNative(EventNode);

// export default EventNode;
