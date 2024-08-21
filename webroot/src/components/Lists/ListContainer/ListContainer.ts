//
//  ListContainer.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/27/2020.
//

import {
    Component,
    mixins,
    Prop,
    toNative
} from 'vue-facing-decorator';
import MixinListManipulation from '@/components/Lists/_mixins/ListManipulation.mixin';
import Pagination from '@components/Lists/Pagination/Pagination.vue';
import Sorting from '@components/Lists/Sorting/Sorting.vue';
import CompactToggle from '@components/Lists/CompactToggle/CompactToggle.vue';

@Component({
    name: 'ListContainer',
    components: {
        Pagination,
        Sorting,
        CompactToggle,
    },
})
class ListContainer extends mixins(MixinListManipulation) {
    @Prop({ required: true }) protected listData!: Array<any>; // Extending class should more specifically type
    @Prop({ required: true }) private pageChange!: (firstIndex: number, lastIndexExclusive: number) => any;
    @Prop({ required: true }) private sortChange!: (newSortOption: string, ascending: boolean) => any;
    @Prop({ default: 0 }) private listSize?: number;
    @Prop({ default: false }) private isLoading?: boolean;
    @Prop({ default: null }) private loadingError?: any;

    //
    // Computed
    //
    get listTotalSize() {
        let size = this.listSize;

        if (!size && this.listData) {
            size = this.listData.length;
        }

        return size;
    }

    get hasRecords() {
        return (this.listData && this.listData.length);
    }
}

export default toNative(ListContainer);

// export { ListContainer };
