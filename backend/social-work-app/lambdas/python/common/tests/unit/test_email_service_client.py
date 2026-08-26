import json
from unittest.mock import MagicMock
from uuid import UUID

from cc_common.config import logger

from tests import TstLambdas

TEST_COMPACT = 'socw'
TEST_FORMER_JURISDICTION = 'tn'
TEST_NEW_JURISDICTION = 'oh'
TEST_PROVIDER_ID = UUID('12345678-1234-5678-1234-567812345678')


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

    def test_send_provider_home_state_change_email_should_invoke_lambda_client_with_expected_parameters(self):
        from cc_common.email_service_client import HomeJurisdictionChangeNotificationTemplateVariables

        mock_lambda_client = MagicMock()
        test_model = self._generate_test_model(mock_lambda_client)

        test_model.send_provider_home_state_change_email(
            compact=TEST_COMPACT,
            jurisdiction=TEST_FORMER_JURISDICTION,
            template_variables=HomeJurisdictionChangeNotificationTemplateVariables(
                provider_first_name='Jane',
                provider_last_name='Smith',
                former_jurisdiction=TEST_FORMER_JURISDICTION,
                current_jurisdiction=TEST_NEW_JURISDICTION,
                license_type='Licensed Clinical Social Worker',
                provider_id=TEST_PROVIDER_ID,
            ),
        )

        mock_lambda_client.invoke.assert_called_once_with(
            FunctionName='test-lambda-name',
            InvocationType='RequestResponse',
            Payload=json.dumps(
                {
                    'compact': TEST_COMPACT,
                    'jurisdiction': TEST_FORMER_JURISDICTION,
                    'template': 'homeJurisdictionChangeNotification',
                    'recipientType': 'JURISDICTION_OPERATIONS_TEAM',
                    'templateVariables': {
                        'providerFirstName': 'Jane',
                        'providerLastName': 'Smith',
                        'providerId': str(TEST_PROVIDER_ID),
                        'previousJurisdiction': TEST_FORMER_JURISDICTION,
                        'newJurisdiction': TEST_NEW_JURISDICTION,
                        'licenseType': 'Licensed Clinical Social Worker',
                    },
                }
            ),
        )

    def test_send_staff_user_inactivity_notification_email_invokes_lambda_with_expected_parameters(self):
        from datetime import date

        from cc_common.email_service_client import StaffUserInactivityNotificationTemplateVariables

        mock_lambda_client = MagicMock()
        test_model = self._generate_test_model(mock_lambda_client)

        test_model.send_staff_user_inactivity_notification_email(
            compact=TEST_COMPACT,
            recipient_emails=['jane@example.com', 'admin@example.com'],
            template_variables=StaffUserInactivityNotificationTemplateVariables(
                staff_user_first_name='Jane',
                staff_user_last_name='Smith',
                staff_user_email='jane@example.com',
                deactivation_date=date(2026, 9, 14),
                inactivity_period_days=60,
            ),
        )

        mock_lambda_client.invoke.assert_called_once_with(
            FunctionName='test-lambda-name',
            InvocationType='RequestResponse',
            Payload=json.dumps(
                {
                    'compact': TEST_COMPACT,
                    'template': 'staffUserInactivityNotification',
                    'recipientType': 'SPECIFIC',
                    'specificEmails': ['jane@example.com', 'admin@example.com'],
                    'templateVariables': {
                        'staffUserFirstName': 'Jane',
                        'staffUserLastName': 'Smith',
                        'staffUserEmail': 'jane@example.com',
                        'deactivationDate': '2026-09-14',
                        'inactivityPeriodDays': 60,
                    },
                }
            ),
        )
