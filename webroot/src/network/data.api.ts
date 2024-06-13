//
//  data.api.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/6/20.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

import { exampleDataApi } from '@/network/exampleApi/data.api';

export class DataApi {
    /**
     * Initialize API Axios interceptors with injected store context.
     * @param {Store} store
     */
    public initInterceptors(store) {
        exampleDataApi.initInterceptors(store);
    }

    /**
     * Example of app-specific API call which is defined in a subfolder
     * in the /network directory and which has their own data.api.ts & interceptors.ts.
     * @return {Promise.<object>}
     */
    public getStyleguidePetsCount(config?: any) {
        return exampleDataApi.getStyleguidePetsCount(config);
    }

    /**
     * Example of app-specific API call which is defined in a subfolder
     * in the /network directory and which has their own data.api.ts & interceptors.ts.
     * @return {Promise.<Array<object>}
     */
    public getStyleguidePets(config?: any) {
        return exampleDataApi.getStyleguidePets(config);
    }

    /**
     * Example of app-specific API call which is defined in a subfolder
     * in the /network directory and which has their own data.api.ts & interceptors.ts.
     * @return {Promise.<User>}
     */
    public getAccount() {
        return exampleDataApi.getAccount();
    }
}

export const dataApi = new DataApi();
