import json
from datetime import datetime, timedelta
from functools import wraps
from unittest.mock import PropertyMock, patch

from cc_common.exceptions import CCInternalException
from common_test.test_constants import DEFAULT_DATE_OF_UPDATE_TIMESTAMP
from moto import mock_aws

from .. import TstFunction

TEST_COMPACT_ABBR = 'aslp'
TEST_COMPACT_NAME = 'Audiology and Speech Language Pathology'
TEST_LICENSE_TYPE = 'speech-language pathologist'

MOCK_SSN_LAST_FOUR = '1234'
MOCK_GIVEN_NAME = 'Joe'
MOCK_FAMILY_NAME = 'Dokes'
MOCK_JURISDICTION_POSTAL_ABBR = 'ky'
MOCK_JURISDICTION_NAME = 'Kentucky'
MOCK_DOB = '1990-01-01'
# this is the provider id defined in the test resource files
MOCK_PROVIDER_ID = '89a6377e-c3a5-40e5-bca5-317ec854c570'

MOCK_IP_ADDRESS = '127.0.0.1'
MOCK_DATETIME_STRING = '2025-01-23T08:15:00+00:00'

MOCK_COGNITO_SUB = '3408b4e8-0061-7052-bbe0-fda9a9369c80'
MOCK_COMPACT_CONNECT_REGISTERED_EMAIL_ADDRESS = 'test@example.com'


def generate_default_compact_config_overrides():
    return {
        'pk': f'{TEST_COMPACT_ABBR}#CONFIGURATION',
        'sk': f'{TEST_COMPACT_ABBR}#CONFIGURATION',
        'compactAbbr': TEST_COMPACT_ABBR,
        'compactName': TEST_COMPACT_NAME,
        'licenseeRegistrationEnabled': True,
        'configuredStates': [{'postalAbbreviation': MOCK_JURISDICTION_POSTAL_ABBR, 'isLive': True}],
    }


def generate_default_jurisdiction_config_overrides():
    return {
        'pk': f'{TEST_COMPACT_ABBR}#CONFIGURATION',
        'sk': f'{TEST_COMPACT_ABBR}#JURISDICTION#{MOCK_JURISDICTION_POSTAL_ABBR}',
        'compact': TEST_COMPACT_ABBR,
        'jurisdictionName': MOCK_JURISDICTION_NAME,
        'postalAbbreviation': MOCK_JURISDICTION_POSTAL_ABBR,
        'licenseeRegistrationEnabled': True,
    }


def generate_test_request():
    return {
        'compact': TEST_COMPACT_ABBR,
        'token': 'valid_token',
        'familyName': MOCK_FAMILY_NAME,
        'givenName': MOCK_GIVEN_NAME,
        'email': 'test@example.com',
        'partialSocial': MOCK_SSN_LAST_FOUR,
        'dob': MOCK_DOB,
        'jurisdiction': MOCK_JURISDICTION_POSTAL_ABBR,
        'licenseType': TEST_LICENSE_TYPE,
    }


def mock_delay_decorator(*args, **kwargs):  # noqa: ARG001 unused-argument
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            return f(*args, **kwargs)

        return decorated_function

    return decorator


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat(DEFAULT_DATE_OF_UPDATE_TIMESTAMP))
class TestProviderRegistration(TstFunction):
    def setUp(self):
        super().setUp()
        patch('cc_common.utils.delayed_function', mock_delay_decorator).start()

        self._load_compact_configuration(overrides=generate_default_compact_config_overrides())
        self._load_jurisdiction_configuration(overrides=generate_default_jurisdiction_config_overrides())

    def _add_mock_provider_records(self, *, is_registered=False, license_data_overrides=None):
        """
        Adds mock provider and license records to the provider table with customizable data.

        :param bool is_registered: If true, addd a home jurisdiction selection record for the provider
        :param dict license_data_overrides: Optional overrides for the license data
        """
        from cc_common.data_model.schema.license.record import LicenseRecordSchema

        with open('../common/tests/resources/dynamo/provider.json') as f:
            provider_data = json.load(f)
            provider_data['providerId'] = MOCK_PROVIDER_ID
            provider_data['compact'] = TEST_COMPACT_ABBR
            if is_registered:
                provider_data['compactConnectRegisteredEmailAddress'] = MOCK_COMPACT_CONNECT_REGISTERED_EMAIL_ADDRESS
            else:
                provider_data.pop('compactConnectRegisteredEmailAddress', None)
            self.config.provider_table.put_item(Item=provider_data)

        with open('../common/tests/resources/dynamo/license.json') as f:
            license_data = json.load(f)
            license_data.update(
                {
                    'ssnLastFour': MOCK_SSN_LAST_FOUR,
                    'dateOfBirth': MOCK_DOB,
                    'licenseType': TEST_LICENSE_TYPE,
                    'givenName': MOCK_GIVEN_NAME,
                    'familyName': MOCK_FAMILY_NAME,
                    'jurisdiction': MOCK_JURISDICTION_POSTAL_ABBR,
                    'compact': TEST_COMPACT_ABBR,
                    'providerId': MOCK_PROVIDER_ID,
                }
            )
            if license_data_overrides:
                license_data.update(license_data_overrides)
            license_schema = LicenseRecordSchema()
            serialized_record = license_schema.dump(license_schema.loads(json.dumps(license_data)))
            self.config.provider_table.put_item(Item=serialized_record)

        return provider_data, license_data

    def _add_mock_provider_records_using_data_classes(self):
        # wrapper function for tests to work with data classes, rather than dictionaries themselves
        from cc_common.data_model.schema.license import LicenseData
        from cc_common.data_model.schema.provider import ProviderData

        provider_data, license_data = self._add_mock_provider_records()
        return ProviderData.from_database_record(provider_data), LicenseData.from_database_record(license_data)

    def _get_api_event(self):
        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)
            event['requestContext']['identity']['sourceIp'] = MOCK_IP_ADDRESS
            return event

    def _get_test_event(self, body_overrides=None):
        """Helper to get a test event with optional body overrides."""
        event = self._get_api_event()
        body = generate_test_request()
        if body_overrides:
            body.update(body_overrides)
        event['body'] = json.dumps(body)
        return event

    @patch('handlers.registration.verify_recaptcha')
    def test_registration_returns_400_if_compact_is_not_configured(self, mock_verify_recaptcha):
        mock_verify_recaptcha.return_value = True
        from handlers.registration import register_provider

        response = register_provider(self._get_test_event(body_overrides={'compact': 'coun'}), self.mock_context)
        self.assertEqual(400, response['statusCode'])
        self.assertEqual(
            {'message': 'Registration is not currently available for the specified license type.'},
            json.loads(response['body']),
        )

    @patch('handlers.registration.verify_recaptcha')
    def test_registration_returns_400_if_compact_is_not_enabled_for_registration(self, mock_verify_recaptcha):
        compact_config_overrides = generate_default_compact_config_overrides()
        # in this case, no environments are enabled for registration
        compact_config_overrides.update({'licenseeRegistrationEnabled': False})
        self._load_compact_configuration(overrides=compact_config_overrides)
        mock_verify_recaptcha.return_value = True
        from handlers.registration import register_provider

        response = register_provider(self._get_test_event(), self.mock_context)
        self.assertEqual(400, response['statusCode'])
        self.assertEqual(
            {
                'message': 'Registration is not currently available for the Audiology and '
                + 'Speech Language Pathology compact.'
            },
            json.loads(response['body']),
        )

    @patch('handlers.registration.verify_recaptcha')
    def test_registration_returns_400_if_jurisdiction_configuration_not_present(self, mock_verify_recaptcha):
        mock_verify_recaptcha.return_value = True
        from handlers.registration import register_provider

        # in this case, Ohio state admins have not specified their configuration values yet, so registration cannot
        # be completed
        response = register_provider(self._get_test_event(body_overrides={'jurisdiction': 'oh'}), self.mock_context)
        self.assertEqual(400, response['statusCode'])
        self.assertEqual(
            {'message': 'Registration is not currently available for the specified state.'},
            json.loads(response['body']),
        )

    @patch('handlers.registration.verify_recaptcha')
    def test_registration_returns_400_if_jurisdiction_not_in_compact_configured_states(self, mock_verify_recaptcha):
        """Test that registration is rejected if jurisdiction is not in compact's configuredStates."""
        mock_verify_recaptcha.return_value = True

        # in this case, the compact does not have the requested state in their list of configuredStates, so registration
        # cannot be completed
        compact_config_overrides = generate_default_compact_config_overrides()
        compact_config_overrides.update({'configuredStates': []})
        self._load_compact_configuration(overrides=compact_config_overrides)

        from handlers.registration import register_provider

        response = register_provider(self._get_test_event(), self.mock_context)
        self.assertEqual(400, response['statusCode'])
        self.assertEqual(
            {'message': 'Registration is not currently available for Kentucky.'},
            json.loads(response['body']),
        )

    @patch('handlers.registration.verify_recaptcha')
    def test_registration_returns_400_if_jurisdiction_not_live_in_configured_states(self, mock_verify_recaptcha):
        """Test that registration is rejected if jurisdiction is not live in compact's configuredStates."""
        mock_verify_recaptcha.return_value = True

        # Update compact configuration to have jurisdiction but not live
        compact_config_overrides = generate_default_compact_config_overrides()
        compact_config_overrides.update(
            {'configuredStates': [{'postalAbbreviation': MOCK_JURISDICTION_POSTAL_ABBR, 'isLive': False}]}
        )
        self._load_compact_configuration(overrides=compact_config_overrides)

        from handlers.registration import register_provider

        response = register_provider(self._get_test_event(), self.mock_context)
        self.assertEqual(400, response['statusCode'])
        self.assertEqual(
            {'message': 'Registration is not currently available for Kentucky.'},
            json.loads(response['body']),
        )

    @patch('handlers.registration.verify_recaptcha')
    def test_registration_succeeds_if_jurisdiction_is_live_in_configured_states(self, mock_verify_recaptcha):
        """Test that registration succeeds if jurisdiction is live in compact's configuredStates."""
        mock_verify_recaptcha.return_value = True
        self._add_mock_provider_records()

        # Default setup already has jurisdiction as live in configuredStates
        from handlers.registration import register_provider

        response = register_provider(self._get_test_event(), self.mock_context)
        self.assertEqual(200, response['statusCode'])
        self.assertEqual({'message': 'request processed'}, json.loads(response['body']))

    @patch('handlers.registration.verify_recaptcha')
    def test_registration_returns_403_if_recaptcha_fails(self, mock_verify_recaptcha):
        mock_verify_recaptcha.return_value = False
        from handlers.registration import register_provider

        response = register_provider(self._get_test_event(), self.mock_context)
        self.assertEqual(403, response['statusCode'])
        mock_verify_recaptcha.assert_called_once_with('valid_token')

    @patch('handlers.registration.verify_recaptcha')
    def test_registration_returns_200_if_no_license_records_found(self, mock_verify_recaptcha):
        mock_verify_recaptcha.return_value = True
        from handlers.registration import register_provider

        response = register_provider(self._get_test_event(), self.mock_context)
        self.assertEqual(200, response['statusCode'])
        self.assertEqual({'message': 'request processed'}, json.loads(response['body']))

    @patch('handlers.registration.verify_recaptcha')
    def test_registration_returns_200_if_no_matching_license_found(self, mock_verify_recaptcha):
        mock_verify_recaptcha.return_value = True
        self._add_mock_provider_records(license_data_overrides={'ssnLastFour': '9876'})  # Different SSN
        from handlers.registration import register_provider

        response = register_provider(self._get_test_event(), self.mock_context)
        self.assertEqual(200, response['statusCode'])
        self.assertEqual({'message': 'request processed'}, json.loads(response['body']))

    def _when_testing_user_that_is_already_registered(self, mock_cognito, overrides: dict | None = None):
        get_user_response = {
            'Username': MOCK_COMPACT_CONNECT_REGISTERED_EMAIL_ADDRESS,
            'UserCreateDate': datetime.fromisoformat(DEFAULT_DATE_OF_UPDATE_TIMESTAMP),
            'UserLastModifiedDate': datetime.fromisoformat(DEFAULT_DATE_OF_UPDATE_TIMESTAMP),
            'Enabled': True,
            'UserStatus': 'FORCE_CHANGE_PASSWORD',
        }

        if overrides:
            get_user_response.update(overrides)

        mock_cognito.admin_get_user.return_value = get_user_response

    @patch('handlers.registration.verify_recaptcha')
    @patch('handlers.registration.config.email_service_client')
    def test_registration_sends_registration_attempt_email_if_provider_already_registered_in_confirmed_state(
        self, mock_email_service_client, mock_verify_recaptcha
    ):
        mock_verify_recaptcha.return_value = True
        self._add_mock_provider_records(is_registered=True)
        from handlers.registration import register_provider

        with patch('handlers.registration.config.cognito_client') as mock_cognito:
            creation_date = datetime.fromisoformat(DEFAULT_DATE_OF_UPDATE_TIMESTAMP) - timedelta(days=2)

            self._when_testing_user_that_is_already_registered(
                mock_cognito,
                overrides={
                    'UserStatus': 'CONFIRMED',
                    'UserCreateDate': creation_date,
                    'UserLastModifiedDate': creation_date,
                },
            )
            response = register_provider(self._get_test_event(), self.mock_context)
            mock_cognito.admin_create_user.assert_not_called()
            mock_cognito.admin_delete_user.assert_not_called()
            mock_email_service_client.send_provider_multiple_registration_attempt_email.assert_called_with(
                compact=TEST_COMPACT_ABBR, provider_email=MOCK_COMPACT_CONNECT_REGISTERED_EMAIL_ADDRESS
            )

        self.assertEqual(200, response['statusCode'])
        self.assertEqual({'message': 'request processed'}, json.loads(response['body']))

    @patch('handlers.registration.verify_recaptcha')
    @patch('handlers.registration.config.email_service_client')
    def test_registration_sends_registration_attempt_email_if_provider_already_registered_less_than_one_day_ago(
        self, mock_email_service_client, mock_verify_recaptcha
    ):
        mock_verify_recaptcha.return_value = True
        self._add_mock_provider_records(is_registered=True)
        from handlers.registration import register_provider

        with patch('handlers.registration.config.cognito_client') as mock_cognito:
            self._when_testing_user_that_is_already_registered(mock_cognito)
            response = register_provider(self._get_test_event(), self.mock_context)
            mock_cognito.admin_create_user.assert_not_called()
            mock_cognito.admin_delete_user.assert_not_called()
            mock_email_service_client.send_provider_multiple_registration_attempt_email.assert_called_with(
                compact=TEST_COMPACT_ABBR, provider_email=MOCK_COMPACT_CONNECT_REGISTERED_EMAIL_ADDRESS
            )

        self.assertEqual(200, response['statusCode'])
        self.assertEqual({'message': 'request processed'}, json.loads(response['body']))

    @patch('handlers.registration.verify_recaptcha')
    def test_registration_allows_user_to_register_again_if_provider_registered_without_login_more_than_one_day_ago(
        self, mock_verify_recaptcha
    ):
        mock_verify_recaptcha.return_value = True
        self._add_mock_provider_records(is_registered=True)
        from handlers.registration import register_provider

        with patch('handlers.registration.config.cognito_client') as mock_cognito:
            creation_date = datetime.fromisoformat(DEFAULT_DATE_OF_UPDATE_TIMESTAMP) - timedelta(days=2)
            self._when_testing_user_that_is_already_registered(
                mock_cognito, overrides={'UserCreateDate': creation_date, 'UserLastModifiedDate': creation_date}
            )
            response = register_provider(self._get_test_event(), self.mock_context)
            mock_cognito.admin_create_user.assert_called_with(
                UserPoolId=self.config.provider_user_pool_id,
                Username=MOCK_COMPACT_CONNECT_REGISTERED_EMAIL_ADDRESS,
                MessageAction='RESEND',
            )

        self.assertEqual(200, response['statusCode'])
        self.assertEqual({'message': 'request processed'}, json.loads(response['body']))

    @patch('handlers.registration.verify_recaptcha')
    def test_registration_cleans_up_old_user_if_never_logged_in_and_user_registers_with_new_license(
        self, mock_verify_recaptcha
    ):
        mock_verify_recaptcha.return_value = True
        provider_data, license_data = self._add_mock_provider_records(is_registered=True)
        from handlers.registration import register_provider

        with patch('handlers.registration.config.cognito_client') as mock_cognito:
            creation_date = datetime.fromisoformat(DEFAULT_DATE_OF_UPDATE_TIMESTAMP) - timedelta(days=2)
            self._when_testing_user_that_is_already_registered(
                mock_cognito, overrides={'UserCreateDate': creation_date, 'UserLastModifiedDate': creation_date}
            )
            response = register_provider(
                self._get_test_event(body_overrides={'email': 'some-other-email@test.com'}), self.mock_context
            )
            mock_cognito.admin_delete_user.assert_called_with(
                UserPoolId=self.config.provider_user_pool_id, Username=MOCK_COMPACT_CONNECT_REGISTERED_EMAIL_ADDRESS
            )
            mock_cognito.admin_create_user.assert_called_with(
                UserPoolId=self.config.provider_user_pool_id,
                Username='some-other-email@test.com',
                UserAttributes=[
                    {'Name': 'custom:compact', 'Value': TEST_COMPACT_ABBR.lower()},
                    {'Name': 'custom:providerId', 'Value': provider_data['providerId']},
                    {'Name': 'email', 'Value': 'some-other-email@test.com'},
                    {'Name': 'email_verified', 'Value': 'true'},
                ],
            )

        self.assertEqual(200, response['statusCode'])
        self.assertEqual({'message': 'request processed'}, json.loads(response['body']))

        # verify the email address was updated on the provider record.
        provider_user_records = self.config.data_client.get_provider_user_records(
            compact=TEST_COMPACT_ABBR, provider_id=provider_data['providerId']
        )

        provider_record = provider_user_records.get_provider_record()

        self.assertEqual('some-other-email@test.com', provider_record.compactConnectRegisteredEmailAddress)

    @patch('handlers.registration.verify_recaptcha')
    def test_registration_creates_cognito_user(self, mock_verify_recaptcha):
        mock_verify_recaptcha.return_value = True
        provider_data, license_data = self._add_mock_provider_records()
        from handlers.registration import register_provider

        response = register_provider(self._get_test_event(), self.mock_context)

        self.assertEqual(200, response['statusCode'])
        self.assertEqual({'message': 'request processed'}, json.loads(response['body']))

        # Verify Cognito user was created with correct attributes
        cognito_users = self.config.cognito_client.list_users(
            UserPoolId=self.config.provider_user_pool_id, Filter='email = "test@example.com"'
        )

        self.assertEqual(1, len(cognito_users['Users']))
        user_attributes = {attr['Name']: attr['Value'] for attr in cognito_users['Users'][0]['Attributes']}

        # We can't predict the `sub`, so we'll just make sure there is one
        sub_value = user_attributes.pop('sub', None)
        self.assertIsNotNone(sub_value, "User should have a 'sub' attribute")

        # Verify all attributes match exactly what we expect (no more, no less)
        expected_attributes = {
            'custom:compact': TEST_COMPACT_ABBR,
            'custom:providerId': provider_data['providerId'],
            'email': 'test@example.com',
            'email_verified': 'true',
        }
        self.assertEqual(expected_attributes, user_attributes)

    @patch('handlers.registration.verify_recaptcha')
    def test_registration_sets_registration_values(self, mock_verify_recaptcha):
        mock_verify_recaptcha.return_value = True
        provider_data, license_data = self._add_mock_provider_records()
        from handlers.registration import register_provider

        response = register_provider(self._get_test_event(), self.mock_context)

        self.assertEqual(200, response['statusCode'])
        self.assertEqual({'message': 'request processed'}, json.loads(response['body']))

        # Verify Cognito user was created with correct attributes
        cognito_users = self.config.cognito_client.list_users(
            UserPoolId=self.config.provider_user_pool_id, Filter='email = "test@example.com"'
        )

        self.assertEqual(1, len(cognito_users['Users']))
        user_attributes = {attr['Name']: attr['Value'] for attr in cognito_users['Users'][0]['Attributes']}

        # We'll check the sub below
        user_attributes.pop('sub', None)

        # Verify all attributes match exactly what we expect (no more, no less)
        expected_attributes = {
            'custom:compact': TEST_COMPACT_ABBR,
            'custom:providerId': provider_data['providerId'],
            'email': 'test@example.com',
            'email_verified': 'true',
        }
        self.assertEqual(expected_attributes, user_attributes)

        # Verify provider record was updated with registration values
        provider_record = self.config.provider_table.get_item(
            Key={
                'pk': f'{TEST_COMPACT_ABBR}#PROVIDER#{provider_data["providerId"]}',
                'sk': f'{TEST_COMPACT_ABBR}#PROVIDER',
            }
        )['Item']
        self.assertEqual(TEST_COMPACT_ABBR, provider_record['compact'])
        self.assertEqual(provider_data['providerId'], provider_record['providerId'])
        self.assertEqual('test@example.com', provider_record['compactConnectRegisteredEmailAddress'])

    @patch('handlers.registration.verify_recaptcha')
    def test_registration_returns_200_if_dob_does_not_match(self, mock_verify_recaptcha):
        mock_verify_recaptcha.return_value = True
        self._add_mock_provider_records(license_data_overrides={'dateOfBirth': '1990-02-02'})
        from handlers.registration import register_provider

        response = register_provider(self._get_test_event(), self.mock_context)
        self.assertEqual(200, response['statusCode'])
        self.assertEqual({'message': 'request processed'}, json.loads(response['body']))

    @patch('handlers.registration.verify_recaptcha')
    def test_registration_returns_200_if_license_type_does_not_match(self, mock_verify_recaptcha):
        mock_verify_recaptcha.return_value = True
        self._add_mock_provider_records(license_data_overrides={'licenseType': 'audiologist'})
        from handlers.registration import register_provider

        response = register_provider(self._get_test_event(), self.mock_context)
        self.assertEqual(200, response['statusCode'])
        self.assertEqual({'message': 'request processed'}, json.loads(response['body']))

    @patch('handlers.registration.verify_recaptcha')
    def test_registration_raises_exception_if_multiple_matching_records(self, mock_verify_recaptcha):
        mock_verify_recaptcha.return_value = True
        # Add first record
        self._add_mock_provider_records()
        # Add second matching record with different provider ID
        self._add_mock_provider_records(license_data_overrides={'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c098'})

        from handlers.registration import register_provider

        with self.assertRaises(CCInternalException) as context:
            register_provider(self._get_test_event(), self.mock_context)

        self.assertEqual('Multiple matching license records found', context.exception.message)

    @patch('handlers.registration.verify_recaptcha')
    def test_registration_raises_exception_on_cognito_failure(self, mock_verify_recaptcha):
        mock_verify_recaptcha.return_value = True
        self._add_mock_provider_records()
        from handlers.registration import register_provider

        # Verify the registration fails with the expected error
        with patch('handlers.registration.config.cognito_client') as mock_cognito:
            mock_cognito.admin_create_user.side_effect = Exception('Failed to create Cognito user')
            with self.assertRaises(CCInternalException) as context:
                register_provider(self._get_test_event(), self.mock_context)
            self.assertEqual('Failed to create user account', context.exception.message)

    @patch('handlers.registration.verify_recaptcha')
    def test_registration_rolls_back_cognito_user_on_dynamo_transaction_failure(self, mock_verify_recaptcha):
        mock_verify_recaptcha.return_value = True
        provider_data, license_data = self._add_mock_provider_records(is_registered=False)
        # Mock DynamoDB to fail the transaction
        from botocore.exceptions import ClientError
        from handlers.registration import register_provider

        with patch('handlers.registration.config.dynamodb_client') as mock_dynamo:
            mock_dynamo.transact_write_items.side_effect = ClientError(
                {
                    'Error': {
                        'Code': 'TransactionCanceledException',
                        'Message': 'Transaction cancelled, please refer cancellation reasons for specific reasons',
                    }
                },
                'TransactWriteItems',
            )

            # Verify the registration fails with the expected error
            with self.assertRaises(CCInternalException) as context:
                register_provider(self._get_test_event(), self.mock_context)
            self.assertEqual('Failed to set registration values', context.exception.message)

        # Verify no Cognito user exists for this email (it should have been deleted during rollback)
        cognito_users = self.config.cognito_client.list_users(
            UserPoolId=self.config.provider_user_pool_id, Filter='email = "test@example.com"'
        )
        self.assertEqual(0, len(cognito_users['Users']))

        # Verify the provider record was rolled back
        provider_record = self.config.provider_table.get_item(
            Key={
                'pk': f'{TEST_COMPACT_ABBR}#PROVIDER#{provider_data["providerId"]}',
                'sk': f'{TEST_COMPACT_ABBR}#PROVIDER',
            }
        ).get('Item')
        # Verify no registration information was added
        self.assertIsNone(provider_record.get('compactConnectRegisteredEmailAddress'))

    @patch('handlers.registration.verify_recaptcha')
    def test_registration_rate_limits_provider_users(self, mock_verify_recaptcha):
        """
        This test checks that the registration endpoint rate limits provider users.
        """
        with patch('cc_common.config._Config.current_standard_datetime', new_callable=PropertyMock) as mock_now:
            mock_verify_recaptcha.return_value = True
            # on the first call, the datetime should be the mock datetime
            # so we can verify the rate limiting record was created
            mock_now.return_value = datetime.fromisoformat(MOCK_DATETIME_STRING)
            from handlers.registration import register_provider

            first_response = register_provider(self._get_test_event(), self.mock_context)
            self.assertEqual(200, first_response['statusCode'])
            self.assertEqual({'message': 'request processed'}, json.loads(first_response['body']))

            mock_datetime = datetime.fromisoformat(MOCK_DATETIME_STRING)
            mock_iso_timestamp = mock_datetime.isoformat()

            # Verify rate limiting record was created
            rate_limiting = self.config.rate_limiting_table.get_item(
                Key={
                    'pk': 'IP#127.0.0.1',
                    'sk': f'REGISTRATION#{mock_iso_timestamp}',
                }
            )['Item']
            # ensure the record is set to expire
            self.assertEqual(int(mock_datetime.timestamp()) + 900, rate_limiting['ttl'])

            # now call the endpoint 3 more times and expect a 429 in the response
            for attempt in range(3):
                mock_time = datetime.fromisoformat(MOCK_DATETIME_STRING)
                # increment the datetime by 1 second
                mock_time += timedelta(seconds=attempt + 1)
                mock_now.return_value = mock_time
                response = register_provider(self._get_test_event(), self.mock_context)
                # for the first 2 attempts, expect a 200
                if attempt < 2:
                    self.assertEqual(200, response['statusCode'])
                else:
                    self.assertEqual(429, response['statusCode'])

    @patch('handlers.registration.verify_recaptcha')
    def test_registration_does_not_block_users_if_beyond_15_minute_window(self, mock_verify_recaptcha):
        """
        This test checks that the registration endpoint rate limits provider users.
        """
        with patch('cc_common.config._Config.current_standard_datetime', new_callable=PropertyMock) as mock_now:
            mock_verify_recaptcha.return_value = True

            from handlers.registration import register_provider

            # call the endpoint 10 times, each incrementing by 5 minutes and expect a 200 in the response
            mock_time = datetime.fromisoformat('2025-01-23T08:00:00+00:00')
            for _ in range(10):
                # increment the datetime by 5 minutes and one second (so the limit is not exceeded)
                mock_time += timedelta(minutes=5, seconds=1)
                mock_now.return_value = mock_time
                response = register_provider(self._get_test_event(), self.mock_context)
                self.assertEqual(200, response['statusCode'])

    @patch('handlers.registration.verify_recaptcha')
    def test_registration_works_with_special_characters(self, mock_verify_recaptcha):
        """Test that registration works with special characters in names that could break key delimiters."""
        mock_verify_recaptcha.return_value = True

        # Test with various special characters that could cause issues without URL encoding
        special_chars_name = {
            'givenName': 'José#Jr',  # Contains both special chars (# and é)
            'familyName': "O'Neill/Smith",  # Contains both / and '
        }

        # Add provider records with special character names
        provider_data, license_data = self._add_mock_provider_records(license_data_overrides=special_chars_name)

        # Create test event with special character names
        event = self._get_test_event(body_overrides=special_chars_name)

        from handlers.registration import register_provider

        response = register_provider(event, self.mock_context)

        self.assertEqual(200, response['statusCode'])
        self.assertEqual({'message': 'request processed'}, json.loads(response['body']))

        # Verify Cognito user was created with correct attributes
        cognito_users = self.config.cognito_client.list_users(
            UserPoolId=self.config.provider_user_pool_id, Filter='email = "test@example.com"'
        )

        self.assertEqual(1, len(cognito_users['Users']))
        user_attributes = {attr['Name']: attr['Value'] for attr in cognito_users['Users'][0]['Attributes']}

        # We can't predict the `sub`, so we'll just make sure there is one
        sub_value = user_attributes.pop('sub', None)
        self.assertIsNotNone(sub_value, "User should have a 'sub' attribute")

        # Verify all attributes match exactly what we expect (no more, no less)
        expected_attributes = {
            'custom:compact': TEST_COMPACT_ABBR,
            'custom:providerId': provider_data['providerId'],
            'email': 'test@example.com',
            'email_verified': 'true',
        }
        self.assertEqual(expected_attributes, user_attributes)

        # Verify provider values were set
        stored_provider_record = self.config.data_client.get_provider_top_level_record(
            compact=TEST_COMPACT_ABBR, provider_id=provider_data['providerId']
        )
        self.assertEqual(
            MOCK_COMPACT_CONNECT_REGISTERED_EMAIL_ADDRESS, stored_provider_record.compactConnectRegisteredEmailAddress
        )
        self.assertEqual(MOCK_JURISDICTION_POSTAL_ABBR, stored_provider_record.currentHomeJurisdiction)

    @patch('handlers.registration.verify_recaptcha')
    def test_registration_works_with_japanese_characters(self, mock_verify_recaptcha):
        """Test that registration works with Japanese characters in names."""
        mock_verify_recaptcha.return_value = True

        # Test with Japanese characters
        japanese_name = {
            'givenName': '太郎',  # Taro
            'familyName': '山田',  # Yamada
        }

        # Add provider records with Japanese names
        provider_data, license_data = self._add_mock_provider_records(license_data_overrides=japanese_name)

        # Create test event with Japanese names
        event = self._get_test_event(body_overrides=japanese_name)

        from handlers.registration import register_provider

        response = register_provider(event, self.mock_context)

        self.assertEqual(200, response['statusCode'])
        self.assertEqual({'message': 'request processed'}, json.loads(response['body']))

        # Verify Cognito user was created with correct attributes
        cognito_users = self.config.cognito_client.list_users(
            UserPoolId=self.config.provider_user_pool_id, Filter='email = "test@example.com"'
        )

        self.assertEqual(1, len(cognito_users['Users']))
        user_attributes = {attr['Name']: attr['Value'] for attr in cognito_users['Users'][0]['Attributes']}

        # We can't predict the `sub`, so we'll just make sure there is one
        sub_value = user_attributes.pop('sub', None)
        self.assertIsNotNone(sub_value, "User should have a 'sub' attribute")

        # Verify all attributes match exactly what we expect (no more, no less)
        expected_attributes = {
            'custom:compact': TEST_COMPACT_ABBR,
            'custom:providerId': provider_data['providerId'],
            'email': 'test@example.com',
            'email_verified': 'true',
        }
        self.assertEqual(expected_attributes, user_attributes)

        # Verify provider values were set
        stored_provider_record = self.config.data_client.get_provider_top_level_record(
            compact=TEST_COMPACT_ABBR, provider_id=provider_data['providerId']
        )
        self.assertEqual(
            MOCK_COMPACT_CONNECT_REGISTERED_EMAIL_ADDRESS, stored_provider_record.compactConnectRegisteredEmailAddress
        )
        self.assertEqual(MOCK_JURISDICTION_POSTAL_ABBR, stored_provider_record.currentHomeJurisdiction)

    @patch('handlers.registration.verify_recaptcha')
    def test_registration_rejects_invalid_email(self, mock_verify_recaptcha):
        """Test that the registration handler rejects an invalid email."""
        mock_verify_recaptcha.return_value = True
        from handlers.registration import register_provider

        # Add a provider record with a valid email, just to see how
        # far the registration goes, if the invalid email is not caught
        provider_data, _license_data = self._add_mock_provider_records()

        # Create a request with an invalid email
        request_body = {
            'email': 'invalid-email',  # Invalid email format
        }

        event = self._get_test_event(body_overrides=request_body)

        resp = register_provider(event, self.mock_context)
        self.assertEqual(400, resp['statusCode'])
        body = json.loads(resp['body'])
        self.assertIn('Invalid request', body['message'])
        self.assertIn('email', body['message'])

        # Verify Cognito user was not created
        cognito_users = self.config.cognito_client.list_users(
            UserPoolId=self.config.provider_user_pool_id, Filter='email = "test@example.com"'
        )
        self.assertEqual(0, len(cognito_users['Users']))

    @patch('handlers.registration.verify_recaptcha')
    def test_registration_rejects_invalid_date_format(self, mock_verify_recaptcha):
        """Test that the registration handler rejects an invalid date format."""
        mock_verify_recaptcha.return_value = True
        from handlers.registration import register_provider

        # Create a request with an invalid date that matches the regex pattern but is still invalid
        request_body = {
            'dob': '2023-13-35',  # Invalid date (month 13, day 35) but matches regex pattern
        }

        event = self._get_test_event(body_overrides=request_body)

        resp = register_provider(event, self.mock_context)
        self.assertEqual(400, resp['statusCode'])
        body = json.loads(resp['body'])
        self.assertIn('Invalid request', body['message'])
        self.assertIn('dob', body['message'])

    @patch('handlers.registration.verify_recaptcha')
    def test_registration_creates_provider_update_record(self, mock_verify_recaptcha):
        """Test that a provider update record is created during registration."""
        from cc_common.data_model.schema.common import UpdateCategory
        from cc_common.data_model.schema.provider import ProviderUpdateData
        from handlers.registration import register_provider

        mock_verify_recaptcha.return_value = True
        provider_data, license_data = self._add_mock_provider_records_using_data_classes()

        response = register_provider(self._get_test_event(), self.mock_context)

        self.assertEqual(200, response['statusCode'])
        self.assertEqual({'message': 'request processed'}, json.loads(response['body']))

        # Verify provider update record was created
        stored_provider_update_records = (
            self.test_data_generator.query_provider_update_records_for_given_record_from_database(provider_data)
        )
        self.assertEqual(1, len(stored_provider_update_records))

        update_data = ProviderUpdateData.from_database_record(stored_provider_update_records[0])

        # Verify the update record has the correct type and fields
        self.assertEqual('providerUpdate', update_data.type)
        self.assertEqual(UpdateCategory.REGISTRATION, update_data.updateType)
        self.assertEqual(provider_data.providerId, update_data.providerId)
        self.assertEqual(TEST_COMPACT_ABBR, update_data.compact)

        # Verify the updated values in the provider update record
        self.assertEqual('test@example.com', update_data.updatedValues.get('compactConnectRegisteredEmailAddress'))
        self.assertEqual(MOCK_JURISDICTION_POSTAL_ABBR, update_data.updatedValues.get('currentHomeJurisdiction'))

        self.assertEqual(
            {
                'compact': provider_data.compact,
                'dateOfUpdate': datetime.fromisoformat(DEFAULT_DATE_OF_UPDATE_TIMESTAMP),
                'previous': {
                    'compact': provider_data.compact,
                    'currentHomeJurisdiction': provider_data.currentHomeJurisdiction,
                    'dateOfBirth': provider_data.dateOfBirth,
                    'dateOfExpiration': provider_data.dateOfExpiration,
                    'dateOfUpdate': provider_data.dateOfUpdate,
                    'familyName': provider_data.familyName,
                    'givenName': provider_data.givenName,
                    'jurisdictionUploadedCompactEligibility': provider_data.jurisdictionUploadedCompactEligibility,
                    'jurisdictionUploadedLicenseStatus': provider_data.jurisdictionUploadedLicenseStatus,
                    'licenseJurisdiction': provider_data.licenseJurisdiction,
                    'middleName': provider_data.middleName,
                    'npi': provider_data.npi,
                    'providerId': provider_data.providerId,
                    'ssnLastFour': provider_data.ssnLastFour,
                },
                'providerId': provider_data.providerId,
                'type': 'providerUpdate',
                'updateType': 'registration',
                'updatedValues': {
                    'compactConnectRegisteredEmailAddress': MOCK_COMPACT_CONNECT_REGISTERED_EMAIL_ADDRESS,
                    'currentHomeJurisdiction': 'ky',
                },
            },
            update_data.to_dict(),
        )

    @patch('handlers.registration.verify_recaptcha')
    def test_registration_strips_whitespace_from_all_string_fields(self, mock_verify_recaptcha):
        """Test that registration strips whitespace from all string fields in the request."""
        mock_verify_recaptcha.return_value = True

        # Add provider records with normal names (no whitespace)
        provider_data, license_data = self._add_mock_provider_records()

        # Create registration request with whitespace around ALL string fields
        fields_with_whitespace = {
            'givenName': f'  {MOCK_GIVEN_NAME}  ',  # Add whitespace around the name
            'familyName': f'  {MOCK_FAMILY_NAME}  ',  # Add whitespace around the name
            'email': '  test@example.com  ',  # Add whitespace around email
            'partialSocial': f'  {MOCK_SSN_LAST_FOUR}  ',  # Add whitespace around SSN
            'jurisdiction': f'  {MOCK_JURISDICTION_POSTAL_ABBR}  ',  # Add whitespace around jurisdiction
            'licenseType': f'  {TEST_LICENSE_TYPE}  ',  # Add whitespace around license type
            'compact': f'  {TEST_COMPACT_ABBR}  ',  # Add whitespace around compact
            'token': '  valid_token  ',  # Add whitespace around token
        }

        from handlers.registration import register_provider

        event = self._get_test_event(body_overrides=fields_with_whitespace)
        response = register_provider(event, self.mock_context)

        # Verify registration succeeds despite whitespace on all fields
        self.assertEqual(200, response['statusCode'])
        self.assertEqual({'message': 'request processed'}, json.loads(response['body']))

        # Verify provider record was updated (confirming the match worked)
        provider_record = self.config.provider_table.get_item(
            Key={
                'pk': f'{TEST_COMPACT_ABBR}#PROVIDER#{provider_data["providerId"]}',
                'sk': f'{TEST_COMPACT_ABBR}#PROVIDER',
            }
        )['Item']

        # If the registration worked, the email should be set
        self.assertEqual('test@example.com', provider_record['compactConnectRegisteredEmailAddress'])

        # Verify Cognito user was created with the correct email (proving email whitespace was stripped)
        cognito_users = self.config.cognito_client.list_users(
            UserPoolId=self.config.provider_user_pool_id, Filter='email = "test@example.com"'
        )
        self.assertEqual(1, len(cognito_users['Users']))

        # Verify the Cognito user has the correct attributes (proving all fields were processed correctly)
        user_attributes = {attr['Name']: attr['Value'] for attr in cognito_users['Users'][0]['Attributes']}
        self.assertEqual(TEST_COMPACT_ABBR, user_attributes['custom:compact'])
        self.assertEqual(provider_data['providerId'], user_attributes['custom:providerId'])
        self.assertEqual('test@example.com', user_attributes['email'])

        mock_verify_recaptcha.assert_called_with('valid_token')
