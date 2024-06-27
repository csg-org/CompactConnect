//
//  sorting.actions.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/22/20.
//

import { MutationTypes } from './sorting.mutations';

export default {
    updateSortOption: ({ commit }, { sortingId, newOption }) => {
        commit(MutationTypes.UPDATE_SORTING_OPTION, { sortingId, newOption });
    },
    updateSortDirection: ({ commit }, { sortingId, newDirection }) => {
        commit(MutationTypes.UPDATE_SORTING_DIRECTION, { sortingId, newDirection });
    },
    resetStoreSorting: ({ commit }) => {
        commit(MutationTypes.RESET_SORTING);
    }
};
