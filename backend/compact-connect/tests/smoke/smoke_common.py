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
    """
    Custom exception to raise when a smoke test fails.
    """

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


def delete_test_staff_user(email, user_sub: str, compact: str):
    """
    Deletes a test staff user from Cognito.
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
    """
    Creates a test staff user in Cognito, stores their data in DynamoDB, and returns their user sub id.
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


def generate_opaque_data(card_number: str):
    """
    Generate a payment nonce using Authorize.Net's Secure Payment Container API.
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
