//
//  license.api.ts
//  CompactConnect
//
//  Created by InspiringApps on 6/18/24.
//

import axios, { AxiosInstance } from 'axios';
import {
    requestError,
    requestSuccess,
    responseSuccess,
    responseError
} from '@network/licenseApi/interceptors';
import { config as envConfig } from '@plugins/EnvConfig/envConfig.plugin';
import { Licensee, LicenseeSerializer } from '@models/Licensee/Licensee.model';

export interface RequestParamsInterfaceLocal {
    compact?: string;
    jurisdiction?: string;
    licenseeId?: string;
    pageSize?: number;
    pageNumber?: number;
    lastKey?: string;
    prevLastKey?: string;
    sortBy?: string;
    sortDirection?: string;
}

export interface RequestParamsInterfaceRemote {
    pagination?: {
        pageSize?: number,
        lastKey?: string,
        prevLastKey?: string,
    },
    sorting?: {
        key?: string,
        direction?: string,
    },
    query: {
        compact?: string,
        jurisdiction?: string,
        providerId?: string,
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
            // withCredentials: true,
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
        const requestParams: RequestParamsInterfaceRemote = { query: {}};

        if (params.compact) {
            requestParams.query.compact = params.compact;
        }

        if (params.jurisdiction) {
            requestParams.query.jurisdiction = params.jurisdiction;
        }

        if (params.licenseeId) {
            requestParams.query.providerId = params.licenseeId;
        } else {
            if (params.pageSize || params.lastKey || params.prevLastKey) {
                requestParams.pagination = {};

                if (params.pageSize) {
                    requestParams.pagination.pageSize = params.pageSize;
                }
                if (params.lastKey) {
                    requestParams.pagination.lastKey = params.lastKey;
                } else if (params.prevLastKey) {
                    requestParams.pagination.prevLastKey = params.prevLastKey;
                }
            }

            if (params.sortBy || params.sortDirection) {
                requestParams.sorting = {};

                if (params.sortBy) {
                    requestParams.sorting.key = params.sortBy;
                }
                if (params.sortDirection) {
                    requestParams.sorting.direction = params.sortDirection;
                }
            }
        }

        return requestParams;
    }

    /**
     * GET Licensees.
     * @param  {RequestParamsInterfaceLocal} [params={}] The request query parameters config.
     * @return {Promise<object>}                         Response metadata + an array of licensees.
     */
    public async getLicensees(params: RequestParamsInterfaceLocal = {}) {
        const requestParams: RequestParamsInterfaceRemote = this.prepRequestPostParams(params);
        const serverReponse: any = await this.api.post(`/v1/compacts/${params.compact}/providers/query`, requestParams);
        const { prevLastKey, lastKey, providers } = serverReponse;
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
        let licensee: Licensee | null = null;

        if (serverResponse?.items?.length) {
            licensee = LicenseeSerializer.fromServer(serverResponse.items[0]);
        }

        const response = { licensee };

        return response;
    }
}

export const licenseDataApi = new LicenseDataApi();
