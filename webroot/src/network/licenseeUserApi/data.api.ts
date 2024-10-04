//
//  user.api.ts
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
} from '@network/licenseeUserApi/interceptors';
import { config as envConfig } from '@plugins/EnvConfig/envConfig.plugin';
import { LicenseeUserSerializer } from '@models/User/User.model';

export interface RequestParamsInterfaceLocal {
    compact?: string;
    search?: string;
    pageSize?: number;
    pageNumber?: number;
    lastKey?: string;
    prevLastKey?: string;
    sortBy?: string;
    sortDirection?: string;
}

export interface DataApiInterface {
    api: AxiosInstance;
}

export class LicenseeUserDataApi implements DataApiInterface {
    api: AxiosInstance;

    public constructor() {
        // Initial Axios config
        this.api = axios.create({
            baseURL: envConfig.apiUrlUser,
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
     * GET User by ID.
     * @param  {string}        compact A compact type.
     * @param  {string}        userId  A user ID.
     * @return {Promise<User>}         A User model instance.
     */
    public async getAuthenticatedLicenseeUser() {
        const serverResponse: any = await this.api.get(`/v1/provider-users/me`);

        const response = LicenseeUserSerializer.fromServer(serverResponse);

        return response;
    }
}

export const licenseeUserDataApi = new LicenseeUserDataApi();
