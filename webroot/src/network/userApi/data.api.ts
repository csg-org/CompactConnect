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
} from '@network/userApi/interceptors';
import { config as envConfig } from '@plugins/EnvConfig/envConfig.plugin';
import { PrivilegePurchaseOptionSerializer } from '@models/PrivilegePurchaseOption/PrivilegePurchaseOption.model';
import { LicenseeUserSerializer } from '@models/LicenseeUser/LicenseeUser.model';
import { StaffUserSerializer } from '@models/StaffUser/StaffUser.model';

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

export class UserDataApi implements DataApiInterface {
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
     * Prep a URI query parameter object for GET requests.
     * @param  {RequestParamsInterfaceLocal} params The request query parameters config.
     * @return {string}                             The URI query param string.
     */
    public prepRequestGetParams(params: RequestParamsInterfaceLocal = {}): string {
        let requestParams = ``;
        const addParam = (key, value) => {
            let operator = '?';

            if (requestParams.length) {
                operator = '&';
            }

            requestParams += `${operator}${key}=${encodeURIComponent(value)}`;
        };

        if (params.search) {
            addParam('search', params.search);
        }
        if (params.pageSize) {
            addParam('pageSize', params.pageSize);
        }
        if (params.lastKey) {
            addParam('lastKey', params.lastKey);
        }
        if (params.sortBy) {
            addParam('sortingKey', params.sortBy);
        }
        if (params.sortDirection) {
            addParam('sortingDirection', params.sortDirection);
        }

        return requestParams;
    }

    /**
     * GET Users.
     * @param  {RequestParamsInterfaceLocal} [params={}] The request query parameters config.
     * @return {Promise<Array<User>>}                    Response metadata + an array of users.
     */
    public async getUsers(params: RequestParamsInterfaceLocal = {}) {
        const requestParams = this.prepRequestGetParams(params);
        const serverResponse: any = await this.api.get(`/v1/compacts/${params.compact}/staff-users${requestParams}`);
        const { pagination = {}, users } = serverResponse;
        const { prevLastKey, lastKey } = pagination;
        const response = {
            prevLastKey,
            lastKey,
            users: users.map((serverItem) => StaffUserSerializer.fromServer(serverItem)),
        };

        return response;
    }

    /**
     * CREATE User.
     * @param  {string}        compact A compact type.
     * @param  {object}        data    The user request data.
     * @return {Promise<User>}         A User model instance.
     */
    public async createUser(compact: string, data: any) {
        const serverResponse = await this.api.post(`/v1/compacts/${compact}/staff-users`, data);
        const response = StaffUserSerializer.fromServer(serverResponse);

        return response;
    }

    /**
     * GET User by ID.
     * @param  {string}        compact A compact type.
     * @param  {string}        userId  A user ID.
     * @return {Promise<User>}         A User model instance.
     */
    public async getUser(compact: string, userId: string) {
        const serverResponse: any = await this.api.get(`/v1/compacts/${compact}/staff-users/${userId}`);
        const response = StaffUserSerializer.fromServer(serverResponse);

        return response;
    }

    /**
     * UPDATE User by ID.
     * @param  {string}        compact A compact type.
     * @param  {string}        userId  A user ID.
     * @param  {object}        data    The user request data.
     * @return {Promise<User>}         A User model instance.
     */
    public async updateUser(compact: string, userId: string, data: any) {
        const serverResponse = await this.api.patch(`/v1/compacts/${compact}/staff-users/${userId}`, data);
        const response = StaffUserSerializer.fromServer(serverResponse);

        return response;
    }

    /**
     * UPDATE Password of authenticated user.
     * @param  {object}          data The request data.
     * @return {Promise<object>}      Axios-formatted response from AWS Cognito.
     */
    public async updateAuthenticatedUserPassword(data: object) {
        const { cognitoRegion } = envConfig;
        const requestData = JSON.stringify(data || {});
        const serverResponse: any = await axios.post(`https://cognito-idp.${cognitoRegion}.amazonaws.com/`, requestData, {
            headers: {
                'Content-Type': `application/x-amz-json-1.1`,
                'X-Amz-Target': `AWSCognitoIdentityProviderService.ChangePassword`,
                Accept: `*/*`,
            },
        });

        return serverResponse;
    }

    /**
     * GET Authenticated Staff User.
     * @return {Promise<User>} A User model instance.
     */
    public async getAuthenticatedStaffUser() {
        const serverResponse: any = await this.api.get(`/v1/staff-users/me`);
        const response = StaffUserSerializer.fromServer(serverResponse);

        return response;
    }

    /**
     * UPDATE Authenticated Staff User.
     * @param  {object}        data The request data.
     * @return {Promise<User>}      A User model instance.
     */
    public async updateAuthenticatedStaffUser(data: object) {
        const serverResponse: any = await this.api.patch(`/v1/staff-users/me`, data);
        const response = StaffUserSerializer.fromServer(serverResponse);

        return response;
    }

    /**
     * GET Authenticated Licensee User.
     * @return {Promise<User>} A User model instance.
     */
    public async getAuthenticatedLicenseeUser() {
        const serverResponse: any = await this.api.get(`/v1/provider-users/me`);

        const response = LicenseeUserSerializer.fromServer(serverResponse);

        return response;
    }

    /**
     * GET Privilege Purchase Information for Authenticated Licensee user.
     * @return {Promise<object>} List of privilege purchase options and compact purchase info.
     */
    public async getPrivilegePurchaseInformation() {
        const serverResponse: any = await this.api.get(`/v1/purchases/privileges/options`);
        const { items } = serverResponse;
        const privilegePurchaseOptions = items.filter((serverItem) => (serverItem.type === 'jurisdiction')).map((serverPurchaseOption) => (PrivilegePurchaseOptionSerializer.fromServer(serverPurchaseOption)));

        const compactCommissionFee = items.filter((serverItem) => (serverItem.type === 'compact')).map((serverFeeObject) => ({
            compactType: serverFeeObject?.compactName,
            feeType: serverFeeObject?.compactCommissionFee?.feeType,
            feeAmount: serverFeeObject?.compactCommissionFee?.feeAmount
        }))[0];

        return { privilegePurchaseOptions, compactCommissionFee };
    }

    /**
     * POST Privilege Purchases for Authenticated Licensee user.
     * @return {Promise<object>} Purchase response object.
     */
    public async postPrivilegePurchases(data: any) {
        const serverResponse: any = await this.api.post(`/v1/purchases/privileges`, data);

        return serverResponse;
    }

    /**
     * POST Upload Military Document Intent for Authenticated Licensee user.
     * @return {Promise<object>} Intent response object containing presigned S3 url and necessary params to upload document.
     */
    public async postUploadMilitaryDocumentIntent(data: any) {
        const serverResponse: any = await this.api.post(`/v1/provider-users/me/military-affiliation`, data);

        return serverResponse;
    }

    /**
     * POST Upload Military Affiliation Document for Authenticated Licensee user.
     * @return {Promise<object>} Document upload response object.
     */
    public async postUploadMilitaryAffiliationDocument(postUrl: string, documentUploadData: any, file: File) {
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
            formData.append(field, documentUploadData[field]);
        });
        formData.append('file', file);

        return axios.post(postUrl, formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
                Accept: '*/*',

            }
        });
    }

    /**
     * PATCH Cancel Military Affiliation.
     * @return {Promise<object>} Purchase response object.
     */
    public async endMilitaryAffiliation() {
        const serverResponse: any = await this.api.patch(`/v1/provider-users/me/military-affiliation`, {
            status: 'inactive'
        });

        return serverResponse;
    }
}

export const userDataApi = new UserDataApi();
