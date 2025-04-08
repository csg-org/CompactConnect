//
//  PrivilegeHistory.ts
//  CompactConnect
//
//  Created by InspiringApps on 3/26/2025.
//

import {
    Component,
    Vue,
    toNative,
    Prop
} from 'vue-facing-decorator';
import PrivilegeEventNode from '@components/PrivilegeEventNode/PrivilegeEventNode.vue';
import StatusTimeBlock from '@components/StatusTimeBlock/StatusTimeBlock.vue';
import { License, LicenseStatus } from '@models/License/License.model';
import { LicenseHistoryItem } from '@models/LicenseHistoryItem/LicenseHistoryItem.model';
import moment from 'moment';

export interface RichEvent {
    event: LicenseHistoryItem,
    isStartOfVisualBlock: boolean,
    isEndOfVisualBlock: boolean,
    isLastEvent: boolean,
    eventLengthBucket: string
}

@Component({
    name: 'PrivilegeHistory',
    components: {
        PrivilegeEventNode,
        StatusTimeBlock
    }
})
class PrivilegeHistory extends Vue {
    // PROPS
    @Prop({ required: true }) privilege!: License;

    //
    // Computed
    //
    get events(): Array<LicenseHistoryItem> {
        return this.privilege?.historyWithFabricatedEvents() || [];
    }

    get preppedEvents(): Array <RichEvent> {
        const preppedEvents = [] as Array <RichEvent>;

        this.events.forEach((event, i) => {
            let isStart = false;
            let isEnd = false;
            const isLastEvent = (i === this.events.length - 1);

            // used for styling the StatusTimeBlocks and distinguising between continuous blocks and new blocks
            // isStart will return true if the event is the first in the timeline or if the status
            // changed between this and the previous event
            if (i === 0) {
                isStart = true;
            } else if ((event.isActivatingEvent() && this.events[i - 1].isDeactivatingEvent())
            || (event.isDeactivatingEvent() && this.events[i - 1].isActivatingEvent())) {
                isStart = true;
            }

            // used for styling the StatusTimeBlocks and distinguising between continuous blocks and new blocks
            // isEnd will return false if the event is the last event in the timeline or if the status
            // changed between this and the next event
            if (isLastEvent) {
                isEnd = false;
            } else if ((event.isActivatingEvent() && this.events[i + 1].isDeactivatingEvent())
            || (event.isDeactivatingEvent() && this.events[i + 1].isActivatingEvent())) {
                isEnd = true;
            }

            // Determine length of time being represented by timeline block
            // Last block must be compared against present to determine length of time
            const nextEventDate = isLastEvent ? moment() : this.events[i + 1].dateOfUpdate;
            const eventGap = moment(nextEventDate).diff(event.dateOfUpdate, 'days');

            let eventLengthBucket = 'short';

            if (eventGap > 364) {
                eventLengthBucket = 'long';
            } else if (eventGap > 30) {
                eventLengthBucket = 'medium';
            }

            preppedEvents.push({
                event,
                isStartOfVisualBlock: isStart,
                isEndOfVisualBlock: isEnd,
                isLastEvent,
                eventLengthBucket,
            });
        });

        return preppedEvents;
    }

    get daysUntilExpiration(): number {
        return moment(this.privilege?.expireDate).diff(moment(), 'days');
    }

    get isExpirationUpcoming(): boolean {
        return this.daysUntilExpiration < 90;
    }

    get isActive(): boolean {
        return this.privilege?.status === LicenseStatus.ACTIVE;
    }

    get expirationText(): string {
        return `${this.$t('licensing.expiringIn')} ${this.daysUntilExpiration} ${this.$t('common.days')}`;
    }
}

export default toNative(PrivilegeHistory);

// export default PrivilegeHistory;
