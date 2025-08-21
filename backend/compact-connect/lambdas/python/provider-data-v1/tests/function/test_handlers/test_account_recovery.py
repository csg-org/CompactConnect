import json
from datetime import date, datetime, timedelta
from functools import wraps
from unittest.mock import MagicMock, PropertyMock, patch

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
MOCK_PASSWORD = 'somePassword10!0'  # noqa: S105 this is not a real secret

mock_email_notification_service = MagicMock()


def return_valid_recaptcha(token):  # noqa: ARG001
    return True


def return_invalid_recaptcha(token):  # noqa: ARG001
    return False


def generate_test_initiate_account_recovery_request():
    return {
        'username': MOCK_COMPACT_CONNECT_REGISTERED_EMAIL_ADDRESS,
        'password': MOCK_PASSWORD,
        'compact': TEST_COMPACT_ABBR,
        'recaptchaToken': 'valid_token',
        'givenName': MOCK_GIVEN_NAME,
        'familyName': MOCK_FAMILY_NAME,
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
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat(MOCK_DATETIME_STRING))
@patch('handlers.account_recovery.config.email_service_client', mock_email_notification_service)
class TestInitiateAccountRecovery(TstFunction):
    def setUp(self):
        super().setUp()
        patch('cc_common.utils.delayed_function', mock_delay_decorator).start()

    def _get_api_event(self):
        return self.test_data_generator.generate_test_api_event()

    def _when_license_record_matches(self, is_registered=True):
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'ssnLastFour': MOCK_SSN_LAST_FOUR,
                'dateOfBirth': date.fromisoformat(MOCK_DOB),
                'licenseType': TEST_LICENSE_TYPE,
                'givenName': MOCK_GIVEN_NAME,
                'familyName': MOCK_FAMILY_NAME,
                'jurisdiction': MOCK_JURISDICTION_POSTAL_ABBR,
                'compact': TEST_COMPACT_ABBR,
                'providerId': MOCK_PROVIDER_ID,
            }
        )

        provider_value_overrides = {
            'compact': TEST_COMPACT_ABBR,
            'providerId': MOCK_PROVIDER_ID,
        }
        if is_registered:
            provider_value_overrides.update(
                {
                    'compactConnectRegisteredEmailAddress': MOCK_COMPACT_CONNECT_REGISTERED_EMAIL_ADDRESS,
                    'currentHomeJurisdiction': MOCK_JURISDICTION_POSTAL_ABBR,
                }
            )

            self._create_provider_cognito_user(
                email=MOCK_COMPACT_CONNECT_REGISTERED_EMAIL_ADDRESS,
                provider_id=MOCK_PROVIDER_ID,
                compact=TEST_COMPACT_ABBR,
                password=MOCK_PASSWORD,
            )

        self.test_data_generator.put_default_provider_record_in_provider_table(
            value_overrides=provider_value_overrides, is_registered=is_registered
        )

    def _get_test_event(self, body_overrides=None):
        """Helper to get a test event with optional body overrides."""
        event = self._get_api_event()
        event['httpMethod'] = 'POST'
        body = generate_test_initiate_account_recovery_request()
        if body_overrides:
            body.update(body_overrides)
        event['body'] = json.dumps(body)
        return event

    @patch('handlers.account_recovery.verify_recaptcha', return_valid_recaptcha)
    def test_initiate_account_recovery_returns_generic_200_if_no_license_match(self):
        from handlers.account_recovery import initiate_account_recovery

        # in this test, we have not added any license records to the db, so there will be no match
        response = initiate_account_recovery(self._get_test_event(), self.mock_context)

        self.assertEqual(200, response['statusCode'])
        self.assertEqual(
            {'message': 'request processed'},
            json.loads(response['body']),
        )

    @patch('handlers.account_recovery.verify_recaptcha', return_invalid_recaptcha)
    def test_initiate_account_recovery_returns_generic_200_if_recaptcha_fails(self):
        from handlers.account_recovery import initiate_account_recovery

        self._when_license_record_matches()
        # in this test, the license would match, but the recaptcha token fails
        response = initiate_account_recovery(self._get_test_event(), self.mock_context)

        self.assertEqual(200, response['statusCode'])
        self.assertEqual(
            {'message': 'request processed'},
            json.loads(response['body']),
        )

    @patch('handlers.account_recovery.verify_recaptcha', return_valid_recaptcha)
    def test_initiate_account_recovery_returns_generic_200_if_provider_not_registered(self):
        from handlers.account_recovery import initiate_account_recovery

        self._when_license_record_matches(is_registered=False)
        # in this test, the license matches, but the provider has not registered yet
        # the endpoint returns a generic 200
        response = initiate_account_recovery(self._get_test_event(), self.mock_context)

        self.assertEqual(200, response['statusCode'])
        self.assertEqual(
            {'message': 'request processed'},
            json.loads(response['body']),
        )

    @patch('handlers.account_recovery.verify_recaptcha', return_valid_recaptcha)
    def test_initiate_account_recovery_returns_generic_200_if_provided_email_does_not_match_with_registered_email(self):
        from handlers.account_recovery import initiate_account_recovery

        self._when_license_record_matches()
        # in this test, the license matches, but the passed in email address
        # does not match with what the provider is currently registered with
        response = initiate_account_recovery(
            self._get_test_event(body_overrides={'username': 'some-other-email@invalid.com'}), self.mock_context
        )

        self.assertEqual(200, response['statusCode'])
        self.assertEqual(
            {'message': 'request processed'},
            json.loads(response['body']),
        )

    @patch('handlers.account_recovery.verify_recaptcha', return_valid_recaptcha)
    def test_initiate_account_recovery_returns_generic_200_if_rate_limited(self):
        from handlers.account_recovery import initiate_account_recovery

        self._when_license_record_matches()

        with patch('cc_common.config._Config.current_standard_datetime', new_callable=PropertyMock) as mock_now:
            for attempt, password in enumerate(['wrongPassword1', 'notEvenClose2', 'anotherAttempt', MOCK_PASSWORD]):
                mock_time = datetime.fromisoformat(MOCK_DATETIME_STRING)
                # increment the datetime by 1 second
                mock_time += timedelta(seconds=attempt + 1)
                mock_now.return_value = mock_time
                # in this test, the license matches, but the caller has attempted to match this
                # password more than 3 times in the last hour, they will be rate limited
                response = initiate_account_recovery(
                    self._get_test_event(body_overrides={'password': password}), self.mock_context
                )

                self.assertEqual(200, response['statusCode'])
                self.assertEqual(
                    {'message': 'request processed'},
                    json.loads(response['body']),
                )

            # verify the attempts were recorded
            window_end = self.config.current_standard_datetime + timedelta(seconds=5)
            window_start = window_end - timedelta(hours=1)
            response = self.config.rate_limiting_table.query(
                KeyConditionExpression='pk = :pk AND sk BETWEEN :start_sk AND :end_sk',
                ExpressionAttributeValues={
                    ':pk': f'PROVIDER#{TEST_COMPACT_ABBR.lower()}#{MOCK_PROVIDER_ID}',
                    ':start_sk': f'MFARECOVERY#{window_start.isoformat()}',
                    ':end_sk': f'MFARECOVERY#{window_end.isoformat()}',
                },
                Select='COUNT',
                ConsistentRead=True,
            )
            self.assertEqual(4, response['Count'])

            # ensure the provider record was not updated with the temp token
            provider_record = self.config.data_client.get_provider_top_level_record(
                compact=TEST_COMPACT_ABBR, provider_id=MOCK_PROVIDER_ID
            )

            # ensure the email was not sent
            mock_email_notification_service.send_provider_account_recovery_confirmation_email.assert_not_called()

            self.assertIsNone(provider_record.recoveryToken)
            self.assertIsNone(provider_record.recoveryExpiry)

    @patch('handlers.account_recovery.verify_recaptcha', return_valid_recaptcha)
    def test_initiate_account_recovery_sends_email_if_authenticated(self):
        from handlers.account_recovery import initiate_account_recovery

        self._when_license_record_matches()

        mock_secret = 'some-url-encoded-secret-string'  # noqa: S105 this is not a real secret
        with patch('handlers.account_recovery.secrets') as mock_secrets:
            mock_secrets.token_urlsafe.return_value = mock_secret
            response = initiate_account_recovery(self._get_test_event(), self.mock_context)
            self.assertEqual(200, response['statusCode'])
            self.assertEqual(
                {'message': 'request processed'},
                json.loads(response['body']),
            )

        # ensure the provider record was not updated with the temp token
        provider_record = self.config.data_client.get_provider_top_level_record(
            compact=TEST_COMPACT_ABBR, provider_id=MOCK_PROVIDER_ID
        )

        self.assertIsNotNone(provider_record.recoveryToken)
        # ensure the expiry is 15 minutes from now
        self.assertEqual(
            (self.config.current_standard_datetime + timedelta(minutes=15)), provider_record.recoveryExpiry
        )

        # ensure the email was not sent
        mock_email_notification_service.send_provider_account_recovery_confirmation_email.assert_called_once_with(
            compact=TEST_COMPACT_ABBR,
            provider_email=provider_record.compactConnectRegisteredEmailAddress,
            provider_id=MOCK_PROVIDER_ID,
            recovery_token=mock_secret,
        )


MOCK_RECOVERY_TOKEN = 'some-mock-recovery-string'  # noqa: S105 this is not a real secret


def generate_test_verify_account_recovery_request():
    return {
        'compact': TEST_COMPACT_ABBR,
        'providerId': MOCK_PROVIDER_ID,
        'recoveryToken': MOCK_RECOVERY_TOKEN,
        'recaptchaToken': 'valid_token',
    }


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat(MOCK_DATETIME_STRING))
class TestVerifyAccountRecovery(TstFunction):
    def setUp(self):
        super().setUp()
        patch('cc_common.utils.delayed_function', mock_delay_decorator).start()

    def _get_api_event(self):
        return self.test_data_generator.generate_test_api_event()

    def _when_recovery_token_on_provider_record(self):
        from cc_common.utils import hash_password

        self._create_provider_cognito_user(
            email=MOCK_COMPACT_CONNECT_REGISTERED_EMAIL_ADDRESS,
            provider_id=MOCK_PROVIDER_ID,
            compact=TEST_COMPACT_ABBR,
            password=MOCK_PASSWORD,
        )

        provider_value_overrides = {
            'compact': TEST_COMPACT_ABBR,
            'providerId': MOCK_PROVIDER_ID,
            'compactConnectRegisteredEmailAddress': MOCK_COMPACT_CONNECT_REGISTERED_EMAIL_ADDRESS,
            'currentHomeJurisdiction': MOCK_JURISDICTION_POSTAL_ABBR,
            'recoveryToken': hash_password(MOCK_RECOVERY_TOKEN),  # Store hashed version in DB
            'recoveryExpiry': datetime.fromisoformat(MOCK_DATETIME_STRING) + timedelta(minutes=15),
        }

        self.test_data_generator.put_default_provider_record_in_provider_table(
            value_overrides=provider_value_overrides, is_registered=True
        )

    def _when_no_recovery_token_on_provider_record(self):
        self._create_provider_cognito_user(
            email=MOCK_COMPACT_CONNECT_REGISTERED_EMAIL_ADDRESS,
            provider_id=MOCK_PROVIDER_ID,
            compact=TEST_COMPACT_ABBR,
            password=MOCK_PASSWORD,
        )

        provider_value_overrides = {
            'compact': TEST_COMPACT_ABBR,
            'providerId': MOCK_PROVIDER_ID,
            'compactConnectRegisteredEmailAddress': MOCK_COMPACT_CONNECT_REGISTERED_EMAIL_ADDRESS,
            'currentHomeJurisdiction': MOCK_JURISDICTION_POSTAL_ABBR,
        }

        self.test_data_generator.put_default_provider_record_in_provider_table(
            value_overrides=provider_value_overrides, is_registered=True
        )

    def _get_test_event(self, body_overrides=None):
        """Helper to get a test event with optional body overrides."""
        event = self._get_api_event()
        event['httpMethod'] = 'POST'
        body = generate_test_verify_account_recovery_request()
        if body_overrides:
            body.update(body_overrides)
        event['body'] = json.dumps(body)
        return event

    @patch('handlers.account_recovery.verify_recaptcha', return_valid_recaptcha)
    def test_verify_account_recovery_removes_recovery_fields_if_successful_verification(self):
        from handlers.account_recovery import verify_account_recovery

        self._when_recovery_token_on_provider_record()
        response = verify_account_recovery(self._get_test_event(), self.mock_context)

        self.assertEqual(200, response['statusCode'])
        self.assertEqual(
            {'message': 'request processed'},
            json.loads(response['body']),
        )

        # ensure the temp recovery fields were removed from the provider record
        provider_record = self.config.data_client.get_provider_top_level_record(
            compact=TEST_COMPACT_ABBR, provider_id=MOCK_PROVIDER_ID
        )

        self.assertIsNone(provider_record.recoveryToken)
        self.assertIsNone(provider_record.recoveryExpiry)

    @patch('handlers.account_recovery.verify_recaptcha', return_valid_recaptcha)
    def test_verify_account_recovery_recreates_cognito_user_account(self):
        from handlers.account_recovery import verify_account_recovery

        self._when_recovery_token_on_provider_record()
        with patch('handlers.account_recovery.config.cognito_client') as mock_cognito_client:
            response = verify_account_recovery(self._get_test_event(), self.mock_context)

            self.assertEqual(200, response['statusCode'])
            self.assertEqual(
                {'message': 'request processed'},
                json.loads(response['body']),
            )

            mock_cognito_client.admin_delete_user.assert_called_once_with(
                UserPoolId=self.config.provider_user_pool_id, Username=MOCK_COMPACT_CONNECT_REGISTERED_EMAIL_ADDRESS
            )
            mock_cognito_client.admin_create_user.assert_called_once_with(
                UserPoolId=self.config.provider_user_pool_id,
                Username=MOCK_COMPACT_CONNECT_REGISTERED_EMAIL_ADDRESS,
                UserAttributes=[
                    {'Name': 'custom:compact', 'Value': TEST_COMPACT_ABBR},
                    {'Name': 'custom:providerId', 'Value': MOCK_PROVIDER_ID},
                    {'Name': 'email', 'Value': MOCK_COMPACT_CONNECT_REGISTERED_EMAIL_ADDRESS},
                    {'Name': 'email_verified', 'Value': 'true'},
                ],
            )

    @patch('handlers.account_recovery.verify_recaptcha', return_invalid_recaptcha)
    def test_verify_account_recovery_returns_failure_if_recaptcha_fails(self):
        from handlers.account_recovery import verify_account_recovery

        self._when_recovery_token_on_provider_record()
        response = verify_account_recovery(self._get_test_event(), self.mock_context)

        self.assertEqual(403, response['statusCode'])
        self.assertEqual(
            {'message': 'Access denied'},
            json.loads(response['body']),
        )

        # ensure the temp recovery fields were not removed
        provider_record = self.config.data_client.get_provider_top_level_record(
            compact=TEST_COMPACT_ABBR, provider_id=MOCK_PROVIDER_ID
        )

        self.assertIsNotNone(provider_record.recoveryToken)
        self.assertIsNotNone(provider_record.recoveryExpiry)

    @patch('handlers.account_recovery.verify_recaptcha', return_valid_recaptcha)
    def test_verify_account_recovery_rate_limits_caller_for_same_provider_account(self):
        from handlers.account_recovery import verify_account_recovery

        self._when_recovery_token_on_provider_record()
        with patch('cc_common.config._Config.current_standard_datetime', new_callable=PropertyMock) as mock_now:
            for attempt, token in enumerate(['wrongToken1', 'notEvenClose2', MOCK_RECOVERY_TOKEN]):
                mock_time = datetime.fromisoformat(MOCK_DATETIME_STRING)
                # increment the datetime by 1 second
                mock_time += timedelta(seconds=attempt + 1)
                mock_now.return_value = mock_time
                response = verify_account_recovery(
                    self._get_test_event(body_overrides={'recoveryToken': token}), self.mock_context
                )
                if attempt < 2:
                    # the first two requests fail due to invalid token
                    self.assertEqual(400, response['statusCode'])
                    self.assertEqual(
                        {'message': 'Invalid or expired recovery link'},
                        json.loads(response['body']),
                    )
                else:
                    # on the third attempt, the caller is rate limited
                    self.assertEqual(429, response['statusCode'])
                    self.assertEqual(
                        {'message': 'Please try again later.'},
                        json.loads(response['body']),
                    )

        # ensure the temp recovery fields were not removed
        provider_record = self.config.data_client.get_provider_top_level_record(
            compact=TEST_COMPACT_ABBR, provider_id=MOCK_PROVIDER_ID
        )

        self.assertIsNotNone(provider_record.recoveryToken)
        self.assertIsNotNone(provider_record.recoveryExpiry)

    @patch('handlers.account_recovery.verify_recaptcha', return_valid_recaptcha)
    def test_verify_account_recovery_removes_recovery_fields_if_token_expired(self):
        from handlers.account_recovery import verify_account_recovery

        self._when_recovery_token_on_provider_record()
        with patch('cc_common.config._Config.current_standard_datetime', new_callable=PropertyMock) as mock_now:
            mock_time = datetime.fromisoformat(MOCK_DATETIME_STRING)
            # increment the datetime by 16 minutes (1 minute past expiry datetime)
            mock_time += timedelta(minutes=16)
            mock_now.return_value = mock_time
            response = verify_account_recovery(self._get_test_event(), self.mock_context)
            # token is valid, but past expiry
            self.assertEqual(400, response['statusCode'])
            self.assertEqual(
                {'message': 'Invalid or expired recovery link'},
                json.loads(response['body']),
            )

        # ensure the temp recovery fields were removed
        provider_record = self.config.data_client.get_provider_top_level_record(
            compact=TEST_COMPACT_ABBR, provider_id=MOCK_PROVIDER_ID
        )

        self.assertIsNone(provider_record.recoveryToken)
        self.assertIsNone(provider_record.recoveryExpiry)

    @patch('handlers.account_recovery.verify_recaptcha', return_valid_recaptcha)
    def test_verify_account_recovery_returns_invalid_response_if_no_token_on_provider_record(self):
        from handlers.account_recovery import verify_account_recovery

        self._when_no_recovery_token_on_provider_record()
        response = verify_account_recovery(self._get_test_event(), self.mock_context)

        self.assertEqual(400, response['statusCode'])
        self.assertEqual(
            {'message': 'Invalid or expired recovery link'},
            json.loads(response['body']),
        )

    @patch('handlers.account_recovery.verify_recaptcha', return_valid_recaptcha)
    def test_verify_account_recovery_returns_invalid_response_if_no_provider_record(self):
        from handlers.account_recovery import verify_account_recovery

        # In this test setup, we don't create the provider record, which will trigger the
        # not found branch and return a 400 response
        response = verify_account_recovery(self._get_test_event(), self.mock_context)

        self.assertEqual(400, response['statusCode'])
        self.assertEqual(
            {'message': 'Invalid or expired recovery link'},
            json.loads(response['body']),
        )
