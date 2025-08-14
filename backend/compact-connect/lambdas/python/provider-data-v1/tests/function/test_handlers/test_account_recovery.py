import json
from datetime import datetime, timedelta, date
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
MOCK_PASSWORD = 'somePassword10!0'


def generate_test_request():
    return {
        "username": MOCK_COMPACT_CONNECT_REGISTERED_EMAIL_ADDRESS,
        "password": MOCK_PASSWORD,
        'compact': TEST_COMPACT_ABBR,
        'recaptchaToken': 'valid_token',
        'givenName': MOCK_GIVEN_NAME,
        'familyName': MOCK_FAMILY_NAME,
        'partialSocial': MOCK_SSN_LAST_FOUR,
        'dob': MOCK_DOB,
        'jurisdiction': MOCK_JURISDICTION_POSTAL_ABBR,
        'licenseType': TEST_LICENSE_TYPE,
    }


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat(DEFAULT_DATE_OF_UPDATE_TIMESTAMP))
class TestInitiateAccountRecovery(TstFunction):

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
            provider_value_overrides.update({
                'compactConnectRegisteredEmailAddress': MOCK_COMPACT_CONNECT_REGISTERED_EMAIL_ADDRESS,
                'currentHomeJurisdiction': MOCK_JURISDICTION_POSTAL_ABBR
            })

            self._create_provider_cognito_user(
                email=MOCK_COMPACT_CONNECT_REGISTERED_EMAIL_ADDRESS,
                provider_id=MOCK_PROVIDER_ID,
                compact=TEST_COMPACT_ABBR,
                password=MOCK_PASSWORD
            )

        self.test_data_generator.put_default_provider_record_in_provider_table(
            value_overrides=provider_value_overrides, is_registered=is_registered)


    def _get_test_event(self, body_overrides=None):
        """Helper to get a test event with optional body overrides."""
        event = self._get_api_event()
        event['httpMethod'] = 'POST'
        body = generate_test_request()
        if body_overrides:
            body.update(body_overrides)
        event['body'] = json.dumps(body)
        return event

    @patch('handlers.account_recovery._verify_recaptcha', lambda token: True)
    def test_initiate_account_recovery_returns_generic_200_if_no_license_match(self):
        from handlers.account_recovery import initiate_account_recovery
        # in this test, we have not added any license records to the db, so there will be no match
        response = initiate_account_recovery(self._get_test_event(), self.mock_context)

        self.assertEqual(200, response['statusCode'])
        self.assertEqual(
            {'message': 'request processed'},
            json.loads(response['body']),
        )

    @patch('handlers.account_recovery._verify_recaptcha', lambda token: False)
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

    @patch('handlers.account_recovery._verify_recaptcha', lambda token: True)
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

    @patch('handlers.account_recovery._verify_recaptcha', lambda token: True)
    def test_initiate_account_recovery_returns_generic_200_if_provided_email_does_not_match_with_registered_email(self):
        from handlers.account_recovery import initiate_account_recovery

        self._when_license_record_matches()
        # in this test, the license matches, but the passed in email address
        # does not match with what the provider is currently registered with
        response = initiate_account_recovery(self._get_test_event(body_overrides={
            'username': 'some-other-email@invalid.com'
        }), self.mock_context)

        self.assertEqual(200, response['statusCode'])
        self.assertEqual(
            {'message': 'request processed'},
            json.loads(response['body']),
        )

    @patch('handlers.account_recovery._verify_recaptcha', lambda token: True)
    @patch('handlers.registration.config.email_service_client')
    def test_initiate_account_recovery_returns_generic_200_if_rate_limited(self, mock_email_service_client):
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
                response = initiate_account_recovery(self._get_test_event(body_overrides={
                    'password': password
                }), self.mock_context)

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
            self.assertEqual(3, response['Count'])

            # ensure the provider record was not updated with the temp token
            provider_record = self.config.data_client.get_provider_top_level_record(
                compact=TEST_COMPACT_ABBR, provider_id=MOCK_PROVIDER_ID)

            # ensure the email was not sent
            mock_email_service_client.send_provider_account_recovery_confirmation_email.assert_not_called()

            self.assertIsNone(provider_record.recoveryToken)
            self.assertIsNone(provider_record.recoveryExpiry)

    @patch('handlers.account_recovery._verify_recaptcha', lambda token: True)
    @patch('handlers.registration.config.email_service_client')
    def test_initiate_account_recovery_sends_email_if_authenticated(self, mock_email_service_client):
        from handlers.account_recovery import initiate_account_recovery

        self._when_license_record_matches()

        response = initiate_account_recovery(self._get_test_event(), self.mock_context)
        self.assertEqual(200, response['statusCode'])
        self.assertEqual(
            {'message': 'request processed'},
            json.loads(response['body']),
        )

        # ensure the provider record was not updated with the temp token
        provider_record = self.config.data_client.get_provider_top_level_record(
            compact=TEST_COMPACT_ABBR, provider_id=MOCK_PROVIDER_ID)

        self.assertIsNotNone(provider_record.recoveryToken)
        self.assertIsNotNone(provider_record.recoveryExpiry)

        # ensure the email was not sent
        mock_email_service_client.send_provider_account_recovery_confirmation_email.assert_called_once_with(
            compact=TEST_COMPACT_ABBR,
            provider_email=provider_record.compactConnectRegisteredEmailAddress,
            provider_id=MOCK_PROVIDER_ID,
            recovery_token=provider_record.recoveryToken
        )






