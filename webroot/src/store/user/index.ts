//
//  index.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

import { state } from './user.state';
import actions from './user.actions';
import getters from './user.getters';
import mutations from './user.mutations';

export default {
    namespaced: true,
    state,
    actions,
    getters,
    mutations,
};
