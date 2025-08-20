"""
HMAC Authentication Module

This module provides decorators for validating ECDSA-based request signatures
as described in the client_hmac_auth.md documentation.
"""

import base64
from collections.abc import Callable
from datetime import UTC, datetime
from functools import wraps
from typing import Any
from urllib.parse import quote

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

from cc_common.config import config, logger
from cc_common.exceptions import CCInvalidRequestException, CCUnauthorizedException
from cc_common.utils import CaseInsensitiveDict


def hmac_auth_required(fn: Callable) -> Callable:
    """
    Decorator to validate HMAC signatures for API requests.

    This decorator validates ECDSA signatures according to the specification:
    - Extracts required headers (X-Algorithm, X-Timestamp, X-Nonce, X-Signature)
    - Validates timestamp is within 5 minutes
    - Reconstructs signature string from request components
    - Verifies signature using public key from DynamoDB
    - Raises appropriate exceptions for validation failures

    :param fn: The function to decorate
    :return: Decorated function
    """

    @wraps(fn)
    def validate_signature(event: dict, context: Any) -> Any:
        # Extract headers using CaseInsensitiveDict for consistent handling
        headers = CaseInsensitiveDict(event.get('headers') or {})

        # Extract required HMAC headers
        algorithm = headers.get('X-Algorithm')
        timestamp_str = headers.get('X-Timestamp')
        nonce = headers.get('X-Nonce')
        signature_b64 = headers.get('X-Signature')

        # Validate all required headers are present
        if not all([algorithm, timestamp_str, nonce, signature_b64]):
            logger.warning(
                'Missing required HMAC headers',
                algorithm=algorithm,
                timestamp=timestamp_str,
                nonce=nonce,
                signature_present=bool(signature_b64),
            )
            raise CCUnauthorizedException('Missing required HMAC authentication headers')

        # Validate algorithm
        if algorithm != 'ECDSA-SHA256':
            logger.warning('Unsupported HMAC algorithm', algorithm=algorithm)
            raise CCUnauthorizedException('Unsupported signature algorithm')

        # Validate timestamp
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
            now = datetime.now(UTC)
            time_diff = abs((timestamp - now).total_seconds())

            if time_diff > 300:  # 5 minutes
                logger.warning(
                    'Request timestamp too old or in future', timestamp=timestamp_str, time_diff_seconds=time_diff
                )
                raise CCUnauthorizedException('Request timestamp is too old or in the future')
        except ValueError as e:
            logger.warning('Invalid timestamp format', timestamp=timestamp_str, error=str(e))
            raise CCInvalidRequestException('Invalid timestamp format') from e

        # Extract compact and jurisdiction from path parameters
        path_params = event.get('pathParameters') or {}
        compact = path_params.get('compact')
        jurisdiction = path_params.get('jurisdiction')

        if not compact or not jurisdiction:
            logger.error('Missing compact or jurisdiction in path parameters', path_params=path_params)
            raise CCInvalidRequestException('Missing compact or jurisdiction parameters')

        # Get public key from DynamoDB
        public_key_pem = _get_public_key_from_dynamodb(compact, jurisdiction)
        if not public_key_pem:
            logger.error('Public key not found for compact/jurisdiction', compact=compact, jurisdiction=jurisdiction)
            raise CCUnauthorizedException('Public key not found for this compact/jurisdiction')

        # Reconstruct signature string
        signature_string = _build_signature_string(event)

        # Verify signature
        if not _verify_signature(signature_string, signature_b64, public_key_pem):
            logger.warning('Invalid signature for request', compact=compact, jurisdiction=jurisdiction)
            raise CCUnauthorizedException('Invalid request signature')

        logger.info('HMAC signature validated successfully', compact=compact, jurisdiction=jurisdiction)

        return fn(event, context)

    return validate_signature


def _get_public_key_from_dynamodb(compact: str, jurisdiction: str) -> str | None:
    """
    Retrieve the public key for a compact/jurisdiction combination from DynamoDB.

    :param compact: The compact abbreviation
    :param jurisdiction: The jurisdiction abbreviation
    :return: PEM-encoded public key or None if not found
    """
    # Query the compact configuration table for the public key
    # Assuming the key is stored with pk=f"HMAC_KEYS#{compact}" and sk=f"{jurisdiction}"
    response = config.compact_configuration_table.get_item(Key={'pk': f'HMAC_KEYS#{compact}', 'sk': jurisdiction})

    return response.get('Item', {}).get('publicKey')


def _build_signature_string(event: dict) -> str:
    """
    Build the signature string according to the HMAC specification.

    The signature string is constructed as:
    HTTP_METHOD\nREQUEST_PATH\nSORTED_QUERY_PARAMETERS\nTIMESTAMP\nNONCE

    :param event: API Gateway event
    :return: Signature string
    """
    # Extract components
    http_method = event.get('httpMethod', '')
    path = event.get('path', '')

    # Handle query parameters
    query_params = event.get('queryStringParameters') or {}
    sorted_params = '&'.join(
        f'{quote(str(k), safe="")}={quote(str(v), safe="")}' for k, v in sorted(query_params.items())
    )

    # Extract timestamp and nonce from headers
    headers = CaseInsensitiveDict(event.get('headers') or {})
    timestamp = headers.get('X-Timestamp', '')
    nonce = headers.get('X-Nonce', '')

    # Build signature string with newlines
    return '\n'.join([http_method, path, sorted_params, timestamp, nonce])


def _verify_signature(signature_string: str, signature_b64: str, public_key_pem: str) -> bool:
    """
    Verify the ECDSA signature using the provided public key.

    :param signature_string: The string that was signed
    :param signature_b64: Base64-encoded signature
    :param public_key_pem: PEM-encoded public key
    :return: True if signature is valid, False otherwise
    """
    try:
        # Load the public key
        public_key = serialization.load_pem_public_key(public_key_pem.encode())

        # Decode the signature
        signature_bytes = base64.b64decode(signature_b64)

        # Parse the signature (DSS format)
        r, s = decode_dss_signature(signature_bytes)

        # Verify the signature
        public_key.verify(signature_bytes, signature_string.encode(), ec.ECDSA(hashes.SHA256()))

        return True
    except InvalidSignature:
        logger.debug('Signature verification failed - invalid signature')
        return False
