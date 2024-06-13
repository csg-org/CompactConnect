//
//  ListManipulation.mixin.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/21/2020.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

import { Component, mixins, Prop } from 'vue-facing-decorator';
import Pagination from './Pagination.mixin';
import Sorting from './Sorting.mixin';
import CompactToggle from './CompactToggle.mixin';

@Component({
    name: 'MixinListManipulation',
})
class MixinListManipulation extends mixins(Pagination, Sorting, CompactToggle) {
    @Prop({ required: true }) protected listData!: Array<any>; // Extending class should more specifically type

    //
    // Computed
    //
    get currentRecords() {
        const {
            firstIndex,
            lastIndex,
            sortedRecords,
            isServerPaging
        } = this;
        let records: Array<any> = [];

        if (isServerPaging) {
            records = this.listData.filter((record) => record.serverPage === this.currentPage);
        } else if (sortedRecords && sortedRecords.length) {
            if (firstIndex >= 0 && lastIndex >= 0) {
                records = sortedRecords.slice(firstIndex, lastIndex);
            }
        }

        return records;
    }
}

// export default toNative(MixinListManipulation);

export default MixinListManipulation;
