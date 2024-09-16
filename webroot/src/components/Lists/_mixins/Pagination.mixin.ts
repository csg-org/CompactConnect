//
//  Pagination.mixin.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/21/2020.
//

import {
    Component,
    Vue,
    Prop
} from 'vue-facing-decorator';
import { paginationTemplate, PageChangeConfig } from '@store/pagination/pagination.state';

@Component({
    name: 'MixinPagination',
})
class MixinPagination extends Vue {
    @Prop({ required: true }) protected listData!: Array<any>; // Extending class should more specifically type
    @Prop({ required: true }) protected listId!: string;
    @Prop({ default: false }) protected excludeBottomPagination?: boolean;
    @Prop({ default: false }) protected excludeTopPagination?: boolean;
    @Prop({ default: false }) protected isServerPaging?: boolean;
    @Prop({ default: null }) protected pagingPrevKey?: string | null;
    @Prop({ default: null }) protected pagingNextKey?: string | null;
    @Prop({ default: [] }) protected pageSizeConfig?: Array<any>;

    //
    // Data
    //
    paginationStore: any = {};
    firstIndex = -1;
    lastIndex = -1;

    //
    // Lifecycle
    //
    created() {
        this.paginationStore = this.$store.state.pagination;
    }

    mounted() {
        const {
            excludeTopPagination,
            excludeBottomPagination,
            pageSizeConfig,
            paginationChange
        } = this;

        // If all pagination is excluded then trigger set the first / last indexes manually
        if (excludeTopPagination && excludeBottomPagination) {
            let pageSize = 999;

            if (pageSizeConfig && pageSizeConfig.length) {
                const defaultPageSizeOption = pageSizeConfig.find(({ isDefault }) => (isDefault));

                pageSize = (defaultPageSizeOption)
                    ? defaultPageSizeOption.value
                    : pageSizeConfig[0].value;
            }

            paginationChange({ firstIndex: 0, lastIndexExclusive: pageSize, prevNext: 0 });
        }
    }

    //
    // Computed
    //
    get currentRecords(): Array<any> {
        const { firstIndex, lastIndex, listData } = this;
        let records: Array<any> = [];

        if (listData && listData.length) {
            if (this.isServerPaging) {
                records = listData.filter((record) => record.serverPage === this.currentPage);
            } else if (firstIndex >= 0 && lastIndex >= 0) {
                records = listData.slice(firstIndex, lastIndex);
            }
        }

        return records;
    }

    get pagination() {
        return this.paginationStore.paginationMap[this.listId] || paginationTemplate;
    }

    get currentPageSize() {
        return this.pagination.size;
    }

    get currentPage() {
        return this.pagination.page;
    }

    //
    // Methods
    //
    // Match pageChange() @Prop signature from /components/Lists/Pagination/Pagination.ts
    async paginationChange({ firstIndex, lastIndexExclusive }: PageChangeConfig) {
        this.firstIndex = firstIndex;
        this.lastIndex = lastIndexExclusive;
    }
}

// export default toNative(MixinPagination);

export default MixinPagination;
