//
//  data.api.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/3/2026.
//

import axios, { AxiosInstance } from 'axios';
import {
    requestError,
    requestSuccess,
    responseSuccess,
    responseError
} from '@network/applicationsApi/interceptors';
import { config as envConfig } from '@plugins/EnvConfig/envConfig.plugin';
import { ApplicationSerializer } from '@models/Application/Application.model';

export interface DataApiInterface {
    api: AxiosInstance;
}

export class ApplicationsDataApi implements DataApiInterface {
    api: AxiosInstance;

    public constructor() {
        // Initial Axios config
        this.api = axios.create({
            baseURL: envConfig.apiUrlUserPsypact,
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
     * @param {Router} router
     * @param {Store}  store
     */
    public initInterceptors(router, store) {
        const requestSuccessInterceptor = requestSuccess(store);
        const requestErrorInterceptor = requestError();
        const responseSuccessInterceptor = responseSuccess();
        const responseErrorInterceptor = responseError(router);

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
     * GET Authenticated Licensee User applications.
     * @return {Promise<object>} Response pagination metadata + an array of Application model instances.
     */
    public async getAuthenticatedLicenseeApplications() {
        const serverResponse: any = await this.api.get(`/v1/provider-users/me/applications`);
        const { items = [], pagination = {}} = serverResponse || {};
        const { prevLastKey, lastKey } = pagination;
        const response = {
            prevLastKey,
            lastKey,
            applications: items.map((serverItem) => ApplicationSerializer.fromServer(serverItem)),
        };

        return response;
    }

    /**
     * GET Authenticated Licensee User application by ID.
     * @param  {string}               applicationId The application ID.
     * @return {Promise<Application>}               An Application model instance.
     */
    public async getAuthenticatedLicenseeApplication(applicationId: string) {
        const serverResponse: any = await this.api.get(`/v1/provider-users/me/applications/${applicationId}`);
        const response = ApplicationSerializer.fromServer(serverResponse);

        return response;
    }
}

export const applicationsDataApi = new ApplicationsDataApi();
