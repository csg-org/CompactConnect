import json
import os
import sys
import time
import uuid

import boto3
import requests
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from config import config, logger


class SmokeTestFailureException(Exception):
    """Custom exception to raise when a smoke test fails."""

    def __init__(self, message):
        super().__init__(message)


provider_data_path = os.path.join('lambdas', 'python', 'staff-users')
common_lib_path = os.path.join('lambdas', 'python', 'common')
sys.path.append(provider_data_path)
sys.path.append(common_lib_path)

with open('cdk.json') as context_file:
    _context = json.load(context_file)['context']
JURISDICTIONS = _context['jurisdictions']
COMPACTS = _context['compacts']
LICENSE_TYPES = _context['license_types']

os.environ['COMPACTS'] = json.dumps(COMPACTS)
os.environ['JURISDICTIONS'] = json.dumps(JURISDICTIONS)
os.environ['LICENSE_TYPES'] = json.dumps(LICENSE_TYPES)

# We have to import this after we've added the common lib to our path and environment
from cc_common.data_model.provider_record_util import ProviderUserRecords  # noqa: E402 F401

# importing this here so it can be easily referenced in the rollback upload tests
from cc_common.data_model.schema.license import LicenseData, LicenseUpdateData  # noqa: E402 F401
from cc_common.data_model.schema.user.record import UserRecordSchema  # noqa: E402
from cc_common.data_model.update_tier_enum import UpdateTierEnum  # noqa: E402

_TEST_STAFF_USER_PASSWORD = 'TestPass123!'  # noqa: S105 test credential for test staff user
_TEMP_STAFF_PASSWORD = 'TempPass123!'  # noqa: S105 temporary password for creating test staff users


def _create_staff_user_in_cognito(*, email: str) -> str:
    """
    Creates a staff user in Cognito and returns the user's sub.
    """

    def get_sub_from_attributes(user_attributes: list):
        for attribute in user_attributes:
            if attribute['Name'] == 'sub':
                return attribute['Value']
        raise ValueError('Failed to find user sub!')

    try:
        user_data = config.cognito_client.admin_create_user(
            UserPoolId=config.cognito_staff_user_pool_id,
            Username=email,
            UserAttributes=[{'Name': 'email', 'Value': email}],
            TemporaryPassword=_TEMP_STAFF_PASSWORD,
        )
        logger.info(f"Created staff user, '{email}'. Setting password.")
        # set this to simplify login flow for user
        config.cognito_client.admin_set_user_password(
            UserPoolId=config.cognito_staff_user_pool_id,
            Username=email,
            Password=_TEST_STAFF_USER_PASSWORD,
            Permanent=True,
        )
        logger.info(f"Set password for staff user, '{email}' in Cognito. New user data: {user_data}")
        return get_sub_from_attributes(user_data['User']['Attributes'])

    except ClientError as e:
        if e.response['Error']['Code'] == 'UsernameExistsException':
            logger.info(f"Staff user, '{email}', already exists in Cognito. Getting user data.")
            user_data = config.cognito_client.admin_get_user(
                UserPoolId=config.cognito_staff_user_pool_id, Username=email
            )
            return get_sub_from_attributes(user_data['UserAttributes'])

        raise e


def delete_test_staff_user(email: str, user_sub: str, compact: str):
    """Deletes a test staff user from Cognito.

    :param email: The email address of the staff user to delete
    :param user_sub: The user's sub ID
    :param compact: The compact identifier
    """
    try:
        logger.info(f"Deleting staff user from cognito, '{email}'")
        config.cognito_client.admin_delete_user(UserPoolId=config.cognito_staff_user_pool_id, Username=email)
        # now clean up the user record in DynamoDB
        pk = f'USER#{user_sub}'
        sk = f'COMPACT#{compact}'
        logger.info(f"Deleting staff user record from DynamoDB, PK: '{pk}', SK: '{sk}'")
        config.staff_users_dynamodb_table.delete_item(Key={'pk': pk, 'sk': sk})
        logger.info(f"Deleted staff user, '{email}', from Cognito and DynamoDB")
    except ClientError as e:
        logger.error(f"Failed to delete staff user data, '{email}': {str(e)}")
        raise e


def create_test_staff_user(*, email: str, compact: str, jurisdiction: str, permissions: dict):
    """Creates a test staff user in Cognito, stores their data in DynamoDB, and returns their user sub id.

    :param email: The email address of the staff user to create
    :param compact: The compact identifier
    :param jurisdiction: The jurisdiction identifier
    :param permissions: The permissions dictionary for the user
    :return: The staff user's sub ID
    """
    logger.info(f"Creating staff user, '{email}', in {compact}/{jurisdiction}")
    user_attributes = {'email': email, 'familyName': 'Dokes', 'givenName': 'Joe'}
    sub = _create_staff_user_in_cognito(email=email)
    schema = UserRecordSchema()
    config.staff_users_dynamodb_table.put_item(
        Item=schema.dump(
            {
                'type': 'user',
                'userId': sub,
                'compact': compact,
                'attributes': user_attributes,
                'permissions': permissions,
                'status': 'active',
            },
        ),
    )
    logger.info(f'Created staff user record in DynamoDB. User data: {user_attributes}')

    return sub


def get_user_tokens(email, password=_TEST_STAFF_USER_PASSWORD, is_staff=False):
    """
    Gets Cognito tokens for a user.
    {
        'IdToken': 'string',
        'AccessToken': 'string',
        'RefreshToken': 'string',
        'ExpiresIn': 123,
        'TokenType': 'string',
        'NewDeviceMetadata': {
            'DeviceKey': 'string',
            'DeviceGroupKey': 'string'
        }
    }
    """
    try:
        logger.info('Getting tokens for user: ' + email + ' user type: ' + ('staff' if is_staff else 'provider'))
        response = config.cognito_client.admin_initiate_auth(
            UserPoolId=config.cognito_staff_user_pool_id if is_staff else config.cognito_provider_user_pool_id,
            ClientId=config.cognito_staff_user_client_id if is_staff else config.cognito_provider_user_client_id,
            AuthFlow='ADMIN_USER_PASSWORD_AUTH',
            AuthParameters={'USERNAME': email, 'PASSWORD': password},
        )

        return response['AuthenticationResult']

    except ClientError as e:
        logger.info(f'Failed to get tokens for user {email}: {str(e)}')
        raise e


def get_provider_user_auth_headers_cached():
    provider_token = os.environ.get('TEST_PROVIDER_USER_ID_TOKEN')
    if not provider_token:
        tokens = get_user_tokens(config.test_provider_user_username, config.test_provider_user_password, is_staff=False)
        os.environ['TEST_PROVIDER_USER_ID_TOKEN'] = tokens['IdToken']

    return {
        'Authorization': 'Bearer ' + os.environ['TEST_PROVIDER_USER_ID_TOKEN'],
    }


def get_staff_user_auth_headers(username: str, password: str = _TEST_STAFF_USER_PASSWORD):
    tokens = get_user_tokens(username, password, is_staff=True)
    return {
        'Authorization': 'Bearer ' + tokens['AccessToken'],
    }


def get_license_type_abbreviation(license_type: str):
    """
    Gets the abbreviation for a specific license type.
    """
    all_license_types = []
    for compact in LICENSE_TYPES:
        all_license_types.extend(LICENSE_TYPES[compact])
    return next((lt['abbreviation'] for lt in all_license_types if lt['name'] == license_type), None)


def get_api_base_url():
    return os.environ['CC_TEST_API_BASE_URL']


def get_provider_user_dynamodb_table():
    return boto3.resource('dynamodb').Table(os.environ['CC_TEST_PROVIDER_DYNAMO_TABLE_NAME'])


def get_rate_limiting_dynamodb_table():
    return boto3.resource('dynamodb').Table(os.environ['CC_TEST_RATE_LIMITING_DYNAMO_TABLE_NAME'])


def get_ssn_dynamodb_table():
    return boto3.resource('dynamodb').Table(os.environ['CC_TEST_SSN_DYNAMO_TABLE_NAME'])


def get_data_events_dynamodb_table():
    return boto3.resource('dynamodb').Table(os.environ['CC_TEST_DATA_EVENT_DYNAMO_TABLE_NAME'])


def get_provider_ssn_lambda_name():
    return os.environ['CC_TEST_GET_PROVIDER_SSN_LAMBDA_NAME']


def get_lambda_client():
    return boto3.client('lambda')


def load_smoke_test_env():
    with open(os.path.join(os.path.dirname(__file__), 'smoke_tests_env.json')) as env_file:
        env_vars = json.load(env_file)
        os.environ.update(env_vars)


def call_provider_users_me_endpoint():
    """Get the provider data from the GET '/v1/provider-users/me' endpoint.

    If a 403 response is received, the token will be refreshed and the request retried once.

    :return: The response body JSON
    :raises SmokeTestFailureException: If the request fails after retry
    """
    # Get the provider data from the GET '/v1/provider-users/me' endpoint.
    get_provider_data_response = requests.get(
        url=config.api_base_url + '/v1/provider-users/me', headers=get_provider_user_auth_headers_cached(), timeout=10
    )

    # If we get a 403, the token may have expired - refresh it and retry once
    if get_provider_data_response.status_code == 403:
        logger.info('Received 403 response, refreshing provider user token and retrying...')
        # Clear the cached token to force a refresh
        if 'TEST_PROVIDER_USER_ID_TOKEN' in os.environ:
            del os.environ['TEST_PROVIDER_USER_ID_TOKEN']

        # Retry with fresh token
        get_provider_data_response = requests.get(
            url=config.api_base_url + '/v1/provider-users/me',
            headers=get_provider_user_auth_headers_cached(),
            timeout=10,
        )

    if get_provider_data_response.status_code != 200:
        raise SmokeTestFailureException(f'Failed to GET provider data. Response: {get_provider_data_response.json()}')
    # return the response body
    return get_provider_data_response.json()


def get_all_provider_database_records():
    # get the provider id and compact from the response
    response = call_provider_users_me_endpoint()
    provider_id = response['providerId']
    compact = response['compact']
    # query the provider database for all records
    query_result = config.provider_user_dynamodb_table.query(
        KeyConditionExpression=Key('pk').eq(f'{compact}#PROVIDER#{provider_id}')
    )

    return query_result['Items']


def get_provider_user_records(compact: str, provider_id: str) -> ProviderUserRecords:
    """
    Get all provider records from DynamoDB and return as ProviderUserRecords utility class.

    :param compact: The compact identifier
    :param provider_id: The provider's ID
    :return: ProviderUserRecords instance containing all records for this provider
    """
    # Query the provider database for all records
    resp = {'Items': []}
    last_evaluated_key = None
    while True:
        pagination = {'ExclusiveStartKey': last_evaluated_key} if last_evaluated_key else {}
        # Grab all records under the provider partition
        query_resp = config.provider_user_dynamodb_table.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('pk').eq(f'{compact}#PROVIDER#{provider_id}'),
            ConsistentRead=True,
            **pagination,
        )

        resp['Items'].extend(query_resp.get('Items', []))

        last_evaluated_key = query_resp.get('LastEvaluatedKey')
        if not last_evaluated_key:
            break

    return ProviderUserRecords(resp['Items'])


def upload_license_record(staff_headers: dict, compact: str, jurisdiction: str, data_overrides: dict = None):
    """Upload a license record using the API with default test data that can be overridden.

    :param staff_headers: Authentication headers for staff user
    :param compact: The compact abbreviation
    :param jurisdiction: The jurisdiction abbreviation
    :param data_overrides: Dict of fields to override in the default license data
    :return: The API response JSON
    """
    # Default test license data
    default_license_data = {
        'npi': '1111111111',
        'licenseNumber': 'TEST-LIC-123',
        'homeAddressPostalCode': '68001',
        'givenName': 'TestProvider',
        'familyName': 'LicenseDeactivation',
        'homeAddressStreet1': '123 Test Street',
        'dateOfBirth': '1985-01-01',
        'dateOfIssuance': '2020-01-01',
        'ssn': '999-99-9999',
        'licenseType': 'speech-language pathologist',
        'dateOfExpiration': '2050-01-01',
        'homeAddressState': 'ne',
        'homeAddressCity': 'Omaha',
        'licenseStatus': 'active',
        'compactEligibility': 'eligible',
        'emailAddress': 'test-license@example.com',
        'phoneNumber': '+15551234567',
    }

    # Apply any overrides
    if data_overrides:
        default_license_data.update(data_overrides)

    post_body = [default_license_data]

    logger.info(
        f'Uploading license record for {jurisdiction} with status "{default_license_data.get("licenseStatus")}"'
    )

    post_response = requests.post(
        url=f'{config.api_base_url}/v1/compacts/{compact}/jurisdictions/{jurisdiction}/licenses',
        headers=staff_headers,
        json=post_body,
        timeout=30,
    )

    if post_response.status_code != 200:
        raise SmokeTestFailureException(f'Failed to upload license record. Response: {post_response.json()}')

    logger.info(f'License record successfully uploaded with status "{default_license_data.get("licenseStatus")}"')
    return post_response.json()


def query_provider_by_name(staff_headers: dict, compact: str, given_name: str, family_name: str):
    """Query for a provider by name and return the provider ID if found.

    :param staff_headers: Authentication headers for staff user
    :param compact: The compact abbreviation
    :param given_name: Provider's given name
    :param family_name: Provider's family name
    :return: The provider ID if found, None otherwise
    """
    query_body = {'query': {'familyName': family_name, 'givenName': given_name}}

    query_response = requests.post(
        url=f'{config.api_base_url}/v1/compacts/{compact}/providers/query',
        headers=staff_headers,
        json=query_body,
        timeout=10,
    )

    if query_response.status_code != 200:
        logger.warning(f'Query failed with status {query_response.status_code}')
        return None

    providers = query_response.json().get('providers', [])
    if providers:
        # Return the first provider id in the list (leave it to the smoke tests to uniquely name their test users)
        return providers[0].get('providerId')

    return None


def wait_for_provider_creation(
    staff_headers: dict, compact: str, given_name: str, family_name: str, max_wait_time: int = 300
):
    """Poll for provider creation after license upload.

    :param staff_headers: Authentication headers for staff user
    :param compact: The compact abbreviation
    :param given_name: Provider's given name
    :param family_name: Provider's family name
    :param max_wait_time: Maximum time to wait in seconds (default: 300 = 5 minutes)
    :return: The provider ID when found
    :raises SmokeTestFailureException: If provider not found within max_wait_time
    """
    import time

    logger.info(f'Waiting for provider creation for {given_name} {family_name}...')

    start_time = time.time()
    check_interval = 30  # Check every 30 seconds
    attempts = 0
    max_attempts = max_wait_time // check_interval

    while attempts < max_attempts:
        attempts += 1

        provider_id = query_provider_by_name(staff_headers, compact, given_name, family_name)
        if provider_id:
            elapsed_time = time.time() - start_time
            logger.info(f'✅ Provider found after {elapsed_time:.1f} seconds. Provider ID: {provider_id}')
            return provider_id

        if attempts < max_attempts:
            logger.info(
                f'Attempt {attempts}/{max_attempts}: Provider not found yet. Waiting {check_interval} seconds...'
            )
            time.sleep(check_interval)

    elapsed_time = time.time() - start_time
    raise SmokeTestFailureException(
        f'Provider not found after {elapsed_time:.1f} seconds. '
        f'The license ingest processing may be taking longer than expected.'
    )


def create_test_privilege_record(
    provider_id: str, compact: str, jurisdiction: str, license_jurisdiction: str, license_type: str
):
    """Create a test privilege record in the database for testing license deactivation.

    :param provider_id: The provider's ID
    :param compact: The compact abbreviation
    :param jurisdiction: The privilege jurisdiction
    :param license_jurisdiction: The license jurisdiction (home state)
    :param license_type: The license type
    :return: The created privilege record data
    """
    import uuid
    from datetime import UTC, date, datetime

    # Get the license type abbreviation to match the expected sort key format
    license_type_abbr = get_license_type_abbreviation(license_type)
    if not license_type_abbr:
        raise SmokeTestFailureException(f'Could not find abbreviation for license type: {license_type}')

    # Generate a test transaction ID
    transaction_id = str(uuid.uuid4())

    # Create privilege record data with correct sort key format
    privilege_data = {
        'pk': f'{compact}#PROVIDER#{provider_id}',
        'sk': f'{compact}#PROVIDER#privilege/{jurisdiction}/{license_type_abbr}#',
        'type': 'privilege',
        'providerId': provider_id,
        'compact': compact,
        'jurisdiction': jurisdiction,
        'licenseJurisdiction': license_jurisdiction,
        'licenseType': license_type,
        'dateOfIssuance': datetime.now(tz=UTC).isoformat(),
        'dateOfRenewal': datetime.now(tz=UTC).isoformat(),
        'dateOfExpiration': date(2050, 1, 1).isoformat(),
        'dateOfUpdate': datetime.now(tz=UTC).isoformat(),
        'compactTransactionId': transaction_id,
        'compactTransactionIdGSIPK': f'COMPACT#{compact}#TX#{transaction_id}#',
        'privilegeId': f'test-privilege-{provider_id}-{jurisdiction}-{license_type_abbr}',
        'administratorSetStatus': 'active',
    }

    # Insert the privilege record
    config.provider_user_dynamodb_table.put_item(Item=privilege_data)
    logger.info(
        f'Created test privilege record for provider {provider_id} in jurisdiction '
        f'{jurisdiction} with license type {license_type} ({license_type_abbr})'
    )

    return privilege_data


def delete_existing_privilege_records(provider_id: str, compact: str, jurisdiction: str):
    """Delete all privilege records and privilege update records for a provider in a specific jurisdiction.

    This function queries for and deletes both privilege records and their associated update records
    using the new SK pattern structure.

    :param provider_id: The provider's ID
    :param compact: The compact abbreviation
    :param jurisdiction: The jurisdiction abbreviation (e.g., 'ne')
    """
    dynamodb_table = config.provider_user_dynamodb_table
    pk = f'{compact}#PROVIDER#{provider_id}'

    # Query for all privilege records in the specified jurisdiction
    original_privilege_records = dynamodb_table.query(
        KeyConditionExpression=Key('pk').eq(pk) & Key('sk').begins_with(f'{compact}#PROVIDER#privilege/{jurisdiction}/')
    ).get('Items', [])

    # Query for all privilege update records in the specified jurisdiction
    privilege_update_sk_prefix = f'{compact}#UPDATE#{UpdateTierEnum.TIER_ONE}#privilege/{jurisdiction}/'
    original_privilege_update_records = []
    last_evaluated_key = None
    while True:
        pagination = {'ExclusiveStartKey': last_evaluated_key} if last_evaluated_key else {}
        query_resp = dynamodb_table.query(
            KeyConditionExpression=Key('pk').eq(pk) & Key('sk').begins_with(privilege_update_sk_prefix),
            **pagination,
        )
        original_privilege_update_records.extend(query_resp.get('Items', []))
        last_evaluated_key = query_resp.get('LastEvaluatedKey')
        if not last_evaluated_key:
            break

    original_privilege_records.extend(original_privilege_update_records)

    # Delete all privilege records
    for privilege in original_privilege_records:
        privilege_pk = privilege['pk']
        privilege_sk = privilege['sk']
        logger.info(f'Deleting privilege record:\n{privilege_pk}\n{privilege_sk}')
        dynamodb_table.delete_item(
            Key={
                'pk': privilege_pk,
                'sk': privilege_sk,
            }
        )
        # give dynamodb time to propagate
        time.sleep(1)

    logger.info(
        f'Deleted privilege record and {len(original_privilege_update_records)} privilege update records for '
        f'jurisdiction {jurisdiction}'
    )


def cleanup_test_provider_records(provider_id: str, compact: str):
    """Clean up all test records for a provider.

    :param provider_id: The provider's ID
    :param compact: The compact abbreviation
    """
    try:
        # Query for all provider records
        provider_record_query_response = config.provider_user_dynamodb_table.query(
            KeyConditionExpression=Key('pk').eq(f'{compact}#PROVIDER#{provider_id}')
        )

        # Delete all provider records
        deleted_count = 0
        for record in provider_record_query_response.get('Items', []):
            config.provider_user_dynamodb_table.delete_item(Key={'pk': record['pk'], 'sk': record['sk']})
            deleted_count += 1

        logger.info(f'Successfully deleted {deleted_count} provider records from provider table')

    except Exception as e:  # noqa: BLE001
        logger.warning(f'Error during cleanup: {str(e)}')


def create_test_app_client(client_name: str, compact: str, jurisdiction: str):
    """
    Create a test app client in Cognito for authentication testing.

    :param client_name: Name for the test app client
    :param compact: Compact abbreviation
    :param jurisdiction: Jurisdiction abbreviation
    :return: Dictionary containing client_id and client_secret
    """
    logger.info(f'Creating test app client: {client_name}')

    try:
        cognito_client = boto3.client('cognito-idp')

        # Create the user pool client
        response = cognito_client.create_user_pool_client(
            UserPoolId=config.cognito_state_auth_user_pool_id,
            ClientName=client_name,
            PreventUserExistenceErrors='ENABLED',
            GenerateSecret=True,
            TokenValidityUnits={'AccessToken': 'minutes'},
            AccessTokenValidity=15,
            AllowedOAuthFlowsUserPoolClient=True,
            AllowedOAuthFlows=['client_credentials'],
            AllowedOAuthScopes=[f'{compact}/readGeneral', f'{jurisdiction}/{compact}.write'],
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


def get_client_credentials_token(client_id: str, client_secret: str, compact: str, jurisdiction: str):
    """
    Get an access token using client credentials flow.

    :param client_id: The client ID
    :param client_secret: The client secret
    :param compact: Compact abbreviation
    :param jurisdiction: Jurisdiction abbreviation
    :return: Access token
    """
    try:
        auth_url = config.state_auth_url

        # Prepare the request data for client credentials flow
        data = {
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret,
            'scope': f'{compact}/readGeneral {jurisdiction}/{compact}.write',
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


def get_client_auth_headers(client_id: str, client_secret: str, compact: str, jurisdiction: str):
    """
    Get authentication headers for client credentials flow.

    :param client_id: The client ID
    :param client_secret: The client secret
    :param compact: Compact abbreviation
    :param jurisdiction: Jurisdiction abbreviation
    :return: Headers dictionary with Authorization header
    """
    access_token = get_client_credentials_token(client_id, client_secret, compact, jurisdiction)
    return {'Authorization': f'Bearer {access_token}'}
