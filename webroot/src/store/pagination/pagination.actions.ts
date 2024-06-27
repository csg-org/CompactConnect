//
//  pagination.actions.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/22/20.
//

import { MutationTypes } from './pagination.mutations';

export default {
    updatePaginationPage: ({ commit }, { paginationId, newPage }) => {
        commit(MutationTypes.UPDATE_PAGINATION_CURRENT_PAGE, { paginationId, newPage });
    },
    updatePaginationSize: ({ commit }, { paginationId, newSize }) => {
        commit(MutationTypes.UPDATE_PAGINATION_PAGE_SIZE, { paginationId, newSize });
    },
    resetStorePagination: ({ commit }) => {
        commit(MutationTypes.RESET_PAGINATION);
    }
};
