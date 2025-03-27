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
import StatusTimeBlock from '@components/StatusTimeBlock/StatusTimeBlock.vue';
import { LicenseHistoryItem } from '@models/LicenseHistoryItem/LicenseHistoryItem.model';

@Component({
    name: 'EventNode',
    components: {
        StatusTimeBlock
    }
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

    get eventType(): string {
        return this.event?.updateType || '';
    }

    //
    // Methods
    //
}

export default toNative(EventNode);

// export default EventNode;
