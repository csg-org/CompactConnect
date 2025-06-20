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
import { PrivilegeAttestationSerializer } from '@models/PrivilegeAttestation/PrivilegeAttestation.model';
import { CompactFeeConfigSerializer } from '@/models/CompactFeeConfig/CompactFeeConfig.model';
import { StateSerializer } from '@models/State/State.model';
import {
    userData,
    staffAccount,
    uploadRequestData,
    licensees,
    users,
    pets,
    privilegePurchaseOptionsResponse,
    attestation,
    compactStates,
    compactConfig,
    stateConfig
} from '@network/mocks/mock.data';

let mockStore: any = null;

const initMockStore = (store) => {
    if (mockStore) {
        return mockStore;
    }

    mockStore = store;

    return mockStore;
};

// Helper to simulate wait time on endpoints where desired, to test things like the loading UI
const wait = (ms = 0) => new Promise((resolve) => {
    const waitMs = (envConfig.isTest) ? 0 : ms; // Skip any simulated waits during automated tests

    setTimeout(() => resolve(true), waitMs);
});

export class DataApi {
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
        return wait(500).then(() => ({
            ...uploadRequestData,
            compact,
            state,
        }));
    }

    // Post state upload
    public stateUploadRequest(url: string, file: File) {
        return wait(500).then(() => ({
            status: true,
            url,
            file,
        }));
    }

    // Post compact payment processor config
    public updatePaymentProcessorConfig(compact: string, config: object) {
        return wait(500).then(() => ({
            message: 'success',
            compact,
            config,
        }));
    }

    // Get compact config
    public getCompactConfig(compact: string) {
        return wait(500).then(() => ({
            ...compactConfig,
            compact,
        }));
    }

    // Put compact config
    public updateCompactConfig(compact: string, config: object) {
        return wait(500).then(() => ({
            message: 'success',
            compact,
            config,
        }));
    }

    // Get state config
    public getCompactStateConfig(compact: string, state: string) {
        return wait(500).then(() => ({
            ...stateConfig,
            compact,
            state
        }));
    }

    // Put state config
    public updateCompactStateConfig(compact: string, state: string, config: object) {
        return wait(500).then(() => ({
            message: 'success',
            compact,
            state,
            config,
        }));
    }

    // ========================================================================
    //                              LICENSE API
    // ========================================================================
    // Create Licensee Account.
    public createLicenseeAccount(compact: string, data: object) {
        return wait(500).then(() => ({
            compact,
            ...data,
        }));
    }

    // Get Licensees
    public getLicensees(params: any = {}) {
        return wait(500).then(() => ({
            prevLastKey: licensees.prevLastKey,
            lastKey: licensees.lastKey,
            licensees: licensees.providers.map((serverItem) => LicenseeSerializer.fromServer(serverItem)),
            params,
        }));
    }

    // Get Licensees (Public)
    public getLicenseesPublic(params: any = {}) {
        return wait(500).then(() => ({
            prevLastKey: licensees.prevLastKey,
            lastKey: licensees.lastKey,
            licensees: licensees.providers.map((serverItem) => LicenseeSerializer.fromServer(serverItem)),
            params,
        }));
    }

    // Get Licensee by ID
    public getLicensee(compact, licenseeId) {
        const serverResponse = licensees.providers.find((item) => item.providerId === licenseeId);
        let response;

        if (serverResponse) {
            response = wait(500).then(() => (LicenseeSerializer.fromServer(licensees.providers[0])));
        } else {
            response = wait(500).then(() => {
                throw new Error('not found');
            });
        }

        return response;
    }

    // Get Licensee by ID (Public)
    public getLicenseePublic(compact, licenseeId) {
        const serverResponse = licensees.providers.find((item) => item.providerId === licenseeId);
        let response;

        if (serverResponse) {
            response = wait(500).then(() => (LicenseeSerializer.fromServer(licensees.providers[0])));
        } else {
            response = wait(500).then(() => {
                throw new Error('not found');
            });
        }

        return response;
    }

    // Get Attestation By ID
    public getAttestation(compact, attestationId) {
        const response = PrivilegeAttestationSerializer.fromServer({
            ...attestation,
            attestationId,
            compact,
        });

        return wait(500).then(() => response);
    }

    // Encumber License for a licensee.
    public encumberLicense(compact, licenseeId, licenseState, licenseType, npdbCategory, startDate) {
        if (!compact) {
            return Promise.reject(new Error('failed license encumber'));
        }

        return wait(500).then(() => ({
            message: 'success',
            compact,
            licenseeId,
            licenseState,
            licenseType,
            npdbCategory,
            startDate,
        }));
    }

    // Unencumber License for a licensee.
    public unencumberLicense(compact, licenseeId, licenseState, licenseType, encumbranceId, endDate) {
        if (!compact) {
            return Promise.reject(new Error('failed license unencumber'));
        }

        return wait(500).then(() => ({
            message: 'success',
            compact,
            licenseeId,
            licenseState,
            licenseType,
            encumbranceId,
            endDate,
        }));
    }

    // Delete Privilege for a licensee.
    public deletePrivilege(compact, licenseeId, privilegeState, licenseType) {
        if (!compact) {
            return Promise.reject(new Error('failed privilege delete'));
        }

        return wait(500).then(() => ({
            message: 'success',
            compact,
            licenseeId,
            privilegeState,
            licenseType,
        }));
    }

    // Encumber Privilege for a licensee.
    public encumberPrivilege(compact, licenseeId, privilegeState, licenseType, npdbCategory, startDate) {
        if (!compact) {
            return Promise.reject(new Error('failed privilege encumber'));
        }

        return wait(500).then(() => ({
            message: 'success',
            compact,
            licenseeId,
            privilegeState,
            licenseType,
            npdbCategory,
            startDate,
        }));
    }

    // Unencumber Privilege for a licensee.
    public unencumberPrivilege(compact, licenseeId, privilegeState, licenseType, encumbranceId, endDate) {
        if (!compact) {
            return Promise.reject(new Error('failed privilege unencumber'));
        }

        return wait(500).then(() => ({
            message: 'success',
            compact,
            licenseeId,
            privilegeState,
            licenseType,
            encumbranceId,
            endDate,
        }));
    }

    // Get full SSN for licensee
    public getLicenseeSsn(compact, licenseeId) {
        return wait(500).then(() => ({
            ssn: '111-11-1111',
            compact,
            licenseeId,
        }));
    }

    // ========================================================================
    //                              STAFF USER API
    // ========================================================================
    // Get Users
    public getUsers() {
        return wait(500).then(() => ({
            prevLastKey: users.prevLastKey,
            lastKey: users.lastKey,
            users: users.items.map((serverItem) => StaffUserSerializer.fromServer(serverItem)),
        }));
    }

    // Create User
    public createUser() {
        return wait(500).then(() => StaffUserSerializer.fromServer(users.items[0]));
    }

    // Get User by ID
    public getUser() {
        return wait(500).then(() => StaffUserSerializer.fromServer(users.items[0]));
    }

    // Update User by ID
    public updateUser() {
        return wait(500).then(() => StaffUserSerializer.fromServer(users.items[0]));
    }

    // Reinvite User by ID
    public reinviteUser() {
        return wait(500).then(() => ({ message: 'success' }));
    }

    // Delete User by ID
    public deleteUser() {
        return wait(500).then(() => ({ message: 'success' }));
    }

    // Update Authenticated user password
    public updateAuthenticatedUserPassword() {
        return wait(500).then(() => ({ success: true }));
    }

    // Get Authenticated Staff User
    public getAuthenticatedStaffUser() {
        return wait(500).then(() => StaffUserSerializer.fromServer(staffAccount));
    }

    // Update Authenticated Staff User
    public updateAuthenticatedStaffUser() {
        return wait(500).then(() => StaffUserSerializer.fromServer(staffAccount));
    }

    // Get Compact States
    public getCompactStates() {
        return wait(500).then(() => compactStates.map((serverItem) => StateSerializer.fromServer({
            abbrev: serverItem.postalAbbreviation,
        })));
    }

    // Get Compact States (Public)
    public getCompactStatesPublic() {
        return wait(500).then(() => compactStates.map((serverItem) => StateSerializer.fromServer({
            abbrev: serverItem.postalAbbreviation,
        })));
    }

    // ========================================================================
    //                              LICENSEE USER API
    // ========================================================================
    // Get Authenticated Licensee User
    public getAuthenticatedLicenseeUser() {
        return wait(500).then(() => LicenseeUserSerializer.fromServer(licensees.providers[0]));
    }

    // Update Authenticated Licensee User
    public updateAuthenticatedLicenseeUser() {
        return wait(500).then(() => LicenseeUserSerializer.fromServer(licensees.providers[0]));
    }

    // Get Privilege Purchase Information for Licensee User
    public getPrivilegePurchaseInformation() {
        return wait(500).then(() => {
            const { items } = privilegePurchaseOptionsResponse;
            const privilegePurchaseOptions = items.filter((serverItem) => (serverItem.type === 'jurisdiction')).map((serverPurchaseOption) => (PrivilegePurchaseOptionSerializer.fromServer(serverPurchaseOption)));
            const compactCommissionFee = items.filter((serverItem) => (serverItem.type === 'compact')).map((serverFeeObject) => (CompactFeeConfigSerializer.fromServer(serverFeeObject)))[0];

            return { privilegePurchaseOptions, compactCommissionFee };
        });
    }

    // Post Privilege Purchases for Licensee User
    public postPrivilegePurchases() {
        return wait(500).then(() => ({ message: 'Successfully processed charge', transactionId: '120044154134' }));
    }

    // Post Upload Military Document Intent
    public postUploadMilitaryDocumentIntent(data) {
        return wait(500).then(() => ({
            ...data,
            documentUploadFields: [{
                url: 'url.com',
                fields: {
                    some: 'asd'
                }
            }]
        }));
    }

    // Post Upload Military Document
    public postUploadMilitaryAffiliationDocument(postUrl: string, documentUploadData: any, file: File) {
        return wait(500).then(() => ({
            status: 204,
            postUrl,
            documentUploadData,
            file
        }));
    }

    // Patch end military affiliation
    public endMilitaryAffiliation() {
        return wait(500).then(() => ({ success: true }));
    }

    // ========================================================================
    //                              EXAMPLE API
    // ========================================================================
    // Get styleguide example count
    public getStyleguidePetsCount() {
        return wait(0).then(async () => pets.length);
    }

    // Get styleguide examples
    public getStyleguidePets() {
        return wait(0).then(async () => pets);
    }

    // Get Account
    public getAccount() {
        return wait(0).then(async () => {
            const mockUser: any = { ...userData };
            const serializedUser = StaffUserSerializer.fromServer(mockUser);

            return serializedUser;
        });
    }
}

export const dataApi = new DataApi();
