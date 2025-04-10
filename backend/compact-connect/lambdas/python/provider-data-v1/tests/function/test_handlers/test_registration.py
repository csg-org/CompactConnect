import json
from datetime import datetime, timedelta
from unittest.mock import PropertyMock, patch

from cc_common.exceptions import CCInternalException
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


def generate_default_compact_config_overrides():
    return {
        'pk': f'{TEST_COMPACT_ABBR}#CONFIGURATION',
        'sk': f'{TEST_COMPACT_ABBR}#CONFIGURATION',
        'compactAbbr': TEST_COMPACT_ABBR,
        'compactName': TEST_COMPACT_NAME,
        'licenseeRegistrationEnabledForEnvironments': ['test'],
    }


def generate_default_jurisdiction_config_overrides():
    return {
        'pk': f'{TEST_COMPACT_ABBR}#CONFIGURATION',
        'sk': f'{TEST_COMPACT_ABBR}#JURISDICTION#{MOCK_JURISDICTION_POSTAL_ABBR}',
        'compact': TEST_COMPACT_ABBR,
        'jurisdictionName': MOCK_JURISDICTION_NAME,
        'postalAbbreviation': MOCK_JURISDICTION_POSTAL_ABBR,
        'licenseeRegistrationEnabledForEnvironments': ['test'],
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


@mock_aws
class TestProviderRegistration(TstFunction):
    def setUp(self):
        super().setUp()

        self._load_compact_configuration(overrides=generate_default_compact_config_overrides())
        self._load_jurisdiction_configuration(overrides=generate_default_jurisdiction_config_overrides())

    def _add_mock_provider_records(self, *, is_registered=False, license_data_overrides=None):
        """
        Adds mock provider and license records to the provider table with customizable data.

        :param bool is_registered: If true, addd a home jurisdiction selection record for the provider
        :param dict license_data_overrides: Optional overrides for the license data
        """
        from cc_common.data_model.schema.home_jurisdiction.record import ProviderHomeJurisdictionSelectionRecordSchema
        from cc_common.data_model.schema.license.record import LicenseRecordSchema

        with open('../common/tests/resources/dynamo/provider.json') as f:
            provider_data = json.load(f)
            provider_data['providerId'] = MOCK_PROVIDER_ID
            if is_registered:
                provider_data['cognitoSub'] = MOCK_COGNITO_SUB
            else:
                provider_data.pop('cognitoSub', None)
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

        if is_registered:
            home_jurisdiction_schema = ProviderHomeJurisdictionSelectionRecordSchema()
            home_jurisdiction_record = {
                'type': 'homeJurisdictionSelection',
                'compact': TEST_COMPACT_ABBR,
                'providerId': MOCK_PROVIDER_ID,
                'jurisdiction': MOCK_JURISDICTION_POSTAL_ABBR,
                'dateOfSelection': datetime.fromisoformat('2024-01-01T00:00:00Z'),
            }
            serialized_record = home_jurisdiction_schema.dump(home_jurisdiction_record)
            self.config.provider_table.put_item(Item=serialized_record)

        return provider_data, license_data

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
        compact_config_overrides.update({'licenseeRegistrationEnabledForEnvironments': []})
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
    def test_registration_returns_400_if_jurisdiction_is_not_enabled_for_registration(self, mock_verify_recaptcha):
        jurisdiction_config_overrides = generate_default_jurisdiction_config_overrides()
        # in this case, no environments are enabled for registration
        jurisdiction_config_overrides.update({'licenseeRegistrationEnabledForEnvironments': []})
        self._load_jurisdiction_configuration(overrides=jurisdiction_config_overrides)
        mock_verify_recaptcha.return_value = True
        from handlers.registration import register_provider

        response = register_provider(self._get_test_event(), self.mock_context)
        self.assertEqual(400, response['statusCode'])
        self.assertEqual(
            {'message': 'Registration is not currently available for Kentucky.'}, json.loads(response['body'])
        )

    @patch('handlers.registration.verify_recaptcha')
    def test_registration_returns_400_if_jurisdiction_is_not_configured_for_registration(self, mock_verify_recaptcha):
        mock_verify_recaptcha.return_value = True
        from handlers.registration import register_provider

        response = register_provider(self._get_test_event(body_overrides={'jurisdiction': 'oh'}), self.mock_context)
        self.assertEqual(400, response['statusCode'])
        self.assertEqual(
            {'message': 'Registration is not currently available for the specified state.'},
            json.loads(response['body']),
        )

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

    @patch('handlers.registration.verify_recaptcha')
    def test_registration_returns_200_if_provider_already_registered(self, mock_verify_recaptcha):
        mock_verify_recaptcha.return_value = True
        self._add_mock_provider_records(is_registered=True)
        from handlers.registration import register_provider

        with patch('handlers.registration.config.cognito_client') as mock_cognito:
            response = register_provider(self._get_test_event(), self.mock_context)
            mock_cognito.admin_create_user.assert_not_called()

        self.assertEqual(200, response['statusCode'])
        self.assertEqual({'message': 'request processed'}, json.loads(response['body']))

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
    def test_registration_creates_home_jurisdiction_selection(self, mock_verify_recaptcha):
        mock_verify_recaptcha.return_value = True
        provider_data, license_data = self._add_mock_provider_records(is_registered=False)
        from handlers.registration import register_provider

        response = register_provider(self._get_test_event(), self.mock_context)

        self.assertEqual(200, response['statusCode'])
        self.assertEqual({'message': 'request processed'}, json.loads(response['body']))

        # Verify home jurisdiction selection record was created
        home_jurisdiction = self.config.provider_table.get_item(
            Key={
                'pk': f'{TEST_COMPACT_ABBR}#PROVIDER#{provider_data["providerId"]}',
                'sk': f'{TEST_COMPACT_ABBR}#PROVIDER#home-jurisdiction#',
            }
        )['Item']
        self.assertEqual('homeJurisdictionSelection', home_jurisdiction['type'])
        self.assertEqual(TEST_COMPACT_ABBR, home_jurisdiction['compact'])
        self.assertEqual(provider_data['providerId'], home_jurisdiction['providerId'])
        self.assertEqual(MOCK_JURISDICTION_POSTAL_ABBR, home_jurisdiction['jurisdiction'])
        self.assertIsNotNone(home_jurisdiction['dateOfSelection'])
        self.assertIsNotNone(home_jurisdiction['dateOfUpdate'])

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
        sub_value = user_attributes.pop('sub', None)

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
        # The user sub should match the value saved on the provider record
        self.assertEqual(sub_value, provider_record['cognitoSub'])

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
        # this simulates having a user shown as not registered, but another user registers for the exact same
        # account in the system at the same time. Highly unlikely, but we check here to make sure the race condition
        # is handled by the conditional expressions
        from cc_common.data_model.schema.home_jurisdiction.record import ProviderHomeJurisdictionSelectionRecordSchema
        from handlers.registration import register_provider

        home_jurisdiction_schema = ProviderHomeJurisdictionSelectionRecordSchema()
        home_jurisdiction_record = {
            'type': 'homeJurisdictionSelection',
            'compact': TEST_COMPACT_ABBR,
            'providerId': MOCK_PROVIDER_ID,
            'jurisdiction': MOCK_JURISDICTION_POSTAL_ABBR,
            'dateOfSelection': datetime.fromisoformat('2024-01-01T00:00:00Z'),
        }
        serialized_record = home_jurisdiction_schema.dump(home_jurisdiction_record)
        self.config.provider_table.put_item(Item=serialized_record)

        # Verify the registration fails with the expected error
        with self.assertRaises(CCInternalException) as context:
            register_provider(self._get_test_event(), self.mock_context)
        self.assertEqual('Failed to set registration values', context.exception.message)

        # Verify no Cognito user exists for this email (it should have been deleted during rollback)
        cognito_users = self.config.cognito_client.list_users(
            UserPoolId=self.config.provider_user_pool_id, Filter='email = "test@example.com"'
        )
        self.assertEqual(0, len(cognito_users['Users']))

        # Verify the provider record was rolled back and the cognitoSub is not present
        provider_record = self.config.provider_table.get_item(
            Key={
                'pk': f'{TEST_COMPACT_ABBR}#PROVIDER#{provider_data["providerId"]}',
                'sk': f'{TEST_COMPACT_ABBR}#PROVIDER',
            }
        ).get('Item')
        self.assertIsNone(provider_record.get('cognitoSub'))

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

        # Verify home jurisdiction selection record was created
        home_jurisdiction = self.config.provider_table.get_item(
            Key={
                'pk': f'{TEST_COMPACT_ABBR}#PROVIDER#{provider_data["providerId"]}',
                'sk': f'{TEST_COMPACT_ABBR}#PROVIDER#home-jurisdiction#',
            }
        )['Item']
        self.assertEqual('homeJurisdictionSelection', home_jurisdiction['type'])
        self.assertEqual(TEST_COMPACT_ABBR, home_jurisdiction['compact'])
        self.assertEqual(provider_data['providerId'], home_jurisdiction['providerId'])
        self.assertEqual(MOCK_JURISDICTION_POSTAL_ABBR, home_jurisdiction['jurisdiction'])
        self.assertIsNotNone(home_jurisdiction['dateOfSelection'])
        self.assertIsNotNone(home_jurisdiction['dateOfUpdate'])

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

        # Verify home jurisdiction selection record was created
        home_jurisdiction = self.config.provider_table.get_item(
            Key={
                'pk': f'{TEST_COMPACT_ABBR}#PROVIDER#{provider_data["providerId"]}',
                'sk': f'{TEST_COMPACT_ABBR}#PROVIDER#home-jurisdiction#',
            }
        )['Item']
        self.assertEqual('homeJurisdictionSelection', home_jurisdiction['type'])
        self.assertEqual(TEST_COMPACT_ABBR, home_jurisdiction['compact'])
        self.assertEqual(provider_data['providerId'], home_jurisdiction['providerId'])
        self.assertEqual(MOCK_JURISDICTION_POSTAL_ABBR, home_jurisdiction['jurisdiction'])
        self.assertIsNotNone(home_jurisdiction['dateOfSelection'])
        self.assertIsNotNone(home_jurisdiction['dateOfUpdate'])

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
