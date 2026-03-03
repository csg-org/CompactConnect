import json
import uuid
from datetime import date, datetime
from unittest.mock import ANY, patch
from uuid import UUID

from common_test.test_constants import (
    DEFAULT_ADVERSE_ACTION_ID,
    DEFAULT_CLINICAL_PRIVILEGE_ACTION_CATEGORY,
    DEFAULT_COMPACT,
    DEFAULT_DATE_OF_UPDATE_TIMESTAMP,
    DEFAULT_EFFECTIVE_DATE,
    DEFAULT_LICENSE_JURISDICTION,
    DEFAULT_LICENSE_TYPE,
    DEFAULT_LICENSE_TYPE_ABBREVIATION,
    DEFAULT_PRIVILEGE_JURISDICTION,
    DEFAULT_PROVIDER_ID,
)
from moto import mock_aws

from . import TstFunction


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat(DEFAULT_DATE_OF_UPDATE_TIMESTAMP))
class TestEncumbranceEvents(TstFunction):
    """Test suite for license encumbrance event handlers."""

    def _generate_license_encumbrance_message(self, message_overrides=None):
        """Generate a test SQS message for license encumbrance events."""
        message = {
            'detail': {
                'compact': DEFAULT_COMPACT,
                'providerId': DEFAULT_PROVIDER_ID,
                'jurisdiction': DEFAULT_LICENSE_JURISDICTION,
                'licenseTypeAbbreviation': DEFAULT_LICENSE_TYPE_ABBREVIATION,
                'eventTime': DEFAULT_DATE_OF_UPDATE_TIMESTAMP,
                'effectiveDate': DEFAULT_EFFECTIVE_DATE,
                'adverseActionId': DEFAULT_ADVERSE_ACTION_ID,
                'adverseActionCategory': DEFAULT_CLINICAL_PRIVILEGE_ACTION_CATEGORY,
            }
        }
        if message_overrides:
            message['detail'].update(message_overrides)
        return message

    def _generate_license_encumbrance_lifting_message(self, message_overrides=None):
        """Generate a test SQS message for license encumbrance lifting events."""
        return self._generate_license_encumbrance_message(message_overrides)

    def _create_sqs_event(self, message):
        """Create a proper SQS event structure with the message in the body."""
        return {'Records': [{'messageId': str(uuid.uuid4()), 'body': json.dumps(message)}]}

    def _when_testing_live_jurisdictions(self):
        from cc_common.config import config
        from handlers.encumbrance_events import license_encumbrance_listener

        # Mock live jurisdictions to home state + one other so we can assert the non-home one is notified
        config.__dict__['live_compact_jurisdictions'] = {
            DEFAULT_COMPACT: [DEFAULT_LICENSE_JURISDICTION, 'ky'],
        }
        try:
            message = self._generate_license_encumbrance_message()
            event = self._create_sqs_event(message)

            license_encumbrance_listener(event, self.mock_context)

        finally:
            config.__dict__.pop('live_compact_jurisdictions', None)

    @patch('cc_common.event_bus_client.EventBusClient._publish_event')
    def test_license_encumbrance_listener_publishes_privilege_encumbrance_for_non_home_live_jurisdictions(
        self, mock_publish_event
    ):
        """When a license is encumbered, privilege encumbrance events are published for each live jurisdiction.

        Verifies that the privilege encumbrance notification is sent for the jurisdiction that is not
        the home state license jurisdiction (i.e. the other live compact jurisdictions).
        """
        self._when_testing_live_jurisdictions()

        # Should have published for each live jurisdiction that isn't the home state license jurisdiction (ky)
        self.assertEqual(1, mock_publish_event.call_count)
        mock_publish_event.assert_called_once_with(
            source='org.compactconnect.data-events',
            detail_type='privilege.encumbrance',
            detail={
                'compact': 'cosm',
                'jurisdiction': 'ky',
                'eventTime': '2024-11-08T23:59:59+00:00',
                'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570',
                'licenseTypeAbbreviation': 'cos',
                'effectiveDate': '2024-11-08',
            },
            event_batch_writer=ANY,
        )

    def _run_license_encumbrance_lifted_listener_with_live_jurisdictions(
        self, live_jurisdictions, message_overrides=None
    ):
        """Set live_compact_jurisdictions, run license encumbrance lifted listener, then restore config."""
        from cc_common.config import config
        from handlers.encumbrance_events import license_encumbrance_lifted_listener

        config.__dict__['live_compact_jurisdictions'] = live_jurisdictions
        try:
            message = self._generate_license_encumbrance_lifting_message(message_overrides)
            event = self._create_sqs_event(message)
            license_encumbrance_lifted_listener(event, self.mock_context)
        finally:
            config.__dict__.pop('live_compact_jurisdictions', None)

    def _when_testing_live_jurisdictions_license_lifted(self):
        """Run license encumbrance lifted listener with live jurisdictions = [home, ky]; call under patch."""
        self._run_license_encumbrance_lifted_listener_with_live_jurisdictions(
            {DEFAULT_COMPACT: [DEFAULT_LICENSE_JURISDICTION, 'ky']}
        )

    @patch('cc_common.event_bus_client.EventBusClient._publish_event')
    def test_license_encumbrance_lifted_listener_publishes_privilege_encumbrance_lifting_for_non_home_jurisdictions(
        self, mock_publish_event
    ):
        """When a license encumbrance is lifted, privilege encumbrance lifting events are published
        for non-home live jurisdictions.

        Verifies that the privilege encumbrance lifting notification is sent for the jurisdiction that is not
        the home state license jurisdiction.
        """
        # Handler fetches provider + license to verify license is unencumbered before publishing
        self.test_data_generator.put_default_provider_record_in_provider_table()
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'jurisdiction': DEFAULT_LICENSE_JURISDICTION,
                'licenseType': DEFAULT_LICENSE_TYPE,
                'encumberedStatus': 'unencumbered',
            }
        )
        self._when_testing_live_jurisdictions_license_lifted()

        # Should have published for each live jurisdiction that isn't the home state license jurisdiction (ky only)
        self.assertEqual(1, mock_publish_event.call_count)
        mock_publish_event.assert_called_once_with(
            source='org.compactconnect.data-events',
            detail_type='privilege.encumbranceLifted',
            detail={
                'compact': DEFAULT_COMPACT,
                'jurisdiction': 'ky',
                'eventTime': DEFAULT_DATE_OF_UPDATE_TIMESTAMP,
                'providerId': DEFAULT_PROVIDER_ID,
                'licenseTypeAbbreviation': DEFAULT_LICENSE_TYPE_ABBREVIATION,
                'effectiveDate': DEFAULT_EFFECTIVE_DATE,
            },
            event_batch_writer=ANY,
        )

    @patch('cc_common.event_bus_client.EventBusClient._publish_event')
    def test_license_encumbrance_lifted_listener_does_not_publish_when_license_still_encumbered(
        self, mock_publish_event
    ):
        """When the license is still encumbered (e.g. another adverse action not yet lifted),
        no events are published."""
        # Set up provider and license that is still encumbered
        self.test_data_generator.put_default_provider_record_in_provider_table()
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'jurisdiction': DEFAULT_LICENSE_JURISDICTION,
                'licenseType': DEFAULT_LICENSE_TYPE,
                'encumberedStatus': 'encumbered',  # License still encumbered
            }
        )

        # Live jurisdictions would normally cause a publish for 'ky'; we verify we skip all publishes
        self._run_license_encumbrance_lifted_listener_with_live_jurisdictions(
            {DEFAULT_COMPACT: [DEFAULT_LICENSE_JURISDICTION, 'ky']}
        )

        mock_publish_event.assert_not_called()

    def _generate_privilege_encumbrance_message(self, message_overrides=None):
        """Generate a test SQS message for privilege encumbrance events."""
        message = {
            'detail': {
                'compact': DEFAULT_COMPACT,
                'providerId': DEFAULT_PROVIDER_ID,
                'jurisdiction': DEFAULT_PRIVILEGE_JURISDICTION,
                'licenseTypeAbbreviation': DEFAULT_LICENSE_TYPE_ABBREVIATION,
                'eventTime': DEFAULT_DATE_OF_UPDATE_TIMESTAMP,
                'effectiveDate': DEFAULT_EFFECTIVE_DATE,
            }
        }
        if message_overrides:
            message['detail'].update(message_overrides)
        return message

    def _generate_privilege_encumbrance_lifting_message(self, message_overrides=None):
        """Generate a test SQS message for privilege encumbrance lifting events."""
        return self._generate_privilege_encumbrance_message(message_overrides)

    @patch('cc_common.email_service_client.EmailServiceClient.send_privilege_encumbrance_state_notification_email')
    def test_privilege_encumbrance_listener_processes_event(self, mock_state_email):
        """Test that privilege encumbrance listener processes events and sends state notifications."""
        from cc_common.email_service_client import EncumbranceNotificationTemplateVariables
        from handlers.encumbrance_events import privilege_encumbrance_notification_listener

        # Set up test data
        self.test_data_generator.put_default_provider_record_in_provider_table()
        self.test_data_generator.put_default_license_record_in_provider_table()

        message = self._generate_privilege_encumbrance_message()
        event = self._create_sqs_event(message)

        # Execute the handler
        result = privilege_encumbrance_notification_listener(event, self.mock_context)

        # Should succeed with no batch failures
        self.assertEqual({'batchItemFailures': []}, result)

        # Verify state notifications: encumbered state + other live compact jurisdictions (default: oh, ne)
        expected_template_variables_ne = EncumbranceNotificationTemplateVariables(
            provider_first_name='Björk',
            provider_last_name='Guðmundsdóttir',
            encumbered_jurisdiction='ne',
            license_type='cosmetologist',
            effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
            provider_id=UUID(DEFAULT_PROVIDER_ID),
        )
        expected_template_variables_oh = EncumbranceNotificationTemplateVariables(
            provider_first_name='Björk',
            provider_last_name='Guðmundsdóttir',
            encumbered_jurisdiction='ne',
            license_type='cosmetologist',
            effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
            provider_id=UUID(DEFAULT_PROVIDER_ID),
        )
        expected_state_calls = [
            {
                'compact': DEFAULT_COMPACT,
                'jurisdiction': DEFAULT_PRIVILEGE_JURISDICTION,
                'template_variables': expected_template_variables_ne,
            },
            {
                'compact': DEFAULT_COMPACT,
                'jurisdiction': DEFAULT_LICENSE_JURISDICTION,
                'template_variables': expected_template_variables_oh,
            },
        ]

        # Verify all state notifications were sent (encumbered + other live states)
        self.assertEqual(2, mock_state_email.call_count)
        actual_state_calls = [call.kwargs for call in mock_state_email.call_args_list]

        # Sort both lists for comparison
        expected_state_calls_sorted = sorted(expected_state_calls, key=lambda x: x['jurisdiction'])
        actual_state_calls_sorted = sorted(actual_state_calls, key=lambda x: x['jurisdiction'])

        self.assertEqual(expected_state_calls_sorted, actual_state_calls_sorted)

    @patch('cc_common.email_service_client.EmailServiceClient.send_privilege_encumbrance_state_notification_email')
    def test_privilege_encumbrance_listener_identifies_notification_jurisdictions(self, mock_state_email):
        """Test that privilege encumbrance listener correctly identifies states to notify."""
        from cc_common.email_service_client import EncumbranceNotificationTemplateVariables
        from handlers.encumbrance_events import privilege_encumbrance_notification_listener

        # Set up test data
        self.test_data_generator.put_default_provider_record_in_provider_table()
        self.test_data_generator.put_default_license_record_in_provider_table()

        # The encumbrance occurs in DEFAULT_PRIVILEGE_JURISDICTION ('ne'); live = [oh, ne]
        message = self._generate_privilege_encumbrance_message()
        event = self._create_sqs_event(message)

        # Execute the handler
        result = privilege_encumbrance_notification_listener(event, self.mock_context)

        # Should succeed with no batch failures
        self.assertEqual({'batchItemFailures': []}, result)

        # Verify state notifications: encumbered + other live compact jurisdictions
        self.assertEqual(2, mock_state_email.call_count)

        calls = mock_state_email.call_args_list
        call_jurisdictions = [call.kwargs['jurisdiction'] for call in calls]
        self.assertEqual(sorted(call_jurisdictions), ['ne', 'oh'])

        # Verify all calls have the correct template_variables structure
        for call in calls:
            self.assertEqual(call.kwargs['compact'], DEFAULT_COMPACT)
            self.assertEqual(
                call.kwargs['template_variables'],
                EncumbranceNotificationTemplateVariables(
                    provider_first_name='Björk',
                    provider_last_name='Guðmundsdóttir',
                    encumbered_jurisdiction='ne',
                    license_type='cosmetologist',
                    effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                    provider_id=UUID(DEFAULT_PROVIDER_ID),
                ),
            )

    def test_privilege_encumbrance_listener_handles_provider_retrieval_failure(self):
        """Test that privilege encumbrance listener handles provider retrieval failures."""
        from handlers.encumbrance_events import privilege_encumbrance_notification_listener

        # Don't create any provider records - should cause retrieval failure
        message = self._generate_privilege_encumbrance_message()
        event = self._create_sqs_event(message)

        # SQS handler wrapper catches exceptions and returns batch item failures
        result = privilege_encumbrance_notification_listener(event, self.mock_context)

        # Should return batch item failure for the message
        expected_failure = {'batchItemFailures': [{'itemIdentifier': event['Records'][0]['messageId']}]}
        self.assertEqual(expected_failure, result)

    @patch('cc_common.email_service_client.EmailServiceClient.send_privilege_encumbrance_state_notification_email')
    def test_privilege_encumbrance_listener_excludes_encumbered_jurisdiction_from_notifications(self, mock_state_email):
        """Test that the jurisdiction where encumbrance occurred is not duplicated in notifications."""
        from cc_common.email_service_client import EncumbranceNotificationTemplateVariables
        from handlers.encumbrance_events import privilege_encumbrance_notification_listener

        # Set up test data
        self.test_data_generator.put_default_provider_record_in_provider_table()
        self.test_data_generator.put_default_license_record_in_provider_table()

        message = self._generate_privilege_encumbrance_message()
        event = self._create_sqs_event(message)

        # Execute the handler
        result = privilege_encumbrance_notification_listener(event, self.mock_context)

        # Should succeed with no batch failures
        self.assertEqual({'batchItemFailures': []}, result)

        # Verify exactly 2 notifications (encumbered state + other live state; ne appears only once)
        self.assertEqual(2, mock_state_email.call_count)

        calls = mock_state_email.call_args_list
        call_jurisdictions = [call.kwargs['jurisdiction'] for call in calls]
        self.assertEqual(sorted(call_jurisdictions), ['ne', 'oh'])

        # Verify all calls have the correct template_variables structure
        for call in calls:
            self.assertEqual(call.kwargs['compact'], DEFAULT_COMPACT)
            self.assertEqual(
                call.kwargs['template_variables'],
                EncumbranceNotificationTemplateVariables(
                    provider_first_name='Björk',
                    provider_last_name='Guðmundsdóttir',
                    encumbered_jurisdiction='ne',
                    license_type='cosmetologist',
                    effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                    provider_id=UUID(DEFAULT_PROVIDER_ID),
                ),
            )

    @patch('cc_common.email_service_client.EmailServiceClient.send_privilege_encumbrance_state_notification_email')
    def test_privilege_encumbrance_listener_notifies_inactive_licenses_and_privileges(self, mock_state_email):
        """Test that inactive licenses and privileges generate notifications."""
        from cc_common.email_service_client import EncumbranceNotificationTemplateVariables
        from handlers.encumbrance_events import privilege_encumbrance_notification_listener

        # Set up test data
        self.test_data_generator.put_default_provider_record_in_provider_table()
        self.test_data_generator.put_default_license_record_in_provider_table()

        message = self._generate_privilege_encumbrance_message()
        event = self._create_sqs_event(message)

        # Execute the handler
        result = privilege_encumbrance_notification_listener(event, self.mock_context)

        # Should succeed with no batch failures
        self.assertEqual({'batchItemFailures': []}, result)

        # Verify 2 notifications (encumbered state + other live state)
        self.assertEqual(2, mock_state_email.call_count)

        calls = mock_state_email.call_args_list
        call_jurisdictions = [call.kwargs['jurisdiction'] for call in calls]
        self.assertEqual(sorted(call_jurisdictions), ['ne', 'oh'])

        # Verify all calls have the correct template_variables structure
        for call in calls:
            self.assertEqual(call.kwargs['compact'], DEFAULT_COMPACT)
            self.assertEqual(
                call.kwargs['template_variables'],
                EncumbranceNotificationTemplateVariables(
                    provider_first_name='Björk',
                    provider_last_name='Guðmundsdóttir',
                    encumbered_jurisdiction='ne',
                    license_type='cosmetologist',
                    effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                    provider_id=UUID(DEFAULT_PROVIDER_ID),
                ),
            )

    @patch(
        'cc_common.email_service_client.EmailServiceClient.send_privilege_encumbrance_lifting_state_notification_email'
    )
    def test_privilege_encumbrance_lifting_notification_listener_processes_event(self, mock_state_email):
        """Test that privilege encumbrance lifting listener processes events and sends state notifications."""
        from cc_common.email_service_client import EncumbranceNotificationTemplateVariables
        from handlers.encumbrance_events import privilege_encumbrance_lifting_notification_listener

        # Set up test data
        self.test_data_generator.put_default_provider_record_in_provider_table()
        self.test_data_generator.put_default_license_record_in_provider_table()

        self.test_data_generator.put_default_adverse_action_record_in_provider_table(
            value_overrides={
                'actionAgainst': 'privilege',
                'effectiveLiftDate': date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                'jurisdiction': 'ne',
                'licenseTypeAbbreviation': DEFAULT_LICENSE_TYPE_ABBREVIATION,
                'licenseType': DEFAULT_LICENSE_TYPE,
            }
        )

        message = self._generate_privilege_encumbrance_lifting_message()
        event = self._create_sqs_event(message)

        # Execute the handler
        result = privilege_encumbrance_lifting_notification_listener(event, self.mock_context)

        # Should succeed with no batch failures
        self.assertEqual({'batchItemFailures': []}, result)

        # Verify state notifications: lifting jurisdiction + other live states
        self.assertEqual(2, mock_state_email.call_count)

        calls = mock_state_email.call_args_list
        call_jurisdictions = [call.kwargs['jurisdiction'] for call in calls]
        self.assertEqual(sorted(call_jurisdictions), ['ne', 'oh'])

        # Verify all calls have the correct template_variables structure
        for call in calls:
            self.assertEqual(call.kwargs['compact'], DEFAULT_COMPACT)
            self.assertEqual(
                call.kwargs['template_variables'],
                EncumbranceNotificationTemplateVariables(
                    provider_first_name='Björk',
                    provider_last_name='Guðmundsdóttir',
                    encumbered_jurisdiction='ne',
                    license_type='cosmetologist',
                    effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                    provider_id=UUID(DEFAULT_PROVIDER_ID),
                ),
            )

    @patch(
        'cc_common.email_service_client.EmailServiceClient.send_privilege_encumbrance_lifting_state_notification_email'
    )
    def test_privilege_encumbrance_lifting_notification_listener_identifies_notification_jurisdictions(
        self, mock_state_email
    ):
        """Test that privilege encumbrance lifting listener correctly identifies states to notify
        (live compact jurisdictions)."""
        from cc_common.email_service_client import EncumbranceNotificationTemplateVariables
        from handlers.encumbrance_events import privilege_encumbrance_lifting_notification_listener

        # Set up test data
        self.test_data_generator.put_default_provider_record_in_provider_table()
        self.test_data_generator.put_default_license_record_in_provider_table()

        self.test_data_generator.put_default_adverse_action_record_in_provider_table(
            value_overrides={
                'actionAgainst': 'privilege',
                'effectiveLiftDate': date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                'jurisdiction': DEFAULT_PRIVILEGE_JURISDICTION,
                'licenseTypeAbbreviation': DEFAULT_LICENSE_TYPE_ABBREVIATION,
                'licenseType': DEFAULT_LICENSE_TYPE,
            }
        )

        # The encumbrance lifting occurs in DEFAULT_PRIVILEGE_JURISDICTION ('ne'); live = [oh, ne]
        message = self._generate_privilege_encumbrance_lifting_message()
        event = self._create_sqs_event(message)

        # Execute the handler
        result = privilege_encumbrance_lifting_notification_listener(event, self.mock_context)

        # Should succeed with no batch failures
        self.assertEqual({'batchItemFailures': []}, result)

        # Verify state notifications: lifting jurisdiction + other live states
        self.assertEqual(2, mock_state_email.call_count)

        calls = mock_state_email.call_args_list
        call_jurisdictions = [call.kwargs['jurisdiction'] for call in calls]
        self.assertEqual(sorted(call_jurisdictions), ['ne', 'oh'])

        # Verify all calls have the correct template_variables structure
        for call in calls:
            self.assertEqual(call.kwargs['compact'], DEFAULT_COMPACT)
            self.assertEqual(
                call.kwargs['template_variables'],
                EncumbranceNotificationTemplateVariables(
                    provider_first_name='Björk',
                    provider_last_name='Guðmundsdóttir',
                    encumbered_jurisdiction='ne',
                    license_type='cosmetologist',
                    effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                    provider_id=UUID(DEFAULT_PROVIDER_ID),
                ),
            )

    @patch(
        'cc_common.email_service_client.EmailServiceClient.send_privilege_encumbrance_lifting_state_notification_email'
    )
    def test_privilege_encumbrance_lifting_notification_listener_determines_latest_effective_lift_date(
        self, mock_state_email
    ):
        """Test that privilege encumbrance lifting listener correctly determines latest effective lift date."""
        from cc_common.email_service_client import EncumbranceNotificationTemplateVariables
        from handlers.encumbrance_events import privilege_encumbrance_lifting_notification_listener

        # In this test, a privilege was encumbered, and its associated license was also encumbered. The
        # encumbrance was lifted for the privilege first, but it was still encumbered by nature of its license
        # being encumbered. The license encumbrance was then lifted, so the latest effective lift date should match
        # with the license adverse action effective lift date
        privilege_effective_lift_date = date.fromisoformat('2024-05-05')
        license_effective_lift_date = date.fromisoformat('2025-06-06')

        # Set up test data
        self.test_data_generator.put_default_provider_record_in_provider_table()

        self.test_data_generator.put_default_adverse_action_record_in_provider_table(
            value_overrides={
                'actionAgainst': 'privilege',
                'effectiveLiftDate': privilege_effective_lift_date,
                'jurisdiction': DEFAULT_PRIVILEGE_JURISDICTION,
                'licenseTypeAbbreviation': DEFAULT_LICENSE_TYPE_ABBREVIATION,
                'licenseType': DEFAULT_LICENSE_TYPE,
            }
        )

        # Create active licenses in multiple jurisdictions (excluding the lifting jurisdiction 'ne')
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'jurisdiction': 'co',
                'jurisdictionUploadedLicenseStatus': 'active',
            }
        )
        self.test_data_generator.put_default_adverse_action_record_in_provider_table(
            value_overrides={
                'actionAgainst': 'license',
                'effectiveLiftDate': license_effective_lift_date,
                'jurisdiction': 'co',
                'licenseTypeAbbreviation': DEFAULT_LICENSE_TYPE_ABBREVIATION,
                'licenseType': DEFAULT_LICENSE_TYPE,
            }
        )

        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'jurisdiction': 'ky',
                'jurisdictionUploadedLicenseStatus': 'active',
            }
        )

        # The encumbrance lifting occurs in DEFAULT_PRIVILEGE_JURISDICTION ('ne')
        message = self._generate_privilege_encumbrance_lifting_message()
        event = self._create_sqs_event(message)

        # Execute the handler
        result = privilege_encumbrance_lifting_notification_listener(event, self.mock_context)

        # Should succeed with no batch failures
        self.assertEqual({'batchItemFailures': []}, result)

        # Verify state notifications: lifting jurisdiction + other live states
        self.assertEqual(2, mock_state_email.call_count)

        calls = mock_state_email.call_args_list
        call_jurisdictions = [call.kwargs['jurisdiction'] for call in calls]
        self.assertEqual(sorted(call_jurisdictions), ['ne', 'oh'])

        # Verify all calls have the correct template_variables structure
        for call in calls:
            self.assertEqual(call.kwargs['compact'], DEFAULT_COMPACT)
            self.assertEqual(
                call.kwargs['template_variables'],
                EncumbranceNotificationTemplateVariables(
                    provider_first_name='Björk',
                    provider_last_name='Guðmundsdóttir',
                    encumbered_jurisdiction='ne',
                    license_type='cosmetologist',
                    effective_date=license_effective_lift_date,
                    provider_id=UUID(DEFAULT_PROVIDER_ID),
                ),
            )

    @patch(
        'cc_common.email_service_client.EmailServiceClient.send_privilege_encumbrance_lifting_state_notification_email'
    )
    def test_privilege_encumbrance_lifting_notification_listener_determines_latest_license_effective_lift_date_when_no_privilege_encumbrance(  # noqa: E501
        self, mock_state_email
    ):
        """Test that privilege encumbrance lifting listener correctly determines latest effective lift date."""
        from cc_common.email_service_client import EncumbranceNotificationTemplateVariables
        from handlers.encumbrance_events import privilege_encumbrance_lifting_notification_listener

        # In this test, a privilege's associated license was encumbered, so the privilege was encumbered as a result.
        # The license encumbrance was then lifted, so the latest effective lift date should match
        # with the license adverse action effective lift date
        license_effective_lift_date = date.fromisoformat('2025-06-06')

        # Set up test data
        self.test_data_generator.put_default_provider_record_in_provider_table()

        # Create active licenses in multiple jurisdictions (excluding the lifting jurisdiction 'ne')
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'jurisdiction': 'co',
                'jurisdictionUploadedLicenseStatus': 'active',
            }
        )
        self.test_data_generator.put_default_adverse_action_record_in_provider_table(
            value_overrides={
                'actionAgainst': 'license',
                'effectiveLiftDate': license_effective_lift_date,
                'jurisdiction': 'co',
                'licenseTypeAbbreviation': DEFAULT_LICENSE_TYPE_ABBREVIATION,
                'licenseType': DEFAULT_LICENSE_TYPE,
            }
        )

        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'jurisdiction': 'ky',
                'jurisdictionUploadedLicenseStatus': 'active',
            }
        )

        # The encumbrance lifting occurs in DEFAULT_PRIVILEGE_JURISDICTION ('ne')
        message = self._generate_privilege_encumbrance_lifting_message()
        event = self._create_sqs_event(message)

        # Execute the handler
        result = privilege_encumbrance_lifting_notification_listener(event, self.mock_context)

        # Should succeed with no batch failures
        self.assertEqual({'batchItemFailures': []}, result)

        # Verify state notifications: lifting jurisdiction + other live states
        self.assertEqual(2, mock_state_email.call_count)

        calls = mock_state_email.call_args_list
        call_jurisdictions = [call.kwargs['jurisdiction'] for call in calls]
        self.assertEqual(sorted(call_jurisdictions), ['ne', 'oh'])

        # Verify all calls have the correct template_variables structure
        for call in calls:
            self.assertEqual(call.kwargs['compact'], DEFAULT_COMPACT)
            self.assertEqual(
                call.kwargs['template_variables'],
                EncumbranceNotificationTemplateVariables(
                    provider_first_name='Björk',
                    provider_last_name='Guðmundsdóttir',
                    encumbered_jurisdiction='ne',
                    license_type='cosmetologist',
                    effective_date=license_effective_lift_date,
                    provider_id=UUID(DEFAULT_PROVIDER_ID),
                ),
            )

    def test_privilege_encumbrance_lifting_notification_listener_handles_provider_retrieval_failure(self):
        """Test that privilege encumbrance lifting listener handles provider retrieval failures."""
        from handlers.encumbrance_events import privilege_encumbrance_lifting_notification_listener

        # Don't create any provider records - should cause retrieval failure
        message = self._generate_privilege_encumbrance_lifting_message()
        event = self._create_sqs_event(message)

        # SQS handler wrapper catches exceptions and returns batch item failures
        result = privilege_encumbrance_lifting_notification_listener(event, self.mock_context)

        # Should return batch item failure for the message
        expected_failure = {'batchItemFailures': [{'itemIdentifier': event['Records'][0]['messageId']}]}
        self.assertEqual(expected_failure, result)

    @patch('cc_common.email_service_client.EmailServiceClient.send_license_encumbrance_state_notification_email')
    def test_license_encumbrance_notification_listener_processes_event(self, mock_state_email):
        """Test that license encumbrance notification listener processes events and sends state notifications."""
        from cc_common.email_service_client import EncumbranceNotificationTemplateVariables
        from handlers.encumbrance_events import license_encumbrance_notification_listener

        # Set up test data
        self.test_data_generator.put_default_provider_record_in_provider_table()

        # Add the license that is being encumbered (in DEFAULT_LICENSE_JURISDICTION = 'oh')
        self.test_data_generator.put_default_license_record_in_provider_table()

        message = self._generate_license_encumbrance_message()
        event = self._create_sqs_event(message)

        # Execute the handler
        result = license_encumbrance_notification_listener(event, self.mock_context)

        # Should succeed with no batch failures
        self.assertEqual({'batchItemFailures': []}, result)

        # Verify state notifications: encumbered + other live states
        self.assertEqual(2, mock_state_email.call_count)

        calls = mock_state_email.call_args_list
        call_jurisdictions = [call.kwargs['jurisdiction'] for call in calls]
        self.assertEqual(sorted(call_jurisdictions), ['ne', 'oh'])

        # Verify all calls have the correct template_variables structure
        for call in calls:
            self.assertEqual(call.kwargs['compact'], DEFAULT_COMPACT)
            self.assertEqual(
                call.kwargs['template_variables'],
                EncumbranceNotificationTemplateVariables(
                    provider_first_name='Björk',
                    provider_last_name='Guðmundsdóttir',
                    encumbered_jurisdiction='oh',
                    license_type='cosmetologist',
                    effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                    provider_id=UUID(DEFAULT_PROVIDER_ID),
                ),
            )

    @patch('cc_common.email_service_client.EmailServiceClient.send_license_encumbrance_state_notification_email')
    def test_license_encumbrance_notification_listener_identifies_notification_jurisdictions(self, mock_state_email):
        """Test that license encumbrance notification listener correctly identifies states to notify."""
        from cc_common.email_service_client import EncumbranceNotificationTemplateVariables
        from handlers.encumbrance_events import license_encumbrance_notification_listener

        # Set up test data
        self.test_data_generator.put_default_provider_record_in_provider_table()

        # Add the license that is being encumbered (in DEFAULT_LICENSE_JURISDICTION = 'oh')
        self.test_data_generator.put_default_license_record_in_provider_table()

        # The encumbrance occurs in DEFAULT_LICENSE_JURISDICTION ('oh'); live = [oh, ne]
        message = self._generate_license_encumbrance_message()
        event = self._create_sqs_event(message)

        # Execute the handler
        result = license_encumbrance_notification_listener(event, self.mock_context)

        # Should succeed with no batch failures
        self.assertEqual({'batchItemFailures': []}, result)

        # Verify state notifications: encumbered + other live states
        self.assertEqual(2, mock_state_email.call_count)

        calls = mock_state_email.call_args_list
        call_jurisdictions = [call.kwargs['jurisdiction'] for call in calls]
        self.assertEqual(sorted(call_jurisdictions), ['ne', 'oh'])

        # Verify all calls have the correct template_variables structure
        for call in calls:
            self.assertEqual(call.kwargs['compact'], DEFAULT_COMPACT)
            self.assertEqual(
                call.kwargs['template_variables'],
                EncumbranceNotificationTemplateVariables(
                    provider_first_name='Björk',
                    provider_last_name='Guðmundsdóttir',
                    encumbered_jurisdiction='oh',
                    license_type='cosmetologist',
                    effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                    provider_id=UUID(DEFAULT_PROVIDER_ID),
                ),
            )

    def test_license_encumbrance_notification_listener_handles_provider_retrieval_failure(self):
        """Test that license encumbrance notification listener handles provider retrieval failures."""
        from handlers.encumbrance_events import license_encumbrance_notification_listener

        # Don't create any provider records - should cause retrieval failure
        message = self._generate_license_encumbrance_message()
        event = self._create_sqs_event(message)

        # SQS handler wrapper catches exceptions and returns batch item failures
        result = license_encumbrance_notification_listener(event, self.mock_context)

        # Should return batch item failure for the message
        expected_failure = {'batchItemFailures': [{'itemIdentifier': event['Records'][0]['messageId']}]}
        self.assertEqual(expected_failure, result)

    @patch('cc_common.email_service_client.EmailServiceClient.send_license_encumbrance_state_notification_email')
    def test_license_encumbrance_notification_listener_excludes_encumbered_jurisdiction_from_notifications(
        self, mock_state_email
    ):
        """Test that the jurisdiction where license encumbrance occurred is not duplicated in notifications."""
        from cc_common.email_service_client import EncumbranceNotificationTemplateVariables
        from handlers.encumbrance_events import license_encumbrance_notification_listener

        # Set up test data
        self.test_data_generator.put_default_provider_record_in_provider_table()

        # Add the license that is being encumbered (in DEFAULT_LICENSE_JURISDICTION = 'oh')
        self.test_data_generator.put_default_license_record_in_provider_table()

        message = self._generate_license_encumbrance_message()
        event = self._create_sqs_event(message)

        # Execute the handler
        result = license_encumbrance_notification_listener(event, self.mock_context)

        # Should succeed with no batch failures
        self.assertEqual({'batchItemFailures': []}, result)

        # Verify exactly 2 notifications (encumbered state + other live state; oh appears only once)
        self.assertEqual(2, mock_state_email.call_count)

        calls = mock_state_email.call_args_list
        call_jurisdictions = [call.kwargs['jurisdiction'] for call in calls]
        self.assertEqual(sorted(call_jurisdictions), ['ne', 'oh'])

        # Verify all calls have the correct template_variables structure
        for call in calls:
            self.assertEqual(call.kwargs['compact'], DEFAULT_COMPACT)
            self.assertEqual(
                call.kwargs['template_variables'],
                EncumbranceNotificationTemplateVariables(
                    provider_first_name='Björk',
                    provider_last_name='Guðmundsdóttir',
                    encumbered_jurisdiction='oh',
                    license_type='cosmetologist',
                    effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                    provider_id=UUID(DEFAULT_PROVIDER_ID),
                ),
            )

    @patch('cc_common.email_service_client.EmailServiceClient.send_license_encumbrance_state_notification_email')
    def test_license_encumbrance_notification_listener_notifies_all_licenses_and_privileges_including_inactive(
        self, mock_state_email
    ):
        """Test that all licenses and privileges generate notifications, including inactive ones."""
        from cc_common.email_service_client import EncumbranceNotificationTemplateVariables
        from handlers.encumbrance_events import license_encumbrance_notification_listener

        # Set up test data
        self.test_data_generator.put_default_provider_record_in_provider_table()

        # Add the license that is being encumbered (in DEFAULT_LICENSE_JURISDICTION = 'oh')
        self.test_data_generator.put_default_license_record_in_provider_table()

        message = self._generate_license_encumbrance_message()
        event = self._create_sqs_event(message)

        # Execute the handler
        result = license_encumbrance_notification_listener(event, self.mock_context)

        # Should succeed with no batch failures
        self.assertEqual({'batchItemFailures': []}, result)

        # Verify 2 notifications (encumbered + other live state)
        self.assertEqual(2, mock_state_email.call_count)

        calls = mock_state_email.call_args_list
        call_jurisdictions = [call.kwargs['jurisdiction'] for call in calls]
        self.assertEqual(sorted(call_jurisdictions), ['ne', 'oh'])

        # Verify all calls have the correct template_variables structure
        for call in calls:
            self.assertEqual(call.kwargs['compact'], DEFAULT_COMPACT)
            self.assertEqual(
                call.kwargs['template_variables'],
                EncumbranceNotificationTemplateVariables(
                    provider_first_name='Björk',
                    provider_last_name='Guðmundsdóttir',
                    encumbered_jurisdiction='oh',
                    license_type='cosmetologist',
                    effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                    provider_id=UUID(DEFAULT_PROVIDER_ID),
                ),
            )

    @patch(
        'cc_common.email_service_client.EmailServiceClient.send_license_encumbrance_lifting_state_notification_email'
    )
    def test_license_encumbrance_lifting_notification_listener_processes_event(self, mock_state_email):
        """Test that license encumbrance lifting notification listener processes events."""
        from cc_common.email_service_client import EncumbranceNotificationTemplateVariables
        from handlers.encumbrance_events import license_encumbrance_lifting_notification_listener

        # Set up test data
        self.test_data_generator.put_default_provider_record_in_provider_table()

        # Add the license where encumbrance is being lifted (in DEFAULT_LICENSE_JURISDICTION = 'oh')
        self.test_data_generator.put_default_license_record_in_provider_table()

        self.test_data_generator.put_default_adverse_action_record_in_provider_table(
            value_overrides={
                'actionAgainst': 'license',
                'effectiveLiftDate': date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                'jurisdiction': DEFAULT_LICENSE_JURISDICTION,
                'licenseTypeAbbreviation': DEFAULT_LICENSE_TYPE_ABBREVIATION,
                'licenseType': DEFAULT_LICENSE_TYPE,
            }
        )

        message = self._generate_license_encumbrance_lifting_message()
        event = self._create_sqs_event(message)

        # Execute the handler
        result = license_encumbrance_lifting_notification_listener(event, self.mock_context)

        # Should succeed with no batch failures
        self.assertEqual({'batchItemFailures': []}, result)

        # Verify state notifications: lifting jurisdiction + other live states
        self.assertEqual(2, mock_state_email.call_count)

        calls = mock_state_email.call_args_list
        call_jurisdictions = [call.kwargs['jurisdiction'] for call in calls]
        self.assertEqual(sorted(call_jurisdictions), ['ne', 'oh'])

        # Verify all calls have the correct template_variables structure
        for call in calls:
            self.assertEqual(call.kwargs['compact'], DEFAULT_COMPACT)
            self.assertEqual(
                call.kwargs['template_variables'],
                EncumbranceNotificationTemplateVariables(
                    provider_first_name='Björk',
                    provider_last_name='Guðmundsdóttir',
                    encumbered_jurisdiction='oh',
                    license_type='cosmetologist',
                    effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                    provider_id=UUID(DEFAULT_PROVIDER_ID),
                ),
            )

    @patch(
        'cc_common.email_service_client.EmailServiceClient.send_license_encumbrance_lifting_state_notification_email'
    )
    def test_license_encumbrance_lifting_notification_listener_identifies_notification_jurisdictions(
        self, mock_state_email
    ):
        """Test that license encumbrance lifting notification listener correctly identifies states to notify."""
        from cc_common.email_service_client import EncumbranceNotificationTemplateVariables
        from handlers.encumbrance_events import license_encumbrance_lifting_notification_listener

        # Set up test data
        self.test_data_generator.put_default_provider_record_in_provider_table()

        # Add the license where encumbrance is being lifted (in DEFAULT_LICENSE_JURISDICTION = 'oh')
        self.test_data_generator.put_default_license_record_in_provider_table()

        # Create active licenses in multiple jurisdictions (excluding the lifting jurisdiction 'oh')
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'jurisdiction': 'ne',
                'jurisdictionUploadedLicenseStatus': 'active',
            }
        )
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'jurisdiction': 'ky',
                'jurisdictionUploadedLicenseStatus': 'active',
            }
        )

        self.test_data_generator.put_default_adverse_action_record_in_provider_table(
            value_overrides={
                'actionAgainst': 'license',
                'effectiveLiftDate': date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                'jurisdiction': DEFAULT_LICENSE_JURISDICTION,
                'licenseTypeAbbreviation': DEFAULT_LICENSE_TYPE_ABBREVIATION,
                'licenseType': DEFAULT_LICENSE_TYPE,
            }
        )

        # The encumbrance lifting occurs in DEFAULT_LICENSE_JURISDICTION ('oh'); live = [oh, ne]
        message = self._generate_license_encumbrance_lifting_message()
        event = self._create_sqs_event(message)

        # Execute the handler
        result = license_encumbrance_lifting_notification_listener(event, self.mock_context)

        # Should succeed with no batch failures
        self.assertEqual({'batchItemFailures': []}, result)

        # Verify state notifications: lifting jurisdiction + other live states
        self.assertEqual(2, mock_state_email.call_count)

        calls = mock_state_email.call_args_list
        call_jurisdictions = [call.kwargs['jurisdiction'] for call in calls]
        self.assertEqual(sorted(call_jurisdictions), ['ne', 'oh'])

        # Verify all calls have the correct template_variables structure
        for call in calls:
            self.assertEqual(call.kwargs['compact'], DEFAULT_COMPACT)
            self.assertEqual(
                EncumbranceNotificationTemplateVariables(
                    provider_first_name='Björk',
                    provider_last_name='Guðmundsdóttir',
                    encumbered_jurisdiction='oh',
                    license_type='cosmetologist',
                    effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                    provider_id=UUID(DEFAULT_PROVIDER_ID),
                ),
                call.kwargs['template_variables'],
            )

    def test_license_encumbrance_lifting_notification_listener_handles_provider_retrieval_failure(self):
        """Test that license encumbrance lifting notification listener handles provider retrieval failures."""
        from handlers.encumbrance_events import license_encumbrance_lifting_notification_listener

        # Don't create any provider records - should cause retrieval failure
        message = self._generate_license_encumbrance_lifting_message()
        event = self._create_sqs_event(message)

        # SQS handler wrapper catches exceptions and returns batch item failures
        result = license_encumbrance_lifting_notification_listener(event, self.mock_context)

        # Should return batch item failure for the message
        expected_failure = {'batchItemFailures': [{'itemIdentifier': event['Records'][0]['messageId']}]}
        self.assertEqual(expected_failure, result)

    @patch(
        'cc_common.email_service_client.EmailServiceClient.send_license_encumbrance_lifting_state_notification_email'
    )
    @patch('cc_common.email_service_client.EmailServiceClient.send_license_encumbrance_state_notification_email')
    def test_license_encumbrance_notification_listeners_handle_no_additional_jurisdictions(
        self, mock_enc_state, mock_lift_state
    ):
        """
        Test that license encumbrance notification listeners handle case where compact has only one live
        jurisdiction (no additional states to notify).
        """
        from cc_common.config import config
        from handlers.encumbrance_events import (
            license_encumbrance_lifting_notification_listener,
            license_encumbrance_notification_listener,
        )

        # Only one live jurisdiction so no "additional" state notifications
        config.__dict__['live_compact_jurisdictions'] = {DEFAULT_COMPACT: [DEFAULT_LICENSE_JURISDICTION]}
        try:
            # Set up test data
            self.test_data_generator.put_default_provider_record_in_provider_table()

            # Add the license that is being encumbered/lifted (in DEFAULT_LICENSE_JURISDICTION = 'oh')
            self.test_data_generator.put_default_license_record_in_provider_table()

            self.test_data_generator.put_default_adverse_action_record_in_provider_table(
                value_overrides={
                    'actionAgainst': 'license',
                    'effectiveLiftDate': date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                    'jurisdiction': DEFAULT_LICENSE_JURISDICTION,
                    'licenseTypeAbbreviation': DEFAULT_LICENSE_TYPE_ABBREVIATION,
                    'licenseType': DEFAULT_LICENSE_TYPE,
                }
            )

            # Test license encumbrance notification
            message = self._generate_license_encumbrance_message()
            event = self._create_sqs_event(message)
            result = license_encumbrance_notification_listener(event, self.mock_context)

            # Should succeed with no batch failures
            self.assertEqual({'batchItemFailures': []}, result)

            # Test license encumbrance lifting notification
            message = self._generate_license_encumbrance_lifting_message()
            event = self._create_sqs_event(message)
            result = license_encumbrance_lifting_notification_listener(event, self.mock_context)

            # Should succeed with no batch failures
            self.assertEqual({'batchItemFailures': []}, result)

            # Verify license encumbrance notifications: only state 'oh' (no additional live jurisdictions)
            from cc_common.email_service_client import EncumbranceNotificationTemplateVariables

            mock_enc_state.assert_called_once_with(
                compact=DEFAULT_COMPACT,
                jurisdiction='oh',
                template_variables=EncumbranceNotificationTemplateVariables(
                    provider_first_name='Björk',
                    provider_last_name='Guðmundsdóttir',
                    encumbered_jurisdiction='oh',
                    license_type='cosmetologist',
                    effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                    provider_id=UUID(DEFAULT_PROVIDER_ID),
                ),
            )

            # Verify license lifting notifications: only state 'oh'
            mock_lift_state.assert_called_once_with(
                compact=DEFAULT_COMPACT,
                jurisdiction='oh',
                template_variables=EncumbranceNotificationTemplateVariables(
                    provider_first_name='Björk',
                    provider_last_name='Guðmundsdóttir',
                    encumbered_jurisdiction='oh',
                    license_type='cosmetologist',
                    effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                    provider_id=UUID(DEFAULT_PROVIDER_ID),
                ),
            )
        finally:
            config.__dict__.pop('live_compact_jurisdictions', None)

    @patch('cc_common.event_bus_client.EventBusClient._publish_event')
    def test_license_encumbrance_lifted_listener_uses_effective_date_from_message(self, mock_publish_event):
        """Test that published privilege encumbrance lifting events use the effectiveDate from the message."""
        # Handler fetches provider + license to verify license is unencumbered before publishing
        self.test_data_generator.put_default_provider_record_in_provider_table()
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'jurisdiction': DEFAULT_LICENSE_JURISDICTION,
                'licenseType': DEFAULT_LICENSE_TYPE,
                'encumberedStatus': 'unencumbered',
            }
        )
        self._run_license_encumbrance_lifted_listener_with_live_jurisdictions(
            {DEFAULT_COMPACT: [DEFAULT_LICENSE_JURISDICTION, 'ky']},
            message_overrides={'effectiveDate': '2024-03-15'},
        )

        mock_publish_event.assert_called_once()
        call_args = mock_publish_event.call_args[1]
        self.assertEqual('privilege.encumbranceLifted', call_args['detail_type'])
        self.assertEqual('2024-03-15', call_args['detail']['effectiveDate'])
        self.assertEqual('ky', call_args['detail']['jurisdiction'])

    def _when_testing_privilege_lift_handler_with_encumbered_privilege(self, encumbered_status, mock_state_email):
        from cc_common.data_model.schema.common import PrivilegeEncumberedStatusEnum
        from handlers.encumbrance_events import privilege_encumbrance_lifting_notification_listener

        # Set up test data: provider and a license so find_best_license_in_current_known_licenses succeeds
        self.test_data_generator.put_default_provider_record_in_provider_table()

        if encumbered_status == PrivilegeEncumberedStatusEnum.ENCUMBERED:
            # Privilege still encumbered: privilege adverse action with no effectiveLiftDate
            # (handler returns early and sends no notifications)
            self.test_data_generator.put_default_adverse_action_record_in_provider_table(
                value_overrides={
                    'actionAgainst': 'privilege',
                    'jurisdiction': DEFAULT_PRIVILEGE_JURISDICTION,
                    'licenseTypeAbbreviation': DEFAULT_LICENSE_TYPE_ABBREVIATION,
                    'licenseType': DEFAULT_LICENSE_TYPE,
                }
            )
            self.test_data_generator.put_default_license_record_in_provider_table()
        else:
            # License still encumbered: privilege adverse action lifted, but license encumbered
            # (handler passes privilege check then skips due to license encumberedStatus)
            self.test_data_generator.put_default_adverse_action_record_in_provider_table(
                value_overrides={
                    'actionAgainst': 'privilege',
                    'effectiveLiftDate': date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                    'jurisdiction': DEFAULT_PRIVILEGE_JURISDICTION,
                    'licenseTypeAbbreviation': DEFAULT_LICENSE_TYPE_ABBREVIATION,
                    'licenseType': DEFAULT_LICENSE_TYPE,
                }
            )
            self.test_data_generator.put_default_license_record_in_provider_table(
                value_overrides={'encumberedStatus': 'encumbered'}
            )

        # Generate privilege encumbrance lifting event
        message = self._generate_privilege_encumbrance_lifting_message()
        event = self._create_sqs_event(message)

        # Execute the handler
        result = privilege_encumbrance_lifting_notification_listener(event, self.mock_context)

        # Should succeed with no batch failures (handler completes successfully)
        self.assertEqual({'batchItemFailures': []}, result)

        # Verify NO notifications were sent because privilege is still encumbered
        mock_state_email.assert_not_called()

    @patch(
        'cc_common.email_service_client.EmailServiceClient.send_privilege_encumbrance_lifting_state_notification_email'
    )
    def test_privilege_encumbrance_lifting_notification_listener_skips_notifications_when_privilege_still_encumbered(
        self, mock_state_email
    ):
        """Test that privilege encumbrance lifting notifications are NOT sent when privilege is still encumbered."""
        from cc_common.data_model.schema.common import PrivilegeEncumberedStatusEnum

        self._when_testing_privilege_lift_handler_with_encumbered_privilege(
            PrivilegeEncumberedStatusEnum.ENCUMBERED, mock_state_email
        )

    @patch(
        'cc_common.email_service_client.EmailServiceClient.send_privilege_encumbrance_lifting_state_notification_email'
    )
    def test_privilege_encumbrance_lifting_notification_listener_skips_notifications_when_privilege_license_encumbered(
        self, mock_state_email
    ):
        """Test that privilege encumbrance lifting notifications are NOT sent when privilege is LICENSE_ENCUMBERED."""
        from cc_common.data_model.schema.common import PrivilegeEncumberedStatusEnum

        self._when_testing_privilege_lift_handler_with_encumbered_privilege(
            PrivilegeEncumberedStatusEnum.LICENSE_ENCUMBERED, mock_state_email
        )

    @patch(
        'cc_common.email_service_client.EmailServiceClient.send_license_encumbrance_lifting_state_notification_email'
    )
    def test_license_encumbrance_lifting_notification_listener_skips_notifications_when_license_still_encumbered(
        self, mock_state_email
    ):
        """Test that license encumbrance lifting notifications are NOT sent when license is still encumbered."""
        from handlers.encumbrance_events import license_encumbrance_lifting_notification_listener

        # Set up test data
        self.test_data_generator.put_default_provider_record_in_provider_table()

        # Create a license that is still ENCUMBERED (has another adverse action)
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'jurisdiction': DEFAULT_LICENSE_JURISDICTION,
                'encumberedStatus': 'encumbered',  # Still encumbered due to another adverse action
            }
        )

        # Generate license encumbrance lifting event
        message = self._generate_license_encumbrance_lifting_message()
        event = self._create_sqs_event(message)

        # Execute the handler
        result = license_encumbrance_lifting_notification_listener(event, self.mock_context)

        # Should succeed with no batch failures (handler completes successfully)
        self.assertEqual({'batchItemFailures': []}, result)

        # Verify NO notifications were sent because license is still encumbered
        mock_state_email.assert_not_called()

    @patch('cc_common.email_service_client.EmailServiceClient.send_license_encumbrance_state_notification_email')
    def test_license_encumbrance_notification_listener_skips_already_sent_notifications_and_retries_failed(
        self, mock_state_email
    ):
        """
        Test that license encumbrance notification listener skips notifications that were already sent successfully
        and only retries notifications that failed in a previous attempt.
        """
        from cc_common.event_state_client import EventType, NotificationTracker, RecipientType
        from handlers.encumbrance_events import license_encumbrance_notification_listener

        # Set up test data (live = [oh, ne]; primary is oh, additional is ne)
        self.test_data_generator.put_default_provider_record_in_provider_table()
        self.test_data_generator.put_default_license_record_in_provider_table()

        message = self._generate_license_encumbrance_message()
        event = self._create_sqs_event(message)

        # Mock previous attempt where the notification to oh succeeded and to ne failed
        tracker = NotificationTracker(compact=DEFAULT_COMPACT, message_id=event['Records'][0]['messageId'])
        tracker.record_success(
            recipient_type=RecipientType.STATE,
            provider_id=DEFAULT_PROVIDER_ID,
            event_type=EventType.LICENSE_ENCUMBRANCE,
            event_time=DEFAULT_DATE_OF_UPDATE_TIMESTAMP,
            jurisdiction=DEFAULT_LICENSE_JURISDICTION,
        )
        tracker.record_failure(
            recipient_type=RecipientType.STATE,
            provider_id=DEFAULT_PROVIDER_ID,
            event_type=EventType.LICENSE_ENCUMBRANCE,
            event_time=DEFAULT_DATE_OF_UPDATE_TIMESTAMP,
            error_message='something failed',
            jurisdiction=DEFAULT_PRIVILEGE_JURISDICTION,
        )

        # Execute listener, which should only retry notification to ne
        license_encumbrance_notification_listener(event, self.mock_context)

        # Re-instantiate tracker to get latest notification attempts
        updated_tracker = NotificationTracker(compact=DEFAULT_COMPACT, message_id=event['Records'][0]['messageId'])

        notification_records = updated_tracker._attempts  # noqa: SLF001

        # ne should now be SUCCESS
        self.assertEqual('SUCCESS', notification_records['NOTIFICATION#state#ne']['status'])

        # Verify only the email to ne was sent (retry)
        mock_state_email.assert_called_once_with(
            compact=DEFAULT_COMPACT,
            jurisdiction=DEFAULT_PRIVILEGE_JURISDICTION,
            template_variables=ANY,
        )

    @patch('cc_common.email_service_client.EmailServiceClient.send_license_encumbrance_state_notification_email')
    def test_license_encumbrance_notification_listener_creates_notification_events_to_track_successful_notifications(
        self,
        mock_state_email,  # noqa: ARG002
    ):
        """
        Test that license encumbrance notification listener stores successful notification events for tracking in the
        event of handler retries.
        """
        from cc_common.event_state_client import NotificationStatus, NotificationTracker
        from handlers.encumbrance_events import license_encumbrance_notification_listener

        # Set up test data (live = [oh, ne])
        self.test_data_generator.put_default_provider_record_in_provider_table()
        self.test_data_generator.put_default_license_record_in_provider_table()

        message = self._generate_license_encumbrance_message()
        event = self._create_sqs_event(message)

        # Execute
        license_encumbrance_notification_listener(event, self.mock_context)

        # Re-instantiate tracker to get latest notification attempts
        updated_tracker = NotificationTracker(compact=DEFAULT_COMPACT, message_id=event['Records'][0]['messageId'])

        notification_records = updated_tracker._attempts  # noqa: SLF001

        expected_sks = [
            'NOTIFICATION#state#ne',
            'NOTIFICATION#state#oh',
        ]

        self.assertEqual(expected_sks, sorted(notification_records.keys()))
        for sk in expected_sks:
            self.assertEqual(NotificationStatus.SUCCESS, notification_records.get(sk).get('status'))
