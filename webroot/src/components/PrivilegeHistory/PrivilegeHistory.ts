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
import { License, LicenseStatus } from '@models/License/License.model';
import { LicenseHistoryItem } from '@models/LicenseHistoryItem/LicenseHistoryItem.model';
import moment from 'moment';

export interface RichEvent {
    event: LicenseHistoryItem,
    isLastEvent: boolean,
    eventLengthBucket: string
}

@Component({
    name: 'PrivilegeHistory',
    components: {
        PrivilegeEventNode
    }
})
class PrivilegeHistory extends Vue {
    // PROPS
    @Prop({ required: true }) privilege!: License;

    //
    // Computed
    //
    get events(): Array<LicenseHistoryItem> {
        return this.privilege?.history || [];
    }

    get preppedEvents(): Array <RichEvent> {
        const preppedEvents = [] as Array <RichEvent>;

        this.events.forEach((event, i) => {
            const isLastEvent = (i === this.events.length - 1);

            // Determine length of time being represented by timeline block
            // Last block must be compared against present to determine length of time
            const nextEventDate = isLastEvent ? moment() : this.events[i + 1].effectiveDate;
            const eventGap = moment(nextEventDate).diff(event.effectiveDate, 'days');

            let eventLengthBucket = 'short';

            if (eventGap > 364) {
                eventLengthBucket = 'long';
            } else if (eventGap > 30) {
                eventLengthBucket = 'medium';
            }

            preppedEvents.push({
                event,
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
