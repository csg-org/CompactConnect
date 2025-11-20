//
//  mock.data.api.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/27/20.
//

import { config as envConfig } from '@plugins/EnvConfig/envConfig.plugin';
import { FeatureGates } from '@/app.config';
import { LicenseeSerializer } from '@models/Licensee/Licensee.model';
import { LicenseHistoryItem, LicenseHistoryItemSerializer } from '@/models/LicenseHistoryItem/LicenseHistoryItem.model';
import { LicenseeUserSerializer } from '@models/LicenseeUser/LicenseeUser.model';
import { StaffUserSerializer } from '@models/StaffUser/StaffUser.model';
import { PrivilegePurchaseOptionSerializer } from '@models/PrivilegePurchaseOption/PrivilegePurchaseOption.model';
import { PrivilegeAttestationSerializer } from '@models/PrivilegeAttestation/PrivilegeAttestation.model';
import { CompactFeeConfigSerializer } from '@/models/CompactFeeConfig/CompactFeeConfig.model';
import { CompactSerializer } from '@models/Compact/Compact.model';
import { State, StateSerializer } from '@models/State/State.model';
import { LicenseType } from '@models/License/License.model';
import {
    userData,
    staffAccount,
    uploadRequestData,
    licensees,
    users,
    pets,
    privilegePurchaseOptionsResponse,
    getAttestation,
    compactStates,
    compactStatesForRegistration,
    compactConfig,
    stateConfig,
    mockPrivilegeHistoryResponses

} from '@network/mocks/mock.data';

let mockStore: any = null;

const initMockStore = (store) => {
    if (mockStore) {
        return mockStore;
    }

    mockStore = store;

    return mockStore;
};

// Authenticated provider index for the current session
const authenticatedProviderUserIndex = 0;

// Get the authenticated provider with bounds checking
const getAuthenticatedProvider = () => {
    const { providers } = licensees;
    const maxIndex = providers.length - 1;

    if (authenticatedProviderUserIndex < 0 || authenticatedProviderUserIndex > maxIndex) {
        const errorMessage = `Mock Data Error: authenticatedProviderUserIndex (${authenticatedProviderUserIndex}) does not exist in mock data. Available providers: 0-${maxIndex}. Falling back to provider at index 0.`;

        console.error(errorMessage);

        return providers[0];
    }

    return providers[authenticatedProviderUserIndex];
};

// License type mapping for matching abbreviations and full names to LicenseType enum values
const licenseTypeMap = {
    ot: LicenseType.OCCUPATIONAL_THERAPIST,
    ota: LicenseType.OCCUPATIONAL_THERAPY_ASSISTANT
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
            ...getAttestation(attestationId),
            attestationId,
            compact,
        });

        return wait(500).then(() => response);
    }

    // Encumber License for a licensee.
    public encumberLicense(
        compact,
        licenseeId,
        licenseState,
        licenseType,
        encumbranceType,
        npdbCategory,
        npdbCategories,
        startDate
    ) {
        const { $features } = (window as any).Vue?.config?.globalProperties || {};

        if (!compact) {
            return Promise.reject(new Error('failed license encumber'));
        }

        return wait(500).then(() => ({
            message: 'success',
            compact,
            licenseeId,
            licenseState,
            licenseType,
            encumbranceType,
            ...($features?.checkGate(FeatureGates.ENCUMBER_MULTI_CATEGORY)
                ? {
                    npdbCategories,
                }
                : {
                    npdbCategory,
                }
            ),
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

    // Create License Investigation for a licensee.
    public createLicenseInvestigation(
        compact,
        licenseeId,
        licenseState,
        licenseType
    ) {
        if (!compact) {
            return Promise.reject(new Error('failed license investigation create'));
        }

        return wait(500).then(() => ({
            message: 'success',
            compact,
            licenseeId,
            licenseState,
            licenseType,
        }));
    }

    // Update License Investigation for a licensee.
    public updateLicenseInvestigation(compact, licenseeId, licenseState, licenseType, investigationId, encumbrance) {
        if (!compact) {
            return Promise.reject(new Error('failed license investigation update'));
        }

        return wait(500).then(() => ({
            message: 'success',
            compact,
            licenseeId,
            licenseState,
            licenseType,
            investigationId,
            encumbrance,
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
    public encumberPrivilege(
        compact,
        licenseeId,
        privilegeState,
        licenseType,
        encumbranceType,
        npdbCategory,
        npdbCategories,
        startDate
    ) {
        const { $features } = (window as any).Vue?.config?.globalProperties || {};

        if (!compact) {
            return Promise.reject(new Error('failed privilege encumber'));
        }

        return wait(500).then(() => ({
            message: 'success',
            compact,
            licenseeId,
            privilegeState,
            licenseType,
            encumbranceType,
            ...($features?.checkGate(FeatureGates.ENCUMBER_MULTI_CATEGORY)
                ? {
                    npdbCategories,
                }
                : {
                    npdbCategory,
                }
            ),
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

    // Create Privilege Investigation for a licensee.
    public createPrivilegeInvestigation(
        compact,
        licenseeId,
        privilegeState,
        licenseType
    ) {
        if (!compact) {
            return Promise.reject(new Error('failed privilege investigation create'));
        }

        return wait(500).then(() => ({
            message: 'success',
            compact,
            licenseeId,
            privilegeState,
            licenseType,
        }));
    }

    // Update Privilege Investigation for a licensee.
    public updatePrivilegeInvestigation(
        compact,
        licenseeId,
        privilegeState,
        licenseType,
        investigationId,
        encumbrance
    ) {
        if (!compact) {
            return Promise.reject(new Error('failed privilege investigation update'));
        }

        return wait(500).then(() => ({
            message: 'success',
            compact,
            licenseeId,
            privilegeState,
            licenseType,
            investigationId,
            encumbrance,
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

    // Get Privilege History (Public)
    public getPrivilegeHistoryPublic(
        compact,
        providerId,
        jurisdiction,
        licenseTypeAbbrev
    ) {
        let response;
        let responseData: any = null;

        responseData = mockPrivilegeHistoryResponses.find((historyEntry) => {
            const mappedLicenseType = licenseTypeMap[String(licenseTypeAbbrev ?? '').toLowerCase()];
            const matches = Boolean(
                historyEntry.providerId === providerId
                && historyEntry.jurisdiction === jurisdiction
                && historyEntry.licenseType === mappedLicenseType
            );

            return matches;
        });

        if (responseData
            && compact
            && providerId
            && jurisdiction
            && licenseTypeAbbrev
        ) {
            response = wait(500).then(() => {
                const licenseHistoryData = {
                    compact: responseData.compact,
                    jurisdiction: responseData.jurisdiction,
                    licenseType: responseData.licenseType,
                    privilegeId: responseData.privilegeId,
                    providerId: responseData.providerId,
                    events: [] as Array<LicenseHistoryItem>,
                };

                if (Array.isArray(responseData.events)) {
                    responseData.events.forEach((serverHistoryItem) => {
                        licenseHistoryData.events.push(LicenseHistoryItemSerializer.fromServer(serverHistoryItem));
                    });
                }

                return licenseHistoryData;
            });
        } else {
            response = wait(500).then(() => {
                throw new Error('not found');
            });
        }

        return response;
    }

    // Get Privilege History (Staff)
    public getPrivilegeHistoryStaff(
        compact,
        providerId,
        jurisdiction,
        licenseTypeAbbrev
    ) {
        let response;
        let responseData: any = null;

        // Find the matching history entry dynamically
        responseData = mockPrivilegeHistoryResponses.find((historyEntry) => {
            const mappedLicenseType = licenseTypeMap[String(licenseTypeAbbrev ?? '').toLowerCase()];
            const matches = Boolean(
                historyEntry.providerId === providerId
                && historyEntry.jurisdiction === jurisdiction
                && historyEntry.licenseType === mappedLicenseType
            );

            return matches;
        });

        if (responseData
            && compact
            && providerId
            && jurisdiction
            && licenseTypeAbbrev
        ) {
            response = wait(500).then(() => {
                const licenseHistoryData = {
                    compact: responseData.compact,
                    jurisdiction: responseData.jurisdiction,
                    licenseType: responseData.licenseType,
                    privilegeId: responseData.privilegeId,
                    providerId: responseData.providerId,
                    events: [] as Array<LicenseHistoryItem>,
                };

                if (Array.isArray(responseData.events)) {
                    responseData.events.forEach((serverHistoryItem) => {
                        licenseHistoryData.events.push(LicenseHistoryItemSerializer.fromServer(serverHistoryItem));
                    });
                }

                return licenseHistoryData;
            });
        } else {
            response = wait(500).then(() => {
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

    // Get Compact State Lists for Registration (Public)
    public getCompactStatesForRegistrationPublic() {
        return wait(500).then(() => Object.entries(compactStatesForRegistration).map(([compactAbbrev, stateList]) => {
            let states: Array<State> = [];

            if (Array.isArray(stateList)) {
                states = stateList.map((stateAbbrev) => StateSerializer.fromServer({ abbrev: stateAbbrev }));
            }

            return CompactSerializer.fromServer({
                type: compactAbbrev,
                memberStates: states,
            });
        }));
    }

    // ========================================================================
    //                              LICENSEE USER API
    // ========================================================================
    // Get Authenticated Licensee User
    public getAuthenticatedLicenseeUser() {
        return wait(500).then(() => LicenseeUserSerializer
            .fromServer(getAuthenticatedProvider()));
    }

    // Update Authenticated Licensee User email address
    public updateAuthenticatedLicenseeUserEmail() {
        return wait(500).then(() => ({ message: 'success' }));
    }

    // Verify Authenticated Licensee User email address
    public verifyAuthenticatedLicenseeUserEmail({ verificationCode }) {
        if (!verificationCode) {
            return wait(500).then(() => { throw new Error('failed email verification'); });
        }

        return wait(500).then(() => ({ message: 'success' }));
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

    // Put Home Jurisdiction State
    public updateHomeJurisdiction() {
        return wait(500).then(() => ({
            message: 'success',
        }));
    }

    /**
     * GET Authenticated Licensee User privilege's history.
     * @param  {string}     jurisdiction jurisdiction of privilege
     * @param  {string}     licenseTypeAbbrev license type abbreviation of privilege
     * @return {Promise<>} A User model instance.
     */
    public getPrivilegeHistoryLicensee(jurisdiction: string, licenseTypeAbbrev: string) {
        let response;
        let responseData: any = null;

        // Get the currently authenticated user
        const authenticatedUser = getAuthenticatedProvider();
        const authenticatedProviderId = authenticatedUser?.providerId;

        // Find the matching history entry dynamically
        responseData = mockPrivilegeHistoryResponses.find((historyEntry) => {
            const mappedLicenseType = licenseTypeMap[String(licenseTypeAbbrev ?? '').toLowerCase()];
            const matches = Boolean(
                historyEntry.providerId === authenticatedProviderId
                && historyEntry.jurisdiction === jurisdiction
                && historyEntry.licenseType === mappedLicenseType
            );

            return matches;
        });

        if (responseData && jurisdiction && licenseTypeAbbrev) {
            response = wait(500).then(() => {
                const licenseHistoryData = {
                    compact: responseData.compact,
                    jurisdiction: responseData.jurisdiction,
                    licenseType: responseData.licenseType,
                    privilegeId: responseData.privilegeId,
                    providerId: responseData.providerId,
                    events: [] as Array<LicenseHistoryItem>,
                };

                if (Array.isArray(responseData.events)) {
                    responseData.events.forEach((serverHistoryItem) => {
                        licenseHistoryData.events.push(LicenseHistoryItemSerializer.fromServer(serverHistoryItem));
                    });
                }

                return licenseHistoryData;
            });
        } else {
            response = wait(500).then(() => {
                throw new Error('not found');
            });
        }

        return response;
    }

    // POST Reset MFA Request for Licensee Account
    public resetMfaLicenseeAccount(data: object) {
        if (!data) {
            return Promise.reject(new Error('failed mfa reset request'));
        }

        return wait(500).then(() => ({ message: 'success', ...data }));
    }

    // POST Confirm MFA Request for Licensee Account
    public confirmMfaLicenseeAccount(data: object) {
        if (!data) {
            return Promise.reject(new Error('failed mfa reset confirm'));
        }

        return wait(2000).then(() => ({ message: 'success', ...data }));
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

    // Perform an example feature gate check within a network call
    public getExampleFeatureGate() {
        const { $features } = (window as any).Vue?.config?.globalProperties || {};

        // Obviously network call functions aren't needed to *just* check a feature gate;
        // This is just an example of how a feature gate can be evaluated in a network call if needed.
        return wait(0).then(() => $features?.checkGate(FeatureGates.EXAMPLE_FEATURE_1) || false);
    }
}

export const dataApi = new DataApi();
