//
//  api.plugin.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

// https://vuejs.org/v2/guide/plugins.html

/* eslint-disable import/no-extraneous-dependencies */

import { dataApi } from '@network/data.api';

export interface API {
    dataApi: any;
}

const api: API = {
    dataApi,
};

export default {
    install: (app) => {
        app.config.globalProperties.$api = api;
    },
};
