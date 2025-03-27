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
        // const curStatus = false;

        this.events.forEach((event, i) => {
            console.log('event', event);

            let isStart = i === 1 ? true : false;
            let isEnd = false;

            if () {

            }

            preppedEvents.push(event);
        });

        return preppedEvents;
    }

    //
    // Methods
    //
}

export default toNative(PrivilegeHistory);

// export default PrivilegeHistory;
