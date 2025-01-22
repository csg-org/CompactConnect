import json
from datetime import datetime
from unittest.mock import patch

from cc_common.exceptions import CCInternalException
from moto import mock_aws

from .. import TstFunction

TEST_COMPACT = 'aslp'
TEST_LICENSE_TYPE = 'speech and language pathologist'

MOCK_SSN_LAST_FOUR = '1234'
MOCK_GIVEN_NAME = 'Joe'
MOCK_FAMILY_NAME = 'Dokes'
MOCK_STATE = 'ky'
MOCK_DOB = '1990-01-01'
# this is the provider id defined in the test resource files
MOCK_PROVIDER_ID = '89a6377e-c3a5-40e5-bca5-317ec854c570'


def generate_test_request():
    return {
        'compact': TEST_COMPACT,
        'token': 'valid_token',
        'familyName': MOCK_FAMILY_NAME,
        'givenName': MOCK_GIVEN_NAME,
        'email': 'test@example.com',
        'partialSocial': MOCK_SSN_LAST_FOUR,
        'dob': MOCK_DOB,
        'state': MOCK_STATE,
        'licenseType': TEST_LICENSE_TYPE,
    }


@mock_aws
class TestProviderRegistration(TstFunction):
    def _add_mock_provider_records(self, *, is_registered=False, license_data_overrides=None):
        """
        Adds mock provider and license records to the provider table with customizable data.

        Args:
            is_registered (bool): If true, addd a home jurisdiction selection record for the provider
            license_data_overrides (dict): Optional overrides for the license data
        """
        from cc_common.data_model.schema.home_jurisdiction.record import ProviderHomeJurisdictionSelectionRecordSchema
        from cc_common.data_model.schema.license.record import LicenseRecordSchema

        with open('../common/tests/resources/dynamo/provider.json') as f:
            provider_data = json.load(f)
            provider_data['providerId'] = MOCK_PROVIDER_ID
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
                    'jurisdiction': MOCK_STATE,
                    'compact': TEST_COMPACT,
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
                'compact': TEST_COMPACT,
                'providerId': MOCK_PROVIDER_ID,
                'jurisdiction': MOCK_STATE,
                'dateOfSelection': datetime.fromisoformat('2024-01-01T00:00:00Z'),
                'dateOfUpdate': datetime.fromisoformat('2024-01-01T00:00:00Z'),
            }
            serialized_record = home_jurisdiction_schema.dump(home_jurisdiction_record)
            self.config.provider_table.put_item(Item=serialized_record)

        return provider_data, license_data

    def get_api_event(self):
        with open('../common/tests/resources/api-event.json') as f:
            return json.load(f)

    def _get_test_event(self, body_overrides=None):
        """Helper to get a test event with optional body overrides."""
        event = self.get_api_event()
        body = generate_test_request()
        if body_overrides:
            body.update(body_overrides)
        event['body'] = json.dumps(body)
        return event

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
        self._add_mock_provider_records(
            license_data_overrides={'ssnLastFour': '9876', 'ssn': '123-12-9876'}
        )  # Different SSN
        from handlers.registration import register_provider

        response = register_provider(self._get_test_event(), self.mock_context)
        self.assertEqual(200, response['statusCode'])
        self.assertEqual({'message': 'request processed'}, json.loads(response['body']))

    @patch('handlers.registration.verify_recaptcha')
    @patch('cc_common.config._Config.cognito_client')
    def test_registration_returns_200_if_provider_already_registered(self, mock_cognito, mock_verify_recaptcha):
        mock_verify_recaptcha.return_value = True
        self._add_mock_provider_records(is_registered=True)
        from handlers.registration import register_provider

        response = register_provider(self._get_test_event(), self.mock_context)
        self.assertEqual(200, response['statusCode'])
        self.assertEqual({'message': 'request processed'}, json.loads(response['body']))
        mock_cognito.admin_create_user.assert_not_called()

    @patch('handlers.registration.verify_recaptcha')
    @patch('cc_common.config._Config.cognito_client')
    def test_registration_creates_cognito_user(self, mock_cognito, mock_verify_recaptcha):
        mock_verify_recaptcha.return_value = True
        provider_data, license_data = self._add_mock_provider_records()
        from handlers.registration import register_provider

        response = register_provider(self._get_test_event(), self.mock_context)

        self.assertEqual(200, response['statusCode'])
        self.assertEqual({'message': 'request processed'}, json.loads(response['body']))

        # Verify Cognito user was created with correct attributes
        mock_cognito.admin_create_user.assert_called_once_with(
            UserPoolId=self.config.user_pool_id,
            Username='test@example.com',
            UserAttributes=[
                {'Name': 'custom:compact', 'Value': TEST_COMPACT},
                {'Name': 'custom:providerId', 'Value': provider_data['providerId']},
                {'Name': 'email', 'Value': 'test@example.com'},
                {'Name': 'email_verified', 'Value': 'true'},
            ],
        )

        # Verify home jurisdiction selection record was created
        home_jurisdiction = self.config.provider_table.get_item(
            Key={
                'pk': f'{TEST_COMPACT}#PROVIDER#{provider_data['providerId']}',
                'sk': f'{TEST_COMPACT}#PROVIDER#home-jurisdiction#',
            }
        )['Item']
        self.assertEqual('homeJurisdictionSelection', home_jurisdiction['type'])
        self.assertEqual(TEST_COMPACT, home_jurisdiction['compact'])
        self.assertEqual(provider_data['providerId'], home_jurisdiction['providerId'])
        self.assertEqual(MOCK_STATE, home_jurisdiction['jurisdiction'])
        self.assertIsNotNone(home_jurisdiction['dateOfSelection'])
        self.assertIsNotNone(home_jurisdiction['dateOfUpdate'])

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
    @patch('cc_common.config._Config.cognito_client')
    def test_registration_rolls_back_home_jurisdiction_selection_on_cognito_failure(
        self, mock_cognito, mock_verify_recaptcha
    ):
        mock_verify_recaptcha.return_value = True
        mock_cognito.admin_create_user.side_effect = Exception('Failed to create Cognito user')
        provider_data, license_data = self._add_mock_provider_records()
        from handlers.registration import register_provider

        # Verify the registration fails with the expected error
        with self.assertRaises(CCInternalException) as context:
            register_provider(self._get_test_event(), self.mock_context)
        self.assertEqual('Failed to create user account', context.exception.message)

        # Verify the home jurisdiction selection record was rolled back (deleted)
        home_jurisdiction = self.config.provider_table.get_item(
            Key={
                'pk': f'{TEST_COMPACT}#PROVIDER#{provider_data['providerId']}',
                'sk': f'{TEST_COMPACT}#PROVIDER#home-jurisdiction#',
            }
        ).get('Item')
        self.assertIsNone(home_jurisdiction)
