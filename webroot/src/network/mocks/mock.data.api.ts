//
//  mock.data.api.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/27/20.
//

import { config as envConfig } from '@plugins/EnvConfig/envConfig.plugin';
import { LicenseeSerializer } from '@models/Licensee/Licensee.model';
import { LicenseeUserSerializer } from '@models/LicenseeUser/LicenseeUser.model';
import { StaffUserSerializer } from '@models/StaffUser/StaffUser.model';
import { PrivilegePurchaseOptionSerializer } from '@models/PrivilegePurchaseOption/PrivilegePurchaseOption.model';
import {
    userData,
    staffAccount,
    stateUploadRequestData,
    licensees,
    users,
    pets,
    privilegePurchaseOptionsResponse
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
    // Helper to simulate wait time on endpoints where desired, to test things like the loading UI
    wait = (ms = 0) => new Promise((resolve) => {
        const waitMs = (envConfig.isTest) ? 0 : ms; // Skip any simulated waits during automated tests

        setTimeout(() => resolve(true), waitMs);
    });

    // Init interceptors
    public initInterceptors(store) {
        initMockStore(store);
        return true;
    }

    // ========================================================================
    //                              STATE API
    // ========================================================================
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
    //                              LICENSE API
    // ========================================================================
    // Get Licensees
    public getLicensees(params: any = {}) {
        return this.wait(500).then(() => ({
            prevLastKey: licensees.prevLastKey,
            lastKey: licensees.lastKey,
            licensees: licensees.items.map((serverItem) => LicenseeSerializer.fromServer(serverItem)),
            params,
        }));
    }

    // Get Licensee by ID
    public getLicensee(compact, licenseeId) {
        const serverResponse = licensees.items.find((item) => item.providerId === licenseeId);
        let response;

        if (serverResponse) {
            response = this.wait(500).then(() => ({
                licensee: LicenseeSerializer.fromServer(licensees.items[0]),
                compact,
                licenseeId,
            }));
        } else {
            response = this.wait(500).then(() => {
                throw new Error('not found');
            });
        }

        return response;
    }

    // ========================================================================
    //                              STAFF USER API
    // ========================================================================
    // Get Users
    public getUsers() {
        return this.wait(500).then(() => ({
            prevLastKey: users.prevLastKey,
            lastKey: users.lastKey,
            users: users.items.map((serverItem) => StaffUserSerializer.fromServer(serverItem)),
        }));
    }

    // Create User
    public createUser() {
        return this.wait(500).then(() => StaffUserSerializer.fromServer(users.items[0]));
    }

    // Get User by ID
    public getUser() {
        return this.wait(500).then(() => StaffUserSerializer.fromServer(users.items[0]));
    }

    // Update User by ID
    public updateUser() {
        return this.wait(500).then(() => StaffUserSerializer.fromServer(users.items[0]));
    }

    // Get Authenticated Staff User
    public getAuthenticatedStaffUser() {
        return this.wait(500).then(() => StaffUserSerializer.fromServer(staffAccount));
    }

    // ========================================================================
    //                              LICENSEE USER API
    // ========================================================================
    // Get Authenticated Licensee User
    public getAuthenticatedLicenseeUser() {
        return this.wait(500).then(() => LicenseeUserSerializer.fromServer(licensees.items[0]));
    }

    // Get Privilege Purchase Information for Licensee User
    public getPrivilegePurchaseInformation() {
        return this.wait(500).then(() => {
            const { items } = privilegePurchaseOptionsResponse;
            const privilegePurchaseOptions = items.filter((serverItem) => (serverItem.type === 'jurisdiction')).map((serverPurchaseOption) => (PrivilegePurchaseOptionSerializer.fromServer(serverPurchaseOption)));

            const compactCommissionFee = items.filter((serverItem) => (serverItem.type === 'compact')).map((serverFeeObject) => ({
                compactType: serverFeeObject?.compactName,
                feeType: serverFeeObject?.compactCommissionFee?.feeType,
                feeAmount: serverFeeObject?.compactCommissionFee?.feeAmount
            }))[0];

            return { privilegePurchaseOptions, compactCommissionFee };
        });
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
            const serializedUser = StaffUserSerializer.fromServer(mockUser);

            return serializedUser;
        });
    }
}

export const dataApi = new DataApi();
