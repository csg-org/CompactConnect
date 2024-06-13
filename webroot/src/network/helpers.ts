//
//  helpers.api.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//  Copyright © 2024. InspiringApps. All rights reserved.
//
import { AxiosResponse } from 'axios';
import { ServerApiTypes } from '@/app.config';
import { AppMessage, MessageTypes } from '@/models/AppMessage/AppMessage.model';

/**
 * Set the apiOrigin value on server records (by reference).
 * @param  {Object|Array<Object>} data      The data to update by reference.
 * @param  {ServerApiTypes}       apiOrigin The name of the API the response came from.
 * @return {*}
 */
const setApiOrigin = (data, apiOrigin: ServerApiTypes) => {
    const updateRecord = (record) => {
        record.apiOrigin = apiOrigin;
    };

    // Add the API origin to the server records
    if (data) {
        if (Array.isArray(data)) {
            // Arrays of objects
            data.forEach((record) => {
                if (typeof record === 'object') {
                    updateRecord(record);
                }
            });
        } else if (typeof data === 'object') {
            // Objects
            updateRecord(data);
        }
    }

    return data;
};

/**
 * Encode request payload from plain JS object to form-urlencoded.
 * @param  {object} pojo Plain old JS object.
 * @return {string}      The encoded form-urlencoded string.
 */
const encodeFormData = (pojo: object): string => {
    let encoded = '';

    if (typeof pojo === 'object') {
        encoded = Object.entries(pojo)
            .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`)
            .join('&');
    }

    return encoded;
};

/**
 * Encode request payload from plain JS object to application/json.
 * @param  {object} pojo Plain old JS object.
 * @return {string}      The encoded application/json string.
 */
const encodeJsonData = (pojo: object): string => {
    let encoded = '';

    if (typeof pojo === 'object') {
        encoded = JSON.stringify(pojo);
    }

    return encoded;
};

/**
 * Convert a network response into a message.
 * @param  {AxiosResponse} response       The response object from Axios.
 * @param  {string}        [apiOrigin=''] The name of the API the response came from.
 * @return {AppMessage}
 */
const createResponseMessage = (response: AxiosResponse, apiOrigin = ''): AppMessage => {
    if (response.status >= 400) {
        const { config, statusText, data } = response;
        const { method, url } = config;
        const errorMessage = statusText || data?.message || ''; // SP = statusText; SV = data.message;

        return new AppMessage({
            type: MessageTypes.error,
            message: `${apiOrigin} Network error (${response.status}): ${errorMessage}. Failed to ${method} ${url}`
        });
    }

    return new AppMessage({
        type: MessageTypes.success,
        message: response.statusText,
    });
};

export {
    setApiOrigin,
    encodeFormData,
    encodeJsonData,
    createResponseMessage,
};
