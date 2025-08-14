# Client HMAC Authentication

## Overview

CompactConnect implements a dual-authentication system for API access to sensitive licensure data. In addition to OAuth2 client credentials authentication via Cognito User Pools, clients must also implement HMAC-based request signing using ECDSA public/private key pairs.

## Purpose and Justification

### Why Dual Authentication?

The licensure data shared through CompactConnect contains highly sensitive personal information including:
- Partial Social Security Numbers
- Personal addresses and contact information
- Professional license details
- Disciplinary actions

A single authentication mechanism creates a single point of failure. If OAuth2 credentials are compromised, an attacker could potentially access all protected data. The HMAC authentication layer provides:

- **Defense in depth**: Two independent authentication mechanisms must be compromised
- **Request integrity**: Each request is cryptographically signed, preventing tampering
- **Non-repudiation**: Only the holder of the private key could have signed the request
- **Replay attack prevention**: Timestamps and nonces prevent request reuse

### Regulatory Compliance

This dual authentication approach helps meet regulatory requirements for protecting sensitive healthcare and professional licensing data by implementing multiple layers of security controls.

## Implementation Requirements

### 1. Key Pair Generation

Generate an ECDSA key pair using the P-256 curve for your client:

```bash
# Generate private key
openssl ecparam -genkey -name prime256v1 -noout -out client_private_key.pem

# Extract public key
openssl ec -in client_private_key.pem -pubout -out client_public_key.pem
```

**Important**: Store the private key securely and never share it. You will provide only the public key to CompactConnect during client registration.

### 2. Request Signing Process

For each API request, you must:

1. **Generate required values**:
   - Timestamp (ISO 8601 format): `2024-01-15T10:30:00Z`
   - Nonce (UUID4 or random string): `550e8400-e29b-41d4-a716-446655440000`

2. **Create signature string** by joining these components with newlines (`\n`):
   ```
   HTTP_METHOD
   REQUEST_PATH
   SORTED_QUERY_PARAMETERS
   TIMESTAMP
   NONCE
   ```

3. **Sign the string** using ECDSA with SHA-256
4. **Base64 encode** the signature
5. **Add headers** to your request

### 3. Required Headers

Every request to protected endpoints must include:

```
Authorization: Bearer <oauth2_access_token>
X-Algorithm: ECDSA-SHA256
X-Timestamp: <iso8601_timestamp>
X-Nonce: <unique_nonce>
X-Signature: <base64_encoded_signature>
```

### 4. Example Implementation

#### Python Example

```python
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
import base64
import uuid
from datetime import datetime

def sign_request(method, path, query_params, private_key_pem):
    # Generate timestamp and nonce
    timestamp = datetime.utcnow().isoformat() + 'Z'
    nonce = str(uuid.uuid4())

    # Sort query parameters
    sorted_params = "&".join(f"{k}={v}" for k, v in sorted(query_params.items()))

    # Create signature string
    signature_string = "\n".join([
        method,
        path,
        sorted_params,
        timestamp,
        nonce
    ])

    # Load private key
    private_key = serialization.load_pem_private_key(
        private_key_pem.encode(),
        password=None
    )

    # Sign the string using ECDSA
    signature = private_key.sign(
        signature_string.encode(),
        ec.ECDSA(hashes.SHA256())
    )

    # Return headers to add to request
    return {
        'X-Algorithm': 'ECDSA-SHA256',
        'X-Timestamp': timestamp,
        'X-Nonce': nonce,
        'X-Signature': base64.b64encode(signature).decode()
    }

# Usage
headers = sign_request(
    'GET',
    '/v1/compacts/aslp/jurisdictions/co/providers/query',
    {'pageSize': '50', 'startDateTime': '2024-01-01T00:00:00Z'},
    private_key_pem
)
```



## Security Considerations

### Timestamp Validation
- Requests must be made within 5 minutes of the timestamp
- Use UTC time in ISO 8601 format
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
- Check both OAuth2 token validity and HMAC signature
- Implement retry logic with exponential backoff

## Client Registration

To implement HMAC authentication:

1. **Receive client credentials and test your client credentials grant flow**
   [See here for more](../app_clients/it_staff_onboarding_instructions/README.md).
2. **Generate your RSA key pair** as described above
3. **Provide your public key** (not the private key) to CompactConnect staff during registration
4. **Test your implementation** against the beta environment

## Troubleshooting

### Common Issues

- **Clock skew**: Ensure system time is accurate (use NTP)
- **Query parameter ordering**: Parameters must be sorted alphabetically by key
- **Newline characters**: Use `\n` (LF) not `\r\n` (CRLF) in signature string
- **Encoding**: Use UTF-8 encoding for all string operations
- **Signature format**: Ensure proper ECDSA with SHA-256
- **Algorithm header**: Must specify `ECDSA-SHA256` in X-Algorithm header

### Testing Your Implementation

Use the provided test vectors and sandbox environment to validate your HMAC implementation before production deployment.

## Support

For technical assistance with HMAC authentication implementation, contact the CompactConnect technical support team with:
- Your client ID
- Sample signature strings (without private keys)
- Error messages or response codes
- Programming language and library versions
