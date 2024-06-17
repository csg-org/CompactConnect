//
//  compact.mutations.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 6/10/20.
//

export enum MutationTypes {
    UPDATE_COMPACT_MODE = '[Compact] Updated specific compact mode',
    RESET_COMPACT = '[Compact] Reset compact store',
}

export default {
    [MutationTypes.UPDATE_COMPACT_MODE]: (state, { compactId, newIsCompact }) => {
        const oldCompact = state.compactMap[compactId] || {};
        const updatedCompact = { ...oldCompact, isCompact: newIsCompact };

        state.compactMap[compactId] = updatedCompact;
    },
    [MutationTypes.RESET_COMPACT]: (state) => {
        state.compactMap = {};
    }
};
