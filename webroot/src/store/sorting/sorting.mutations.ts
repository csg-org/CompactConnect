//
//  sorting.mutations.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

export enum MutationTypes {
    UPDATE_SORTING_OPTION = '[Sorting] Updated specific sort option',
    UPDATE_SORTING_DIRECTION = '[Sorting] Updated specific sort direction',
    RESET_SORTING = '[Sorting] Reset sort store',
}

export default {
    [MutationTypes.UPDATE_SORTING_DIRECTION]: (state, { sortingId, newDirection }) => {
        const oldSort = state.sortingMap[sortingId] || {};
        const updatedSort = { ...oldSort, direction: newDirection };

        state.sortingMap[sortingId] = updatedSort;
    },
    [MutationTypes.UPDATE_SORTING_OPTION]: (state, { sortingId, newOption }) => {
        const oldSort = state.sortingMap[sortingId] || {};
        const updatedSort = { ...oldSort, option: newOption };

        state.sortingMap[sortingId] = updatedSort;
    },
    [MutationTypes.RESET_SORTING]: (state) => {
        state.sortingMap = {};
    }
};
