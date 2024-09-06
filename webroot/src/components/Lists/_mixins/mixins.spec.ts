//
//  mixins.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/21/2020.
//

import { mountShallow } from '@tests/helpers/setup';
import CompactToggleMixin from '@components/Lists/_mixins/CompactToggle.mixin';
import ListManipulationMixin from '@components/Lists/_mixins/ListManipulation.mixin';
import PaginationMixin from '@components/Lists/_mixins/Pagination.mixin';
import SortingMixin from '@components/Lists/_mixins/Sorting.mixin';

const chaiMatchPattern = require('chai-match-pattern');
const chai = require('chai').use(chaiMatchPattern);

const { expect } = chai;

describe('CompactToggle mixin', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(CompactToggleMixin);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(CompactToggleMixin).exists()).to.equal(true);
    });
    it('should toggle the compact setting', async () => {
        const wrapper = await mountShallow(CompactToggleMixin);
        const component = wrapper.vm;

        expect(component.isCompact).to.equal(false);

        component.compactToggle(true);

        expect(component.isCompact).to.equal(true);
    });
});
describe('ListManipulation mixin', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(ListManipulationMixin);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(ListManipulationMixin).exists()).to.equal(true);
    });
    it('should have current page records from server', async () => {
        const wrapper = await mountShallow(ListManipulationMixin, {
            props: {
                listData: [],
                isServerPaging: true,
            },
        });
        const component = wrapper.vm;

        expect(component.currentRecords).to.matchPattern([]);
    });
    it('should have current page records from local data', async () => {
        const wrapper = await mountShallow(ListManipulationMixin, {
            props: {
                listData: [{ id: 1 }],
                isServerPaging: false,
                sortOptions: [{ value: 'id', name: 'id', sortingMethod: () => 1 }],
            },
        });
        const component = wrapper.vm;

        component.paginationChange({ firstIndex: 1, lastIndexExclusive: 1, prevNext: 0 });

        expect(component.currentRecords).to.matchPattern([]);
    });
});
describe('Pagination mixin', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(PaginationMixin);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(PaginationMixin).exists()).to.equal(true);
    });
    it('should have current page records from server', async () => {
        const wrapper = await mountShallow(PaginationMixin, {
            props: {
                listData: [{ id: 1 }],
                isServerPaging: true,
            },
        });
        const component = wrapper.vm;

        expect(component.currentRecords).to.matchPattern([]);
    });
    it('should have current page records from local data', async () => {
        const wrapper = await mountShallow(PaginationMixin, {
            props: {
                listData: [{ id: 1 }],
                isServerPaging: false,
            },
        });
        const component = wrapper.vm;

        component.paginationChange({ firstIndex: 1, lastIndexExclusive: 1, prevNext: 0 });

        expect(component.currentRecords).to.matchPattern([]);
    });
    it('should get current page size default value', async () => {
        const wrapper = await mountShallow(PaginationMixin);
        const component = wrapper.vm;

        expect(component.currentPageSize).to.equal(25);
    });
    it('should get current page size selected value', async () => {
        const wrapper = await mountShallow(PaginationMixin, {
            props: {
                listId: '1',
            },
        });
        const component = wrapper.vm;

        await component.$store.dispatch('pagination/updatePaginationSize', {
            paginationId: '1',
            newSize: 200,
        });

        expect(component.currentPageSize).to.equal(200);
    });
    it('should handle when pagination UI is excluded', async () => {
        const wrapper = await mountShallow(PaginationMixin, {
            props: {
                listData: [{ id: 1 }],
                isServerPaging: false,
                excludeTopPagination: true,
                excludeBottomPagination: true,
                pageSizeConfig: [{ value: 1 }],
            },
        });
        const component = wrapper.vm;

        expect(component.firstIndex).to.equal(0);
        expect(component.lastIndex).to.equal(1);
    });
});
describe('Sorting mixin', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(SortingMixin);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(SortingMixin).exists()).to.equal(true);
    });
    it('should update the sorting selections', async () => {
        const wrapper = await mountShallow(SortingMixin);
        const component = wrapper.vm;

        component.sortingChange('id', false);

        expect(component.selectedSort).to.equal('id');
        expect(component.isAscending).to.equal(false);
    });
    it('should have a valid no-sort fallback method', async () => {
        const wrapper = await mountShallow(SortingMixin);
        const component = wrapper.vm;

        expect(component.noSort()).to.equal(0);
    });
});
