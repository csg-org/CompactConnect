//
//  data.api.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/6/20.
//

import axios, { AxiosInstance } from 'axios';
import {
    requestError,
    requestSuccess,
    responseSuccess,
    responseError
} from '@network/exampleApi/interceptors';
import { userData, pets } from '@network/mocks/mock.data';
import { config as envConfig } from '@plugins/EnvConfig/envConfig.plugin';

export interface DataApiInterface {
    api: AxiosInstance;
}

export class ExampleDataApi implements DataApiInterface {
    api: AxiosInstance;
    wait = (ms = 0) => new Promise((resolve) => setTimeout(() => resolve(true), ms));

    public constructor() {
        // Initial Axios config
        this.api = axios.create({
            baseURL: envConfig.apiUrlExample,
            // withCredentials: true,
            timeout: 30000,
            headers: {
                'Cache-Control': 'no-cache',
                Accept: 'application/json',
                get: {
                    Accept: 'application/json',
                },
                post: {
                    'Content-Type': 'multipart/form-data',
                },
                put: {
                    'Content-Type': 'multipart/form-data',
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
     * Example of a GET /Account endpoint call.
     * @return {Promise<User>} User account object.
     */
    public getAccount() {
        return this.api.get(`Account`).then((response: any = userData) => response);
    }

    /**
     * Example of a GET Pets count endpoint call.
     * @return {Promise<object>} Object with count property.
     */
    public getStyleguidePetsCount(config?: any) {
        // Mock what a server would do with paging, sorting, etc.
        const {
            pageSize,
            pageNum,
            sortBy,
            sortDir
        } = config || {};
        let response = pets;

        if (sortBy) {
            response = response.sort((a, b) => {
                const value1 = a[sortBy] || '';
                const value2 = b[sortBy] || '';
                let sort = 0;

                if (value1 > value2) {
                    sort = 1;
                } else if (value1 < value2) {
                    sort = -1;
                }

                return sort;
            });

            if (sortDir === 'desc') {
                response = response.reverse();
            }
        }

        if (pageSize) {
            let firstIndex = 0;
            let lastIndex = pageSize - 1;

            if (pageNum) {
                firstIndex = (pageNum * pageSize) - pageSize;
                lastIndex = pageNum * pageSize;
            }

            response = response.slice(firstIndex, lastIndex + 1);
        }

        return this.wait(0).then(() => ({
            count: response.length,
        }));
    }

    /**
     * Example of a GET Pets endpoint call.
     * @return {Promise<Array<object>>} Array of pet objects.
     */
    public getStyleguidePets(config?: any) {
        // Mock what a server would do with paging, sorting, etc.
        const {
            pageSize,
            pageNum,
            sortBy,
            sortDir
        } = config || {};
        let response = pets;

        if (sortBy) {
            response = response.sort((a, b) => {
                const value1 = a[sortBy] || '';
                const value2 = b[sortBy] || '';
                let sort = 0;

                if (value1 > value2) {
                    sort = 1;
                } else if (value1 < value2) {
                    sort = -1;
                }

                return sort;
            });

            if (sortDir === 'desc') {
                response = response.reverse();
            }
        }

        if (pageSize) {
            let firstIndex = 0;
            let lastIndex = pageSize - 1;

            if (pageNum) {
                firstIndex = (pageNum * pageSize) - pageSize;
                lastIndex = pageNum * pageSize;
            }

            response = response.slice(firstIndex, lastIndex + 1).map((record) => ({
                ...record,
                serverPage: pageNum || 1,
            }));
        }

        return this.wait(1000).then(() => response);
    }
}

export const exampleDataApi = new ExampleDataApi();
