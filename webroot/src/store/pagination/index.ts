//
//  index.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/22/20.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

import { state } from './pagination.state';
import actions from './pagination.actions';
import mutations from './pagination.mutations';

export default {
    namespaced: true,
    state,
    actions,
    mutations,
};
