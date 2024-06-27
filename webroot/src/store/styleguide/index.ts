//
//  index.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

import { state } from './styleguide.state';
import actions from './styleguide.actions';
import getters from './styleguide.getters';
import mutations from './styleguide.mutations';

export default {
    namespaced: true,
    state,
    actions,
    getters,
    mutations,
};
