//
//  data.api.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/6/20.
//

import { stateDataApi } from '@network/stateApi/data.api';
import { licenseDataApi } from '@network/licenseApi/data.api';
import { userDataApi } from '@network/userApi/data.api';
import { exampleDataApi } from '@network/exampleApi/data.api';
import { PaymentProcessorConfig, CompactConfig, CompactStateConfig } from '@models/Compact/Compact.model';

export class DataApi {
    /**
     * Initialize API Axios interceptors with injected store context.
     * @param {Router} router
     */
    public initInterceptors(router) {
        stateDataApi.initInterceptors(router);
        licenseDataApi.initInterceptors(router);
        userDataApi.initInterceptors(router);
        exampleDataApi.initInterceptors(router);
    }

    // ========================================================================
    //                              STATE API
    // ========================================================================
    /**
     * GET State upload request configuration.
     * @param  {string}           compact The compact type.
     * @param  {string}           state   The 2-character state abbreviation.
     * @return {Promise<object>}          An upload request configuration object
     */
    public getStateUploadRequestConfig(compact: string, state: string) {
        return stateDataApi.getUploadRequestConfig(compact, state);
    }

    /**
     * POST State upload request.
     * @param  {string}   config The remote bucket upload configuration.
     * @param  {File}     file   The file to upload.
     * @return {Promise<any>}    The bucket response.
     */
    public stateUploadRequest(config: any, file: File) {
        return stateDataApi.uploadRequest(config, file);
    }

    /**
     * POST Compact payment processer config.
     * @param  {string}                 compact The compact string ID (aslp, octp, coun).
     * @param  {PaymentProcessorConfig} config  The payment processer config data.
     * @return {Promise<object>}                The server response.
     */
    public updatePaymentProcessorConfig(compact: string, config: PaymentProcessorConfig) {
        return stateDataApi.updatePaymentProcessorConfig(compact, config);
    }

    /**
     * GET Compact config.
     * @param  {string}          compact The compact string ID (aslp, octp, coun).
     * @return {Promise<object>}         The server response.
     */
    public getCompactConfig(compact: string) {
        return stateDataApi.getCompactConfig(compact);
    }

    /**
     * PUT Compact config.
     * @param  {string}          compact The compact string ID (aslp, octp, coun).
     * @param  {CompactConfig}   config  The compact config data.
     * @return {Promise<object>}         The server response.
     */
    public updateCompactConfig(compact: string, config: CompactConfig) {
        return stateDataApi.updateCompactConfig(compact, config);
    }

    /**
     * GET State config.
     * @param  {string}          compact The compact string ID (aslp, octp, coun).
     * @param  {string}          state   The 2-character state abbreviation.
     * @return {Promise<object>}         The server response.
     */
    public getCompactStateConfig(compact: string, state: string) {
        return stateDataApi.getCompactStateConfig(compact, state);
    }

    /**
     * PUT State config.
     * @param  {string}             compact The compact string ID (aslp, octp, coun).
     * @param  {string}             state   The 2-character state abbreviation.
     * @param  {CompactStateConfig} config  The compact config data.
     * @return {Promise<object>}            The server response.
     */
    public updateCompactStateConfig(compact: string, state: string, config: CompactStateConfig) {
        return stateDataApi.updateCompactStateConfig(compact, state, config);
    }

    // ========================================================================
    //                              LICENSE API
    // ========================================================================
    /**
     * POST Create Licensee Account.
     * @param  {string}       compact The compact string ID (aslp, ot, counseling).
     * @param  {object}       data    The user request data.
     * @return {Promise<any>}         The server response.
     */
    public createLicenseeAccount(compact: string, data: object) {
        return licenseDataApi.createAccount(compact, data);
    }

    /**
     * GET Licensees.
     * @param  {object}         [params] The request query parameters config.
     * @return {Promise<Array>}          An array of users server response.
     */
    public getLicensees(params) {
        return licenseDataApi.getLicensees(params);
    }

    /**
     * GET Licensees (Public).
     * @param  {object}         [params] The request query parameters config.
     * @return {Promise<Array>}          An array of users server response.
     */
    public getLicenseesPublic(params) {
        return licenseDataApi.getLicenseesPublic(params);
    }

    /**
     * GET Licensee by ID.
     * @param  {string}          compact    A compact type.
     * @param  {string}          licenseeId A licensee ID.
     * @return {Promise<object>}            A licensee server response.
     */
    public getLicensee(compact, licenseeId) {
        return licenseDataApi.getLicensee(compact, licenseeId);
    }

    /**
     * GET Licensee by ID (Public).
     * @param  {string}          compact    A compact type.
     * @param  {string}          licenseeId A licensee ID.
     * @return {Promise<object>}            A licensee server response.
     */
    public getLicenseePublic(compact, licenseeId) {
        return licenseDataApi.getLicenseePublic(compact, licenseeId);
    }

    /**
     * GET Attestation by ID.
     * @param  {string}          compact       A compact type.
     * @param  {string}          attestationId An attestation ID.
     * @return {Promise<object>}               A PrivilegeAttestation model instance.
     */
    public getAttestation(compact, attestationId) {
        return licenseDataApi.getAttestation(compact, attestationId);
    }

    /**
     * POST Encumber License for a licensee.
     * @param  {string}           compact         The compact string ID (aslp, octp, coun).
     * @param  {string}           licenseeId      The Licensee ID.
     * @param  {string}           licenseState    The 2-character state abbreviation for the License.
     * @param  {string}           licenseType     The license type.
     * @param  {string}           encumbranceType The discipline action type.
     * @param  {string}           npdbCategory    The NPDB category name.
     * @param  {Array<string>}    npdbCategories  The NPDB category list.
     * @param  {string}           startDate       The encumber start date.
     * @return {Promise<object>}                  The server response.
     */
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
        return licenseDataApi.encumberLicense(
            compact,
            licenseeId,
            licenseState,
            licenseType,
            encumbranceType,
            npdbCategory,
            npdbCategories,
            startDate
        );
    }

    /**
     * PATCH Un-encumber License for a licensee.
     * @param  {string}           compact       The compact string ID (aslp, octp, coun).
     * @param  {string}           licenseeId    The Licensee ID.
     * @param  {string}           licenseState  The 2-character state abbreviation for the License.
     * @param  {string}           licenseType   The license type.
     * @param  {string}           encumbranceId The Encumbrance ID.
     * @param  {string}           endDate       The encumber end date.
     * @return {Promise<object>}                The server response.
     */
    public unencumberLicense(compact, licenseeId, licenseState, licenseType, encumbranceId, endDate) {
        return licenseDataApi.unencumberLicense(
            compact,
            licenseeId,
            licenseState,
            licenseType,
            encumbranceId,
            endDate
        );
    }

    /**
     * POST Create License Investigation for a licensee.
     * @param  {string}           compact      The compact string ID (aslp, octp, coun).
     * @param  {string}           licenseeId   The Licensee ID.
     * @param  {string}           licenseState The 2-character state abbreviation for the License.
     * @param  {string}           licenseType  The license type.
     * @return {Promise<object>}               The server response.
     */
    public createLicenseInvestigation(
        compact,
        licenseeId,
        licenseState,
        licenseType
    ) {
        return licenseDataApi.createLicenseInvestigation(
            compact,
            licenseeId,
            licenseState,
            licenseType
        );
    }

    /**
     * Update License Investigation for a licensee.
     * @param  {string}           compact         The compact string ID (aslp, octp, coun).
     * @param  {string}           licenseeId      The Licensee ID.
     * @param  {string}           licenseState    The 2-character state abbreviation for the License.
     * @param  {string}           licenseType     The license type.
     * @param  {string}           investigationId The Investigation ID.
     * @param  {object}           [encumbrance]   Optional encumbrance config to add to the privilege.
     * @return {Promise<object>}                  The server response.
     */
    public updateLicenseInvestigation(compact, licenseeId, licenseState, licenseType, investigationId, encumbrance) {
        return licenseDataApi.updateLicenseInvestigation(
            compact,
            licenseeId,
            licenseState,
            licenseType,
            investigationId,
            encumbrance
        );
    }

    /**
     * DELETE Privilege for a licensee.
     * @param  {string}           compact        The compact string ID (aslp, octp, coun).
     * @param  {string}           licenseeId     The Licensee ID.
     * @param  {string}           privilegeState The 2-character state abbreviation for the Privilege.
     * @param  {string}           licenseType    The license type.
     * @param  {string}           notes          The deletion notes.
     * @return {Promise<object>}                 The server response.
     */
    public deletePrivilege(compact, licenseeId, privilegeState, licenseType, notes) {
        return licenseDataApi.deletePrivilege(compact, licenseeId, privilegeState, licenseType, notes);
    }

    /**
     * POST Encumber Privilege for a licensee.
     * @param  {string}           compact         The compact string ID (aslp, octp, coun).
     * @param  {string}           licenseeId      The Licensee ID.
     * @param  {string}           privilegeState  The 2-character state abbreviation for the Privilege.
     * @param  {string}           licenseType     The license type.
     * @param  {string}           encumbranceType The discipline action type.
     * @param  {string}           npdbCategory    The NPDB category name.
     * @param  {Array<string>}    npdbCategories  The NPDB category list.
     * @param  {string}           startDate       The encumber start date.
     * @return {Promise<object>}                  The server response.
     */
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
        return licenseDataApi.encumberPrivilege(
            compact,
            licenseeId,
            privilegeState,
            licenseType,
            encumbranceType,
            npdbCategory,
            npdbCategories,
            startDate
        );
    }

    /**
     * PATCH Un-encumber Privilege for a licensee.
     * @param  {string}           compact        The compact string ID (aslp, octp, coun).
     * @param  {string}           licenseeId     The Licensee ID.
     * @param  {string}           privilegeState The 2-character state abbreviation for the Privilege.
     * @param  {string}           licenseType    The license type.
     * @param  {string}           encumbranceId  The Encumbrance ID.
     * @param  {string}           endDate        The encumber end date.
     * @return {Promise<object>}                 The server response.
     */
    public unencumberPrivilege(compact, licenseeId, privilegeState, licenseType, encumbranceId, endDate) {
        return licenseDataApi.unencumberPrivilege(
            compact,
            licenseeId,
            privilegeState,
            licenseType,
            encumbranceId,
            endDate
        );
    }

    /**
     * POST Create Privilege Investigation for a licensee.
     * @param  {string}           compact        The compact string ID (aslp, octp, coun).
     * @param  {string}           licenseeId     The Licensee ID.
     * @param  {string}           privilegeState The 2-character state abbreviation for the License.
     * @param  {string}           licenseType    The license type.
     * @return {Promise<object>}                 The server response.
     */
    public createPrivilegeInvestigation(
        compact,
        licenseeId,
        privilegeState,
        licenseType
    ) {
        return licenseDataApi.createPrivilegeInvestigation(
            compact,
            licenseeId,
            privilegeState,
            licenseType
        );
    }

    /**
     * Update Privilege Investigation for a licensee.
     * @param  {string}           compact         The compact string ID (aslp, octp, coun).
     * @param  {string}           licenseeId      The Licensee ID.
     * @param  {string}           privilegeState  The 2-character state abbreviation for the License.
     * @param  {string}           licenseType     The license type.
     * @param  {string}           investigationId The Investigation ID.
     * @param  {object}           [encumbrance]   Optional encumbrance config to add to the privilege.
     * @return {Promise<object>}                  The server response.
     */
    public updatePrivilegeInvestigation(
        compact,
        licenseeId,
        privilegeState,
        licenseType,
        investigationId,
        encumbrance
    ) {
        return licenseDataApi.updatePrivilegeInvestigation(
            compact,
            licenseeId,
            privilegeState,
            licenseType,
            investigationId,
            encumbrance
        );
    }

    /**
     * GET Licensee SSN by ID.
     * @param  {string}          compact    A compact type.
     * @param  {string}          licenseeId A licensee ID.
     * @return {Promise<object>}            The server response.
     */
    public getLicenseeSsn(compact, licenseeId) {
        return licenseDataApi.getLicenseeSsn(compact, licenseeId);
    }

    /**
     * GET Privilege History as a staff user.
     * @param  {string}     compact compact of privilege
     * @param  {string}     providerId providerId of privilege holder
     * @param  {string}     jurisdiction jurisdiction of privilege
     * @param  {string}     licenseTypeAbbrev licenseTypeAbbrev of privilege
     * @return {Promise<object>} A PrivilegeHistory model instance.
     */
    public getPrivilegeHistoryStaff(
        compact: string,
        providerId: string,
        jurisdiction: string,
        licenseTypeAbbrev: string
    ) {
        return licenseDataApi.getPrivilegeHistoryStaff(
            compact,
            providerId,
            jurisdiction,
            licenseTypeAbbrev
        );
    }

    /**
     * GET Privilege History as an unauthenticated user.
     * @param  {string}     compact compact of privilege
     * @param  {string}     providerId providerId of privilege holder
     * @param  {string}     jurisdiction jurisdiction of privilege
     * @param  {string}     licenseTypeAbbrev licenseTypeAbbrev of privilege
     * @return {Promise<object>} A PrivilegeHistory model instance.
     */
    public getPrivilegeHistoryPublic(
        compact: string,
        providerId: string,
        jurisdiction: string,
        licenseTypeAbbrev: string
    ) {
        return licenseDataApi.getPrivilegeHistoryPublic(
            compact,
            providerId,
            jurisdiction,
            licenseTypeAbbrev
        );
    }

    // ========================================================================
    //                              USER API
    // ========================================================================
    /**
     * GET Users.
     * @param  {object}         [params] The request query parameters config.
     * @return {Promise<Array>}          An array of users.
     */
    public getUsers(params) {
        return userDataApi.getUsers(params);
    }

    /**
     * CREATE User.
     * @param  {string}        compact A compact type.
     * @param  {object}        data    The user request data.
     * @return {Promise<User>}         A User model instance.
     */
    public createUser(compact, data) {
        return userDataApi.createUser(compact, data);
    }

    /**
     * GET User by ID.
     * @param  {string}          compact A compact type.
     * @param  {string}          userId  A user ID.
     * @return {Promise<User>}           A User model instance.
     */
    public getUser(compact, userId) {
        return userDataApi.getUser(compact, userId);
    }

    /**
     * UPDATE User by ID.
     * @param  {string}        compact A compact type.
     * @param  {string}        userId  A user ID.
     * @param  {object}        data    The user request data.
     * @return {Promise<User>}         A User model instance.
     */
    public updateUser(compact, userId, data) {
        return userDataApi.updateUser(compact, userId, data);
    }

    /**
     * REINVITE User by ID.
     * @param  {string}          compact A compact type.
     * @param  {string}          userId  A user ID.
     * @return {Promise<object>}         The server response.
     */
    public reinviteUser(compact, userId) {
        return userDataApi.reinviteUser(compact, userId);
    }

    /**
     * DELETE User by ID.
     * @param  {string}          compact A compact type.
     * @param  {string}          userId  A user ID.
     * @return {Promise<object>}         The server response.
     */
    public deleteUser(compact, userId) {
        return userDataApi.deleteUser(compact, userId);
    }

    /**
     * UPDATE Password of authenticated user.
     * @param  {object}          data The request data.
     * @return {Promise<object>}      Axios-formatted response from AWS Cognito.
     */
    public updateAuthenticatedUserPassword(data) {
        return userDataApi.updateAuthenticatedUserPassword(data);
    }

    /**
     * GET Authenticated Staff User.
     * @return {Promise<User>} A User model instance.
     */
    public getAuthenticatedStaffUser() {
        return userDataApi.getAuthenticatedStaffUser();
    }

    /**
     * UPDATE Authenticated Staff User.
     * @return {Promise<User>} A User model instance.
     */
    public updateAuthenticatedStaffUser(data) {
        return userDataApi.updateAuthenticatedStaffUser(data);
    }

    /**
     * GET Compact States.
     * @param  {string}                compact A compact type.
     * @return {Promise<Array<State>>}         A list of State instances.
     */
    public getCompactStates(compact) {
        return userDataApi.getCompactStates(compact);
    }

    /**
     * GET Compact States (Public).
     * @param  {string}                compact A compact type.
     * @return {Promise<Array<State>>}         A list of State instances.
     */
    public getCompactStatesPublic(compact) {
        return userDataApi.getCompactStatesPublic(compact);
    }

    /**
     * GET Compact State Lists for Registration (Public).
     * @return {Promise<Array<Compact>>} A list of Compact instances.
     */
    public getCompactStatesForRegistrationPublic() {
        return userDataApi.getCompactStatesForRegistrationPublic();
    }

    /**
     * GET Privilege Purchase Information for Authenticated Licensee user.
     * @return {Promise<object>} List of privilege purchase options and compact purchase info.
     */
    public getPrivilegePurchaseInformation() {
        return userDataApi.getPrivilegePurchaseInformation();
    }

    // ========================================================================
    //                              LICENSEE USER API
    // ========================================================================
    /**
     * GET Authenticated Licensee User.
     * @return {Promise<User>} A User model instance.
     */
    public getAuthenticatedLicenseeUser() {
        return userDataApi.getAuthenticatedLicenseeUser();
    }

    /**
     * UPDATE Authenticated Licensee User email address.
     * @param  {object}          data The request data.
     * @return {Promise<object>}      The server response.
     */
    public updateAuthenticatedLicenseeUserEmail(data) {
        return userDataApi.updateAuthenticatedLicenseeUserEmail(data);
    }

    /**
     * VERIFY Authenticated Licensee User email address.
     * @param  {object}          data The request data.
     * @return {Promise<object>}      The server response.
     */
    public verifyAuthenticatedLicenseeUserEmail(data) {
        return userDataApi.verifyAuthenticatedLicenseeUserEmail(data);
    }

    /**
     * POST Privilege Purchases for Authenticated Licensee user.
     * @return {Promise<object>} Purchase response object.
     */
    public postPrivilegePurchases(data: any) {
        return userDataApi.postPrivilegePurchases(data);
    }

    /**
     * POST Upload Military Document Intent for Authenticated Licensee user.
     * @return {Promise<object>} Intent response object containing presigned S3 url and necessary params to upload document.
     */
    public postUploadMilitaryDocumentIntent(data: any) {
        return userDataApi.postUploadMilitaryDocumentIntent(data);
    }

    /**
     * POST Upload Military Affiliation Document for Authenticated Licensee user.
     * @return {Promise<object>} Document upload response object.
     */
    public postUploadMilitaryAffiliationDocument(postUrl: string, documentUploadData: any, file: File) {
        return userDataApi.postUploadMilitaryAffiliationDocument(postUrl, documentUploadData, file);
    }

    /**
     * PATCH Cancel Military Affiliation.
     * @return {Promise<object>} Purchase response object.
     */
    public endMilitaryAffiliation() {
        return userDataApi.endMilitaryAffiliation();
    }

    /**
     * UPDATE Home Jurisdiction for Authenticated Licensee User.
     * @param  {object}          data   The request data.
     * @return {Promise<object>}        Server response.
     */
    public async updateHomeJurisdiction(data: any) {
        return userDataApi.updateHomeJurisdiction(data);
    }

    /**
     * GET Authenticated Licensee User privilege's history.
     * @param  {string}     jurisdiction jurisdiction of privilege
     * @param  {string}     licenseTypeAbbrev license type abbreviation of privilege
     * @return {Promise<>} A User model instance.
     */
    public getPrivilegeHistoryLicensee(jurisdiction: string, licenseTypeAbbrev: string) {
        return userDataApi.getPrivilegeHistoryLicensee(jurisdiction, licenseTypeAbbrev);
    }

    /**
     * POST Reset MFA Request for Licensee Account.
     * @param  {object}          data The user request data.
     * @return {Promise<object>}      The server response.
     */
    public resetMfaLicenseeAccount(data: object) {
        return userDataApi.resetMfaLicenseeAccount(data);
    }

    /**
     * POST Confirm MFA Request for Licensee Account.
     * @param  {object}          data The user request data.
     * @return {Promise<object>}      The server response.
     */
    public confirmMfaLicenseeAccount(data: object) {
        return userDataApi.confirmMfaLicenseeAccount(data);
    }

    // ========================================================================
    //                              EXAMPLE API
    // ========================================================================
    /**
     * Example of app-specific API call which is defined in a subfolder
     * in the /network directory and which has their own data.api.ts & interceptors.ts.
     * @return {Promise<object>}
     */
    public getStyleguidePetsCount(config?: any) {
        return exampleDataApi.getStyleguidePetsCount(config);
    }

    /**
     * Example of app-specific API call which is defined in a subfolder
     * in the /network directory and which has their own data.api.ts & interceptors.ts.
     * @return {Promise<Array<object>>}
     */
    public getStyleguidePets(config?: any) {
        return exampleDataApi.getStyleguidePets(config);
    }

    /**
     * Example of app-specific API call which is defined in a subfolder
     * in the /network directory and which has their own data.api.ts & interceptors.ts.
     * @return {Promise<User>}
     */
    public getAccount() {
        return exampleDataApi.getAccount();
    }

    /**
     * Example of a network call that can evaluate feature gates if needed.
     * @return {Promise<Boolean>}
     */
    public getExampleFeatureGate() {
        return exampleDataApi.getExampleFeatureGate();
    }
}

export const dataApi = new DataApi();
