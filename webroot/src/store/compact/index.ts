//
//  index.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 6/10/20.
//

import { state } from './compact.state';
import actions from './compact.actions';
import mutations from './compact.mutations';

export default {
    namespaced: true,
    state,
    actions,
    mutations,
};
