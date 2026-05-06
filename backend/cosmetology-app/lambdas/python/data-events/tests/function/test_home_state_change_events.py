import json
from datetime import datetime
from unittest.mock import patch
from uuid import UUID, uuid4

from common_test.test_constants import (
    DEFAULT_COMPACT,
    DEFAULT_DATE_OF_UPDATE_TIMESTAMP,
    DEFAULT_LICENSE_JURISDICTION,
    DEFAULT_LICENSE_TYPE_ABBREVIATION,
    DEFAULT_PRIVILEGE_JURISDICTION,
    DEFAULT_PROVIDER_ID, DEFAULT_LICENSE_TYPE,
)
from moto import mock_aws

from . import TstFunction

TEST_FORMER_LICENSE_JURISDICTION = 'az'

@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat(DEFAULT_DATE_OF_UPDATE_TIMESTAMP))
class TestHomeStateChangeEvents(TstFunction):
    """Test suite for investigation event handlers."""

    def _generate_license_home_state_change_message(self, message_overrides=None):
        """Generate a test SQS message for license home state change events."""
        message = {
            'detail': {
                'compact': DEFAULT_COMPACT,
                'providerId': DEFAULT_PROVIDER_ID,
                'jurisdiction': DEFAULT_LICENSE_JURISDICTION,
                'licenseTypeAbbreviation': DEFAULT_LICENSE_TYPE_ABBREVIATION,
                'eventTime': DEFAULT_DATE_OF_UPDATE_TIMESTAMP,
                'formerLicenseJurisdiction': TEST_FORMER_LICENSE_JURISDICTION
            }
        }
        if message_overrides:
            message['detail'].update(message_overrides)
        return message

    def _create_sqs_event(self, message):
        """Create a proper SQS event structure with the message in the body."""
        return {'Records': [{'messageId': '123', 'body': json.dumps(message)}]}

    @patch('cc_common.email_service_client.EmailServiceClient.send_provider_home_state_change_email')
    def test_license_homes_state_change_listener_sends_notification_to_former_state(self, mock_state_email):
        """Test that license home state change listener sends an email notification to the former state."""
        from cc_common.email_service_client import HomeJurisdictionChangeNotificationTemplateVariables
        from handlers.home_state_change_events import home_state_change_notification_listener

        # Set up test data with registered provider
        self.test_data_generator.put_default_provider_record_in_provider_table()

        # Add the license for the former home state
        self.test_data_generator.put_default_license_record_in_provider_table(value_overrides={
            'jurisdiction': TEST_FORMER_LICENSE_JURISDICTION
        })
        # Add license for the current home state
        self.test_data_generator.put_default_license_record_in_provider_table()

        message = self._generate_license_home_state_change_message()
        event = self._create_sqs_event(message)

        # Execute the handler
        result = home_state_change_notification_listener(event, self.mock_context)

        # Should succeed with no batch failures
        self.assertEqual({'batchItemFailures': []}, result)

        expected_template_variables = HomeJurisdictionChangeNotificationTemplateVariables(
            provider_first_name='Björk',
            provider_last_name='Guðmundsdóttir',
            former_jurisdiction=TEST_FORMER_LICENSE_JURISDICTION,
            current_jurisdiction=DEFAULT_LICENSE_JURISDICTION,
            license_type=DEFAULT_LICENSE_TYPE,
            provider_id=UUID(DEFAULT_PROVIDER_ID),
        )
        expected_state_call = [
            {
                'compact': DEFAULT_COMPACT,
                # we only send to the former home state
                'jurisdiction': TEST_FORMER_LICENSE_JURISDICTION,
                'template_variables': expected_template_variables,
            },
        ]

        # Verify state notification was sent
        self.assertEqual(1, mock_state_email.call_count)
        actual_state_calls = [call.kwargs for call in mock_state_email.call_args_list]

        self.assertEqual(expected_state_call, actual_state_calls)
