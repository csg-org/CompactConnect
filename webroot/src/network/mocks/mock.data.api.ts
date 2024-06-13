//
//  mock.data.api.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/27/20.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

import { UserSerializer } from '@models/User/User.model';
import { userData, pets } from '@network/mocks/mock.data';

let mockStore: any = null;

const initMockStore = (store) => {
    if (mockStore) {
        return mockStore;
    }

    mockStore = store;

    return mockStore;
};

export class DataApi {
    // Helper to simulate wait time on endpoints where desired
    wait = (ms = 0) => new Promise((resolve) => setTimeout(() => resolve(true), ms));

    // Init interceptors
    public initInterceptors(store) {
        initMockStore(store);
        return true;
    }

    // Get styleguide example count
    public getStyleguidePetsCount() {
        return this.wait(0).then(async () => pets.length);
    }

    // Get styleguide examples
    public getStyleguidePets() {
        return this.wait(0).then(async () => pets);
    }

    // Get Account
    public getAccount() {
        return this.wait(0).then(async () => {
            const mockUser: any = { ...userData };
            const serializedUser = UserSerializer.fromServer(mockUser);

            return serializedUser;
        });
    }
}

export const dataApi = new DataApi();
