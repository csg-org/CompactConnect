import json
import os
import sys
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

# We have to import this after we've added the common lib to our path and environment
from cc_common.data_model.schema.user.record import UserRecordSchema  # noqa: E402

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
    # Get the provider data from the GET '/v1/provider-users/me' endpoint.
    get_provider_data_response = requests.get(
        url=config.api_base_url + '/v1/provider-users/me', headers=get_provider_user_auth_headers_cached(), timeout=10
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
        'dateOfRenewal': '2025-01-01',
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
        'attestations': [],
    }

    # Insert the privilege record
    config.provider_user_dynamodb_table.put_item(Item=privilege_data)
    logger.info(
        f'Created test privilege record for provider {provider_id} in jurisdiction '
        f'{jurisdiction} with license type {license_type} ({license_type_abbr})'
    )

    return privilege_data


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


def generate_opaque_data(card_number: str):
    """Generate a payment nonce using Authorize.Net's Secure Payment Container API.

    This allows us to create payment nonces programmatically for testing.

    :param card_number: The test card number to use for generating the opaque data
    :return: The opaque data object containing the payment nonce
    """

    # Call the purchase privilege options endpoint and extract the api login id and
    # public key from the compact configuration object that is returned.
    headers = get_provider_user_auth_headers_cached()
    response = requests.get(
        url=f'{config.api_base_url}/v1/purchases/privileges/options',
        headers=headers,
        timeout=10,
    )

    if response.status_code != 200:
        raise SmokeTestFailureException(f'Failed to get purchase privilege options. Response: {response.json()}')

    response_body = response.json()
    compact_data = next((item for item in response_body['items'] if item.get('type') == 'compact'), None)

    if not compact_data:
        raise SmokeTestFailureException('No compact data found in purchase privilege options response')

    if 'paymentProcessorPublicFields' not in compact_data:
        raise SmokeTestFailureException('No paymentProcessorPublicFields found in compact data')

    payment_fields = compact_data['paymentProcessorPublicFields']
    api_login_id = payment_fields.get('apiLoginId')
    public_client_key = payment_fields.get('publicClientKey')

    if not api_login_id or not public_client_key:
        raise SmokeTestFailureException(f'Missing credentials in paymentProcessorPublicFields: {payment_fields}')

    # Generate the payment nonce using the secure payment container API
    unique_id = str(uuid.uuid4())

    # Create the secure payment container request
    request_data = {
        'securePaymentContainerRequest': {
            'merchantAuthentication': {
                'name': api_login_id,
                'clientKey': public_client_key,  # Use the public client key
            },
            'refId': '12345',
            'data': {
                'type': 'TOKEN',
                'id': unique_id,
                'token': {
                    'cardNumber': card_number,
                    'expirationDate': '122030',
                    'cardCode': '999',
                    'fullName': 'SmokeTest User',
                },
            },
        }
    }

    # Make the API request
    test_url = 'https://apitest.authorize.net/xml/v1/request.api'
    headers = {'Content-Type': 'application/json'}
    response = requests.post(test_url, json=request_data, headers=headers, timeout=30)

    if response.status_code == 200:
        response_data = json.loads(response.content.decode('utf-8-sig'))

        # Extract the payment nonce from the response
        # The exact structure may vary, but it should contain the opaque data
        if 'opaqueData' in response_data:
            logger.info('Generated opaque data.')
            return response_data['opaqueData']
        logger.error(f'No opaqueData in response: {response_data}')
        raise SmokeTestFailureException(f'No opaqueData in response: {response_data}')
    logger.error(f'Failed to generate payment nonce: {response.status_code} - {response.text}')
    raise SmokeTestFailureException(f'Failed to generate payment nonce: {response.status_code} - {response.text}')
