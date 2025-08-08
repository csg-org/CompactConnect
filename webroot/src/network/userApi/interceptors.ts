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
    // Endpoints in the below list are accessible to users who are logged in via the licensee userpool
    // and as such require sending that token to authorize their use. All other endpoints are only accessible
    // by users logged in via the staff user pool and will therefore send those tokens to authorize.
    const licenseeUserEndPoints = [
        '/v1/provider-users/me',
        '/v1/provider-users/me/email',
        '/v1/provider-users/me/email/verify',
        '/v1/purchases/privileges/options',
        '/v1/purchases/privileges',
        '/v1/provider-users/me/military-affiliation',
        '/v1/provider-users/me/home-jurisdiction'
    ];
    const { headers, url } = requestConfig;
    let authToken;
    let authTokenType;

    if (licenseeUserEndPoints.includes(url) || (url.includes('me') && url.includes('history'))) {
        authToken = authStorage.getItem(tokens.licensee.ID_TOKEN);
        authTokenType = authStorage.getItem(tokens.licensee.AUTH_TOKEN_TYPE);
    } else {
        authToken = authStorage.getItem(tokens.staff.AUTH_TOKEN);
        authTokenType = authStorage.getItem(tokens.staff.AUTH_TOKEN_TYPE);
    }

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
    let serverResponse;

    if (axiosResponse) {
        // Get API response
        serverResponse = axiosResponse.data || {};

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
    requestError,
    responseSuccess,
    responseError,
};
