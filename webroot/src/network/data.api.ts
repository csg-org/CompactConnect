//
//  data.api.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/6/20.
//

import { stateDataApi } from '@network/stateApi/data.api';
import { licenseDataApi } from '@network/licenseApi/data.api';
import { staffUserDataApi } from '@network/staffUserApi/data.api';
import { licenseeUserDataApi } from '@network/licenseeUserApi/data.api';
import { exampleDataApi } from '@network/exampleApi/data.api';

export class DataApi {
    /**
     * Initialize API Axios interceptors with injected store context.
     * @param {Store} store
     */
    public initInterceptors(store) {
        stateDataApi.initInterceptors(store);
        licenseDataApi.initInterceptors(store);
        staffUserDataApi.initInterceptors(store);
        licenseeUserDataApi.initInterceptors(store);
        exampleDataApi.initInterceptors(store);
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

    // ========================================================================
    //                              LICENSE API
    // ========================================================================
    /**
     * GET Licensees.
     * @param  {object}         [params] The request query parameters config.
     * @return {Promise<Array>}          An array of users server response.
     */
    public getLicensees(params) {
        return licenseDataApi.getLicensees(params);
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

    // ========================================================================
    //                              USER API
    // ========================================================================
    /**
     * GET Users.
     * @param  {object}         [params] The request query parameters config.
     * @return {Promise<Array>}          An array of users.
     */
    public getUsers(params) {
        return staffUserDataApi.getUsers(params);
    }

    /**
     * CREATE User.
     * @param  {string}        compact A compact type.
     * @param  {object}        data    The user request data.
     * @return {Promise<User>}         A User model instance.
     */
    public createUser(compact, data) {
        return staffUserDataApi.createUser(compact, data);
    }

    /**
     * GET User by ID.
     * @param  {string}          compact A compact type.
     * @param  {string}          userId  A user ID.
     * @return {Promise<User>}           A User model instance.
     */
    public getUser(compact, userId) {
        return staffUserDataApi.getUser(compact, userId);
    }

    /**
     * UPDATE User by ID.
     * @param  {string}        compact A compact type.
     * @param  {string}        userId  A user ID.
     * @param  {object}        data    The user request data.
     * @return {Promise<User>}         A User model instance.
     */
    public updateUser(compact, userId, data) {
        return staffUserDataApi.updateUser(compact, userId, data);
    }

    /**
     * GET Authenticated Staff User.
     * @return {Promise<User>} A User model instance.
     */
    public getAuthenticatedStaffUser() {
        return staffUserDataApi.getAuthenticatedStaffUser();
    }

    // ========================================================================
    //                              LICENSEE USER API
    // ========================================================================
    /**
     * GET Authenticated Licensee User.
     * @return {Promise<User>} A User model instance.
     */
    public getAuthenticatedLicenseeUser() {
        return licenseeUserDataApi.getAuthenticatedLicenseeUser();
    }

    /**
     * GET Authenticated Staff User.
     * @return {Promise<User>} A User model instance.
     */
    public getAuthenticatedStaffUser() {
        return userDataApi.getAuthenticatedStaffUser();
    }

    // ========================================================================
    //                              EXAMPLE API
    // ========================================================================
    /**
     * Example of app-specific API call which is defined in a subfolder
     * in the /network directory and which has their own data.api.ts & interceptors.ts.
     * @return {Promise.<object>}
     */
    public getStyleguidePetsCount(config?: any) {
        return exampleDataApi.getStyleguidePetsCount(config);
    }

    /**
     * Example of app-specific API call which is defined in a subfolder
     * in the /network directory and which has their own data.api.ts & interceptors.ts.
     * @return {Promise.<Array<object>}
     */
    public getStyleguidePets(config?: any) {
        return exampleDataApi.getStyleguidePets(config);
    }

    /**
     * Example of app-specific API call which is defined in a subfolder
     * in the /network directory and which has their own data.api.ts & interceptors.ts.
     * @return {Promise.<User>}
     */
    public getAccount() {
        return exampleDataApi.getAccount();
    }
}

export const dataApi = new DataApi();
