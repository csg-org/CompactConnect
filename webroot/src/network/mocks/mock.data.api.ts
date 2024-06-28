//
//  mock.data.api.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/27/20.
//

import { UserSerializer } from '@models/User/User.model';
import {
    userData,
    stateUploadRequestData,
    pets
} from '@network/mocks/mock.data';

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

    // Get state upload request configuration.
    public getStateUploadRequestConfig(compact: string, state: string) {
        return this.wait(500).then(() => ({
            ...stateUploadRequestData,
            compact,
            state,
        }));
    }

    // Post state upload
    public stateUploadRequest(url: string, file: File) {
        return this.wait(500).then(() => ({
            status: true,
            url,
            file,
        }));
    }

    // ========================================================================
    //                              EXAMPLE API
    // ========================================================================
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
