//
//  pagination.mutations.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

import { paginationTemplate } from './pagination.state';

export enum MutationTypes {
    UPDATE_PAGINATION_CURRENT_PAGE = '[Pagination] Updated specific pagination current page',
    UPDATE_PAGINATION_PAGE_SIZE = '[Pagination] Updated specific pagination page size',
    RESET_PAGINATION = '[Pagination] Reset pagination store'
}

const updatePaginationItem = (oldPagination, newPagination) => {
    const paginationToUpdate = oldPagination || paginationTemplate;

    return {
        ...paginationToUpdate,
        ...newPagination
    };
};

export default {
    [MutationTypes.UPDATE_PAGINATION_CURRENT_PAGE]: (state, { paginationId, newPage }) => {
        const oldPagination = state.paginationMap[paginationId] || paginationTemplate;
        const updatedPagination = updatePaginationItem(oldPagination, { page: newPage });

        state.paginationMap[paginationId] = updatedPagination;
    },
    [MutationTypes.UPDATE_PAGINATION_PAGE_SIZE]: (state, { paginationId, newSize }) => {
        const oldPagination = state.paginationMap[paginationId] || paginationTemplate;
        const updatedPagination = updatePaginationItem(oldPagination, { size: newSize });

        state.paginationMap[paginationId] = updatedPagination;
    },
    [MutationTypes.RESET_PAGINATION]: (state) => {
        state.paginationMap = {};
    }
};
