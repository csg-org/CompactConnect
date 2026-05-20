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
 * State-api endpoints additionally require ECDSA-SHA256 request signatures on top of the
 * bearer token. When ZAP_STATE_SIGNATURE_PRIVATE_KEY and ZAP_STATE_SIGNATURE_KEY_ID are set,
 * every state-api request is signed per backend/compact-connect/docs/client_signature_auth.md;
 * otherwise state-api requests will 401 with "Missing required X-Key-Id header".
 *
 * Tokens come from env vars set by the workflow or manual-scan.sh:
 *   ZAP_AUTH_STAFF_TOKEN, ZAP_AUTH_PROVIDER_TOKEN, ZAP_AUTH_STATE_TOKEN,
 *   ZAP_STATE_SIGNATURE_PRIVATE_KEY (PKCS#8 PEM), ZAP_STATE_SIGNATURE_KEY_ID
 */

var HttpSender = Java.type('org.parosproxy.paros.network.HttpSender');
const System = Java.type('java.lang.System');
const Signature = Java.type('java.security.Signature');
const KeyFactory = Java.type('java.security.KeyFactory');
const PKCS8EncodedKeySpec = Java.type('java.security.spec.PKCS8EncodedKeySpec');
const Base64 = Java.type('java.util.Base64');
const UUID = Java.type('java.util.UUID');
const Instant = Java.type('java.time.Instant');
const ChronoUnit = Java.type('java.time.temporal.ChronoUnit');
const StandardCharsets = Java.type('java.nio.charset.StandardCharsets');
const URLEncoder = Java.type('java.net.URLEncoder');

const TOKENS = {
    staff: System.getenv('ZAP_AUTH_STAFF_TOKEN'),
    provider: System.getenv('ZAP_AUTH_PROVIDER_TOKEN'),
    state: System.getenv('ZAP_AUTH_STATE_TOKEN'),
};

const SIGNATURE_KEY_ID = System.getenv('ZAP_STATE_SIGNATURE_KEY_ID');
const SIGNATURE_PRIVATE_KEY = loadSignaturePrivateKey(System.getenv('ZAP_STATE_SIGNATURE_PRIVATE_KEY'));

const PROVIDER_PATH_PREFIX = /^\/v1\/(provider-users|purchases)(\/|$)/;
const PROVIDER_ATTESTATION_PATH = /^\/v1\/compacts\/[^\/]+\/attestations\/[^\/]+$/;

function classifyRequest(host, path) {
    if (host.indexOf('state-api.') === 0) return 'state';
    if (PROVIDER_PATH_PREFIX.test(path)) return 'provider';
    if (PROVIDER_ATTESTATION_PATH.test(path)) return 'provider';
    return 'staff';
}

function loadSignaturePrivateKey(pem) {
    if (!pem) return null;
    const body = String(pem)
        .replace(/-----BEGIN [^-]+-----/g, '')
        .replace(/-----END [^-]+-----/g, '')
        .replace(/\s+/g, '');
    try {
        const keyBytes = Base64.getDecoder().decode(body);
        const spec = new PKCS8EncodedKeySpec(keyBytes);
        return KeyFactory.getInstance('EC').generatePrivate(spec);
    } catch (e) {
        print('Failed to parse ZAP_STATE_SIGNATURE_PRIVATE_KEY (expected PKCS#8 PEM): ' + e);
        return null;
    }
}

function rfc3986Encode(s) {
    return String(URLEncoder.encode(s, 'UTF-8'))
        .replace(/\+/g, '%20')
        .replace(/\*/g, '%2A')
        .replace(/%7E/g, '~');
}

function canonicalQuery(rawQuery) {
    if (!rawQuery) return '';
    const pairs = [];
    const items = String(rawQuery).split('&');
    for (let i = 0; i < items.length; i++) {
        if (!items[i]) continue;
        const eq = items[i].indexOf('=');
        const k = eq >= 0 ? items[i].substring(0, eq) : items[i];
        const v = eq >= 0 ? items[i].substring(eq + 1) : '';
        // Decode any existing encoding, then re-encode per RFC 3986 so the canonical
        // form matches what the server recomputes. Fall back to raw on malformed input.
        let dk, dv;
        try { dk = decodeURIComponent(k); } catch (e) { dk = k; }
        try { dv = decodeURIComponent(v); } catch (e) { dv = v; }
        pairs.push({ k: rfc3986Encode(dk), v: rfc3986Encode(dv) });
    }
    pairs.sort((a, b) => (a.k < b.k ? -1 : a.k > b.k ? 1 : a.v < b.v ? -1 : a.v > b.v ? 1 : 0));
    return pairs.map((p) => p.k + '=' + p.v).join('&');
}

function signStateRequest(method, path, rawQuery) {
    if (!SIGNATURE_PRIVATE_KEY || !SIGNATURE_KEY_ID) return null;
    const timestamp = String(Instant.now().truncatedTo(ChronoUnit.SECONDS).toString());
    const nonce = String(UUID.randomUUID().toString());
    const stringToSign = [method, path, canonicalQuery(rawQuery), timestamp, nonce, SIGNATURE_KEY_ID].join('\n');
    const sig = Signature.getInstance('SHA256withECDSA');
    sig.initSign(SIGNATURE_PRIVATE_KEY);
    sig.update(String(stringToSign).getBytes(StandardCharsets.UTF_8));
    return {
        'X-Algorithm': 'ECDSA-SHA256',
        'X-Timestamp': timestamp,
        'X-Nonce': nonce,
        'X-Key-Id': SIGNATURE_KEY_ID,
        'X-Signature': String(Base64.getEncoder().encodeToString(sig.sign())),
    };
}

function sendingRequest(msg, initiator, helper) {
    if (initiator === HttpSender.AUTHENTICATION_INITIATOR || !msg.isInScope()) return;

    const uri = msg.getRequestHeader().getURI();
    const host = String(uri.getHost());
    const path = String(uri.getPath());
    const kind = classifyRequest(host, path);
    const token = TOKENS[kind];

    if (!token) {
        print('No ' + kind + ' token available for ' + uri.toString());
        return;
    }
    msg.getRequestHeader().setHeader('Authorization', 'Bearer ' + token);

    // State API requires ECDSA signature headers in addition to the bearer token.
    // See backend/compact-connect/docs/client_signature_auth.md and owasp-zap/README.md.
    if (kind === 'state') {
        const method = String(msg.getRequestHeader().getMethod());
        const rawQuery = uri.getQuery();
        const sigHeaders = signStateRequest(method, path, rawQuery == null ? '' : String(rawQuery));
        if (sigHeaders) {
            for (const name in sigHeaders) {
                msg.getRequestHeader().setHeader(name, sigHeaders[name]);
            }
        }
    }
}

function responseReceived(msg, initiator, helper) {
    const statusCode = msg.getResponseHeader().getStatusCode();
    print(
        statusCode,
        msg.getRequestHeader().getMethod(),
        msg.getRequestHeader().getURI().toString()
    );
    // To debug auth issues, uncomment this for a hint
    // if (statusCode === 401 || statusCode == 403 ) {
    //     print('Request header:', msg.getRequestHeader().getHeader('Authorization').substring(0, 16));
    //     print('Response body:', msg.getResponseBody().toString());
    // }
}
