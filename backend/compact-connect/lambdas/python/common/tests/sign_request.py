"""
Client Reference Implementation for HMAC Request Signing

This module provides a validated reference implementation for signing API requests
using ECDSA with SHA-256 as required by the CompactConnect HMAC authentication system.

The sign_request function in this module is tested and validated against the actual
authentication system, making it a reliable reference for client implementations.

For complete documentation, see: docs/client_hmac_auth.md
"""

import base64
from urllib.parse import quote

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec


def sign_request(method: str, path: str, query_params: dict, timestamp: str, nonce: str, private_key_pem: str) -> dict:
    """
    Sign a request using ECDSA with SHA-256.

    This function provides a reference implementation for clients to understand
    how to properly sign requests for the CompactConnect HMAC authentication system.

    The signature string is constructed as:
    HTTP_METHOD\nREQUEST_PATH\nSORTED_QUERY_PARAMETERS\nTIMESTAMP\nNONCE

    Where query parameters are sorted alphabetically and URL-encoded.

    :param method: HTTP method (e.g., 'GET', 'POST')
    :param path: Request path (e.g., '/v1/compacts/aslp/jurisdictions/al/providers/query')
    :param query_params: Dictionary of query parameters
    :param timestamp: ISO 8601 timestamp in UTC (e.g., '2024-01-15T10:30:00Z' or '2024-01-15T10:30:00+00:00')
    :param nonce: Unique nonce (e.g., UUID4 string)
    :param private_key_pem: PEM-encoded ECDSA private key
    :return: Dictionary containing headers to add to request
    """
    # Sort and URL-encode query parameters
    sorted_params = '&'.join(
        f'{quote(str(k), safe="")}={quote(str(v), safe="")}' for k, v in sorted(query_params.items())
    )

    # Create signature string
    signature_string = '\n'.join([method, path, sorted_params, timestamp, nonce])

    # Load private key
    private_key = serialization.load_pem_private_key(private_key_pem.encode(), password=None)

    # Sign the string using ECDSA
    signature = private_key.sign(signature_string.encode(), ec.ECDSA(hashes.SHA256()))

    # Return headers to add to request
    return {
        'X-Algorithm': 'ECDSA-SHA256',
        'X-Timestamp': timestamp,
        'X-Nonce': nonce,
        'X-Signature': base64.b64encode(signature).decode(),
    }
