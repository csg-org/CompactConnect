//
//  index.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

import { createStore } from 'vuex';
import globalStore from './global';
import styleguideStore from './styleguide';
import userStore from './user';
import paginationStore from './pagination';
import sortingStore from './sorting';
import compactStore from './compact';
import licenseStore from './license';

export default createStore({
    strict: process.env.NODE_ENV !== 'production', // throw if state is mutated outside of mutation handler (dev mode only since it's somewhat expensive; https://vuex.vuejs.org/guide/strict.html)
    state: globalStore.state,
    actions: globalStore.actions,
    getters: globalStore.getters,
    mutations: globalStore.mutations,
    modules: {
        styleguide: styleguideStore,
        user: userStore,
        pagination: paginationStore,
        sorting: sortingStore,
        compact: compactStore,
        license: licenseStore,
    },
});
