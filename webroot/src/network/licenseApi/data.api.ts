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
import { LicenseeSerializer } from '@models/Licensee/Licensee.model';

export interface RequestParamsInterface {
    pageSize?: number;
    pageNumber?: number;
    lastKey?: string;
    sortBy?: string;
    sortDirection?: string;
    licenseeId?: string;
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
     * @param  {RequestParamsInterface} params The request query parameters config.
     * @return {object}                        The URI query param object.
     */
    public prepRequestPostParams(params: RequestParamsInterface = {}): string {
        const requestParams: any = {};

        if (params.licenseeId) {
            requestParams.providerId = params.licenseeId;
        } else {
            if (params.pageSize || params.lastKey) {
                requestParams.pagination = {};

                if (params.pageSize) {
                    requestParams.pagination.pageSize = params.pageSize;
                }
                if (params.lastKey) {
                    requestParams.pagination.lastKey = params.lastKey;
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
     * @param  {RequestParamsInterface} [params={}] The request query parameters config.
     * @return {Promise<object>}                    Response metadata + an array of licensees.
     */
    public async getLicensees(params: RequestParamsInterface = {}) {
        const requestParams: any = this.prepRequestPostParams(params);

        // Temp for limited server paging support
        requestParams.compact = 'aslp';
        requestParams.jurisdiction = 'al';

        const serverReponse: any = await this.api.post(`/v0/providers/licenses-noauth/query`, requestParams);
        const { lastKey, items } = serverReponse;
        const response = {
            lastKey,
            licensees: items.map((serverItem) => LicenseeSerializer.fromServer(serverItem)),
        };

        return response;
    }

    /**
     * GET Licensee by ID.
     * @param  {string}                 licenseeId  A licensee ID.
     * @param  {RequestParamsInterface} [params={}] The request query parameters config.
     * @return {Promise<object>}                    A licensee server response.
     */
    public async getLicensee(licenseeId: string, params: RequestParamsInterface = {}) {
        const requestParams = this.prepRequestPostParams({ ...params, licenseeId });
        const serverReponse = await this.api.post(`/v0/providers/licenses-noauth/query`, requestParams);
        const licensee = LicenseeSerializer.fromServer(serverReponse);
        const response = { licensee };

        return response;
    }
}

export const licenseDataApi = new LicenseDataApi();
