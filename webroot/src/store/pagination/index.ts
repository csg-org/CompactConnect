//
//  index.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/22/20.
//

import { state } from './pagination.state';
import actions from './pagination.actions';
import mutations from './pagination.mutations';

export class PageExhaustError extends Error {
    constructor(message) {
        super(message);
        this.name = 'PageExhaustError';
    }
}

export default {
    namespaced: true,
    state,
    actions,
    mutations,
};
