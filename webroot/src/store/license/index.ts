//
//  index.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

import { state } from './license.state';
import actions from './license.actions';
import getters from './license.getters';
import mutations from './license.mutations';

export default {
    namespaced: true,
    state,
    actions,
    getters,
    mutations,
};
