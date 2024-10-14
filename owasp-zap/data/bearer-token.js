/*
 * This script is intended to be used along with authentication/OfflineTokenRefresher.js to
 * handle an OAUTH2 offline token refresh workflow.
 *
 * authentication/OfflineTokenRefresher.js will automatically fetch the new access token for every unauthorized
 * request determined by the "Logged Out" or "Logged In" indicator previously set in Context -> Authentication.
 *
 *  httpsender/AddBearerTokenHeader.js will add the new access token to all requests in scope
 * made by ZAP (except the authentication ones) as an "Authorization: Bearer [access_token]" HTTP Header.
 *
 * @author Laura Pardo <lpardo at redhat.com>
 */

var HttpSender = Java.type('org.parosproxy.paros.network.HttpSender');
// var ScriptVars = Java.type('org.zaproxy.zap.extension.script.ScriptVars');
const System = Java.type('java.lang.System');

function sendingRequest(msg, initiator, helper) {
    // add Authorization header to all request in scope except the authorization request itself
    if (initiator !== HttpSender.AUTHENTICATION_INITIATOR && msg.isInScope()) {
        // const token = ScriptVars.getGlobalVar('accessToken');
        const token = System.getenv('TOKEN');
        if (!token) {
            print('Token not defined');
            return
        }
        print(
            'Adding Authorization header to request: ',
            msg.getRequestHeader().getMethod(),
            msg.getRequestHeader().getURI().toString()
        );
        msg.getRequestHeader().setHeader(
            'Authorization',
            'Bearer ' + token
        );
    }
}

function responseReceived(msg, initiator, helper) {
    print('Response code: ', msg.getResponseHeader().getStatusCode());
}
