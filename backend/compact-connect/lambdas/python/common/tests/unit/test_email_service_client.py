import json
from datetime import UTC, date, datetime
from unittest.mock import MagicMock

from cc_common.config import logger

from tests import TstLambdas

TEST_COMPACT = 'aslp'
TEST_JURISDICTION = 'oh'


class TestEmailServiceClient(TstLambdas):
    def _generate_test_model(self, mock_lambda_client):
        from cc_common.email_service_client import EmailServiceClient

        mock_lambda_client.invoke.return_value = {
            'StatusCode': 200,
            'LogResult': 'string',
            'Payload': '{"message": "Email message sent"}',
            'ExecutedVersion': '1',
        }

        return EmailServiceClient(
            lambda_client=mock_lambda_client, email_notification_service_lambda_name='test-lambda-name', logger=logger
        )

    def test_privilege_deactivation_provider_notification_should_invoke_lambda_client_with_expected_parameters(self):
        mock_lambda_client = MagicMock()
        test_model = self._generate_test_model(mock_lambda_client)

        test_model.send_provider_privilege_deactivation_email(
            compact=TEST_COMPACT, provider_email='test@test.com', privilege_id='123'
        )

        mock_lambda_client.invoke.assert_called_once_with(
            FunctionName='test-lambda-name',
            InvocationType='RequestResponse',
            Payload=json.dumps(
                {
                    'compact': TEST_COMPACT,
                    'template': 'privilegeDeactivationProviderNotification',
                    'recipientType': 'SPECIFIC',
                    'specificEmails': [
                        'test@test.com',
                    ],
                    'templateVariables': {
                        'privilegeId': '123',
                    },
                }
            ),
        )

    def test_privilege_deactivation_jurisdiction_notification_should_invoke_lambda_client_with_expected_parameters(
        self,
    ):
        mock_lambda_client = MagicMock()
        test_model = self._generate_test_model(mock_lambda_client)

        test_model.send_jurisdiction_privilege_deactivation_email(
            compact=TEST_COMPACT,
            jurisdiction=TEST_JURISDICTION,
            privilege_id='123',
            provider_first_name='John',
            provider_last_name='Doe',
        )

        mock_lambda_client.invoke.assert_called_once_with(
            FunctionName='test-lambda-name',
            InvocationType='RequestResponse',
            Payload=json.dumps(
                {
                    'compact': TEST_COMPACT,
                    'jurisdiction': TEST_JURISDICTION,
                    'template': 'privilegeDeactivationJurisdictionNotification',
                    'recipientType': 'JURISDICTION_SUMMARY_REPORT',
                    'templateVariables': {'privilegeId': '123', 'providerFirstName': 'John', 'providerLastName': 'Doe'},
                }
            ),
        )

    def test_compact_transaction_report_email_should_invoke_lambda_client_with_expected_parameters(self):
        mock_lambda_client = MagicMock()
        test_model = self._generate_test_model(mock_lambda_client)

        test_model.send_compact_transaction_report_email(
            compact=TEST_COMPACT,
            report_s3_path='s3://test-bucket/test-path',
            reporting_cycle='monthly',
            start_date=datetime(2024, 1, 1, tzinfo=UTC),
            end_date=datetime(2024, 1, 31, tzinfo=UTC),
        )

        mock_lambda_client.invoke.assert_called_once_with(
            FunctionName='test-lambda-name',
            InvocationType='RequestResponse',
            Payload=json.dumps(
                {
                    'compact': TEST_COMPACT,
                    'template': 'CompactTransactionReporting',
                    'recipientType': 'COMPACT_SUMMARY_REPORT',
                    'templateVariables': {
                        'reportS3Path': 's3://test-bucket/test-path',
                        'reportingCycle': 'monthly',
                        'startDate': '2024-01-01',
                        'endDate': '2024-01-31',
                    },
                }
            ),
        )

    def test_jurisdiction_transaction_report_email_should_invoke_lambda_client_with_expected_parameters(self):
        mock_lambda_client = MagicMock()
        test_model = self._generate_test_model(mock_lambda_client)

        test_model.send_jurisdiction_transaction_report_email(
            compact=TEST_COMPACT,
            jurisdiction=TEST_JURISDICTION,
            report_s3_path='s3://test-bucket/test-path',
            reporting_cycle='monthly',
            start_date=datetime(2024, 1, 1, tzinfo=UTC),
            end_date=datetime(2024, 1, 31, tzinfo=UTC),
        )

        mock_lambda_client.invoke.assert_called_once_with(
            FunctionName='test-lambda-name',
            InvocationType='RequestResponse',
            Payload=json.dumps(
                {
                    'compact': TEST_COMPACT,
                    'jurisdiction': TEST_JURISDICTION,
                    'template': 'JurisdictionTransactionReporting',
                    'recipientType': 'JURISDICTION_SUMMARY_REPORT',
                    'templateVariables': {
                        'reportS3Path': 's3://test-bucket/test-path',
                        'reportingCycle': 'monthly',
                        'startDate': '2024-01-01',
                        'endDate': '2024-01-31',
                    },
                }
            ),
        )

    def test_provider_email_verification_code_should_invoke_lambda_client_with_expected_parameters(self):
        mock_lambda_client = MagicMock()
        test_model = self._generate_test_model(mock_lambda_client)

        test_model.send_provider_email_verification_code(
            compact=TEST_COMPACT, provider_email='newuser@example.com', verification_code='1234'
        )

        mock_lambda_client.invoke.assert_called_once_with(
            FunctionName='test-lambda-name',
            InvocationType='RequestResponse',
            Payload=json.dumps(
                {
                    'compact': TEST_COMPACT,
                    'template': 'providerEmailVerificationCode',
                    'recipientType': 'SPECIFIC',
                    'specificEmails': [
                        'newuser@example.com',
                    ],
                    'templateVariables': {
                        'verificationCode': '1234',
                    },
                }
            ),
        )

    def test_provider_email_change_notification_should_invoke_lambda_client_with_expected_parameters(self):
        mock_lambda_client = MagicMock()
        test_model = self._generate_test_model(mock_lambda_client)

        test_model.send_provider_email_change_notification(
            compact=TEST_COMPACT, old_email_address='olduser@example.com', new_email_address='newuser@example.com'
        )

        mock_lambda_client.invoke.assert_called_once_with(
            FunctionName='test-lambda-name',
            InvocationType='RequestResponse',
            Payload=json.dumps(
                {
                    'compact': TEST_COMPACT,
                    'template': 'providerEmailChangeNotification',
                    'recipientType': 'SPECIFIC',
                    'specificEmails': [
                        'olduser@example.com',
                    ],
                    'templateVariables': {
                        'newEmailAddress': 'newuser@example.com',
                    },
                }
            ),
        )

    def test_provider_account_recovery_confirmation_should_invoke_lambda_client_with_expected_parameters(self):
        mock_lambda_client = MagicMock()
        test_model = self._generate_test_model(mock_lambda_client)

        test_model.send_provider_account_recovery_confirmation_email(
            compact=TEST_COMPACT,
            provider_email='123@example.com',
            provider_id='123',
            recovery_token='456',  # noqa: S106 test mock token
        )

        mock_lambda_client.invoke.assert_called_once_with(
            FunctionName='test-lambda-name',
            InvocationType='RequestResponse',
            Payload=json.dumps(
                {
                    'compact': TEST_COMPACT,
                    'template': 'providerAccountRecoveryConfirmation',
                    'recipientType': 'SPECIFIC',
                    'specificEmails': [
                        '123@example.com',
                    ],
                    'templateVariables': {
                        'providerId': '123',
                        'recoveryToken': '456',
                    },
                }
            ),
        )

    def test_privilege_expiration_reminder_should_invoke_lambda_client_with_expected_parameters(self):
        from cc_common.email_service_client import PrivilegeExpirationReminderTemplateVariables

        mock_lambda_client = MagicMock()
        test_model = self._generate_test_model(mock_lambda_client)

        privileges = [
            {
                'jurisdiction': 'Ohio',
                'licenseType': 'aud',
                'privilegeId': 'AUD-OH-001',
                'dateOfExpiration': '2026-02-16',
            },
            {
                'jurisdiction': 'Kentucky',
                'licenseType': 'slp',
                'privilegeId': 'SLP-KY-002',
                'dateOfExpiration': '2026-03-01',
            },
        ]

        template_variables = PrivilegeExpirationReminderTemplateVariables(
            provider_first_name='John',
            expiration_date=date(2026, 2, 16),
            privileges=privileges,
        )

        test_model.send_privilege_expiration_reminder_email(
            compact=TEST_COMPACT,
            provider_email='provider@example.com',
            template_variables=template_variables,
        )

        mock_lambda_client.invoke.assert_called_once_with(
            FunctionName='test-lambda-name',
            InvocationType='RequestResponse',
            Payload=json.dumps(
                {
                    'compact': TEST_COMPACT,
                    'template': 'privilegeExpirationReminder',
                    'recipientType': 'SPECIFIC',
                    'specificEmails': [
                        'provider@example.com',
                    ],
                    'templateVariables': {
                        'providerFirstName': 'John',
                        'expirationDate': '2026-02-16',
                        'privileges': privileges,
                    },
                }
            ),
        )
