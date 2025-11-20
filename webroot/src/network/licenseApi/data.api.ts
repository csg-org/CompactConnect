//
//  license.api.ts
//  CompactConnect
//
//  Created by InspiringApps on 6/18/24.
//

import { authStorage, tokens, FeatureGates } from '@/app.config';
import axios, { AxiosInstance } from 'axios';
import {
    requestError,
    requestSuccess,
    responseSuccess,
    responseError
} from '@network/licenseApi/interceptors';
import { config as envConfig } from '@plugins/EnvConfig/envConfig.plugin';
import { LicenseeSerializer } from '@models/Licensee/Licensee.model';
import { PrivilegeAttestation, PrivilegeAttestationSerializer } from '@models/PrivilegeAttestation/PrivilegeAttestation.model';
import { LicenseHistoryItemSerializer, LicenseHistoryItem } from '@/models/LicenseHistoryItem/LicenseHistoryItem.model';

export interface RequestParamsInterfaceLocal {
    isPublic?: boolean;
    compact?: string;
    jurisdiction?: string;
    licenseeId?: string;
    licenseeFirstName?: string;
    licenseeLastName?: string;
    pageSize?: number;
    pageNumber?: number;
    lastKey?: string;
    getNextPage?: boolean;
    getPrevPage?: boolean;
    prevLastKey?: string;
    sortBy?: string;
    sortDirection?: string;
}

export interface RequestParamsInterfaceRemote {
    pagination?: {
        pageSize?: number,
        lastKey?: string,
    },
    sorting?: {
        key?: string,
        direction?: string,
    },
    query: {
        compact?: string,
        jurisdiction?: string,
        providerId?: string,
        givenName?: string,
        familyName?: string,
    },
}

export interface DataApiInterface {
    api: AxiosInstance;
}

export class LicenseDataApi implements DataApiInterface {
    api: AxiosInstance;

    public constructor() {
        // Initial Axios config
        this.api = axios.create({
            baseURL: envConfig.apiUrlLicense,
            timeout: 30000,
            headers: {
                'Cache-Control': 'no-cache',
                Accept: 'application/json',
                get: {
                    Accept: 'application/json',
                },
                post: {
                    'Content-Type': 'application/json',
                },
                put: {
                    'Content-Type': 'application/json',
                },
            },
        });
    }

    /**
     * Attach Axios interceptors with injected contexts.
     * https://github.com/axios/axios#interceptors
     * @param {Store} store
     */
    public initInterceptors(store) {
        const requestSuccessInterceptor = requestSuccess();
        const requestErrorInterceptor = requestError();
        const responseSuccessInterceptor = responseSuccess();
        const responseErrorInterceptor = responseError(store);

        // Request Interceptors
        this.api.interceptors.request.use(
            requestSuccessInterceptor,
            requestErrorInterceptor
        );
        // Response Interceptors
        this.api.interceptors.response.use(
            responseSuccessInterceptor,
            responseErrorInterceptor
        );
    }

    /**
     * Prep a URI query parameter object for POST requests.
     * @param  {RequestParamsInterfaceLocal} params The request query parameters config.
     * @return {object}                             The URI query param object.
     */
    public prepRequestPostParams(params: RequestParamsInterfaceLocal = {}): RequestParamsInterfaceRemote {
        const {
            jurisdiction,
            licenseeId,
            licenseeFirstName,
            licenseeLastName,
            pageSize,
            lastKey,
            sortBy,
            sortDirection,
        } = params;
        const hasSearchTerms = Boolean(licenseeId || licenseeFirstName || licenseeLastName);
        const requestParams: RequestParamsInterfaceRemote = { query: {}};

        if (jurisdiction) {
            requestParams.query.jurisdiction = jurisdiction;
        }

        if (hasSearchTerms) {
            if (licenseeId) {
                requestParams.query.providerId = licenseeId;
            }
            if (licenseeFirstName) {
                requestParams.query.givenName = licenseeFirstName;
            }
            if (licenseeLastName) {
                requestParams.query.familyName = licenseeLastName;
            }
        }

        if (!licenseeId) {
            if (pageSize || lastKey) {
                requestParams.pagination = {};

                if (pageSize) {
                    requestParams.pagination.pageSize = pageSize;
                }
                if (lastKey) {
                    requestParams.pagination.lastKey = lastKey;
                }
            }

            if (sortBy || sortDirection) {
                requestParams.sorting = {};

                if (sortBy) {
                    requestParams.sorting.key = sortBy;
                }
                if (sortDirection) {
                    requestParams.sorting.direction = sortDirection;
                }
            }
        }

        return requestParams;
    }

    /**
     * POST Create Licensee Account
     * @param  {string}        compact A compact type.
     * @param  {object}        data    The user request data.
     * @return {Promise<any>}          The server response.
     */
    public async createAccount(compact: string, data: object) {
        const requestData = { ...data, compact };
        const serverResponse = await this.api.post(`/v1/provider-users/registration`, requestData);

        return serverResponse;
    }

    /**
     * GET Licensees.
     * @param  {RequestParamsInterfaceLocal} [params={}] The request query parameters config.
     * @return {Promise<object>}                         Response metadata + an array of licensees.
     */
    public async getLicensees(params: RequestParamsInterfaceLocal = {}) {
        const requestParams: RequestParamsInterfaceRemote = this.prepRequestPostParams(params);
        const serverReponse: any = await this.api.post(`/v1/compacts/${params.compact}/providers/query`, requestParams);
        const { pagination = {}, providers } = serverReponse;
        const { prevLastKey, lastKey } = pagination;
        const response = {
            prevLastKey,
            lastKey,
            licensees: providers.map((serverItem) => LicenseeSerializer.fromServer(serverItem)),
        };

        return response;
    }

    /**
     * GET Licensees (Public).
     * @param  {RequestParamsInterfaceLocal} [params={}] The request query parameters config.
     * @return {Promise<object>}                         Response metadata + an array of licensees.
     */
    public async getLicenseesPublic(params: RequestParamsInterfaceLocal = {}) {
        const requestParams: RequestParamsInterfaceRemote = this.prepRequestPostParams(params);
        const serverReponse: any = await this.api.post(`/v1/public/compacts/${params.compact}/providers/query`, requestParams);
        const { pagination = {}, providers } = serverReponse;
        const { prevLastKey, lastKey } = pagination;
        const response = {
            prevLastKey,
            lastKey,
            licensees: providers.map((serverItem) => LicenseeSerializer.fromServer(serverItem)),
        };

        return response;
    }

    /**
     * GET Licensee by ID.
     * @param  {string}          licenseeId A licensee ID.
     * @return {Promise<object>}            A licensee server response.
     */
    public async getLicensee(compact: string, licenseeId: string) {
        const serverResponse: any = await this.api.get(`/v1/compacts/${compact}/providers/${licenseeId}`);

        return LicenseeSerializer.fromServer(serverResponse);
    }

    /**
     * GET Licensee by ID (Public).
     * @param  {string}          licenseeId A licensee ID.
     * @return {Promise<object>}            A licensee server response.
     */
    public async getLicenseePublic(compact: string, licenseeId: string) {
        const serverResponse: any = await this.api.get(`/v1/public/compacts/${compact}/providers/${licenseeId}`);

        return LicenseeSerializer.fromServer(serverResponse);
    }

    /**
     * GET Attestations by ID for a compact.
     * @param  {string}           compact       The compact string ID (aslp, octp, coun).
     * @param  {string}           attestationId The attestationId (from /backend/compact-connect/compact-config/*.yml).
     * @return {Promise<object>}                A PrivilegeAttestation model instance.
     */
    public async getAttestation(compact: string, attestationId: string) {
        const serverResponse: any = await this.api.get(`/v1/compacts/${compact}/attestations/${attestationId}`);
        const response: PrivilegeAttestation = PrivilegeAttestationSerializer.fromServer(serverResponse);

        return response;
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
    public async encumberLicense(
        compact: string,
        licenseeId: string,
        licenseState: string,
        licenseType: string,
        encumbranceType: string,
        npdbCategory: string,
        npdbCategories: Array<string>,
        startDate: string
    ) {
        const { $features } = (window as any).Vue?.config?.globalProperties || {};
        const serverResponse: any = await this.api.post(`/v1/compacts/${compact}/providers/${licenseeId}/licenses/jurisdiction/${licenseState}/licenseType/${licenseType}/encumbrance`, {
            encumbranceType,
            ...($features?.checkGate(FeatureGates.ENCUMBER_MULTI_CATEGORY)
                ? {
                    clinicalPrivilegeActionCategories: npdbCategories,
                }
                : {
                    clinicalPrivilegeActionCategory: npdbCategory,
                }
            ),
            encumbranceEffectiveDate: startDate,
        });

        return serverResponse;
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
    public async unencumberLicense(
        compact: string,
        licenseeId: string,
        licenseState: string,
        licenseType: string,
        encumbranceId: string,
        endDate: string
    ) {
        const serverResponse: any = await this.api.patch(`/v1/compacts/${compact}/providers/${licenseeId}/licenses/jurisdiction/${licenseState}/licenseType/${licenseType}/encumbrance/${encumbranceId}`, {
            effectiveLiftDate: endDate,
        });

        return serverResponse;
    }

    /**
     * POST Create License Investigation for a licensee.
     * @param  {string}           compact         The compact string ID (aslp, octp, coun).
     * @param  {string}           licenseeId      The Licensee ID.
     * @param  {string}           licenseState    The 2-character state abbreviation for the License.
     * @param  {string}           licenseType     The license type.
     * @return {Promise<object>}                  The server response.
     */
    public async createLicenseInvestigation(
        compact: string,
        licenseeId: string,
        licenseState: string,
        licenseType: string
    ) {
        const serverResponse: any = await this.api.post(`/v1/compacts/${compact}/providers/${licenseeId}/licenses/jurisdiction/${licenseState}/licenseType/${licenseType}/investigation`, {});

        return serverResponse;
    }

    /**
     * PATCH Update License Investigation for a licensee.
     * @param  {string}        compact         The compact string ID (aslp, octp, coun).
     * @param  {string}        licenseeId      The Licensee ID.
     * @param  {string}        licenseState    The 2-character state abbreviation for the License.
     * @param  {string}        licenseType     The license type.
     * @param  {string}        investigationId The Investigation ID.
     * @param  {object}        [encumbrance]   Optional encumbrance config to add to the license.
     *   @param  {string}        encumbranceType The discipline action type.
     *   @param  {string}        npdbCategory    The NPDB category name.
     *   @param  {Array<string>} npdbCategories  The NPDB category list.
     *   @param  {string}        startDate       The encumber start date.
     * @return {Promise<object>}               The server response.
     */
    public async updateLicenseInvestigation(
        compact: string,
        licenseeId: string,
        licenseState: string,
        licenseType: string,
        investigationId: string,
        encumbrance?: {
            encumbranceType: string,
            npdbCategory: string,
            npdbCategories: Array<string>,
            startDate: string
        }
    ) {
        const { $features } = (window as any).Vue?.config?.globalProperties || {};
        const serverResponse: any = await this.api.patch(`/v1/compacts/${compact}/providers/${licenseeId}/licenses/jurisdiction/${licenseState}/licenseType/${licenseType}/investigation/${investigationId}`, {
            action: 'close',
            ...(encumbrance
                ? {
                    encumbrance: {
                        encumbranceType: encumbrance.encumbranceType,
                        ...($features?.checkGate(FeatureGates.ENCUMBER_MULTI_CATEGORY)
                            ? {
                                clinicalPrivilegeActionCategories: encumbrance.npdbCategories,
                            }
                            : {
                                clinicalPrivilegeActionCategory: encumbrance.npdbCategory,
                            }
                        ),
                        encumbranceEffectiveDate: encumbrance.startDate,
                    },
                }
                : {}
            ),
        });

        return serverResponse;
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
    public async deletePrivilege(
        compact: string,
        licenseeId: string,
        privilegeState: string,
        licenseType: string,
        notes: string
    ) {
        const serverResponse: any = await this.api.post(`/v1/compacts/${compact}/providers/${licenseeId}/privileges/jurisdiction/${privilegeState}/licenseType/${licenseType}/deactivate`, {
            deactivationNote: notes,
        });

        return serverResponse;
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
    public async encumberPrivilege(
        compact: string,
        licenseeId: string,
        privilegeState: string,
        licenseType: string,
        encumbranceType: string,
        npdbCategory: string,
        npdbCategories: Array<string>,
        startDate: string
    ) {
        const { $features } = (window as any).Vue?.config?.globalProperties || {};
        const serverResponse: any = await this.api.post(`/v1/compacts/${compact}/providers/${licenseeId}/privileges/jurisdiction/${privilegeState}/licenseType/${licenseType}/encumbrance`, {
            encumbranceType,
            ...($features?.checkGate(FeatureGates.ENCUMBER_MULTI_CATEGORY)
                ? {
                    clinicalPrivilegeActionCategories: npdbCategories,
                }
                : {
                    clinicalPrivilegeActionCategory: npdbCategory,
                }
            ),
            encumbranceEffectiveDate: startDate,
        });

        return serverResponse;
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
    public async unencumberPrivilege(
        compact: string,
        licenseeId: string,
        privilegeState: string,
        licenseType: string,
        encumbranceId: string,
        endDate: string
    ) {
        const serverResponse: any = await this.api.patch(`/v1/compacts/${compact}/providers/${licenseeId}/privileges/jurisdiction/${privilegeState}/licenseType/${licenseType}/encumbrance/${encumbranceId}`, {
            effectiveLiftDate: endDate,
        });

        return serverResponse;
    }

    /**
     * POST Create Privilege Investigation for a licensee.
     * @param  {string}           compact        The compact string ID (aslp, octp, coun).
     * @param  {string}           licenseeId     The Licensee ID.
     * @param  {string}           privilegeState The 2-character state abbreviation for the Privilege.
     * @param  {string}           licenseType    The license type.
     * @return {Promise<object>}                 The server response.
     */
    public async createPrivilegeInvestigation(
        compact: string,
        licenseeId: string,
        privilegeState: string,
        licenseType: string
    ) {
        const serverResponse: any = await this.api.post(`/v1/compacts/${compact}/providers/${licenseeId}/privileges/jurisdiction/${privilegeState}/licenseType/${licenseType}/investigation`, {});

        return serverResponse;
    }

    /**
     * PATCH Update Privilege Investigation for a licensee.
     * @param  {string}          compact         The compact string ID (aslp, octp, coun).
     * @param  {string}          licenseeId      The Licensee ID.
     * @param  {string}          privilegeState  The 2-character state abbreviation for the Privilege.
     * @param  {string}          licenseType     The license type.
     * @param  {string}          investigationId The Investigation ID.
     * @param  {object}          [encumbrance]   Optional encumbrance config to add to the privilege.
     *   @param  {string}          encumbranceType The discipline action type.
     *   @param  {string}          npdbCategory    The NPDB category name.
     *   @param  {Array<string>}   npdbCategories  The NPDB category list.
     *   @param  {string}          startDate       The encumber start date.
     * @return {Promise<object>}                 The server response.
     */
    public async updatePrivilegeInvestigation(
        compact: string,
        licenseeId: string,
        privilegeState: string,
        licenseType: string,
        investigationId: string,
        encumbrance?: {
            encumbranceType: string,
            npdbCategory: string,
            npdbCategories: Array<string>,
            startDate: string
        }
    ) {
        const { $features } = (window as any).Vue?.config?.globalProperties || {};
        const serverResponse: any = await this.api.patch(`/v1/compacts/${compact}/providers/${licenseeId}/privileges/jurisdiction/${privilegeState}/licenseType/${licenseType}/investigation/${investigationId}`, {
            action: 'close',
            ...(encumbrance
                ? {
                    encumbrance: {
                        encumbranceType: encumbrance.encumbranceType,
                        ...($features?.checkGate(FeatureGates.ENCUMBER_MULTI_CATEGORY)
                            ? {
                                clinicalPrivilegeActionCategories: encumbrance.npdbCategories,
                            }
                            : {
                                clinicalPrivilegeActionCategory: encumbrance.npdbCategory,
                            }
                        ),
                        encumbranceEffectiveDate: encumbrance.startDate,
                    },
                }
                : {}
            ),
        });

        return serverResponse;
    }

    /**
     * GET SSN for licensee by ID.
     * @param  {string}          licenseeId A licensee ID.
     * @return {Promise<object>}            The server response.
     */
    public async getLicenseeSsn(compact: string, licenseeId: string) {
        // This endpoint requires bypassing our regular error-handler interceptors.
        const authTokenStaff = authStorage.getItem(tokens.staff.AUTH_TOKEN);
        const authTokenStaffType = authStorage.getItem(tokens.staff.AUTH_TOKEN_TYPE);
        const serverResponse: any = await axios.get(`${envConfig.apiUrlLicense}/v1/compacts/${compact}/providers/${licenseeId}/ssn`, {
            headers: {
                'Cache-Control': 'no-cache',
                Accept: 'application/json',
                Authorization: `${authTokenStaffType} ${authTokenStaff}`,
            },
        });

        return serverResponse.data || {};
    }

    /**
     * GET Authenticated Privilege History as a staff user.
     * @param  {string}     compact compact of privilege
     * @param  {string}     providerId providerId of privilege holder
     * @param  {string}     jurisdiction jurisdiction of privilege
     * @param  {string}     licenseTypeAbbrev licenseTypeAbbrev of privilege
     * @return {Promise<object>} Privilege History data.
     */
    public async getPrivilegeHistoryStaff(
        compact: string,
        providerId: string,
        jurisdiction: string,
        licenseTypeAbbrev: string
    ) {
        const serverResponse: any = await this.api.get(
            `/v1/compacts/${compact}/providers/${providerId}/privileges/jurisdiction/${jurisdiction.toLowerCase()}/licenseType/${licenseTypeAbbrev.toLowerCase()}/history`
        );

        const licenseHistoryData = {
            compact: serverResponse.compact,
            jurisdiction: serverResponse.jurisdiction,
            licenseType: serverResponse.licenseType,
            privilegeId: serverResponse.privilegeId,
            providerId: serverResponse.providerId,
            events: [] as Array<LicenseHistoryItem>,
        };

        if (Array.isArray(serverResponse.events)) {
            serverResponse.events.forEach((serverHistoryItem) => {
                licenseHistoryData.events.push(LicenseHistoryItemSerializer.fromServer(serverHistoryItem));
            });
        }

        return licenseHistoryData;
    }

    /**
     * GET Privilege History as an unauthenticated user.
     * @param  {string}     compact compact of privilege
     * @param  {string}     providerId providerId of privilege holder
     * @param  {string}     jurisdiction jurisdiction of privilege
     * @param  {string}     licenseTypeAbbrev licenseTypeAbbrev of privilege
     * @return {Promise<object>} Privilege History data.
     */
    public async getPrivilegeHistoryPublic(
        compact: string,
        providerId: string,
        jurisdiction: string,
        licenseTypeAbbrev: string
    ) {
        const serverResponse: any = await this.api.get(
            `/v1/public/compacts/${compact}/providers/${providerId}/jurisdiction/${jurisdiction.toLowerCase()}/licenseType/${licenseTypeAbbrev.toLowerCase()}/history`
        );

        const licenseHistoryData = {
            compact: serverResponse.compact,
            jurisdiction: serverResponse.jurisdiction,
            licenseType: serverResponse.licenseType,
            privilegeId: serverResponse.privilegeId,
            providerId: serverResponse.providerId,
            events: [] as Array<LicenseHistoryItem>,
        };

        if (Array.isArray(serverResponse.events)) {
            serverResponse.events.forEach((serverHistoryItem) => {
                licenseHistoryData.events.push(LicenseHistoryItemSerializer.fromServer(serverHistoryItem));
            });
        }

        return licenseHistoryData;
    }
}

export const licenseDataApi = new LicenseDataApi();
