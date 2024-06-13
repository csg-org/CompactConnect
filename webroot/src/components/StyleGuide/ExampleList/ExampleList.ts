//
//  ExampleList.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/30/2021.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

import {
    Component,
    Prop,
    Vue,
    toNative
} from 'vue-facing-decorator';
import Section from '@components/Section/Section.vue';
import ListContainer from '@components/Lists/ListContainer/ListContainer.vue';
import ExampleRow from '@components/StyleGuide/ExampleRow/ExampleRow.vue';
import { SortDirection } from '@store/sorting/sorting.state';

@Component({
    name: 'ExampleList',
    components: {
        Section,
        ListContainer,
        ExampleRow,
    }
})
class ExampleList extends Vue {
    @Prop({ required: true }) protected listId!: string;

    //
    // Lifecycle
    //
    async created() {
        await this.setDefaultSort();
        await this.fetchListData();
    }

    //
    // Computed
    //
    get sortingStore() {
        return this.$store.state.sorting;
    }

    get paginationStore() {
        return this.$store.state.pagination;
    }

    get styleguideStore() {
        return this.$store.state.styleguide;
    }

    get sortOptions() {
        const options = [
            { value: 'name', name: this.$t('styleGuide.list.name') },
            { value: 'size', name: this.$t('styleGuide.list.size') },
            { value: 'isEvil', name: this.$t('styleGuide.list.isEvil') },
        ];

        return options;
    }

    get headerRecord() {
        const record = {
            name: this.$t('styleGuide.list.name'),
            size: this.$t('styleGuide.list.size'),
            isEvil: this.$t('styleGuide.list.isEvil'),
        };

        return record;
    }

    //
    // Methods
    //
    async setDefaultSort() {
        const { listId } = this;
        const defaultSortOption = this.sortOptions[0];
        const { option, direction } = this.sortingStore.sortingMap[listId] || {};

        if (!option) {
            await this.$store.dispatch('sorting/updateSortOption', {
                sortingId: listId,
                newOption: defaultSortOption.value,
            });
        }

        if (!direction) {
            await this.$store.dispatch('sorting/updateSortDirection', {
                sortingId: listId,
                newDirection: SortDirection.asc,
            });
        }
    }

    async fetchListData() {
        const sorting = this.sortingStore.sortingMap[this.listId];
        const { option, direction } = sorting || {};
        const pagination = this.paginationStore.paginationMap[this.listId];
        const { page, size } = pagination || {};
        const requestConfig: any = {};

        if (option) {
            requestConfig.sortBy = option;
            requestConfig.sortDir = direction;
        }

        await this.$store.dispatch('styleguide/getPetsCountRequest', requestConfig);
        await this.$store.dispatch('styleguide/getPetsRequest', {
            ...requestConfig,
            pageNum: page,
            pageSize: size,
        });
    }

    async sortingChange() {
        // console.log('sort changed'); // @DEBUG
        await this.fetchListData();
    }

    async paginationChange() {
        // console.log('pagination changed'); // @DEBUG
        await this.fetchListData();
    }
}

export default toNative(ExampleList);

// export { ExampleList };
