//
//  data.api.ts
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
} from '@network/stateApi/interceptors';
import { config as envConfig } from '@plugins/EnvConfig/envConfig.plugin';

export interface DataApiInterface {
    api: AxiosInstance;
}

export class StateDataApi implements DataApiInterface {
    api: AxiosInstance;

    public constructor() {
        // Initial Axios config
        this.api = axios.create({
            baseURL: envConfig.apiUrlState,
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
     * GET Upload request configuration.
     * @param  {string}           compact The compact string ID (aslp, ot, counseling).
     * @param  {string}           state   The 2-character state abbreviation.
     * @return {Promise<object>}          An upload request configuration object.
     */
    public getUploadRequestConfig(compact: string, state: string) {
        return this.api.get(`v0/providers/${compact}/${state}/licenses-noauth/bulk-upload`);
    }

    /**
     * POST Upload request.
     * @return {Promise}
     */
    public uploadRequest(config: any, file: File) {
        const { url, fields = {}} = config?.upload || {};
        const formData = new FormData();
        const s3FieldOrder = [ // S3 is picky about the order of the FormData fields
            'key',
            'x-amz-algorithm',
            'x-amz-credential',
            'x-amz-date',
            'x-amz-signature',
            'x-amz-security-token',
            'policy',
        ];

        s3FieldOrder.forEach((field) => {
            formData.append(field, fields[field]);
        });
        formData.append('file', file);

        return axios.post(url, formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
                Accept: '*/*',

            }
        });
    }
}

export const stateDataApi = new StateDataApi();
