# Client DSA Authentication

## Overview

CompactConnect implements a dual-authentication system for API access to sensitive licensure data. In addition to OAuth2 client credentials authentication via Cognito User Pools, clients must also implement DSA-based request signing using ECDSA public/private key pairs.

## Purpose and Justification

### Why Dual Authentication?

The licensure data shared through CompactConnect contains highly sensitive personal information including:
- Partial Social Security Numbers
- Personal addresses and contact information
- Professional license details
- Disciplinary actions

A single authentication mechanism creates a single point of failure. If OAuth2 credentials are compromised, an attacker could potentially access all protected data. The DSA authentication layer provides:

- **Defense in depth**: Two independent authentication mechanisms must be compromised
- **Request integrity**: Each request is cryptographically signed, preventing tampering
- **Non-repudiation**: Only the holder of the private key could have signed the request
- **Replay attack prevention**: Timestamps and nonces prevent request reuse

### Regulatory Compliance

This dual authentication approach helps meet regulatory requirements for protecting sensitive healthcare and professional licensing data by implementing multiple layers of security controls.

## Implementation Requirements

### Authentication Modes

CompactConnect supports two authentication modes:

1. **Required DSA Authentication** (`@dsa_auth_required`): Endpoints that always require valid DSA signatures
2. **Optional DSA Authentication** (`@optional_dsa_auth`): Endpoints that require DSA signatures only when a public key is configured for the compact/state combination

### 1. Key Pair Generation

Generate an ECDSA key pair using the P-256 curve for your client (you may need to install openssl first, depending on your operating system):

```bash
# Generate private key
openssl ecparam -genkey -name prime256v1 -noout -out client_private_key.pem

# Extract public key
openssl ec -in client_private_key.pem -pubout -out client_public_key.pub
```

**Important**: Store the private key securely and never share it. You will provide only the public key to CompactConnect during client registration.

### 2. Request Signing Process

For each API request, you must:

1. **Generate required values**:
   - Timestamp (ISO 8601 format): `2024-01-15T10:30:00Z` or `2024-01-15T10:30:00+00:00`
   - Nonce (UUID4 or random string): `550e8400-e29b-41d4-a716-446655440000`

2. **Create signature string** by joining these components with newlines (`\n`):
   ```text
   HTTP_METHOD
   REQUEST_PATH
   SORTED_QUERY_PARAMETERS
   TIMESTAMP
   NONCE
   KEY_ID
   ```

3. **Sign the string** using ECDSA with SHA-256
4. **Base64 encode** the signature
5. **Add headers** to your request

### 3. Required Headers

Every request to protected endpoints must include:

```http
Authorization: Bearer <oauth2_access_token>
X-Algorithm: ECDSA-SHA256
X-Timestamp: <iso8601_timestamp>
X-Nonce: <unique_nonce>
X-Key-Id: <key_identifier>
X-Signature: <base64_encoded_signature>
```

### 4. Example Implementation

#### Python Example

We maintain an example implementation, which we use to test and validate our own authentication mechanism
[here](../lambdas/python/common/common_test/sign_request.py). You can use this as a reference for your own
implementation.


## Security Considerations

### Timestamp Validation
- Requests must be made within 1 minute of the timestamp
- Use UTC time in ISO 8601 format (`2024-01-15T10:30:00Z` or `2024-01-15T10:30:00+00:00`)
- Ensure your system clock is synchronized

### Nonce Management
- Generate a unique nonce for each request
- UUIDs or cryptographically random strings are recommended
- Do not reuse nonces within the timestamp window

### Private Key Security
- Store private keys securely (HSM, key vault, encrypted storage)
- Implement key rotation procedures
- Never log or transmit private keys
- Use appropriate file permissions (600) on key files

### Error Handling
- Authentication failures will return HTTP 401 or 403
- Check both OAuth2 token validity and DSA signature
- Implement retry logic with exponential backoff

## Client Registration

To implement DSA authentication:

1. **Receive client credentials and test your client credentials grant flow**
   [See here for more](../app_clients/it_staff_onboarding_instructions/README.md).
2. **Generate your ECDSA key pair** as described above
3. **Provide your public key and key ID** (not the private key) to CompactConnect staff during registration
4. **Test your implementation** against the beta environment

### Key Management

CompactConnect supports key rotation to allow clients to update their signing keys without downtime:

- **Key IDs**: Each public key is associated with a unique key ID that clients must include in the `X-Key-Id` header
- **Multiple Keys**: Clients can have multiple active keys simultaneously during rotation periods
- **Key Rollover**: When rotating keys, clients can continue using old keys while new keys are being validated
- **Database Schema**: Keys are stored with the pattern `pk: <compact>#DSA_KEYS`, `sk: <compact>#JURISDICTION#<jurisdiction>#<key-id>`

## Troubleshooting

### Common Issues

- **Clock skew**: Ensure system time is accurate (use NTP)
- **Timestamp format**: Both `Z` and `+00:00` UTC suffixes are supported
- **Query parameter ordering**: Parameters must be sorted alphabetically by key
- **Newline characters**: Use `\n` (LF) not `\r\n` (CRLF) in signature string
- **Encoding**: Use UTF-8 encoding for all string operations
- **Signature format**: Ensure proper ECDSA with SHA-256
- **Algorithm header**: Must specify `ECDSA-SHA256` in X-Algorithm header
- **Key ID header**: Must include `X-Key-Id` header with a valid key identifier

### Testing Your Implementation

Use the provided test vectors and sandbox environment to validate your DSA implementation before production deployment.

### Optional DSA Authentication

For endpoints that support optional DSA authentication:

- If no public key is configured for the compact/state combination, requests proceed without DSA validation
- If a public key is configured, full DSA validation is enforced
- This allows for gradual rollout of DSA authentication across different compacts and states

## Support

For technical assistance with DSA authentication implementation, contact the CompactConnect technical support team with:
- Your client ID
- Sample signature strings (without private keys)
- Error messages or response codes
- Programming language and library versions
