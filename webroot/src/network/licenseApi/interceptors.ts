//
//  interceptors.ts
//  CompactConnect
//
//  Created by InspiringApps on 6/18/24.
//
import { authStorage, tokens } from '@/app.config';

// ============================================================================
// =                           REQUEST INTERCEPTORS                           =
// ============================================================================
/**
 * Get Axios API request interceptor.
 * @return {AxiosInterceptor} Function that amends the outgoing client API request.
 */
export const requestSuccess = () => async (requestConfig) => {
    const authToken = authStorage.getItem(tokens.staff.AUTH_TOKEN);
    const authTokenType = authStorage.getItem(tokens.staff.AUTH_TOKEN_TYPE);
    const { headers } = requestConfig;

    // Add auth token
    headers.Authorization = `${authTokenType} ${authToken}`;

    return requestConfig;
};

/**
 * Get Axios API request error interceptor.
 * @NOTE: Not sure what triggers this; perhaps a code error in the request chain?
 * @return {AxiosInterceptor} Function that handles error with the outgoing client API request.
 */
export const requestError = () => (error) => Promise.reject(error);

// ============================================================================
// =                          RESPONSE INTERCEPTORS                           =
// ============================================================================
/**
 * Get Axios API response success interceptor.
 * @return {AxiosInterceptor} Function that extracts the incoming server API response (from within the Axios response wrapper).
 */
export const responseSuccess = () => (response) => {
    const serverData = response.data;

    return serverData;
};

/**
 * Get Axios API response error interceptor.
 * @param  {Router} router      The vue router
 * @return {AxiosInterceptor} Function that extracts the incoming server API response (from within the Axios response wrapper).
 */
export const responseError = (router) => (error) => {
    const axiosResponse = error.response;
    let serverResponse = (axiosResponse) ? axiosResponse.data : null;

    if (axiosResponse) {
        // Get API response
        serverResponse = axiosResponse.data || {};
        serverResponse.responseStatus = axiosResponse.status;

        switch (axiosResponse.status) {
        case 401:
            router.push({ name: 'Logout' });
            break;
        default:
            // Continue
        }
    } else {
        // API unavailable
        serverResponse = error;
    }

    return Promise.reject(serverResponse);
};

export default {
    requestSuccess,
    responseSuccess,
    responseError,
};
