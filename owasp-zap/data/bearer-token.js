/*
 * Adapted from https://github.com/zaproxy/community-scripts/blob/main/httpsender/AddBearerTokenHeader.js
 *
 * Selects an Authorization bearer token based on the target URL. CompactConnect fronts three
 * distinct Cognito pools behind the scan targets:
 *   - Staff pool for most endpoints on api.test.compactconnect.org
 *   - Provider users pool for /v1/provider-users/*, /v1/purchases/*, and the GET on
 *     /v1/compacts/{compact}/attestations/{attestationId}
 *   - State auth M2M pool for state-api.test.compactconnect.org
 *
 * Tokens come from env vars set by the workflow or manual-scan.sh:
 *   ZAP_AUTH_STAFF_TOKEN, ZAP_AUTH_PROVIDER_TOKEN, ZAP_AUTH_STATE_TOKEN
 */

var HttpSender = Java.type('org.parosproxy.paros.network.HttpSender');
const System = Java.type('java.lang.System');

const TOKENS = {
    staff: System.getenv('ZAP_AUTH_STAFF_TOKEN'),
    provider: System.getenv('ZAP_AUTH_PROVIDER_TOKEN'),
    state: System.getenv('ZAP_AUTH_STATE_TOKEN'),
};

const PROVIDER_PATH_PREFIX = /^\/v1\/(provider-users|purchases)(\/|$)/;
const PROVIDER_ATTESTATION_PATH = /^\/v1\/compacts\/[^\/]+\/attestations\/[^\/]+$/;

function classifyRequest(host, path) {
    if (host.indexOf('state-api.') === 0) return 'state';
    if (PROVIDER_PATH_PREFIX.test(path)) return 'provider';
    if (PROVIDER_ATTESTATION_PATH.test(path)) return 'provider';
    return 'staff';
}

function sendingRequest(msg, initiator, helper) {
    if (initiator === HttpSender.AUTHENTICATION_INITIATOR || !msg.isInScope()) return;

    const uri = msg.getRequestHeader().getURI();
    const kind = classifyRequest(String(uri.getHost()), String(uri.getPath()));
    const token = TOKENS[kind];

    if (!token) {
        print('No ' + kind + ' token available for ' + uri.toString());
        return;
    }
    msg.getRequestHeader().setHeader('Authorization', 'Bearer ' + token);
}

function responseReceived(msg, initiator, helper) {
    const statusCode = msg.getResponseHeader().getStatusCode();
    const uri = msg.getRequestHeader().getURI();
    print(
        statusCode,
        msg.getRequestHeader().getMethod(),
        uri.toString()
    );
    // TEMP: diagnose state /providers/query baseline — only the clean URL
    const path = String(uri.getPath());
    if (String(uri.getHost()).indexOf('state-api.') === 0 && path === '/v1/compacts/aslp/jurisdictions/oh/providers/query') {
        const ctype = msg.getRequestHeader().getHeader('Content-Type') || '(none)';
        const body = String(msg.getRequestBody().toString()).replace(/\n/g, ' ').substring(0, 300);
        const resp = String(msg.getResponseBody().toString()).replace(/\n/g, ' ').substring(0, 300);
        print('[state-query ' + statusCode + '] CT:' + ctype + ' REQ:' + body + ' RESP:' + resp);
    }
    // To debug auth issues, uncomment this for a hint
    // if (statusCode === 401 || statusCode == 403 ) {
    //     print('Request header:', msg.getRequestHeader().getHeader('Authorization').substring(0, 16));
    //     print('Response body:', msg.getResponseBody().toString());
    // }
}
