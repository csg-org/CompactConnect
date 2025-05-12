import json
from datetime import UTC, datetime
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
