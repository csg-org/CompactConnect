# ruff: noqa: ARG002 tests have mock email client which requires us to pass in an argument even when not used

import json
from datetime import datetime
from unittest.mock import patch

from common_test.test_constants import DEFAULT_COMPACT, DEFAULT_PROVIDER_ID
from moto import mock_aws

from .. import TstFunction

TEST_NEW_EMAIL = 'testNewEmail@test.com'
TEST_OLD_EMAIL = 'testOldEmail@test.com'
TEST_VERIFICATION_CODE = '1234'
# set the expiration to 15 minutes from mock datetime
TEST_TOKEN_EXPIRATION = datetime.fromisoformat('2024-11-09T00:15:00+00:00')
MOCK_CURRENT_TIME = datetime.fromisoformat('2024-11-08T23:59:59+00:00')


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', MOCK_CURRENT_TIME)
class TestPatchProviderUsersEmail(TstFunction):
    def _when_testing_provider_user_event_with_custom_claims(self, new_email=TEST_NEW_EMAIL):
        self.test_data_generator.put_default_provider_record_in_provider_table(
            value_overrides={
                'compactConnectRegisteredEmailAddress': TEST_OLD_EMAIL,
            }
        )
        event = self.test_data_generator.generate_test_api_event()
        event['httpMethod'] = 'PATCH'
        event['resource'] = '/v1/provider-users/me/email'
        event['requestContext']['authorizer']['claims']['custom:providerId'] = DEFAULT_PROVIDER_ID
        event['requestContext']['authorizer']['claims']['custom:compact'] = DEFAULT_COMPACT
        event['body'] = json.dumps({'newEmailAddress': new_email})

        return event

    def _when_user_already_exists_with_provided_email_address(self, email):
        """Create a Cognito user with the provided email address to simulate email already in use"""
        self.config.cognito_client.admin_create_user(
            UserPoolId=self.config.provider_user_pool_id,
            Username=email,
            UserAttributes=[
                {'Name': 'email', 'Value': email},
                {'Name': 'email_verified', 'Value': 'true'},
            ],
            MessageAction='SUPPRESS',  # Don't send welcome email
        )

    @patch('cc_common.config._Config.email_service_client')
    def test_endpoint_returns_400_if_cognito_user_already_using_provided_email(self, mock_email_service_client):
        from handlers.provider_users import provider_users_api_handler

        # Create a user with the email we're trying to change to
        self._when_user_already_exists_with_provided_email_address(TEST_NEW_EMAIL)

        event = self._when_testing_provider_user_event_with_custom_claims()

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])
        resp_body = json.loads(resp['body'])
        self.assertEqual('Email address is already in use', resp_body['message'])

    @patch('cc_common.config._Config.email_service_client')
    def test_endpoint_returns_400_if_invalid_email_provided(self, mock_email_service_client):
        from handlers.provider_users import provider_users_api_handler

        # Test with invalid email format
        event = self._when_testing_provider_user_event_with_custom_claims(new_email='invalid-email')

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])
        resp_body = json.loads(resp['body'])
        self.assertEqual('Invalid email address format', resp_body['message'])

    @patch('cc_common.config._Config.email_service_client')
    def test_endpoint_returns_expected_message_response_on_success(self, mock_email_service_client):
        from handlers.provider_users import provider_users_api_handler

        event = self._when_testing_provider_user_event_with_custom_claims()

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        resp_body = json.loads(resp['body'])
        self.assertEqual({'message': 'Verification code sent to new email address'}, resp_body)

    @patch('cc_common.config._Config.email_service_client')
    def test_endpoint_sets_pending_values_on_provider_record_when_email_not_already_in_use(
        self, mock_email_service_client
    ):
        from cc_common.data_model.schema.provider import ProviderData
        from handlers.provider_users import provider_users_api_handler

        event = self._when_testing_provider_user_event_with_custom_claims()

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        # Get the updated provider record from the database
        test_provider_record = self.test_data_generator.generate_default_provider()
        stored_provider_data = ProviderData.from_database_record(
            self.test_data_generator.load_provider_data_record_from_database(test_provider_record)
        )

        # Verify pending email fields were set
        self.assertEqual(TEST_NEW_EMAIL, stored_provider_data.pendingEmailAddress)
        self.assertIsNotNone(stored_provider_data.emailVerificationCode)  # 4-digit code was generated
        self.assertEqual(4, len(stored_provider_data.emailVerificationCode))
        self.assertIsNotNone(stored_provider_data.emailVerificationExpiry)

        # Verify original email is unchanged
        self.assertEqual(TEST_OLD_EMAIL, stored_provider_data.compactConnectRegisteredEmailAddress)

    @patch('cc_common.config._Config.email_service_client')
    @patch('random.randint')
    def test_endpoint_calls_email_service_client_with_verification_code(self, mock_randint, mock_email_service_client):
        from handlers.provider_users import provider_users_api_handler

        # Mock the verification code generation
        mock_randint.return_value = 1234

        event = self._when_testing_provider_user_event_with_custom_claims()

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        # Verify email service was called with correct parameters
        mock_email_service_client.send_provider_email_verification_code.assert_called_once_with(
            compact=DEFAULT_COMPACT, provider_email=TEST_NEW_EMAIL, verification_code='1234'
        )

    @patch('cc_common.config._Config.email_service_client')
    def test_endpoint_trims_whitespace_from_email(self, mock_email_service_client):
        from cc_common.data_model.schema.provider import ProviderData
        from handlers.provider_users import provider_users_api_handler

        # Test with email that has leading and trailing whitespace (preserve case)
        email_with_whitespace = '  TestNewEmail@Test.COM  '
        expected_trimmed_email = 'TestNewEmail@Test.COM'
        event = self._when_testing_provider_user_event_with_custom_claims(new_email=email_with_whitespace)

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        # Get the updated provider record from the database
        test_provider_record = self.test_data_generator.generate_default_provider()
        stored_provider_data = ProviderData.from_database_record(
            self.test_data_generator.load_provider_data_record_from_database(test_provider_record)
        )

        # Verify email was trimmed but case was preserved
        self.assertEqual(expected_trimmed_email, stored_provider_data.pendingEmailAddress)

    @patch('cc_common.config._Config.email_service_client')
    def test_endpoint_overwrites_existing_pending_verification(self, mock_email_service_client):
        from cc_common.data_model.schema.provider import ProviderData
        from handlers.provider_users import provider_users_api_handler

        # First, make an initial email change request
        first_new_email = 'first@example.com'
        event = self._when_testing_provider_user_event_with_custom_claims(new_email=first_new_email)

        resp = provider_users_api_handler(event, self.mock_context)
        self.assertEqual(200, resp['statusCode'])

        # Get the provider record after first request
        test_provider_record = self.test_data_generator.generate_default_provider()
        stored_provider_data = ProviderData.from_database_record(
            self.test_data_generator.load_provider_data_record_from_database(test_provider_record)
        )

        first_verification_code = stored_provider_data.emailVerificationCode
        first_expiry_time = stored_provider_data.emailVerificationExpiry

        # Verify first request was stored
        self.assertEqual(first_new_email, stored_provider_data.pendingEmailAddress)
        self.assertIsNotNone(first_verification_code)
        self.assertIsNotNone(first_expiry_time)

        # Now make a second email change request to a different email
        second_new_email = 'second@example.com'
        event = self._when_testing_provider_user_event_with_custom_claims(new_email=second_new_email)

        resp = provider_users_api_handler(event, self.mock_context)
        self.assertEqual(200, resp['statusCode'])

        # Get the provider record after second request
        stored_provider_data = ProviderData.from_database_record(
            self.test_data_generator.load_provider_data_record_from_database(test_provider_record)
        )

        # Verify second request overwrote the first
        self.assertEqual(second_new_email, stored_provider_data.pendingEmailAddress)
        self.assertNotEqual(first_verification_code, stored_provider_data.emailVerificationCode)

        # Verify email service was called twice (once for each request)
        self.assertEqual(2, mock_email_service_client.send_provider_email_verification_code.call_count)

    @patch('cc_common.config._Config.email_service_client')
    def test_endpoint_sets_expiry_time_to_expected_value(self, mock_email_service_client):
        from datetime import timedelta

        from cc_common.data_model.schema.provider import ProviderData
        from handlers.provider_users import provider_users_api_handler

        event = self._when_testing_provider_user_event_with_custom_claims()

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        # Get the updated provider record from the database
        test_provider_record = self.test_data_generator.generate_default_provider()
        stored_provider_data = ProviderData.from_database_record(
            self.test_data_generator.load_provider_data_record_from_database(test_provider_record)
        )

        # Calculate expected expiry time (15 minutes from current time)
        expected_expiry = MOCK_CURRENT_TIME + timedelta(minutes=15)

        # Verify expiry time is exactly 15 minutes from request time
        self.assertEqual(expected_expiry, stored_provider_data.emailVerificationExpiry)


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
class TestPostProviderUsersEmailVerify(TstFunction):
    def _when_testing_provider_user_event_with_custom_claims(
        self, code=TEST_VERIFICATION_CODE, expiration=TEST_TOKEN_EXPIRATION
    ):
        self.test_data_generator.put_default_provider_record_in_provider_table(
            value_overrides={
                'compactConnectRegisteredEmailAddress': TEST_OLD_EMAIL,
                'pendingEmailAddress': TEST_NEW_EMAIL,
                'emailVerificationCode': '1234',
                'emailVerificationExpiry': expiration,
            }
        )

        event = self.test_data_generator.generate_test_api_event()
        event['httpMethod'] = 'POST'
        event['resource'] = '/v1/provider-users/me/email/verify'
        event['requestContext']['authorizer']['claims']['custom:providerId'] = DEFAULT_PROVIDER_ID
        event['requestContext']['authorizer']['claims']['custom:compact'] = DEFAULT_COMPACT
        event['body'] = json.dumps({'verificationCode': code})

        return event

    @patch('cc_common.config._Config.email_service_client')
    def test_endpoint_returns_400_if_no_pending_email_address_on_provider_record(self, mock_email_service_client):
        from handlers.provider_users import provider_users_api_handler

        # Create provider without pending email fields
        self.test_data_generator.put_default_provider_record_in_provider_table(
            value_overrides={
                'compactConnectRegisteredEmailAddress': TEST_OLD_EMAIL,
            }
        )

        event = self.test_data_generator.generate_test_api_event()
        event['httpMethod'] = 'POST'
        event['resource'] = '/v1/provider-users/me/email/verify'
        event['requestContext']['authorizer']['claims']['custom:providerId'] = DEFAULT_PROVIDER_ID
        event['requestContext']['authorizer']['claims']['custom:compact'] = DEFAULT_COMPACT
        event['body'] = json.dumps({'verificationCode': TEST_VERIFICATION_CODE})

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])
        resp_body = json.loads(resp['body'])
        self.assertEqual(
            'No email verification in progress. Please submit a new email address first.', resp_body['message']
        )

    @patch('cc_common.config._Config.email_service_client')
    def test_endpoint_returns_400_if_invalid_verification_code_provided(self, mock_email_service_client):
        from handlers.provider_users import provider_users_api_handler

        # Use wrong verification code
        event = self._when_testing_provider_user_event_with_custom_claims(code='9999')

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])
        resp_body = json.loads(resp['body'])
        self.assertEqual('Invalid verification code.', resp_body['message'])

    @patch('cc_common.config._Config.email_service_client')
    def test_endpoint_returns_400_if_verification_code_expired(self, mock_email_service_client):
        from handlers.provider_users import provider_users_api_handler

        # Use expired verification code (expiry in the past)
        expired_time = datetime.fromisoformat('2024-11-08T23:00:00+00:00')
        event = self._when_testing_provider_user_event_with_custom_claims(expiration=expired_time)

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])
        resp_body = json.loads(resp['body'])
        self.assertEqual(
            'Verification code has expired. Please submit another email update request.', resp_body['message']
        )

    @patch('cc_common.config._Config.email_service_client')
    def test_endpoint_returns_expected_message_response_on_success(self, mock_email_service_client):
        from handlers.provider_users import provider_users_api_handler

        # First create the old email user in Cognito so we can update it
        self.config.cognito_client.admin_create_user(
            UserPoolId=self.config.provider_user_pool_id,
            Username=TEST_OLD_EMAIL,
            UserAttributes=[
                {'Name': 'email', 'Value': TEST_OLD_EMAIL},
                {'Name': 'email_verified', 'Value': 'true'},
                {'Name': 'custom:compact', 'Value': DEFAULT_COMPACT},
                {'Name': 'custom:providerId', 'Value': DEFAULT_PROVIDER_ID},
            ],
            MessageAction='SUPPRESS',
        )

        event = self._when_testing_provider_user_event_with_custom_claims()

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        resp_body = json.loads(resp['body'])
        self.assertEqual({'message': 'Email address updated successfully'}, resp_body)

    @patch('cc_common.config._Config.email_service_client')
    def test_endpoint_deletes_pending_fields_if_verification_code_expired(self, mock_email_service_client):
        from cc_common.data_model.schema.provider import ProviderData
        from handlers.provider_users import provider_users_api_handler

        # Use expired verification code
        expired_time = datetime.fromisoformat('2024-11-08T23:00:00+00:00')
        event = self._when_testing_provider_user_event_with_custom_claims(expiration=expired_time)

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])

        # Verify pending fields were cleared
        test_provider_record = self.test_data_generator.generate_default_provider()
        stored_provider_data = ProviderData.from_database_record(
            self.test_data_generator.load_provider_data_record_from_database(test_provider_record)
        )

        # Pending fields should be cleared
        self.assertIsNone(stored_provider_data.pendingEmailAddress)
        self.assertIsNone(stored_provider_data.emailVerificationCode)
        self.assertIsNone(stored_provider_data.emailVerificationExpiry)

    @patch('cc_common.config._Config.email_service_client')
    def test_endpoint_updates_cognito_user_with_expected_values(self, mock_email_service_client):
        from handlers.provider_users import provider_users_api_handler

        # First create the old email user in Cognito so we can update it
        self.config.cognito_client.admin_create_user(
            UserPoolId=self.config.provider_user_pool_id,
            Username=TEST_OLD_EMAIL,
            UserAttributes=[
                {'Name': 'email', 'Value': TEST_OLD_EMAIL},
                {'Name': 'email_verified', 'Value': 'true'},
                {'Name': 'custom:compact', 'Value': DEFAULT_COMPACT},
                {'Name': 'custom:providerId', 'Value': DEFAULT_PROVIDER_ID},
            ],
            MessageAction='SUPPRESS',
        )

        event = self._when_testing_provider_user_event_with_custom_claims()

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        # Verify Cognito user was updated with correct attributes
        cognito_users = self.config.cognito_client.list_users(
            UserPoolId=self.config.provider_user_pool_id, Filter=f'email = "{TEST_NEW_EMAIL}"'
        )

        self.assertEqual(1, len(cognito_users['Users']))
        user_attributes = {attr['Name']: attr['Value'] for attr in cognito_users['Users'][0]['Attributes']}

        # We can't predict the `sub`, so we'll just make sure there is one
        sub_value = user_attributes.pop('sub', None)
        self.assertIsNotNone(sub_value, "User should have a 'sub' attribute")

        # Verify all attributes match exactly what we expect (no more, no less)
        expected_attributes = {
            'custom:compact': DEFAULT_COMPACT,
            'custom:providerId': DEFAULT_PROVIDER_ID,
            'email': TEST_NEW_EMAIL,
            'email_verified': 'true',
        }

        self.assertEqual(expected_attributes, user_attributes)

    @patch('cc_common.config._Config.email_service_client')
    def test_endpoint_updates_dynamo_provider_record_with_expected_values(self, mock_email_service_client):
        from cc_common.data_model.schema.provider import ProviderData
        from handlers.provider_users import provider_users_api_handler

        # First create the old email user in Cognito so we can update it
        self.config.cognito_client.admin_create_user(
            UserPoolId=self.config.provider_user_pool_id,
            Username=TEST_OLD_EMAIL,
            UserAttributes=[
                {'Name': 'email', 'Value': TEST_OLD_EMAIL},
                {'Name': 'email_verified', 'Value': 'true'},
                {'Name': 'custom:compact', 'Value': DEFAULT_COMPACT},
                {'Name': 'custom:providerId', 'Value': DEFAULT_PROVIDER_ID},
            ],
            MessageAction='SUPPRESS',
        )

        event = self._when_testing_provider_user_event_with_custom_claims()

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        # Verify provider record was updated correctly
        test_provider_record = self.test_data_generator.generate_default_provider()
        stored_provider_data = ProviderData.from_database_record(
            self.test_data_generator.load_provider_data_record_from_database(test_provider_record)
        )

        # Email should be updated
        self.assertEqual(TEST_NEW_EMAIL, stored_provider_data.compactConnectRegisteredEmailAddress)

        # Pending fields should be cleared
        self.assertIsNone(stored_provider_data.pendingEmailAddress)
        self.assertIsNone(stored_provider_data.emailVerificationCode)
        self.assertIsNone(stored_provider_data.emailVerificationExpiry)

    @patch('cc_common.config._Config.email_service_client')
    def test_endpoint_creates_dynamo_provider_update_record_with_expected_values(self, mock_email_service_client):
        from cc_common.data_model.schema.provider import ProviderUpdateData
        from handlers.provider_users import provider_users_api_handler

        # First create the old email user in Cognito so we can update it
        self.config.cognito_client.admin_create_user(
            UserPoolId=self.config.provider_user_pool_id,
            Username=TEST_OLD_EMAIL,
            UserAttributes=[
                {'Name': 'email', 'Value': TEST_OLD_EMAIL},
                {'Name': 'email_verified', 'Value': 'true'},
                {'Name': 'custom:compact', 'Value': DEFAULT_COMPACT},
                {'Name': 'custom:providerId', 'Value': DEFAULT_PROVIDER_ID},
            ],
            MessageAction='SUPPRESS',
        )

        event = self._when_testing_provider_user_event_with_custom_claims()

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        # now get all the update records for the provider
        test_provider_record = self.test_data_generator.generate_default_provider()
        stored_provider_update_records = (
            self.test_data_generator.query_provider_update_records_for_given_record_from_database(test_provider_record)
        )
        self.assertEqual(1, len(stored_provider_update_records))

        update_data = ProviderUpdateData.from_database_record(stored_provider_update_records[0])
        # the updateType should be emailChange
        self.assertEqual('emailChange', update_data.updateType)
        # the updateData should include the new email and old email for audit trail
        self.assertEqual(TEST_NEW_EMAIL, update_data.updatedValues['compactConnectRegisteredEmailAddress'])
        self.assertEqual(TEST_OLD_EMAIL, update_data.previous['compactConnectRegisteredEmailAddress'])

    @patch('cc_common.config._Config.email_service_client')
    def test_endpoint_calls_email_service_client_with_change_notification(self, mock_email_service_client):
        from handlers.provider_users import provider_users_api_handler

        # First create the old email user in Cognito so we can update it
        self.config.cognito_client.admin_create_user(
            UserPoolId=self.config.provider_user_pool_id,
            Username=TEST_OLD_EMAIL,
            UserAttributes=[
                {'Name': 'email', 'Value': TEST_OLD_EMAIL},
                {'Name': 'email_verified', 'Value': 'true'},
                {'Name': 'custom:compact', 'Value': DEFAULT_COMPACT},
                {'Name': 'custom:providerId', 'Value': DEFAULT_PROVIDER_ID},
            ],
            MessageAction='SUPPRESS',
        )

        event = self._when_testing_provider_user_event_with_custom_claims()

        resp = provider_users_api_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        # Verify email service was called to notify old email address
        mock_email_service_client.send_provider_email_change_notification.assert_called_once_with(
            compact=DEFAULT_COMPACT, old_email_address=TEST_OLD_EMAIL, new_email_address=TEST_NEW_EMAIL
        )
