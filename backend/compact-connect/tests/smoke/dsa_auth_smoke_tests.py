#!/usr/bin/env python3
# ruff: noqa: T201  we use print statements for smoke testing
import os
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import boto3
import requests
from botocore.exceptions import ClientError
from config import logger
from smoke_common import (
    SmokeTestFailureException,
    config,
    load_smoke_test_env,
)

# Add the common library path to import the sign_request function
common_lib_path = os.path.join('lambdas', 'python', 'common')
sys.path.append(common_lib_path)

# Import the sign_request function from the common library
from common_test.sign_request import sign_request  # noqa: E402

COMPACT = 'aslp'
JURISDICTION = 'ne'
TEST_CLIENT_NAME = 'test-dsa-auth-client'
TEST_KEY_ID = 'test-dsa-key-001'

# This script can be run locally to test the DSA authentication flow against a sandbox environment
# of the Compact Connect State API.
# To run this script, create a smoke_tests_env.json file in the same directory as this script using the
# 'smoke_tests_env_example.json' file as a template.


def get_compact_configuration_table():
    """Get the compact configuration DynamoDB table."""
    return config.compact_configuration_dynamodb_table


def get_state_api_base_url():
    """Get the state API base URL from config."""
    return config.state_api_base_url


def get_state_auth_url():
    """Get the state auth URL from config."""
    return config.state_auth_url


def create_test_app_client():
    """
    Create a test app client in Cognito for DSA authentication testing.

    :return: Dictionary containing client_id and client_secret
    """
    logger.info(f'Creating test app client: {TEST_CLIENT_NAME}')

    try:
        cognito_client = boto3.client('cognito-idp')

        # Create the user pool client
        response = cognito_client.create_user_pool_client(
            UserPoolId=config.cognito_state_auth_user_pool_id,
            ClientName=TEST_CLIENT_NAME,
            PreventUserExistenceErrors='ENABLED',
            GenerateSecret=True,
            TokenValidityUnits={'AccessToken': 'minutes'},
            AccessTokenValidity=15,
            AllowedOAuthFlowsUserPoolClient=True,
            AllowedOAuthFlows=['client_credentials'],
            AllowedOAuthScopes=[f'{COMPACT}/readGeneral', f'{JURISDICTION}/{COMPACT}.write'],
        )

        user_pool_client = response.get('UserPoolClient', {})
        client_id = user_pool_client.get('ClientId')
        client_secret = user_pool_client.get('ClientSecret')

        if not client_id or not client_secret:
            raise SmokeTestFailureException('Failed to extract client ID or secret from AWS response')

        logger.info(f'Successfully created test app client with ID: {client_id}')
        return {'client_id': client_id, 'client_secret': client_secret}

    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.error(f'Failed to create app client: {error_code} - {error_message}')
        raise SmokeTestFailureException(f'Failed to create app client: {error_code} - {error_message}') from e


def delete_test_app_client(client_id: str):
    """Delete the test app client from Cognito."""
    try:
        cognito_client = boto3.client('cognito-idp')
        cognito_client.delete_user_pool_client(UserPoolId=config.cognito_state_auth_user_pool_id, ClientId=client_id)
        logger.info(f'Successfully deleted test app client: {client_id}')
    except ClientError as e:
        logger.error(f'Failed to delete app client {client_id}: {str(e)}')
        # Don't raise here as this is cleanup


def get_client_credentials_token(client_id: str, client_secret: str):
    """
    Get an access token using client credentials flow.

    :param client_id: The client ID
    :param client_secret: The client secret
    :return: Access token
    """
    try:
        auth_url = get_state_auth_url()

        # Prepare the request data for client credentials flow
        data = {
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret,
            'scope': f'{COMPACT}/readGeneral {JURISDICTION}/{COMPACT}.write',
        }

        headers = {'Content-Type': 'application/x-www-form-urlencoded', 'Accept': 'application/json'}

        response = requests.post(auth_url, data=data, headers=headers, timeout=10)

        if response.status_code != 200:
            raise SmokeTestFailureException(
                f'Failed to get access token. Status: {response.status_code}, Response: {response.text}'
            )

        token_data = response.json()
        access_token = token_data.get('access_token')

        if not access_token:
            raise SmokeTestFailureException('No access token in response')

        logger.info('Successfully obtained access token using client credentials')
        return access_token

    except requests.RequestException as e:
        logger.error(f'Failed to get client credentials token: {str(e)}')
        raise SmokeTestFailureException(f'Failed to get client credentials token: {str(e)}') from e


def get_client_auth_headers(client_id: str, client_secret: str):
    """
    Get authentication headers for client credentials flow.

    :param client_id: The client ID
    :param client_secret: The client secret
    :return: Headers dictionary with Authorization header
    """
    access_token = get_client_credentials_token(client_id, client_secret)
    return {'Authorization': f'Bearer {access_token}'}


def configure_dsa_public_key(public_key_pem: str):
    """
    Configure a DSA public key in the compact configuration table.

    :param public_key_pem: PEM-encoded public key content
    """
    logger.info(f'Configuring DSA public key: {TEST_KEY_ID}')

    try:
        table = get_compact_configuration_table()

        # Check if key already exists
        pk = f'{COMPACT}#DSA_KEYS'
        sk = f'{COMPACT}#JURISDICTION#{JURISDICTION}#{TEST_KEY_ID}'

        response = table.get_item(Key={'pk': pk, 'sk': sk})

        if 'Item' in response:
            logger.info(f'DSA key {TEST_KEY_ID} already exists, overwriting')

        # Create the item
        item = {
            'pk': pk,
            'sk': sk,
            'publicKey': public_key_pem,
            'compact': COMPACT,
            'jurisdiction': JURISDICTION,
            'keyId': TEST_KEY_ID,
            'createdAt': datetime.now(UTC).isoformat(),
        }

        # Write to DynamoDB
        table.put_item(Item=item)

        logger.info(f'Successfully configured DSA public key: {TEST_KEY_ID}')

    except ClientError as e:
        logger.error(f'Failed to configure DSA public key: {str(e)}')
        raise SmokeTestFailureException(f'Failed to configure DSA public key: {str(e)}') from e


def remove_dsa_public_key():
    """Remove the test DSA public key from the compact configuration table."""
    try:
        table = get_compact_configuration_table()

        pk = f'{COMPACT}#DSA_KEYS'
        sk = f'{COMPACT}#JURISDICTION#{JURISDICTION}#{TEST_KEY_ID}'

        table.delete_item(Key={'pk': pk, 'sk': sk})
        logger.info(f'Successfully removed DSA public key: {TEST_KEY_ID}')

    except ClientError as e:
        logger.error(f'Failed to remove DSA public key: {str(e)}')
        # Don't raise here as this is cleanup


def load_test_keys():
    """
    Load the test private and public keys from the resources directory.

    :return: Tuple of (private_key_pem, public_key_pem)
    """
    # Find the resources directory relative to this script
    script_dir = Path(__file__).parent
    resources_dir = script_dir.parent.parent / 'lambdas' / 'python' / 'common' / 'tests' / 'resources'

    private_key_path = resources_dir / 'client_private_key.pem'
    public_key_path = resources_dir / 'client_public_key.pem'

    if not private_key_path.exists():
        raise SmokeTestFailureException(f'Private key file not found: {private_key_path}')
    if not public_key_path.exists():
        raise SmokeTestFailureException(f'Public key file not found: {public_key_path}')

    with open(private_key_path) as f:
        private_key_pem = f.read()

    with open(public_key_path) as f:
        public_key_pem = f.read()

    logger.info('Successfully loaded test keys')
    return private_key_pem, public_key_pem


def create_signed_headers(method: str, path: str, query_params: dict, private_key_pem: str):
    """
    Create DSA-signed headers for a request.

    :param method: HTTP method (e.g., 'GET', 'POST')
    :param path: Request path
    :param query_params: Query parameters dictionary
    :param private_key_pem: PEM-encoded private key
    :return: Headers dictionary with DSA authentication headers
    """
    # Generate current timestamp and nonce
    timestamp = datetime.now(UTC).isoformat()
    nonce = str(uuid.uuid4())

    # Sign the request
    return sign_request(
        method=method,
        path=path,
        query_params=query_params,
        timestamp=timestamp,
        nonce=nonce,
        key_id=TEST_KEY_ID,
        private_key_pem=private_key_pem,
    )


def test_bulk_upload_endpoint_without_dsa(client_id: str, client_secret: str):
    """
    Test the bulk-upload endpoint without DSA authentication (should succeed when no keys configured).

    :param client_id: The client ID for authentication
    :param client_secret: The client secret for authentication
    """
    logger.info('Testing bulk-upload endpoint without DSA authentication')

    headers = get_client_auth_headers(client_id, client_secret)

    response = requests.get(
        url=get_state_api_base_url() + f'/v1/compacts/{COMPACT}/jurisdictions/{JURISDICTION}/licenses/bulk-upload',
        headers=headers,
        timeout=10,
    )

    if response.status_code != 200:
        raise SmokeTestFailureException(
            f'Bulk-upload endpoint should succeed without DSA when no keys configured. '
            f'Response: {response.status_code} - {response.text}'
        )

    logger.info('Bulk-upload endpoint succeeded without DSA authentication (as expected)')


def test_bulk_upload_endpoint_without_dsa_after_key_configuration(client_id: str, client_secret: str):
    """
    Test the bulk-upload endpoint without DSA authentication after keys are configured (should fail).

    :param client_id: The client ID for authentication
    :param client_secret: The client secret for authentication
    """
    logger.info('Testing bulk-upload endpoint without DSA authentication after key configuration')

    headers = get_client_auth_headers(client_id, client_secret)

    response = requests.get(
        url=get_state_api_base_url() + f'/v1/compacts/{COMPACT}/jurisdictions/{JURISDICTION}/licenses/bulk-upload',
        headers=headers,
        timeout=10,
    )

    if response.status_code == 200:
        raise SmokeTestFailureException('Bulk-upload endpoint should fail without DSA when keys are configured')

    if response.status_code != 401:
        logger.warning(f'Expected 401 but got {response.status_code}: {response.text}')

    logger.info('Bulk-upload endpoint correctly rejected without DSA authentication')


def test_bulk_upload_endpoint_with_dsa(client_id: str, client_secret: str, private_key_pem: str):
    """
    Test the bulk-upload endpoint with valid DSA authentication.

    :param client_id: The client ID for authentication
    :param client_secret: The client secret for authentication
    :param private_key_pem: PEM-encoded private key for signing
    """
    logger.info('Testing bulk-upload endpoint with DSA authentication')

    # Get client credentials headers
    client_headers = get_client_auth_headers(client_id, client_secret)

    # Create DSA headers
    dsa_headers = create_signed_headers(
        method='GET',
        path=f'/v1/compacts/{COMPACT}/jurisdictions/{JURISDICTION}/licenses/bulk-upload',
        query_params={},
        private_key_pem=private_key_pem,
    )

    # Combine headers
    headers = {**client_headers, **dsa_headers}

    response = requests.get(
        url=get_state_api_base_url() + f'/v1/compacts/{COMPACT}/jurisdictions/{JURISDICTION}/licenses/bulk-upload',
        headers=headers,
        timeout=10,
    )

    if response.status_code != 200:
        raise SmokeTestFailureException(
            f'Bulk-upload endpoint should succeed with valid DSA authentication. '
            f'Response: {response.status_code} - {response.text}'
        )

    # Verify response structure
    response_data = response.json()
    if 'upload' not in response_data:
        raise SmokeTestFailureException('Bulk-upload response missing upload field')

    logger.info('Bulk-upload endpoint succeeded with DSA authentication')


def test_providers_query_endpoint_with_dsa(client_id: str, client_secret: str, private_key_pem: str):
    """
    Test the providers/query endpoint with valid DSA authentication.

    :param client_id: The client ID for authentication
    :param client_secret: The client secret for authentication
    :param private_key_pem: PEM-encoded private key for signing
    """
    logger.info('Testing providers/query endpoint with DSA authentication')

    # Get client credentials headers
    client_headers = get_client_auth_headers(client_id, client_secret)

    # Create request body with a 7-day time range
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(days=7)

    request_body = {
        'query': {
            'startDateTime': start_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'endDateTime': end_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
        }
    }

    # Create DSA headers
    dsa_headers = create_signed_headers(
        method='POST',
        path=f'/v1/compacts/{COMPACT}/jurisdictions/{JURISDICTION}/providers/query',
        query_params={},
        private_key_pem=private_key_pem,
    )

    # Combine headers
    headers = {**client_headers, **dsa_headers}
    headers['Content-Type'] = 'application/json'

    response = requests.post(
        url=get_state_api_base_url() + f'/v1/compacts/{COMPACT}/jurisdictions/{JURISDICTION}/providers/query',
        headers=headers,
        json=request_body,
        timeout=10,
    )

    if response.status_code != 200:
        raise SmokeTestFailureException(
            f'Providers/query endpoint should succeed with valid DSA authentication. '
            f'Response: {response.status_code} - {response.text}'
        )

    # Verify response structure
    response_data = response.json()
    if 'providers' not in response_data:
        raise SmokeTestFailureException('Providers/query response missing providers field')

    if 'pagination' not in response_data:
        raise SmokeTestFailureException('Providers/query response missing pagination field')

    logger.info('Providers/query endpoint succeeded with DSA authentication')


def dsa_authentication_smoke_test():
    """
    Comprehensive smoke test for DSA authentication system.

    This test exercises the DSA authentication by:
    1. Creating a test app client in Cognito
    2. Testing bulk-upload endpoint without DSA (should succeed when no keys configured)
    3. Configuring a DSA public key for the test compact/state
    4. Testing bulk-upload endpoint without DSA (keys configured - should fail)
    5. Testing bulk-upload endpoint with valid DSA authentication
    6. Testing providers/query endpoint with valid DSA authentication
    """
    logger.info('Starting DSA authentication smoke test')

    # Load test keys
    private_key_pem, public_key_pem = load_test_keys()

    # Create test app client
    client_credentials = create_test_app_client()
    client_id = client_credentials['client_id']
    client_secret = client_credentials['client_secret']

    try:
        # Step 1: Test bulk-upload endpoint without DSA (no keys configured)
        test_bulk_upload_endpoint_without_dsa(client_id, client_secret)

        # Step 2: Configure DSA public key
        configure_dsa_public_key(public_key_pem)

        # Step 3: Test bulk-upload endpoint without DSA (keys configured - should fail)
        test_bulk_upload_endpoint_without_dsa_after_key_configuration(client_id, client_secret)

        # Step 4: Test bulk-upload endpoint with valid DSA authentication
        test_bulk_upload_endpoint_with_dsa(client_id, client_secret, private_key_pem)

        # Step 5: Test providers/query endpoint with valid DSA authentication
        test_providers_query_endpoint_with_dsa(client_id, client_secret, private_key_pem)

        logger.info('DSA authentication smoke test completed successfully')

    finally:
        # Cleanup
        logger.info('Cleaning up test resources')
        remove_dsa_public_key()
        delete_test_app_client(client_id)


if __name__ == '__main__':
    load_smoke_test_env()

    try:
        dsa_authentication_smoke_test()
        logger.info('DSA authentication smoke test passed')
    except SmokeTestFailureException as e:
        logger.error(f'DSA authentication smoke test failed: {str(e)}')
        raise
