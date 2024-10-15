/*
 * Adapted from https://github.com/zaproxy/community-scripts/blob/main/httpsender/AddBearerTokenHeader.js
 * This script adds a bearer token to all requests in scope except the authorization request itself
 * The token is retrieved from the environment variable TOKEN, which can be acquired separately from ZAP.
 */

var HttpSender = Java.type('org.parosproxy.paros.network.HttpSender');
// var ScriptVars = Java.type('org.zaproxy.zap.extension.script.ScriptVars');
const System = Java.type('java.lang.System');

const token = System.getenv('ZAP_AUTH_HEADER_VALUE');


function sendingRequest(msg, initiator, helper) {
    // add Authorization header to all request in scope except the authorization request itself
    if (initiator !== HttpSender.AUTHENTICATION_INITIATOR && msg.isInScope()) {
        // const token = ScriptVars.getGlobalVar('accessToken');
        if (!token) {
            print('Token not defined');
            return
        }
        msg.getRequestHeader().setHeader(
            'Authorization',
            'Bearer ' + token
        );
    }
}

function responseReceived(msg, initiator, helper) {
    const statusCode = msg.getResponseHeader().getStatusCode();
    print(
        statusCode,
        msg.getRequestHeader().getMethod(),
        msg.getRequestHeader().getURI().toString()
    );
    if (statusCode === 401 || statusCode == 403 ) {
        print('Request header:', msg.getRequestHeader().getHeader('Authorization').substring(0, 16));
        print('Response body:', msg.getResponseBody().toString());
    }
}
