//
//  Pagination.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/21/2020.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

import {
    Component,
    mixins,
    Prop,
    Watch
} from 'vue-facing-decorator';
import { reactive, computed, nextTick } from 'vue';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import { DEFAULT_PAGE, DEFAULT_PAGE_SIZE } from '@store/pagination/pagination.state';
import InputSelect from '@components/Forms/InputSelect/InputSelect.vue';
import LeftCaretIcon from '@components/Icons/LeftCaretIcon/LeftCaretIcon.vue';
import RightCaretIcon from '@components/Icons/RightCaretIcon/RightCaretIcon.vue';
import { FormInput } from '@/models/FormInput/FormInput.model';

const MAX_PAGES_VISIBLE = 7;

const createPaginationItem = (pageNum, currentPage) => ({
    id: pageNum,
    clickable: pageNum > 0,
    displayValue: (pageNum > 0) ? pageNum : '...',
    selected: pageNum === currentPage
});

@Component({
    name: 'Pagination',
    components: {
        InputSelect,
        LeftCaretIcon,
        RightCaretIcon
    }
})
export default class Pagination extends mixins(MixinForm) {
    @Prop({ required: true }) private pageChange!: (firstIndex: number, lastIndexExclusive: number) => any;
    @Prop({ required: true }) private listSize!: number;
    @Prop({ required: true }) private paginationId!: string;
    @Prop() private pageSizeConfig?: Array<{ value: number; name: string; isDefault?: boolean }>;
    @Prop() private ariaLabel?: string;

    //
    // Data
    //
    paginationStore: any = {};
    ellipsis = (key) => createPaginationItem(key, -1);
    defaultPageSizeOptions = [
        { value: 5, name: '5', isDefault: true },
        { value: 10, name: '10', isDefault: false },
        { value: 20, name: '20', isDefault: false },
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

        pageChange(firstIndex, lastIndex);
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

    get pageSize() {
        const pagination = this.paginationStore.paginationMap[this.paginationId];

        return (pagination) ? pagination.size : this.defaultPageSize;
    }

    get pageCount() {
        return Math.ceil(this.listSize / this.pageSize);
    }

    get isFirstPage() {
        return this.currentPage === 1;
    }

    get isLastPage() {
        return this.currentPage === this.pageCount;
    }

    get pages() {
        const { currentPage, pageCount, ellipsis } = this;

        const visiblePagesCount = Math.min(MAX_PAGES_VISIBLE, pageCount) || 1;
        const visiblePagesThreshold = (visiblePagesCount - 1) / 2;
        const tempArray = Array(visiblePagesCount - 1);
        const paginationDisplaysArray = [...tempArray.keys()].map((i) => i + 1);
        const firstPage = () => createPaginationItem(1, currentPage);
        const lastPage = () => createPaginationItem(pageCount, currentPage);
        let pageItems;

        if (pageCount <= MAX_PAGES_VISIBLE) {
            pageItems = paginationDisplaysArray.map((index) => {
                const item = createPaginationItem(index, currentPage);

                return item;
            });
            pageItems.push(lastPage());
        } else if (currentPage <= visiblePagesThreshold) {
            pageItems = paginationDisplaysArray.map((index) => {
                const item = createPaginationItem(index, currentPage);

                return item;
            });
            pageItems[pageItems.length - 1] = ellipsis(0);
            pageItems.push(lastPage());
        } else if (currentPage > pageCount - visiblePagesThreshold) {
            pageItems = paginationDisplaysArray.map((paginationDisplay, index) => {
                const item = createPaginationItem(pageCount - index, currentPage);

                return item;
            });
            pageItems.reverse();
            pageItems[0] = ellipsis(0);
            pageItems.unshift(firstPage());
        } else {
            pageItems = [];
            pageItems.push(firstPage());
            pageItems.push(ellipsis(0));
            pageItems.push(createPaginationItem(currentPage - 1, currentPage));
            pageItems.push(createPaginationItem(currentPage, currentPage));
            pageItems.push(createPaginationItem(currentPage + 1, currentPage));
            pageItems.push(ellipsis(-1));
            pageItems.push(lastPage());
        }

        return pageItems;
    }

    //
    // Watchers
    //
    @Watch('$props', { deep: true }) calculateNewIndices() {
        nextTick(() => {
            const {
                pageSize, pageChange, $store, paginationId
            } = this;
            const newFirstIndex = 1 - 1;

            $store.dispatch('pagination/updatePaginationPage', { paginationId, newPage: 1 });
            pageChange(newFirstIndex, newFirstIndex + pageSize);
        });
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

    setPage(newPage) {
        const { pageSize } = this;
        const zeroBasedIndex = (newPage - 1) * pageSize;

        if (this.currentPage !== newPage) {
            this.$store.dispatch('pagination/updatePaginationPage', { paginationId: this.paginationId, newPage });
            this.pageChange(zeroBasedIndex, zeroBasedIndex + pageSize);
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
        pageChange(newFirstIndex, newFirstIndex + newSize);
    }
}
