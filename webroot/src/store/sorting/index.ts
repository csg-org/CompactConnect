//
//  index.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/22/20.
//  Copyright © 2024. InspiringApps. All rights reserved.
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
