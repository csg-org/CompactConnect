//
//  Pagination.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/21/2020.
//

import {
    Component,
    mixins,
    Prop,
    Watch
} from 'vue-facing-decorator';
import { reactive, computed, nextTick } from 'vue';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import { DEFAULT_PAGE, DEFAULT_PAGE_SIZE, PageChangeConfig } from '@store/pagination/pagination.state';
import InputSelect from '@components/Forms/InputSelect/InputSelect.vue';
import LeftCaretIcon from '@components/Icons/LeftCaretIcon/LeftCaretIcon.vue';
import RightCaretIcon from '@components/Icons/RightCaretIcon/RightCaretIcon.vue';
import { FormInput } from '@/models/FormInput/FormInput.model';

// const MAX_PAGES_VISIBLE = 7;

const createPaginationItem = (pageNum, currentPage) => ({
    id: pageNum,
    clickable: pageNum > 0 && pageNum !== currentPage,
    displayValue: (pageNum > 0) ? pageNum : '...',
    selected: pageNum > 0 && pageNum === currentPage
});

@Component({
    name: 'Pagination',
    components: {
        InputSelect,
        LeftCaretIcon,
        RightCaretIcon
    },
})
export default class Pagination extends mixins(MixinForm) {
    @Prop({ required: true }) private paginationId!: string; // The pagination store id of the list instance
    @Prop({ required: true }) private listSize!: number; // The total number of list items (not all server APIs provide this)
    @Prop({ required: true }) pagingPrevKey!: string | null; // The server API paging key for the previous page results
    @Prop({ required: true }) pagingNextKey!: string | null; // The server API paging key for the next page results
    @Prop() private pageSizeConfig?: Array<{ value: number; name: string; isDefault?: boolean }>; // Optional custom config of the page size selector (options for how many items are shown per page)
    @Prop() private ariaLabel?: string; // Optional aria label for the pagination container element
    @Prop({ required: true }) private pageChange!: (config: PageChangeConfig) => any; // A callback method that will be called on page-change

    //
    // Data
    //
    paginationStore: any = {};
    ellipsis = (key) => createPaginationItem(key, -1);
    defaultPageSizeOptions = [
        { value: 25, name: '25', isDefault: true },
    ];

    defaultPageSize = DEFAULT_PAGE_SIZE;

    //
    // Lifecycle
    //
    created() {
        this.paginationStore = this.$store.state.pagination;
        this.initFormInputs();

        const {
            paginationId,
            pageSizeConfig,
            paginationStore,
            $store
        } = this;
        const pagination = paginationStore.paginationMap[paginationId];

        if (pageSizeConfig) {
            let defaultPageSizeOption = pageSizeConfig.find(({ isDefault }) => (isDefault));

            if (!defaultPageSizeOption) {
                defaultPageSizeOption = this.defaultPageSizeOptions.find(({ isDefault }) => (isDefault));
            }

            this.defaultPageSize = (defaultPageSizeOption)
                ? defaultPageSizeOption.value
                : pageSizeConfig[0].value;

            $store.dispatch('pagination/updatePaginationSize', { paginationId, newSize: this.defaultPageSize });
        }

        if (!pagination) {
            $store.dispatch('pagination/updatePaginationPage', { paginationId, newPage: 1 });
        }
    }

    mounted() {
        const { currentPage, pageSize, pageChange } = this;
        const firstIndex = (currentPage - 1) * pageSize;
        const lastIndex = currentPage * pageSize;

        pageChange({ firstIndex, lastIndexExclusive: lastIndex, prevNext: 0 });
    }

    //
    // Computed
    //
    get pageSizeOptions(): Array<any> {
        const { pageSizeConfig, defaultPageSizeOptions } = this;
        let options = pageSizeConfig;

        if (!options || !options.length) {
            options = defaultPageSizeOptions;
        }

        return options;
    }

    get currentPage(): number {
        const pagination = this.paginationStore.paginationMap[this.paginationId];

        return (pagination) ? pagination.page : DEFAULT_PAGE;
    }

    get pageSize(): number {
        const pagination = this.paginationStore.paginationMap[this.paginationId];

        return (pagination) ? pagination.size : this.defaultPageSize;
    }

    get pageCount(): number {
        return Math.ceil(this.listSize / this.pageSize);
    }

    get isFirstPage(): boolean {
        return this.currentPage === 1;
    }

    get isLastPage(): boolean {
        return this.currentPage === this.pageCount;
    }

    get pages(): Array<object> {
        const { currentPage, ellipsis } = this;
        const pageItems: Array<any> = [];

        if (currentPage === 1) {
            pageItems.push(createPaginationItem(1, currentPage));
        } else if (currentPage === 2) {
            pageItems.push(createPaginationItem(1, currentPage));
            pageItems.push(createPaginationItem(2, currentPage));
        } else if (currentPage > 2) {
            pageItems.push(createPaginationItem(1, currentPage));
            pageItems.push(ellipsis(0));
            pageItems.push(createPaginationItem(currentPage, currentPage));
        }

        return pageItems;
    }

    //
    // Watchers
    //
    @Watch('$props.paginationId') handleUpdatePagingId() {
        this.resetPaging();
    }

    @Watch('$props.listSize') handleUpdateListSize() {
        this.resetPaging();
    }

    @Watch('$props.pageSizeConfig', { deep: true }) handleUpdatePageSizeConfig() {
        this.resetPaging();
    }

    //
    // Methods
    //
    initFormInputs(): void {
        this.formData = reactive({
            pageSizeOptions: new FormInput({
                id: 'page-size',
                name: 'page-size',
                label: computed(() => this.$t('paging.pageSize')),
                value: this.pageSize,
                valueOptions: this.pageSizeOptions.map((option) => ({
                    value: option.value,
                    name: option.name,
                })),
            }),
        });
    }

    setPage(newPage: number, increment?: number) {
        const { pageSize } = this;
        const zeroBasedIndex = (newPage - 1) * pageSize;

        if (this.currentPage !== newPage) {
            this.$store.dispatch('pagination/updatePaginationPage', { paginationId: this.paginationId, newPage });
            this.pageChange({
                firstIndex: zeroBasedIndex,
                lastIndexExclusive: zeroBasedIndex + pageSize,
                prevNext: increment,
            });
        }
    }

    setSize(formInput: FormInput) {
        const newSize = Number(formInput.value);
        const {
            listSize,
            currentPage,
            paginationId,
            pageChange,
            $store
        } = this;
        let newFirstIndex = (currentPage - 1) * newSize;

        if (newFirstIndex >= listSize) {
            const newPageCount = Math.ceil(listSize / newSize);

            newFirstIndex = (newPageCount - 1) * newSize;
            $store.dispatch('pagination/updatePaginationPage', { paginationId, newPage: newPageCount });
        }

        $store.dispatch('pagination/updatePaginationSize', { paginationId, newSize });
        pageChange({
            firstIndex: newFirstIndex,
            lastIndexExclusive: newFirstIndex + newSize,
            prevNext: 0,
        });
    }

    resetPaging(): void {
        // If any variables that affect paging have changed (page size, etc.) then we need to reset to the first page with the new variables.
        nextTick(() => {
            const { pageSize, pageChange, paginationId } = this;

            this.$store.dispatch('pagination/updatePaginationPage', { paginationId, newPage: 1 });
            pageChange({
                firstIndex: 0,
                lastIndexExclusive: pageSize,
                prevNext: 0,
            });
        });
    }
}
