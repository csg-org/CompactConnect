//
//  index.js
//  CompactConnect
//
//  Created by InspiringApps on 7/22/2024.
//

// ============================================================================
//                               CONFIGURATION                                =
// ============================================================================
/**
 * Configuration of supported domains per environment.
 * @type {object}
 */
const environments = {
    csg: {
        prod: {
            webFrontend: `app.compactconnect.org`,
            dataApi: `api.compactconnect.org`,
            s3Upload: `prod-persistentstack-bulkuploadsbucketda4bdcd0-zq5o0q8uqq5i.s3.amazonaws.com`,
            cognitoStaff: `compact-connect-staff.auth.us-east-1.amazoncognito.com`,
            cognitoProvider: `compact-connect-provider.auth.us-east-1.amazoncognito.com`,
        },
        test: {
            webFrontend: `app.test.compactconnect.org`,
            dataApi: `api.test.compactconnect.org`,
            s3Upload: `test-persistentstack-bulkuploadsbucketda4bdcd0-gxzuwbuqfepm.s3.amazonaws.com`,
            cognitoStaff: `compact-connect-staff-test.auth.us-east-1.amazoncognito.com`,
            cognitoProvider: `compact-connect-provider-test.auth.us-east-1.amazoncognito.com`,
        },
    },
    ia: {
        prod: {
            webFrontend: `app.jcc.iaapi.io`,
            dataApi: `api.jcc.iaapi.io`,
            s3Upload: ``, // Waiting for environment configuration.
            cognitoStaff: ``, // Waiting for environment configuration.
            cognitoProvider: ``, // Waiting for environment configuration.
        },
        test: {
            webFrontend: `app.test.jcc.iaapi.io`,
            dataApi: `api.test.jcc.iaapi.io`,
            s3Upload: `test-persistentstack-bulkuploadsbucketda4bdcd0-er1izmgsrdva.s3.amazonaws.com`,
            cognitoStaff: `ia-cc-staff-test.auth.us-east-1.amazoncognito.com`,
            cognitoProvider: `ia-cc-provider-test.auth.us-east-1.amazoncognito.com`,
        },
        justin: {
            webFrontend: `app.justin.jcc.iaapi.io`,
            dataApi: `api.test.jcc.iaapi.io`,
            s3Upload: `test-persistentstack-mockbulkuploadsbucket0e8f27eb-4h1anohxetmp.s3.amazonaws.com`,
            cognitoStaff: ``, // Waiting for environment configuration.
            cognitoProvider: ``, // Waiting for environment configuration.
        },
    },
};

// ============================================================================
//                                   HELPERS                                  =
// ============================================================================
/**
 * Get the request domain from the lambda event record.
 * @param  {object} eventRecord The cloudfront record from the lambda event.
 * @return {string}             The bare domain of the request domain.
 */
const getRequestDomain = (eventRecord) => {
    let requestDomain = environments.csg.prod.webFrontend;

    if (eventRecord) {
        const requestHostHeaderValue = eventRecord.request?.headers?.host?.[0]?.value;

        if (requestHostHeaderValue) {
            requestDomain = requestHostHeaderValue;
        }
    }

    return requestDomain;
};

/**
 * Get a fully qualified domain URI with the protocol scheme.
 * @param  {string} domain The bare domain string.
 * @return {string}        The fully-qualified domain string.
 */
const getFullyQualified = (domain) => {
    const protocol = 'https://';
    let fullyQualified = '';

    if (domain && typeof domain === 'string' && !domain.startsWith(protocol)) {
        fullyQualified = `${protocol}${domain}`;
    }

    return fullyQualified;
};

/**
 * Helper to get the fully-qualified domains for connected services based on the request domain.
 * @param  {string} requestDomain The bare domain of the request.
 * @return {object}               A map of fully-qualified domains for the request environment.
 *   @return {string} dataApi       The data API fully-qualified domain.
 *   @return {string} s3Upload      The S3 fully-qualified domain for uploading state files.
 *   @return {string} cognitoStaff  The Cognito fully-qualified domain for authenticating staff users.
 */
const getEnvironmentUrls = (requestDomain) => {
    const environmentUrls = {};
    let environment;

    switch (requestDomain) {
    case environments.csg.prod.webFrontend:
        environment = environments.csg.prod;
        break;
    case environments.csg.test.webFrontend:
        environment = environments.csg.test;
        break;
    case environments.ia.prod.webFrontend:
        environment = environments.ia.prod;
        break;
    case environments.ia.test.webFrontend:
        environment = environments.ia.test;
        break;
    case environments.ia.justin.webFrontend:
        environment = environments.ia.justin;
        break;
    default:
        environment = environments.csg.prod;
        break;
    }

    environmentUrls.dataApi = getFullyQualified(environment.dataApi);
    environmentUrls.s3Upload = getFullyQualified(environment.s3Upload);
    environmentUrls.cognitoStaff = getFullyQualified(environment.cognitoStaff);
    environmentUrls.cognitoProvider = getFullyQualified(environment.cognitoProvider);

    return environmentUrls;
};

/**
 * Helper to escape CSP src keywords.
 * @param  {string} keyword The standard keyword value.
 * @return {string}         The escaped keyword value.
 */
const srcKeywordEscape = (keyword) => {
    let escaped = '';

    if (keyword && typeof keyword === 'string') {
        escaped = `'${keyword}'`.toLowerCase();
    }

    return escaped;
};

/**
 * Helper to automatically escape and prep CSP src keyword values (by reference).
 * @param  {Array<string>} srcList       The CSP src list.
 * @param  {string}        [listName=''] Optional src list name for logging.
 */
const srcKeywordsEscape = (srcList, listName = '') => {
    // https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Security-Policy#keyword_values
    const srcKeywordsConfig = [
        { value: 'self', isAllowed: true },
        { value: 'none', isAllowed: true },
        { value: 'strict-dynamic', isAllowed: true },
        { value: 'report-sample', isAllowed: true },
        { value: 'inline-speculation-rules', isAllowed: true },
        { value: 'unsafe-inline', isAllowed: false },
        { value: 'unsafe-eval', isAllowed: false },
        { value: 'unsafe-hashes', isAllowed: false },
        { value: 'wasm-unsafe-eval', isAllowed: false },
    ];
    const srcKeywords = srcKeywordsConfig.map((config) => config.value.toLowerCase());

    if (Array.isArray(srcList)) {
        srcList.forEach((srcItem, idx) => {
            const isString = typeof srcItem === 'string';

            if (!isString) {
                srcList[idx] = '';
            } else {
                const srcItemLowerCase = srcItem.toLowerCase();

                if (srcKeywords.includes(srcItemLowerCase)) {
                    const keywordConfig = srcKeywordsConfig.find((config) => srcItemLowerCase === config.value.toLowerCase());

                    if (keywordConfig) {
                        if (!keywordConfig.isAllowed) {
                            console.warn(`${listName} ${srcItem} keyword is not allowed in srcKeywordsConfig policy. We likely should not be using this keyword for security reasons.`.trim());
                            srcList[idx] = '';
                        } else {
                            srcList[idx] = srcKeywordEscape(srcItem);
                        }
                    }
                }
            }
        });
    }
};

/**
 * Helper to build a CSP src group list string from input params.
 * @param  {string}        name src name for the CSP group.
 * @param  {Array<string>} list The static src list for the CSP group.
 * @return {string}             The prepped src list string;
 */
const buildSrcString = (name = '', list = []) => {
    let srcString = '';

    if (Array.isArray(list)) {
        srcKeywordsEscape(list, name);
        srcString = `${name} ${list.join(' ')};`;
    }

    return srcString;
};

// ============================================================================
//                               RESPONSE HEADERS                             =
// ============================================================================
/**
 * Set the CSP header on the response (by reference).
 * @param {string} requestDomain The domain making the request.
 * @param {object} [headers={}]  The event response headers (updated by reference).
 */
const setCspHeader = (requestDomain, headers = {}) => {
    const domains = getEnvironmentUrls(requestDomain);
    const cognitoIdpUrl = 'https://cognito-idp.us-east-1.amazonaws.com';

    // https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Security-Policy
    headers['content-security-policy'] = [{
        key: 'Content-Security-Policy',
        value: `${[
            `default-src 'none';`,
            buildSrcString('manifest-src', [
                'self',
            ]),
            buildSrcString('script-src', [
                'self',
            ]),
            buildSrcString('script-src-elem', [
                'self',
            ]),
            buildSrcString('script-src-attr', [
                'self',
            ]),
            buildSrcString('worker-src', [
                'self',
            ]),
            buildSrcString('style-src', [
                'self',
                'https://fonts.googleapis.com',
            ]),
            buildSrcString('style-src-elem', [
                'self',
                'https://fonts.googleapis.com',
            ]),
            buildSrcString('style-src-attr', [
                'self',
            ]),
            buildSrcString('font-src', [
                'self',
                'https://fonts.gstatic.com',
            ]),
            buildSrcString('img-src', [
                'self',
                'data:',
                domains.dataApi,
            ]),
            buildSrcString('media-src', [
                'self',
                domains.dataApi,
            ]),
            buildSrcString('frame-src', [
                'self',
            ]),
            buildSrcString('frame-ancestors', [
                'none'
            ]),
            buildSrcString('object-src', [
                'none',
            ]),
            buildSrcString('form-action', [
                'none',
            ]),
            buildSrcString('connect-src', [
                'self',
                domains.dataApi,
                domains.s3Upload,
                domains.cognitoStaff,
                domains.cognitoProvider,
                cognitoIdpUrl,
            ]),
        ].join(' ')}`,
    }];
};

/**
 * Set security headers on the response (by reference).
 * @param {string} requestDomain The domain making the request.
 * @param {object} [headers={}]  The event response headers (updated by reference).
 */
const setSecurityHeaders = (requestDomain, headers = {}) => {
    // Strict-Transport-Security
    headers['strict-transport-security'] = [{
        key: 'Strict-Transport-Security',
        value: 'max-age=31536000; includeSubdomains; preload',
    }];
    // X-Content-Type-Options
    headers['x-content-type-options'] = [{
        key: 'X-Content-Type-Options',
        value: 'nosniff',
    }];
    // X-Frame-Options
    headers['x-frame-options'] = [{
        key: 'X-Frame-Options',
        value: 'DENY',
    }];
    // Referrer-Policy
    headers['referrer-policy'] = [{
        key: 'Referrer-Policy',
        value: 'strict-origin-when-cross-origin',
    }];
    // Server
    headers.server = [{
        key: 'Server',
        value: 'CompactConnect',
    }];
    // Content-Security-Policy
    setCspHeader(requestDomain, headers);
};

// ============================================================================
//                                 LAMBDA ENTRY                               =
// ============================================================================
exports.handler = async (event) => {
    // https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/lambda-event-structure.html
    const eventRecord = event?.Records[0]?.cf || {};
    const requestDomain = getRequestDomain(eventRecord);
    const response = eventRecord.response || {};
    const responseHeaders = response.headers || {};

    setSecurityHeaders(requestDomain, responseHeaders);

    return response;
};
