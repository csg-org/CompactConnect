//
//  index.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

import { state } from './global.state';
import actions from './global.actions';
import getters from './global.getters';
import mutations from './global.mutations';
import plugins from './global.plugins';

export default {
    state,
    actions,
    getters,
    mutations,
    plugins: [plugins],
};
