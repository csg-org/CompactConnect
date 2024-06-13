//
//  compact.actions.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 6/10/20.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

import { MutationTypes } from './compact.mutations';

export default {
    updateCompactMode: ({ commit }, { compactId, isCompact }) => {
        commit(MutationTypes.UPDATE_COMPACT_MODE, { compactId, newIsCompact: isCompact });
    },
    resetStoreSorting: ({ commit }) => {
        commit(MutationTypes.RESET_COMPACT);
    }
};
