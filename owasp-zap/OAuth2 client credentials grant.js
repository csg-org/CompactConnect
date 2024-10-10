// Make sure any Java classes used explicitly are imported
const HttpRequestHeader = Java.type('org.parosproxy.paros.network.HttpRequestHeader');
const HttpHeader = Java.type('org.parosproxy.paros.network.HttpHeader');
const URI = Java.type('org.apache.commons.httpclient.URI');
const ScriptVars = Java.type('org.zaproxy.zap.extension.script.ScriptVars');


function authenticate(helper, paramsValues, credentials) {
    print('Authenticating via JavaScript script...');

    // Prepare the login submission request details
    const tokenUrl = paramsValues.get('IDP Token URL');
    const fullUrl = tokenUrl
        + '?grant_type=client_credentials'
        + '&client_id=' + encodeURIComponent(credentials.getParam('client id'))
        + '&client_secret=' + encodeURIComponent(credentials.getParam('client secret'))
        + '&scope=profile+aslp/admin+aslp/write+aslp/read'
    const requestUri = new URI(
        fullUrl,
        false
    );

    // Build the submission request header
    var requestHeader = new HttpRequestHeader(
      HttpRequestHeader.POST,
      requestUri,
      HttpHeader.HTTP11
    );
    requestHeader.setHeader('Content-Type', 'application/x-www-form-urlencoded');
    requestHeader.setHeader('Accept', 'application/json');

    // Build the submission request message
    var msg = helper.prepareMessage();
    msg.setRequestHeader(requestHeader);
    msg.getRequestHeader().setContentLength(msg.getRequestBody().length());

    // Send the request message
    print('Sending ' + HttpRequestHeader.POST + ' request to ' + requestUri);
    helper.sendAndReceive(msg);
    print('Received response status code: ' + msg.getResponseHeader().getStatusCode());

    const parsedResponse = JSON.parse(msg.getResponseBody().toString());

    // Capture any of the tokens returned by the identity provider
    if (parsedResponse.access_token != undefined) {
        print('Authentication success. Access token = ' + parsedResponse.access_token)
        ScriptVars.setGlobalVar('accessToken', parsedResponse.access_token)
    }
    if (parsedResponse.id_token) {
        print('Authentication success. ID token = ' + parsedResponse.id_token)
        ScriptVars.setGlobalVar('idToken', parsedResponse.id_token)
    }
    if (parsedResponse.refresh_token) {
        print('Authentication success. Refresh token = ' + parsedResponse.refresh_token)
        ScriptVars.setGlobalVar('refreshToken', parsedResponse.refresh_token)
    }
    return msg;
}

// This function is called during the script loading to obtain a list of the names of the required configuration parameters,
// that will be shown in the Session Properties -> Authentication panel for configuration. They can be used
// to input dynamic data into the script, from the user interface (e.g. a login URL, name of POST parameters etc.)
function getRequiredParamsNames(){
    return ['IDP Token URL'];
}

// This function is called during the script loading to obtain a list of the names of the optional configuration parameters,
// that will be shown in the Session Properties -> Authentication panel for configuration. They can be used
// to input dynamic data into the script, from the user interface (e.g. a login URL, name of POST parameters etc.)
function getOptionalParamsNames(){
    return [];
}

// This function is called during the script loading to obtain a list of the names of the parameters that are required,
// as credentials, for each User configured corresponding to an Authentication using this script
function getCredentialsParamsNames(){
    return ['client id', 'client secret'];
}

// This optional function is called during the script loading to obtain the logged in indicator.
// NOTE: although optional this function must be implemented along with the function getLoggedOutIndicator().
//function getLoggedInIndicator() {
//  return "LoggedInIndicator";
//}

// This optional function is called during the script loading to obtain the logged out indicator.
// NOTE: although optional this function must be implemented along with the function getLoggedInIndicator().
//function getLoggedOutIndicator() {
//  return "LoggedOutIndicator";
//}
