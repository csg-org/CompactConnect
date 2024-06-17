//
//  index.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/22/20.
//

import { state } from './sorting.state';
import actions from './sorting.actions';
import mutations from './sorting.mutations';

export default {
    namespaced: true,
    state,
    actions,
    mutations,
};
