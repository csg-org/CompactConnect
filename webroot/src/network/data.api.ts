//
//  data.api.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/6/20.
//

import { stateDataApi } from '@network/stateApi/data.api';
import { licenseDataApi } from '@network/licenseApi/data.api';
import { exampleDataApi } from '@network/exampleApi/data.api';

export class DataApi {
    /**
     * Initialize API Axios interceptors with injected store context.
     * @param {Store} store
     */
    public initInterceptors(store) {
        stateDataApi.initInterceptors(store);
        licenseDataApi.initInterceptors(store);
        exampleDataApi.initInterceptors(store);
    }

    // ========================================================================
    //                              STATE API
    // ========================================================================
    /**
     * GET State upload request configuration.
     * @param  {string}           compact The compact string ID (aslp, ot, counseling).
     * @param  {string}           state   The 2-character state abbreviation.
     * @return {Promise<object>}         An upload request configuration object
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
     * @param  {string}          licenseeId A licensee ID.
     * @param  {object}          [params]   The request query parameters config.
     * @return {Promise<object>}            A licensee server response.
     */
    public getLicensee(licenseeId, params) {
        return licenseDataApi.getLicensee(licenseeId, params);
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
