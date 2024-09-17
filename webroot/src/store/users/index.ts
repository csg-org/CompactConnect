//
//  index.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 9/4/2024.
//

import { state } from './users.state';
import actions from './users.actions';
import getters from './users.getters';
import mutations from './users.mutations';

export default {
    namespaced: true,
    state,
    actions,
    getters,
    mutations,
};
