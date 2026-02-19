"""
Signature Authentication Module

This module provides decorators for validating ECDSA-based request signatures.
"""

import base64
from collections.abc import Callable
from datetime import UTC, datetime
from functools import wraps
from typing import Any
from urllib.parse import quote

from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from cc_common.config import config, logger
from cc_common.exceptions import (
    CCInvalidRequestException,
    CCUnauthorizedCustomResponseException,
    CCUnauthorizedException,
)
from cc_common.utils import CaseInsensitiveDict


def required_signature_auth(fn: Callable) -> Callable:
    """
    Decorator to validate signatures for API requests.

    This decorator validates ECDSA signatures according to the specification:
    - Extracts required headers (X-Algorithm, X-Timestamp, X-Nonce, X-Signature, X-Key-Id)
    - Validates timestamp is within configurable max clock skew
    - Reconstructs signature string from request components
    - Verifies signature using public key from DynamoDB
    - Raises appropriate exceptions for validation failures

    :param fn: The function to decorate
    :return: Decorated function
    """

    @wraps(fn)
    def validate_signature(event: dict, context: Any) -> Any:
        # Extract compact and jurisdiction from path parameters
        compact, jurisdiction = _extract_path_parameters(event)

        # Extract key ID from headers (required)
        key_id = _extract_key_id(event)
        if not key_id:
            logger.warning('Missing X-Key-Id header', compact=compact, jurisdiction=jurisdiction)
            raise CCUnauthorizedCustomResponseException('Missing required X-Key-Id header')

        # Get public key from DynamoDB (required)
        public_key_pem = _get_public_key_from_dynamodb(compact, jurisdiction, key_id)
        if not public_key_pem:
            logger.warning(
                'Public key not found for compact/jurisdiction/key_id',
                compact=compact,
                jurisdiction=jurisdiction,
                key_id=key_id,
            )
            raise CCUnauthorizedCustomResponseException('Public key not found for this compact/jurisdiction/key-id')

        # Validate signature
        _validate_signature(event, compact, jurisdiction, public_key_pem)

        logger.info('Signature validated successfully', compact=compact, jurisdiction=jurisdiction, key_id=key_id)
        return fn(event, context)

    return validate_signature


def optional_signature_auth(fn: Callable) -> Callable:
    """
    Decorator for optional signature validation.

    This decorator checks if signature keys are configured for the compact/state combination.
    If keys are configured and X-Key-Id is provided, it enforces signature validation.
    If no keys are configured, it allows the request to proceed without signature validation.
    If keys are configured but no X-Key-Id is provided, access is denied.

    This is useful for endpoints that support both signature-authenticated and Oauth-only access,
    where the authentication requirement is determined by whether signature keys are configured.

    :param fn: The function to decorate
    :return: Decorated function
    """

    @wraps(fn)
    def validate_optional_signature(event: dict, context: Any) -> Any:
        # Extract compact and jurisdiction from path parameters
        compact, jurisdiction = _extract_path_parameters(event)

        # Get all configured keys for this compact/jurisdiction in a single query
        configured_keys = _get_configured_keys_for_jurisdiction(compact, jurisdiction)

        if not configured_keys:
            # No keys configured - allow request to proceed without signature validation
            logger.info(
                'No signature keys configured for compact/jurisdiction - proceeding without signature validation',
                compact=compact,
                jurisdiction=jurisdiction,
            )
            return fn(event, context)

        # Keys are configured - check if X-Key-Id is provided
        key_id = _extract_key_id(event)
        if not key_id:
            logger.warning(
                'Signature keys configured but no X-Key-Id provided - denying access',
                compact=compact,
                jurisdiction=jurisdiction,
            )
            raise CCUnauthorizedCustomResponseException('X-Key-Id header required when signature keys are configured')

        # Get public key for the specific key ID from our cached keys
        public_key_pem = configured_keys.get(key_id)
        if not public_key_pem:
            logger.warning(
                'Public key not found for compact/jurisdiction/key_id',
                compact=compact,
                jurisdiction=jurisdiction,
                key_id=key_id,
            )
            raise CCUnauthorizedCustomResponseException('Public key not found for this compact/jurisdiction/key-id')

        # Validate signature
        _validate_signature(event, compact, jurisdiction, public_key_pem)

        logger.info(
            'Optional signature validated successfully', compact=compact, jurisdiction=jurisdiction, key_id=key_id
        )
        return fn(event, context)

    return validate_optional_signature


def _extract_path_parameters(event: dict) -> tuple[str, str]:
    """
    Extract compact and jurisdiction from path parameters.

    :param event: API Gateway event
    :return: Tuple of (compact, jurisdiction)
    :raises CCInvalidRequestException: If compact or jurisdiction is missing
    """
    path_params = event.get('pathParameters') or {}
    compact = path_params.get('compact')
    jurisdiction = path_params.get('jurisdiction')

    if not compact or not jurisdiction:
        logger.error('Missing compact or jurisdiction in path parameters', path_params=path_params)
        raise CCInvalidRequestException('Missing compact or jurisdiction parameters')

    return compact, jurisdiction


def _extract_key_id(event: dict) -> str | None:
    """
    Extract key ID from request headers.

    :param event: API Gateway event
    :return: Key ID or None if not present
    """
    headers = CaseInsensitiveDict(event.get('headers') or {})
    return headers.get('X-Key-Id')


def _validate_nonce_format(nonce: str) -> None:
    """
    Validate that a nonce contains only alphanumeric characters and hyphens, and is not longer than 256 characters.

    :param nonce: The nonce to validate
    :raises CCInvalidRequestException: If the nonce format is invalid
    """
    if not nonce:
        raise CCUnauthorizedCustomResponseException('Nonce cannot be empty')

    if len(nonce) > 256:
        logger.warning('Nonce too long', nonce_length=len(nonce), max_length=256)
        raise CCUnauthorizedCustomResponseException('Nonce cannot be longer than 256 characters')

    # Check that nonce contains only alphanumeric characters and hyphens
    import re

    if not re.match(r'^[a-zA-Z0-9-]+$', nonce):
        logger.warning('Invalid nonce format - contains invalid characters', nonce=nonce)
        raise CCUnauthorizedCustomResponseException('Nonce can only contain alphanumeric characters and hyphens')


def _validate_signature(event: dict, compact: str, jurisdiction: str, public_key_pem: str) -> None:
    """
    Validate signature for a request.

    This function performs all the signature validation steps:
    - Extracts and validates required headers
    - Validates timestamp
    - Reconstructs and verifies signature

    :param event: API Gateway event
    :param compact: Compact abbreviation
    :param jurisdiction: Jurisdiction abbreviation
    :param public_key_pem: PEM-encoded public key
    :raises CCUnauthorizedException: If signature validation fails
    """
    # Extract headers using CaseInsensitiveDict for consistent handling
    headers = CaseInsensitiveDict(event.get('headers') or {})

    # Extract required signature headers
    algorithm = headers.get('X-Algorithm')
    timestamp_str = headers.get('X-Timestamp')
    nonce = headers.get('X-Nonce')
    signature_b64 = headers.get('X-Signature')
    key_id = headers.get('X-Key-Id')

    # Validate all required headers are present
    if not all([algorithm, timestamp_str, nonce, signature_b64, key_id]):
        logger.warning(
            'Missing required signature headers',
            algorithm=algorithm,
            timestamp=timestamp_str,
            nonce=nonce,
            signature_present=bool(signature_b64),
            key_id=key_id,
            compact=compact,
            jurisdiction=jurisdiction,
        )
        raise CCUnauthorizedCustomResponseException('Missing required signature authentication headers')

    # Validate nonce format (before we try to calculate the signature string)
    _validate_nonce_format(nonce)

    # Validate algorithm
    if algorithm != 'ECDSA-SHA256':
        logger.warning(
            'Unsupported signature algorithm', algorithm=algorithm, compact=compact, jurisdiction=jurisdiction
        )
        raise CCUnauthorizedCustomResponseException('Unsupported signature algorithm')

    # Validate timestamp
    try:
        timestamp = datetime.fromisoformat(timestamp_str)
        if timestamp.tzinfo is None:
            # Treat naive timestamps as UTC to avoid mismatched aware vs naive comparisons
            timestamp = timestamp.replace(tzinfo=UTC)
        now = config.current_standard_datetime
        time_diff = abs((timestamp - now).total_seconds())

        if time_diff > config.signature_max_clock_skew_seconds:
            logger.warning(
                'Request timestamp too old or too far in the future',
                timestamp=timestamp_str,
                time_diff_seconds=time_diff,
                max_clock_skew_seconds=config.signature_max_clock_skew_seconds,
            )
            raise CCUnauthorizedCustomResponseException('Request timestamp is too old or too far in the future')
    except ValueError as e:
        logger.warning('Invalid timestamp format', timestamp=timestamp_str, error=str(e))
        raise CCUnauthorizedCustomResponseException('Invalid timestamp format') from e

    # Reconstruct signature string
    signature_string = _build_signature_string(event)

    # Verify signature
    if not _verify_signature(signature_string, signature_b64, public_key_pem):
        logger.warning('Invalid signature for request', compact=compact, jurisdiction=jurisdiction)
        raise CCUnauthorizedCustomResponseException('Invalid request signature')

    # Validate and store nonce to prevent reuse
    _validate_and_store_nonce(compact, jurisdiction, nonce)


def _get_public_key_from_dynamodb(compact: str, jurisdiction: str, key_id: str) -> str | None:
    """
    Retrieve the public key for a compact/jurisdiction/key_id combination from DynamoDB.

    :param compact: The compact abbreviation
    :param jurisdiction: The jurisdiction abbreviation
    :param key_id: The key ID
    :return: PEM-encoded public key or None if not found
    """
    # Query the compact configuration table for the public key
    response = config.compact_configuration_table.get_item(
        Key={'pk': f'{compact}#SIGNATURE_KEYS#{jurisdiction}', 'sk': f'{compact}#JURISDICTION#{jurisdiction}#{key_id}'}
    )

    return response.get('Item', {}).get('publicKey')


def _get_configured_keys_for_jurisdiction(compact: str, jurisdiction: str) -> dict[str, str]:
    """
    Retrieve all configured signature keys for a specific jurisdiction.

    This function queries DynamoDB to get all key IDs and their corresponding public keys
    for a given compact and jurisdiction. It returns a dictionary mapping key_id to public_key_pem.

    :param compact: The compact abbreviation
    :param jurisdiction: The jurisdiction abbreviation
    :return: Dictionary of key_id to public_key_pem
    """
    # Query for all keys with the jurisdiction prefix
    response = config.compact_configuration_table.query(
        KeyConditionExpression=Key('pk').eq(f'{compact}#SIGNATURE_KEYS#{jurisdiction}')
        & Key('sk').begins_with(f'{compact}#JURISDICTION#{jurisdiction}#'),
    )

    configured_keys: dict[str, str] = {}
    for item in response.get('Items', []):
        key_id = item['sk'].split('#')[-1]  # Extract key_id from sk
        public_key_pem = item['publicKey']
        configured_keys[key_id] = public_key_pem

    return configured_keys


def _build_signature_string(event: dict) -> str:
    """
    Build the signature string according to the signature specification.

    The signature string is constructed as:
    HTTP_METHOD\nREQUEST_PATH\nSORTED_QUERY_PARAMETERS\nTIMESTAMP\nNONCE\nKEY_ID

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

    # Extract timestamp, nonce, and key_id from headers
    headers = CaseInsensitiveDict(event.get('headers') or {})
    timestamp = headers.get('X-Timestamp', '')
    nonce = headers.get('X-Nonce', '')
    key_id = headers.get('X-Key-Id', '')

    # Build signature string with newlines
    return '\n'.join([http_method, path, sorted_params, timestamp, nonce, key_id])


def _validate_and_store_nonce(compact: str, jurisdiction: str, nonce: str) -> None:
    """
    Validate that a nonce has not been used before and store it to prevent reuse.

    This function uses a conditional write to DynamoDB to atomically check if the nonce
    already exists and store it if it doesn't. If the nonce already exists, it raises
    a CCUnauthorizedException.

    :param compact: The compact abbreviation
    :param jurisdiction: The jurisdiction abbreviation
    :param nonce: The nonce to validate and store
    :raises CCUnauthorizedException: If the nonce has already been used
    """
    try:
        # Calculate TTL based on 3x the configured signature clock skew
        ttl = int(config.current_standard_datetime.timestamp()) + (3 * config.signature_max_clock_skew_seconds)

        # Attempt to store the nonce with a condition that it doesn't already exist
        config.rate_limiting_table.put_item(
            Item={
                'pk': f'NONCE#{compact}#JURISDICTION#{jurisdiction}',
                'sk': f'NONCE#{nonce}',
                'ttl': ttl,
            },
            ConditionExpression=Attr('pk').not_exists() & Attr('sk').not_exists(),
        )

        logger.debug('Nonce stored successfully', compact=compact, jurisdiction=jurisdiction, nonce=nonce)

    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            logger.warning(
                'Nonce reuse detected',
                compact=compact,
                jurisdiction=jurisdiction,
                nonce=nonce,
            )
            raise CCUnauthorizedCustomResponseException('Nonce has already been used') from e
        logger.error('Failed to validate nonce', error=str(e), compact=compact, jurisdiction=jurisdiction)
        raise CCUnauthorizedException('Failed to validate nonce') from e


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

        # Verify the signature
        public_key.verify(signature_bytes, signature_string.encode(), ec.ECDSA(hashes.SHA256()))

        return True
    except (InvalidSignature, ValueError):
        logger.debug('Signature verification failed - invalid signature or format')
        return False
