# Client Signature Authentication

## Overview

The CompactConnect State-API implements a dual-authentication system for API access to sensitive licensure data. In
*addition* to OAuth2 client credentials authentication via Cognito User Pools, clients must also implement request
signing using ECDSA public/private key pairs.

## Purpose and Justification

### Why Dual Authentication?

The licensure data shared through CompactConnect contains highly sensitive personal information including:
- Last four of Social Security Numbers
- Personal addresses and contact information
- Professional license details
- Disciplinary actions

A single authentication mechanism creates a single point of failure. If OAuth2 credentials are compromised, an attacker
could potentially access protected data. The signature authentication layer provides:

- **Defense in depth**: Two independent authentication mechanisms must be compromised
- **Request integrity**: Each request is cryptographically signed, preventing tampering
- **Non-repudiation**: Only the holder of the private key could have signed the request
- **Replay attack prevention**: Timestamps and nonces prevent request reuse

## Authentication Modes

CompactConnect supports two authentication modes, which are implemented *in addition to the normal Oauth2
authentication, which is required on all State-API endpoints*:

1. **Required Signature Authentication**: Endpoints that always require valid signatures. If a state has no configured
   public key, they will not have access to these endpoints.
2. **Optional Signature Authentication**: Endpoints that require signatures only when a public key is configured for
   the compact/state combination (i.e. the POST license endpoint). If a state has no configured public key, they will
   still have access to this endpoint, however, once the state configures a public key, they will be required to include
   signatures to requests on these endpoints as well.

### Required Signature Authentication

State-API endpoints that read data _out_ of CompactConnect require signature authentication as an additional auth
factor. For endpoints that require signature authentication:

- A public key will need to be configured for each compact/state combination, before these endpoints will be accessible.
- All requests to these endpoints will be denied unless a public key is configured and valid signatures are present
  on the requests.

### Optional Signature Authentication

Other API endpoints in the State-API support optional signature authentication. For these endpoints:

- If no public key is configured for the compact/state combination, requests may proceed without signature validation
- If any public key is configured for the client's compact/state, signature authentication is enforced
- Optional signature auth allows for gradual rollout of signature authentication across different compacts and states
- Note that, when you are preparing to adopt signature authentication, you will want to start signing requests with
  _optional_ signatures _before_ you configure the public key with CompactConnect, because signature auth will be
  enforced as soon as the public key is configured in the system.

## Implementation of Signature Authentication

Signature authentication will require creating a private/public key pair, implementing the signing algorithm for all
requests to CompactConnect, then configuring the public key with CompactConnect, so that signatures can be validated.

### 1. Key Pair Generation

Generate an ECDSA key pair using the P-256 curve for your client (you may need to install openssl first, depending on
your operating system):

```bash
# Generate private key
openssl ecparam -genkey -name prime256v1 -noout -out client_private_key.pem

# Extract public key
openssl ec -in client_private_key.pem -pubout -out client_public_key.pub
```

#### Private Key Security
- Store private keys securely (HSM, key vault, encrypted storage)
- Implement key rotation procedures
- Never log or transmit private keys

**Important**: You will provide only the **public** key to CompactConnect during client registration.

### 2. Request Signing Process

For each API request, you must:

1. **Generate required values**:
   - Timestamp (ISO 8601 format): `2024-01-15T10:30:00Z` or `2024-01-15T10:30:00+00:00`
   - Nonce (unique UUID4 or random string): `550e8400-e29b-41d4-a716-446655440000`

2. **Create signature string** by joining these components with newlines (`\n`):
   ```text
   HTTP_METHOD
   REQUEST_PATH
   SORTED_QUERY_PARAMETERS
   TIMESTAMP
   NONCE
   KEY_ID
   ```

#### Canonical query string

- Percent-encode keys and values per RFC 3986 (space as %20, not +; do not encode unreserved characters).
- Sort first by key, then by value, using byte-order of the percent-encoded strings.
- Join as `key=value` pairs with `&` as the separator.
- If there are no query parameters, include an empty line (only `\n` in the signature string).

3. **Sign the string** using ECDSA with SHA-256. The signature format MUST be ASN.1 DER (most libraries produce DER by
   default).
4. **Base64-encode** the DER signature (do not hex-encode).
5. **Add required headers** to the request.

#### Required Headers

Every request to protected endpoints must include:

```http
Authorization: Bearer <oauth2_access_token>
X-Algorithm: ECDSA-SHA256
X-Timestamp: <iso8601_timestamp>
X-Nonce: <unique_nonce>
X-Key-Id: <key_identifier>
X-Signature: <base64_encoded_signature>
```

### 3. Configure the Public Key with CompactConnect

To configure your public key, contact the CompactConnect technical support team with:
- The **state and compact** this public key is for
- The **environment** the key is for
- The **public key data** in PEM format (it should start with `-----BEGIN PUBLIC KEY-----`). Sharing this key via normal
  communications channels is fine, since the _public_ key is not sensitive. *Do not share your **private** key with
  CompactConnect staff*.
- The **key id** you will reference this key with in your requests (and when coordinating future key rotations).

Once CompactConnect staff enter your public key into the system, signature validation will be enabled (and enforced
for *both required and optional signature auth endpoints*).

### Example Signature Implementation

We maintain an example implementation, which we use to test and validate our own authentication mechanism
[here](../lambdas/python/common/common_test/sign_request.py) and some example HTTP request data in a text file
[here](./signature_auth_examples.txt). You can use this as a reference for your
own implementation.

### Key Management

CompactConnect supports key rotation to allow clients to update their signing keys without downtime:

- **Key IDs**: Each public key is associated with a unique key ID that clients must include in the `X-Key-Id` header
- **Multiple Keys**: Clients can have multiple active keys simultaneously during rotation periods
- **Key Rollover**: When rotating keys, clients can continue using old keys while new keys are being validated

## Troubleshooting

### Timestamp Validation
- The API compares the signed timestamp header with server time as part of signature validation.
- Requests must be made within 1 minute of the signed timestamp, when received by the API.
- Use UTC time in ISO 8601 format (`2024-01-15T10:30:00Z` or `2024-01-15T10:30:00+00:00`).
- Ensure your system clock is synchronized and accurate as clock skew can cause validation to fail.

### Nonce Management
- Generate a unique nonce for each request
- UUIDs or cryptographically random strings are recommended
- **Never reuse nonces** - each nonce must be unique across requests
- Nonces can only contain alphanumeric characters (a-z, A-Z, 0-9) and hyphens (-)
- Nonces cannot be longer than 256 characters

### Other Common Issues
- **Query parameter ordering**: Parameters must be sorted alphabetically by key
- **Newline characters**: Use `\n` (LF) not `\r\n` (CRLF) in signature string
- **Encoding**: Use UTF-8 encoding for all string operations
- **Signature format**: Ensure proper ECDSA with SHA-256
- **Required headers**: Ensure you are including all required headers

### Testing Your Implementation

Use the provided beta environment to validate your signature implementation before production deployment.

## Support

For technical assistance with signature authentication implementation, contact the CompactConnect technical support team
with:
- Your client ID
- Sample signature strings (without private keys)
- Error messages or response codes
