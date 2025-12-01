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
import PaginationLegacy from '@components/Lists/PaginationLegacy/PaginationLegacy.vue';
import Sorting from '@components/Lists/Sorting/Sorting.vue';
import CompactToggle from '@components/Lists/CompactToggle/CompactToggle.vue';

@Component({
    name: 'ListContainer',
    components: {
        PaginationLegacy,
        Sorting,
        CompactToggle,
    },
})
class ListContainer extends mixins(MixinListManipulation) {
    @Prop({ required: true }) protected listData!: Array<any>; // Extending class should more specifically type
    @Prop({ default: true }) private isLegacyPaging?: boolean;
    @Prop({ required: true }) private pageChange!: (firstIndex: number, lastIndexExclusive: number) => any;
    @Prop({ required: true }) private sortChange!: (newSortOption: string, ascending: boolean) => any;
    @Prop({ default: 0 }) private listSize?: number;
    @Prop({ default: false }) private isLoading?: boolean;
    @Prop({ default: null }) private loadingError?: any;
    @Prop({ default: '' }) private emptyListMessage?: string;

    //
    // Computed
    //
    get listTotalSize(): number {
        let size = this.listSize || 0;

        if (!size && this.listData) {
            size = this.listData.length;
        }

        return size;
    }

    get hasRecords(): boolean {
        return Boolean(this.listData && this.listData.length);
    }

    get loadingErrorDisplay(): string {
        let errorDisplay = this.$t('serverErrors.networkError');

        if (this.loadingError?.message) {
            errorDisplay = this.loadingError.message;
        }

        return errorDisplay;
    }

    get emptyMessage(): string {
        return this.emptyListMessage || this.$t('serverErrors.noRecords');
    }
}

export default toNative(ListContainer);

// export { ListContainer };
