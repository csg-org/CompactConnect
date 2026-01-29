import json
import uuid
from datetime import datetime
from unittest.mock import patch

from common_test.test_constants import (
    DEFAULT_COMPACT,
    DEFAULT_DATE_OF_UPDATE_TIMESTAMP,
    DEFAULT_PROVIDER_ID,
)
from moto import mock_aws

from . import TstFunction


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat(DEFAULT_DATE_OF_UPDATE_TIMESTAMP))
class TestHomeJurisdictionChangeEvents(TstFunction):
    """Test suite for home jurisdiction change event handlers."""

    def _generate_home_jurisdiction_change_message(self, previous_jurisdiction: str, new_jurisdiction: str):
        """Generate a test EventBridge message for home jurisdiction change events."""
        return {
            'detail': {
                'compact': DEFAULT_COMPACT,
                'providerId': DEFAULT_PROVIDER_ID,
                'previousHomeJurisdiction': previous_jurisdiction,
                'newHomeJurisdiction': new_jurisdiction,
                'eventTime': DEFAULT_DATE_OF_UPDATE_TIMESTAMP,
            }
        }

    def _create_sqs_event(self, message):
        """Create a proper SQS event structure with the message in the body."""
        return {'Records': [{'messageId': str(uuid.uuid4()), 'body': json.dumps(message)}]}

    @patch('cc_common.email_service_client.EmailServiceClient.send_home_jurisdiction_change_old_state_notification')
    @patch('cc_common.email_service_client.EmailServiceClient.send_home_jurisdiction_change_new_state_notification')
    def test_both_states_notified_when_changing_compact_state(self, mock_send_new_state, mock_send_old_state):
        """Test that both old and new states are notified when changing to another compact state."""
        from handlers.home_jurisdiction_events import home_jurisdiction_change_notification_listener

        # Set up test data
        self.test_data_generator.put_default_provider_record_in_provider_table(
            value_overrides={
                'givenName': 'John',
                'familyName': 'Doe',
                'currentHomeJurisdiction': 'oh',
            }
        )

        # Set up jurisdiction configurations for both states
        self.test_data_generator.put_default_jurisdiction_configuration_in_configuration_table(
            value_overrides={
                'compact': DEFAULT_COMPACT,
                'postalAbbreviation': 'oh',
                'jurisdictionName': 'Ohio',
                'jurisdictionOperationsTeamEmails': ['oh-ops@example.com'],
            }
        )
        self.test_data_generator.put_default_jurisdiction_configuration_in_configuration_table(
            value_overrides={
                'compact': DEFAULT_COMPACT,
                'postalAbbreviation': 'tx',
                'jurisdictionName': 'Texas',
                'jurisdictionOperationsTeamEmails': ['tx-ops@example.com'],
            }
        )

        message = self._generate_home_jurisdiction_change_message('oh', 'tx')
        event = self._create_sqs_event(message)

        # Execute the handler
        result = home_jurisdiction_change_notification_listener(event, self.mock_context)

        # Should succeed with no batch failures
        self.assertEqual({'batchItemFailures': []}, result)

        # Verify both emails were sent
        mock_send_old_state.assert_called_once()
        mock_send_new_state.assert_called_once()

        # Verify old state notification details
        old_state_call = mock_send_old_state.call_args
        self.assertEqual(DEFAULT_COMPACT, old_state_call.kwargs['compact'])
        self.assertEqual('oh', old_state_call.kwargs['jurisdiction'])
        self.assertEqual('John', old_state_call.kwargs['provider_first_name'])
        self.assertEqual('Doe', old_state_call.kwargs['provider_last_name'])
        self.assertEqual('tx', old_state_call.kwargs['new_jurisdiction'])

        # Verify new state notification details
        new_state_call = mock_send_new_state.call_args
        self.assertEqual(DEFAULT_COMPACT, new_state_call.kwargs['compact'])
        self.assertEqual('tx', new_state_call.kwargs['jurisdiction'])
        self.assertEqual('John', new_state_call.kwargs['provider_first_name'])
        self.assertEqual('Doe', new_state_call.kwargs['provider_last_name'])
        self.assertEqual('oh', new_state_call.kwargs['previous_jurisdiction'])

    @patch('cc_common.email_service_client.EmailServiceClient.send_home_jurisdiction_change_old_state_notification')
    @patch('cc_common.email_service_client.EmailServiceClient.send_home_jurisdiction_change_new_state_notification')
    def test_only_old_state_notified_when_changing_to_other(self, mock_send_new_state, mock_send_old_state):
        """Test that only old state is notified when changing to 'other' (non-compact state)."""
        from handlers.home_jurisdiction_events import home_jurisdiction_change_notification_listener

        # Set up test data
        self.test_data_generator.put_default_provider_record_in_provider_table(
            value_overrides={
                'givenName': 'Jane',
                'familyName': 'Smith',
                'currentHomeJurisdiction': 'oh',
            }
        )

        # Set up jurisdiction configuration for old state only
        self.test_data_generator.put_default_jurisdiction_configuration_in_configuration_table(
            value_overrides={
                'compact': DEFAULT_COMPACT,
                'postalAbbreviation': 'oh',
                'jurisdictionName': 'Ohio',
                'jurisdictionOperationsTeamEmails': ['oh-ops@example.com'],
            }
        )

        message = self._generate_home_jurisdiction_change_message('oh', 'other')
        event = self._create_sqs_event(message)

        # Execute the handler
        result = home_jurisdiction_change_notification_listener(event, self.mock_context)

        # Should succeed with no batch failures
        self.assertEqual({'batchItemFailures': []}, result)

        # Verify only old state was notified
        mock_send_old_state.assert_called_once()
        mock_send_new_state.assert_not_called()

    @patch('cc_common.email_service_client.EmailServiceClient.send_home_jurisdiction_change_old_state_notification')
    @patch('cc_common.email_service_client.EmailServiceClient.send_home_jurisdiction_change_new_state_notification')
    def test_no_old_state_notification_when_previous_is_other(self, mock_send_new_state, mock_send_old_state):
        """Test that old state is not notified when previous jurisdiction is 'other'."""
        from cc_common.data_model.schema.fields import OTHER_JURISDICTION
        from handlers.home_jurisdiction_events import home_jurisdiction_change_notification_listener

        # Set up test data
        self.test_data_generator.put_default_provider_record_in_provider_table(
            value_overrides={
                'givenName': 'Bob',
                'familyName': 'Johnson',
                'currentHomeJurisdiction': OTHER_JURISDICTION,
            }
        )

        # Set up jurisdiction configuration for new state only
        self.test_data_generator.put_default_jurisdiction_configuration_in_configuration_table(
            value_overrides={
                'compact': DEFAULT_COMPACT,
                'postalAbbreviation': 'tx',
                'jurisdictionName': 'Texas',
                'jurisdictionOperationsTeamEmails': ['tx-ops@example.com'],
            }
        )

        message = self._generate_home_jurisdiction_change_message(OTHER_JURISDICTION, 'tx')
        event = self._create_sqs_event(message)

        # Execute the handler
        result = home_jurisdiction_change_notification_listener(event, self.mock_context)

        # Should succeed with no batch failures
        self.assertEqual({'batchItemFailures': []}, result)

        # Verify only new state was notified
        mock_send_old_state.assert_not_called()
        mock_send_new_state.assert_called_once()

    @patch('cc_common.email_service_client.EmailServiceClient.send_home_jurisdiction_change_old_state_notification')
    @patch('cc_common.email_service_client.EmailServiceClient.send_home_jurisdiction_change_new_state_notification')
    def test_idempotency_prevents_duplicate_notifications(self, mock_send_new_state, mock_send_old_state):
        """Test that NotificationTracker prevents duplicate notifications on retries."""
        from handlers.home_jurisdiction_events import home_jurisdiction_change_notification_listener

        # Set up test data
        self.test_data_generator.put_default_provider_record_in_provider_table(
            value_overrides={
                'givenName': 'Test',
                'familyName': 'User',
                'currentHomeJurisdiction': 'oh',
            }
        )

        # Set up jurisdiction configurations for both states
        self.test_data_generator.put_default_jurisdiction_configuration_in_configuration_table(
            value_overrides={
                'compact': DEFAULT_COMPACT,
                'postalAbbreviation': 'oh',
                'jurisdictionName': 'Ohio',
                'jurisdictionOperationsTeamEmails': ['oh-ops@example.com'],
            }
        )
        self.test_data_generator.put_default_jurisdiction_configuration_in_configuration_table(
            value_overrides={
                'compact': DEFAULT_COMPACT,
                'postalAbbreviation': 'tx',
                'jurisdictionName': 'Texas',
                'jurisdictionOperationsTeamEmails': ['tx-ops@example.com'],
            }
        )

        message = self._generate_home_jurisdiction_change_message('oh', 'tx')
        event = self._create_sqs_event(message)

        # First execution - should send notification
        result1 = home_jurisdiction_change_notification_listener(event, self.mock_context)
        self.assertEqual({'batchItemFailures': []}, result1)
        self.assertEqual(1, mock_send_old_state.call_count)
        self.assertEqual(1, mock_send_new_state.call_count)

        # Second execution with same message ID - should skip (idempotency)
        result2 = home_jurisdiction_change_notification_listener(event, self.mock_context)
        self.assertEqual({'batchItemFailures': []}, result2)
        # Should still be 1, not 2
        self.assertEqual(1, mock_send_old_state.call_count)
        self.assertEqual(1, mock_send_new_state.call_count)

    @patch('cc_common.email_service_client.EmailServiceClient.send_home_jurisdiction_change_old_state_notification')
    def test_error_handling_records_failure(self, mock_send_old_state):
        """Test that email failures are recorded properly and cause batch item failure."""
        from handlers.home_jurisdiction_events import home_jurisdiction_change_notification_listener

        # Set up test data
        self.test_data_generator.put_default_provider_record_in_provider_table(
            value_overrides={
                'givenName': 'Error',
                'familyName': 'Test',
                'currentHomeJurisdiction': 'oh',
            }
        )

        # Set up jurisdiction configurations for both states
        self.test_data_generator.put_default_jurisdiction_configuration_in_configuration_table(
            value_overrides={
                'compact': DEFAULT_COMPACT,
                'postalAbbreviation': 'oh',
                'jurisdictionName': 'Ohio',
                'jurisdictionOperationsTeamEmails': ['oh-ops@example.com'],
            }
        )
        self.test_data_generator.put_default_jurisdiction_configuration_in_configuration_table(
            value_overrides={
                'compact': DEFAULT_COMPACT,
                'postalAbbreviation': 'tx',
                'jurisdictionName': 'Texas',
                'jurisdictionOperationsTeamEmails': ['tx-ops@example.com'],
            }
        )

        # Simulate email send failure
        mock_send_old_state.side_effect = Exception('Email service unavailable')

        message = self._generate_home_jurisdiction_change_message('oh', 'tx')
        event = self._create_sqs_event(message)

        # Execute the handler - should return item failure
        result = home_jurisdiction_change_notification_listener(event, self.mock_context)

        # Should have one batch item failure
        self.assertEqual(1, len(result['batchItemFailures']))

    @patch('cc_common.email_service_client.EmailServiceClient.send_home_jurisdiction_change_old_state_notification')
    @patch('cc_common.email_service_client.EmailServiceClient.send_home_jurisdiction_change_new_state_notification')
    def test_no_notification_when_jurisdiction_has_no_operations_emails(self, mock_send_new_state, mock_send_old_state):
        """Test that notifications are skipped when jurisdiction has no operations team emails."""
        from handlers.home_jurisdiction_events import home_jurisdiction_change_notification_listener

        # Set up test data
        self.test_data_generator.put_default_provider_record_in_provider_table(
            value_overrides={
                'givenName': 'No',
                'familyName': 'Emails',
                'currentHomeJurisdiction': 'oh',
            }
        )

        # Set up jurisdiction configurations with no operations emails
        self.test_data_generator.put_default_jurisdiction_configuration_in_configuration_table(
            value_overrides={
                'compact': DEFAULT_COMPACT,
                'postalAbbreviation': 'oh',
                'jurisdictionName': 'Ohio',
                'jurisdictionOperationsTeamEmails': [],
            }
        )
        self.test_data_generator.put_default_jurisdiction_configuration_in_configuration_table(
            value_overrides={
                'compact': DEFAULT_COMPACT,
                'postalAbbreviation': 'tx',
                'jurisdictionName': 'Texas',
                'jurisdictionOperationsTeamEmails': [],
            }
        )

        message = self._generate_home_jurisdiction_change_message('oh', 'tx')
        event = self._create_sqs_event(message)

        # Execute the handler
        result = home_jurisdiction_change_notification_listener(event, self.mock_context)

        # Should succeed with no batch failures
        self.assertEqual({'batchItemFailures': []}, result)

        # Verify no emails were sent
        mock_send_old_state.assert_not_called()
        mock_send_new_state.assert_not_called()

    @patch('cc_common.email_service_client.EmailServiceClient.send_home_jurisdiction_change_old_state_notification')
    @patch('cc_common.email_service_client.EmailServiceClient.send_home_jurisdiction_change_new_state_notification')
    def test_no_notification_when_jurisdiction_config_not_found(self, mock_send_new_state, mock_send_old_state):
        """Test that notifications are skipped when jurisdiction configuration is not found."""
        from handlers.home_jurisdiction_events import home_jurisdiction_change_notification_listener

        # Set up test data
        self.test_data_generator.put_default_provider_record_in_provider_table(
            value_overrides={
                'givenName': 'No',
                'familyName': 'Config',
                'currentHomeJurisdiction': 'oh',
            }
        )

        # Don't set up any jurisdiction configurations - they won't be found

        message = self._generate_home_jurisdiction_change_message('oh', 'tx')
        event = self._create_sqs_event(message)

        # Execute the handler
        result = home_jurisdiction_change_notification_listener(event, self.mock_context)

        # Should succeed with no batch failures
        self.assertEqual({'batchItemFailures': []}, result)

        # Verify no emails were sent
        mock_send_old_state.assert_not_called()
        mock_send_new_state.assert_not_called()
