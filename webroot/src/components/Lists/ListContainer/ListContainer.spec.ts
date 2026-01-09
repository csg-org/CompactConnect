//
//  ListContainer.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/27/2020.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import ListContainer from '@components/Lists/ListContainer/ListContainer.vue';
import Sorting from '@components/Lists/Sorting/Sorting.vue';
import PaginationLegacy from '@components/Lists/PaginationLegacy/PaginationLegacy.vue';

describe('ListContainer component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(ListContainer, {
            props: {
                list: [],
                paginationId: 'test',
                // pageChange: () => null,
                // sortingId: 'test',
                // sortChange: () => null,
                sortOptions: []
            },
        });

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(ListContainer).exists()).to.equal(true);
    });
    it('should have expected default UI with no records', async () => {
        const wrapper = await mountShallow(ListContainer, {
            props: {
                list: [],
                paginationId: 'test',
                // pageChange: () => null,
                // sortingId: 'test',
                // sortChange: () => null,
                sortOptions: []
            },
        });

        expect(wrapper.find('.no-records').exists(), 'no records').to.equal(true);
        expect(wrapper.findAllComponents(Sorting).length, 'sorting elements').to.equal(0);
        expect(wrapper.findAllComponents(PaginationLegacy).length, 'pagination elements').to.equal(0);
    });
    it('should have expected default UI with records', async () => {
        const wrapper = await mountShallow(ListContainer, {
            props: {
                listData: ['x'],
                paginationId: 'test',
                pageChange: () => null,
                sortingId: 'test',
                // sortChange: () => null,
                sortOptions: []
            },
        });

        expect(wrapper.find('.no-records').exists(), 'no records').to.equal(false);
        expect(wrapper.findAllComponents(Sorting).length, 'sorting elements').to.equal(0);
        expect(wrapper.findAllComponents(PaginationLegacy).length, 'pagination elements').to.equal(2);
    });
    it('should exclude top pagination', async () => {
        const wrapper = await mountShallow(ListContainer, {
            props: {
                listData: ['x'],
                paginationId: 'component',
                pageChange: () => null,
                excludeTopPagination: true,
                sortingId: 'component',
                // sortChange: () => null,
                sortOptions: []
            },
        });

        expect(wrapper.findAllComponents(PaginationLegacy).length).to.equal(1);
    });
    it('should exclude bottom pagination', async () => {
        const wrapper = await mountShallow(ListContainer, {
            props: {
                listData: ['x'],
                paginationId: 'component',
                pageChange: () => null,
                excludeBottomPagination: true,
                sortingId: 'component',
                // sortChange: () => null,
                sortOptions: []
            },
        });

        expect(wrapper.findAllComponents(PaginationLegacy).length).to.equal(1);
    });
    it('should exclude all pagination', async () => {
        const wrapper = await mountShallow(ListContainer, {
            props: {
                listData: ['x'],
                paginationId: 'component',
                pageChange: () => null,
                excludeTopPagination: true,
                excludeBottomPagination: true,
                // sortingId: 'component',
                // sortChange: () => null,
                sortOptions: []
            },
        });

        expect(wrapper.findAllComponents(PaginationLegacy).length).to.equal(0);
    });
    it('should exclude sorting', async () => {
        const wrapper = await mountShallow(ListContainer, {
            props: {
                listData: ['x'],
                paginationId: 'component',
                pageChange: () => null,
                excludeSorting: true,
            },
        });

        expect(wrapper.findAllComponents(Sorting).length).to.equal(0);
    });
    it('should calculate list total size', async () => {
        const wrapper = await mountShallow(ListContainer, {
            props: {
                listData: ['x'],
                paginationId: 'component',
                pageChange: () => null,
                sortingId: 'component',
                // sortChange: () => null,
                sortOptions: [],
                includeCompactToggle: true,
            },
        });
        const component = wrapper.vm;

        expect(component.listTotalSize).to.equal(1);
    });
});
