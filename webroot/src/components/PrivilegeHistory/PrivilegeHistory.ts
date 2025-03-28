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
import EventNode from '@components/EventNode/EventNode.vue';
import StatusTimeBlock from '@components/StatusTimeBlock/StatusTimeBlock.vue';
import { License } from '@models/License/License.model';
import moment from 'moment';

@Component({
    name: 'PrivilegeHistory',
    components: {
        EventNode,
        StatusTimeBlock
    }
})
class PrivilegeHistory extends Vue {
    // PROPS
    @Prop({ required: true }) privilege?: License;

    //
    // Data
    //

    //
    // Lifecycle
    //

    //
    // Computed
    //
    get events(): any {
        return this.privilege?.history || [];
    }

    get preppedEvents(): any {
        const preppedEvents = [] as Array <any>;

        this.events.forEach((event, i) => {
            let isStart = false;
            let isEnd = false;

            if (i === 0) {
                isStart = true;
            } else if ((event.isActivatingEvent() && this.events[i - 1].isDeactivatingEvent())
            || (event.isDeactivatingEvent() && this.events[i - 1].isActivatingEvent())) {
                isStart = true;
            }

            if (i === this.events.length - 1) {
                isEnd = false;
            } else if ((event.isActivatingEvent() && this.events[i + 1].isDeactivatingEvent())
            || (event.isDeactivatingEvent() && this.events[i + 1].isActivatingEvent())) {
                isEnd = true;
            }

            preppedEvents.push({ event, isEnd, isStart });
        });

        return preppedEvents;
    }

    get daysUntilExpiration(): number {
        return moment(this.privilege?.expireDate).diff(moment(), 'days');
    }

    get isExpirationUpcoming(): boolean {
        return this.daysUntilExpiration < 90;
    }

    get isExpired(): boolean {
        return this.privilege?.isExpired() || false;
    }

    get expText(): string {
        return `${this.$t('licensing.expiringIn')} ${this.daysUntilExpiration} ${this.$t('common.days')}`;
    }

    //
    // Methods
    //
}

export default toNative(PrivilegeHistory);

// export default PrivilegeHistory;
