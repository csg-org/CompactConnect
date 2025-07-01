import json
from datetime import date, datetime
from unittest.mock import patch
from uuid import UUID

from boto3.dynamodb.conditions import Key
from common_test.test_constants import (
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
        return {'Records': [{'messageId': '123', 'body': json.dumps(message)}]}

    @patch('cc_common.event_bus_client.EventBusClient._publish_event')
    def test_license_encumbrance_listener_encumbers_unencumbered_privileges_successfully(self, mock_publish_event):
        """Test that license encumbrance event successfully encumbers associated unencumbered privileges."""
        from cc_common.data_model.schema.common import PrivilegeEncumberedStatusEnum
        from handlers.encumbrance_events import license_encumbrance_listener

        # Set up test data
        self.test_data_generator.put_default_provider_record_in_provider_table()

        # Create privileges with matching license jurisdiction and type - one unencumbered, another already encumbered
        self.test_data_generator.put_default_privilege_record_in_provider_table(
            value_overrides={
                'licenseJurisdiction': DEFAULT_LICENSE_JURISDICTION,
                'licenseTypeAbbreviation': DEFAULT_LICENSE_TYPE_ABBREVIATION,
                'encumberedStatus': 'unencumbered',
                'jurisdiction': 'ne',
            }
        )

        self.test_data_generator.put_default_privilege_record_in_provider_table(
            value_overrides={
                'licenseJurisdiction': DEFAULT_LICENSE_JURISDICTION,
                'licenseTypeAbbreviation': DEFAULT_LICENSE_TYPE_ABBREVIATION,
                'encumberedStatus': 'encumbered',  # Already encumbered
                'jurisdiction': 'ky',  # Different jurisdiction to distinguish
            }
        )

        message = self._generate_license_encumbrance_message()
        event = self._create_sqs_event(message)

        # Execute the handler
        license_encumbrance_listener(event, self.mock_context)

        # Verify that only the unencumbered privilege was encumbered
        provider_records = self.config.data_client.get_provider_user_records(
            compact=DEFAULT_COMPACT,
            provider_id=DEFAULT_PROVIDER_ID,
        )

        privileges = provider_records.get_privilege_records()

        # Find the privileges by jurisdiction
        previously_unencumbered_privilege = next(p for p in privileges if p.jurisdiction == 'ne')
        previously_encumbered_privilege = next(p for p in privileges if p.jurisdiction == 'ky')

        # Verify the unencumbered privilege is now LICENSE_ENCUMBERED
        self.assertEqual(
            PrivilegeEncumberedStatusEnum.LICENSE_ENCUMBERED, previously_unencumbered_privilege.encumberedStatus
        )

        # Verify the already encumbered privilege remains ENCUMBERED (not changed)
        self.assertEqual(PrivilegeEncumberedStatusEnum.ENCUMBERED, previously_encumbered_privilege.encumberedStatus)

        # Verify that a privilege encumbrance event was published for the affected privilege
        mock_publish_event.assert_called_once()
        call_args = mock_publish_event.call_args[1]

        # Extract and verify event_batch_writer separately
        called_event_batch_writer = call_args.pop('event_batch_writer')
        from cc_common.event_batch_writer import EventBatchWriter

        self.assertIsInstance(called_event_batch_writer, EventBatchWriter)

        # Now verify the rest with comprehensive assertion
        self.assertEqual(
            {
                'source': 'org.compactconnect.data-events',
                'detail_type': 'privilege.encumbrance',
                'detail': {
                    'compact': DEFAULT_COMPACT,
                    'providerId': DEFAULT_PROVIDER_ID,
                    'jurisdiction': 'ne',  # The privilege jurisdiction
                    'licenseTypeAbbreviation': DEFAULT_LICENSE_TYPE_ABBREVIATION,
                    'effectiveDate': DEFAULT_EFFECTIVE_DATE,
                    'eventTime': DEFAULT_DATE_OF_UPDATE_TIMESTAMP,
                },
            },
            call_args,
        )

    @patch('cc_common.event_bus_client.EventBusClient._publish_event')
    def test_license_encumbrance_listener_handles_no_matching_privileges(self, mock_publish_event):
        """Test that license encumbrance event handles case where no matching privileges exist."""
        from handlers.encumbrance_events import license_encumbrance_listener

        # Set up test data with no matching privileges
        self.test_data_generator.put_default_provider_record_in_provider_table()

        # Create privilege with different license jurisdiction/type
        self.test_data_generator.put_default_privilege_record_in_provider_table(
            value_overrides={
                'licenseJurisdiction': 'ky',  # Different jurisdiction
                'licenseTypeAbbreviation': 'aud',  # Different license type
                # note there is no encumberedStatus present
            }
        )

        message = self._generate_license_encumbrance_message()
        event = self._create_sqs_event(message)

        # Execute the handler - should not raise any exceptions
        license_encumbrance_listener(event, self.mock_context)

        # Verify no privileges were modified
        provider_records = self.config.data_client.get_provider_user_records(
            compact=DEFAULT_COMPACT,
            provider_id=DEFAULT_PROVIDER_ID,
        )

        privileges = provider_records.get_privilege_records()
        self.assertEqual(1, len(privileges))
        self.assertIsNone(privileges[0].encumberedStatus)

        # Verify no privilege encumbrance events were published since no privileges were affected
        mock_publish_event.assert_not_called()

    @patch('cc_common.event_bus_client.EventBusClient._publish_event')
    def test_license_encumbrance_listener_handles_all_privileges_already_encumbered(self, mock_publish_event):
        """Test that license encumbrance event handles case where all matching privileges are already encumbered."""
        from cc_common.data_model.schema.common import PrivilegeEncumberedStatusEnum
        from handlers.encumbrance_events import license_encumbrance_listener

        # Set up test data
        self.test_data_generator.put_default_provider_record_in_provider_table()

        # Create privileges that are already encumbered
        self.test_data_generator.put_default_privilege_record_in_provider_table(
            value_overrides={
                'licenseJurisdiction': DEFAULT_LICENSE_JURISDICTION,
                'licenseTypeAbbreviation': DEFAULT_LICENSE_TYPE_ABBREVIATION,
                'encumberedStatus': 'encumbered',
            }
        )

        message = self._generate_license_encumbrance_message()
        event = self._create_sqs_event(message)

        # Execute the handler
        license_encumbrance_listener(event, self.mock_context)

        # Verify privilege status remains unchanged
        provider_records = self.config.data_client.get_provider_user_records(
            compact=DEFAULT_COMPACT,
            provider_id=DEFAULT_PROVIDER_ID,
        )

        privileges = provider_records.get_privilege_records()
        self.assertEqual(1, len(privileges))
        self.assertEqual(PrivilegeEncumberedStatusEnum.ENCUMBERED, privileges[0].encumberedStatus)

        # Verify no privilege encumbrance events were published since no privileges were affected
        mock_publish_event.assert_not_called()

    def test_license_encumbrance_listener_creates_privilege_update_records(self):
        """Test that license encumbrance event creates appropriate privilege update records."""
        from handlers.encumbrance_events import license_encumbrance_listener

        # Set up test data
        self.test_data_generator.put_default_provider_record_in_provider_table()
        privilege = self.test_data_generator.put_default_privilege_record_in_provider_table()

        message = self._generate_license_encumbrance_message()
        event = self._create_sqs_event(message)

        # Execute the handler
        license_encumbrance_listener(event, self.mock_context)

        # Verify privilege update record was created
        serialized_privilege = privilege.serialize_to_database_record()
        privilege_update_records = self._provider_table.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('pk').eq(serialized_privilege['pk'])
            & Key('sk').begins_with(f'{serialized_privilege["sk"]}UPDATE'),
        )

        self.assertEqual(1, len(privilege_update_records['Items']))
        update_record = privilege_update_records['Items'][0]
        self.assertEqual('encumbrance', update_record['updateType'])
        self.assertEqual({'encumberedStatus': 'licenseEncumbered'}, update_record['updatedValues'])

    @patch('cc_common.event_bus_client.EventBusClient._publish_event')
    def test_license_encumbrance_lifted_listener_unencumbers_license_encumbered_privileges_successfully(
        self, mock_publish_event
    ):
        """Test that license encumbrance lifting event successfully unencumbers LICENSE_ENCUMBERED privileges."""
        from cc_common.data_model.schema.common import PrivilegeEncumberedStatusEnum
        from handlers.encumbrance_events import license_encumbrance_lifted_listener

        # Set up test data
        self.test_data_generator.put_default_provider_record_in_provider_table()

        # Set up license record that is unencumbered (so privileges should be unencumbered)
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'jurisdiction': DEFAULT_LICENSE_JURISDICTION,
                'licenseType': DEFAULT_LICENSE_TYPE,
                'encumberedStatus': 'unencumbered',  # License is unencumbered
            }
        )

        # Privilege with encumbrance status as result of license encumbrance
        self.test_data_generator.put_default_privilege_record_in_provider_table(
            value_overrides={
                'licenseJurisdiction': DEFAULT_LICENSE_JURISDICTION,
                'licenseTypeAbbreviation': DEFAULT_LICENSE_TYPE_ABBREVIATION,
                'encumberedStatus': 'licenseEncumbered',  # Should be unencumbered
                'jurisdiction': DEFAULT_PRIVILEGE_JURISDICTION,
            }
        )

        # Privilege encumbered due to its own adverse action (should NOT be unencumbered)
        self.test_data_generator.put_default_privilege_record_in_provider_table(
            value_overrides={
                'licenseJurisdiction': DEFAULT_LICENSE_JURISDICTION,
                'licenseTypeAbbreviation': DEFAULT_LICENSE_TYPE_ABBREVIATION,
                'encumberedStatus': 'encumbered',  # Should remain encumbered
                'jurisdiction': 'ky',  # Different jurisdiction to distinguish
            }
        )

        message = self._generate_license_encumbrance_lifting_message()
        event = self._create_sqs_event(message)

        # Execute the handler
        license_encumbrance_lifted_listener(event, self.mock_context)

        # Verify results
        provider_records = self.config.data_client.get_provider_user_records(
            compact=DEFAULT_COMPACT,
            provider_id=DEFAULT_PROVIDER_ID,
        )

        privileges = provider_records.get_privilege_records()

        # Find the privileges by jurisdiction
        privilege_with_previous_license_encumbered_status = next(
            p for p in privileges if p.jurisdiction == DEFAULT_PRIVILEGE_JURISDICTION
        )
        privilege_with_previous_encumbered_status = next(p for p in privileges if p.jurisdiction == 'ky')

        # Verify the LICENSE_ENCUMBERED privilege is now unencumbered
        self.assertEqual(
            PrivilegeEncumberedStatusEnum.UNENCUMBERED,
            privilege_with_previous_license_encumbered_status.encumberedStatus,
        )

        # Verify the self-encumbered privilege remains encumbered
        self.assertEqual(
            PrivilegeEncumberedStatusEnum.ENCUMBERED, privilege_with_previous_encumbered_status.encumberedStatus
        )

        # Verify that a privilege encumbrance lifting event was published for the affected privilege
        mock_publish_event.assert_called_once()
        call_args = mock_publish_event.call_args[1]

        # Extract and verify event_batch_writer separately
        called_event_batch_writer = call_args.pop('event_batch_writer')
        from cc_common.event_batch_writer import EventBatchWriter

        self.assertIsInstance(called_event_batch_writer, EventBatchWriter)

        # Now verify the rest with comprehensive assertion
        self.assertEqual(
            {
                'source': 'org.compactconnect.data-events',
                'detail_type': 'privilege.encumbranceLifted',
                'detail': {
                    'compact': DEFAULT_COMPACT,
                    'providerId': DEFAULT_PROVIDER_ID,
                    'jurisdiction': DEFAULT_PRIVILEGE_JURISDICTION,  # The privilege jurisdiction
                    'licenseTypeAbbreviation': DEFAULT_LICENSE_TYPE_ABBREVIATION,
                    'effectiveDate': DEFAULT_EFFECTIVE_DATE,
                    'eventTime': DEFAULT_DATE_OF_UPDATE_TIMESTAMP,
                },
            },
            call_args,
        )

    def test_license_encumbrance_lifted_listener_handles_no_license_encumbered_privileges(self):
        """Test that license encumbrance lifting event handles case where no LICENSE_ENCUMBERED privileges exist."""
        from cc_common.data_model.schema.common import PrivilegeEncumberedStatusEnum
        from handlers.encumbrance_events import license_encumbrance_lifted_listener

        # Set up test data with no LICENSE_ENCUMBERED privileges
        self.test_data_generator.put_default_provider_record_in_provider_table()

        # Create privilege with different encumbrance status
        self.test_data_generator.put_default_privilege_record_in_provider_table(
            value_overrides={
                'licenseJurisdiction': DEFAULT_LICENSE_JURISDICTION,
                'licenseTypeAbbreviation': DEFAULT_LICENSE_TYPE_ABBREVIATION,
                'encumberedStatus': 'encumbered',  # Not LICENSE_ENCUMBERED
            }
        )

        message = self._generate_license_encumbrance_lifting_message()
        event = self._create_sqs_event(message)

        # Execute the handler - should not raise any exceptions
        license_encumbrance_lifted_listener(event, self.mock_context)

        # Verify no privileges were modified
        provider_records = self.config.data_client.get_provider_user_records(
            compact=DEFAULT_COMPACT,
            provider_id=DEFAULT_PROVIDER_ID,
        )

        privileges = provider_records.get_privilege_records()
        self.assertEqual(1, len(privileges))
        self.assertEqual(PrivilegeEncumberedStatusEnum.ENCUMBERED, privileges[0].encumberedStatus)

    def test_license_encumbrance_lifted_listener_creates_privilege_update_records(self):
        """Test that license encumbrance lifting event creates appropriate privilege update records."""
        from handlers.encumbrance_events import license_encumbrance_lifted_listener

        # Set up test data
        self.test_data_generator.put_default_provider_record_in_provider_table()

        # Set up license record that is unencumbered (so privileges should be unencumbered)
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'jurisdiction': DEFAULT_LICENSE_JURISDICTION,
                'licenseType': DEFAULT_LICENSE_TYPE,
                'encumberedStatus': 'unencumbered',  # License is unencumbered
            }
        )

        privilege = self.test_data_generator.put_default_privilege_record_in_provider_table(
            value_overrides={
                'licenseJurisdiction': DEFAULT_LICENSE_JURISDICTION,
                'licenseTypeAbbreviation': DEFAULT_LICENSE_TYPE_ABBREVIATION,
                'encumberedStatus': 'licenseEncumbered',
            }
        )

        message = self._generate_license_encumbrance_lifting_message()
        event = self._create_sqs_event(message)

        # Execute the handler
        license_encumbrance_lifted_listener(event, self.mock_context)

        # Verify privilege update record was created
        privilege_update_records = self._provider_table.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('pk').eq(privilege.serialize_to_database_record()['pk'])
            & Key('sk').begins_with(f'{privilege.compact}#PROVIDER#privilege/{privilege.jurisdiction}/slp#UPDATE'),
        )

        self.assertEqual(1, len(privilege_update_records['Items']))
        update_record = privilege_update_records['Items'][0]
        self.assertEqual('lifting_encumbrance', update_record['updateType'])
        self.assertEqual({'encumberedStatus': 'unencumbered'}, update_record['updatedValues'])

    @patch('cc_common.event_bus_client.EventBusClient._publish_event')
    def test_license_encumbrance_listener_handles_multiple_matching_privileges(self, mock_publish_event):
        """Test that license encumbrance event handles multiple matching privileges correctly."""
        from cc_common.data_model.schema.common import PrivilegeEncumberedStatusEnum
        from handlers.encumbrance_events import license_encumbrance_listener

        # Set up test data
        self.test_data_generator.put_default_provider_record_in_provider_table()

        # Create multiple privileges with same license jurisdiction and type
        self.test_data_generator.put_default_privilege_record_in_provider_table(
            value_overrides={
                'licenseJurisdiction': DEFAULT_LICENSE_JURISDICTION,
                'licenseType': DEFAULT_LICENSE_TYPE,
                'jurisdiction': 'ne',
            }
        )

        self.test_data_generator.put_default_privilege_record_in_provider_table(
            value_overrides={
                'licenseJurisdiction': DEFAULT_LICENSE_JURISDICTION,
                'licenseType': DEFAULT_LICENSE_TYPE,
                'jurisdiction': 'ky',
            }
        )

        message = self._generate_license_encumbrance_message()
        event = self._create_sqs_event(message)

        # Execute the handler
        license_encumbrance_listener(event, self.mock_context)

        # Verify both privileges were encumbered
        provider_records = self.config.data_client.get_provider_user_records(
            compact=DEFAULT_COMPACT,
            provider_id=DEFAULT_PROVIDER_ID,
        )

        privileges = provider_records.get_privilege_records()
        self.assertEqual(2, len(privileges))

        for privilege in privileges:
            self.assertEqual(PrivilegeEncumberedStatusEnum.LICENSE_ENCUMBERED, privilege.encumberedStatus)

        # Verify that privilege encumbrance events were published for both affected privileges
        self.assertEqual(2, mock_publish_event.call_count)

        # Extract the call arguments for verification
        call_args_list = [call[1] for call in mock_publish_event.call_args_list]
        published_jurisdictions = {call_args['detail']['jurisdiction'] for call_args in call_args_list}

        # Verify events were published for both privilege jurisdictions
        self.assertEqual({'ne', 'ky'}, published_jurisdictions)

        # Verify the structure of each published event
        for call_args in call_args_list:
            # Extract and verify event_batch_writer separately
            called_event_batch_writer = call_args.pop('event_batch_writer')
            from cc_common.event_batch_writer import EventBatchWriter

            self.assertIsInstance(called_event_batch_writer, EventBatchWriter)

            # Now verify the rest with comprehensive assertion
            expected_call_args = {
                'source': 'org.compactconnect.data-events',
                'detail_type': 'privilege.encumbrance',
                'detail': {
                    'compact': DEFAULT_COMPACT,
                    'providerId': DEFAULT_PROVIDER_ID,
                    'jurisdiction': call_args['detail']['jurisdiction'],  # Will be either 'ne' or 'ky'
                    'licenseTypeAbbreviation': DEFAULT_LICENSE_TYPE_ABBREVIATION,
                    'effectiveDate': DEFAULT_EFFECTIVE_DATE,
                    'eventTime': DEFAULT_DATE_OF_UPDATE_TIMESTAMP,
                },
            }
            self.assertEqual(expected_call_args, call_args)

    def test_license_encumbrance_lifted_listener_handles_multiple_license_encumbered_privileges(self):
        """Test that license encumbrance lifting event handles multiple LICENSE_ENCUMBERED privileges correctly."""
        from cc_common.data_model.schema.common import PrivilegeEncumberedStatusEnum
        from handlers.encumbrance_events import license_encumbrance_lifted_listener

        # Set up test data
        self.test_data_generator.put_default_provider_record_in_provider_table()

        # Set up license record that is unencumbered (so privileges should be unencumbered)
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'jurisdiction': DEFAULT_LICENSE_JURISDICTION,
                'licenseType': DEFAULT_LICENSE_TYPE,
                'encumberedStatus': 'unencumbered',  # License is unencumbered
            }
        )

        # Create multiple LICENSE_ENCUMBERED privileges
        self.test_data_generator.put_default_privilege_record_in_provider_table(
            value_overrides={
                'licenseJurisdiction': DEFAULT_LICENSE_JURISDICTION,
                'licenseType': DEFAULT_LICENSE_TYPE,
                'encumberedStatus': 'licenseEncumbered',
                'jurisdiction': 'ne',
            }
        )

        self.test_data_generator.put_default_privilege_record_in_provider_table(
            value_overrides={
                'licenseJurisdiction': DEFAULT_LICENSE_JURISDICTION,
                'licenseType': DEFAULT_LICENSE_TYPE,
                'encumberedStatus': 'licenseEncumbered',
                'jurisdiction': 'ky',
            }
        )

        message = self._generate_license_encumbrance_lifting_message()
        event = self._create_sqs_event(message)

        # Execute the handler
        license_encumbrance_lifted_listener(event, self.mock_context)

        # Verify both privileges were unencumbered
        provider_records = self.config.data_client.get_provider_user_records(
            compact=DEFAULT_COMPACT,
            provider_id=DEFAULT_PROVIDER_ID,
        )

        privileges = provider_records.get_privilege_records()
        self.assertEqual(2, len(privileges))

        for privilege in privileges:
            self.assertEqual(PrivilegeEncumberedStatusEnum.UNENCUMBERED, privilege.encumberedStatus)

    def test_license_encumbrance_listener_handles_mixed_license_types(self):
        """Test that license encumbrance event only affects privileges with matching license type."""
        from cc_common.data_model.schema.common import PrivilegeEncumberedStatusEnum
        from handlers.encumbrance_events import license_encumbrance_listener

        # Set up test data
        self.test_data_generator.put_default_provider_record_in_provider_table()

        # Create privilege with matching license type
        self.test_data_generator.put_default_privilege_record_in_provider_table(
            value_overrides={
                'licenseJurisdiction': DEFAULT_LICENSE_JURISDICTION,
                'licenseType': DEFAULT_LICENSE_TYPE,
                'jurisdiction': 'ne',
            }
        )

        # Create privilege with different license type
        self.test_data_generator.put_default_privilege_record_in_provider_table(
            value_overrides={
                'licenseJurisdiction': DEFAULT_LICENSE_JURISDICTION,
                'licenseType': 'audiologist',  # Different license type
                'jurisdiction': 'ky',
            }
        )

        message = self._generate_license_encumbrance_message()
        event = self._create_sqs_event(message)

        # Execute the handler
        license_encumbrance_listener(event, self.mock_context)

        # Verify only the matching privilege was encumbered
        provider_records = self.config.data_client.get_provider_user_records(
            compact=DEFAULT_COMPACT,
            provider_id=DEFAULT_PROVIDER_ID,
        )

        privileges = provider_records.get_privilege_records()

        matching_privilege_after = next(p for p in privileges if p.jurisdiction == 'ne')
        different_type_privilege_after = next(p for p in privileges if p.jurisdiction == 'ky')

        self.assertEqual(PrivilegeEncumberedStatusEnum.LICENSE_ENCUMBERED, matching_privilege_after.encumberedStatus)
        self.assertIsNone(
            different_type_privilege_after.encumberedStatus,
            f'licenseEncumbered is not None: {different_type_privilege_after.encumberedStatus}',
        )

    def test_license_encumbrance_listener_handles_mixed_license_jurisdictions(self):
        """Test that license encumbrance event only affects privileges with matching license jurisdiction."""
        from cc_common.data_model.schema.common import PrivilegeEncumberedStatusEnum
        from handlers.encumbrance_events import license_encumbrance_listener

        # Set up test data
        self.test_data_generator.put_default_provider_record_in_provider_table()

        # Create privilege with matching license jurisdiction
        self.test_data_generator.put_default_privilege_record_in_provider_table(
            value_overrides={
                'licenseJurisdiction': DEFAULT_LICENSE_JURISDICTION,
                'licenseTypeAbbreviation': DEFAULT_LICENSE_TYPE_ABBREVIATION,
                'jurisdiction': 'ne',
            }
        )

        # Create privilege with different license jurisdiction
        self.test_data_generator.put_default_privilege_record_in_provider_table(
            value_overrides={
                'licenseJurisdiction': 'ky',  # Different license jurisdiction
                'licenseTypeAbbreviation': DEFAULT_LICENSE_TYPE_ABBREVIATION,
                'jurisdiction': 'tx',
            }
        )

        message = self._generate_license_encumbrance_message()
        event = self._create_sqs_event(message)

        # Execute the handler
        license_encumbrance_listener(event, self.mock_context)

        # Verify only the matching privilege was encumbered
        provider_records = self.config.data_client.get_provider_user_records(
            compact=DEFAULT_COMPACT,
            provider_id=DEFAULT_PROVIDER_ID,
        )

        privileges = provider_records.get_privilege_records()

        matching_privilege = next(p for p in privileges if p.jurisdiction == 'ne')
        different_jurisdiction_privilege = next(p for p in privileges if p.jurisdiction == 'tx')

        self.assertEqual(PrivilegeEncumberedStatusEnum.LICENSE_ENCUMBERED, matching_privilege.encumberedStatus)
        self.assertIsNone(different_jurisdiction_privilege.encumberedStatus)

    def test_license_encumbrance_lifted_listener_handles_mixed_license_jurisdictions(self):
        """Test that license encumbrance lifting event only affects privileges with matching license jurisdiction."""
        from cc_common.data_model.schema.common import PrivilegeEncumberedStatusEnum
        from handlers.encumbrance_events import license_encumbrance_lifted_listener

        # Set up test data
        self.test_data_generator.put_default_provider_record_in_provider_table()

        # Set up license record that is unencumbered (so privileges should be unencumbered)
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'jurisdiction': DEFAULT_LICENSE_JURISDICTION,
                'licenseType': DEFAULT_LICENSE_TYPE,
                'encumberedStatus': 'unencumbered',  # License is unencumbered
            }
        )

        # Create privilege with matching license jurisdiction (should be unencumbered)
        self.test_data_generator.put_default_privilege_record_in_provider_table(
            value_overrides={
                'licenseJurisdiction': DEFAULT_LICENSE_JURISDICTION,
                'licenseType': DEFAULT_LICENSE_TYPE,
                'encumberedStatus': 'licenseEncumbered',
                'jurisdiction': 'ne',
            }
        )

        # Create privilege with different license jurisdiction (should remain encumbered)
        self.test_data_generator.put_default_privilege_record_in_provider_table(
            value_overrides={
                'licenseJurisdiction': 'ky',  # Different license jurisdiction
                'licenseType': DEFAULT_LICENSE_TYPE,
                'encumberedStatus': 'licenseEncumbered',
                'jurisdiction': 'tx',
            }
        )

        message = self._generate_license_encumbrance_lifting_message()
        event = self._create_sqs_event(message)

        # Execute the handler
        license_encumbrance_lifted_listener(event, self.mock_context)

        # Verify only the matching privilege was unencumbered
        provider_records = self.config.data_client.get_provider_user_records(
            compact=DEFAULT_COMPACT,
            provider_id=DEFAULT_PROVIDER_ID,
        )

        privileges = provider_records.get_privilege_records()

        matching_privilege_after = next(p for p in privileges if p.jurisdiction == 'ne')
        different_jurisdiction_privilege_after = next(p for p in privileges if p.jurisdiction == 'tx')

        # Matching privilege should be unencumbered
        self.assertEqual(PrivilegeEncumberedStatusEnum.UNENCUMBERED, matching_privilege_after.encumberedStatus)
        # Different jurisdiction privilege should remain license encumbered
        self.assertEqual(
            PrivilegeEncumberedStatusEnum.LICENSE_ENCUMBERED, different_jurisdiction_privilege_after.encumberedStatus
        )

    def test_license_encumbrance_lifted_listener_handles_mixed_license_types(self):
        """Test that license encumbrance lifting event only affects privileges with matching license type."""
        from cc_common.data_model.schema.common import PrivilegeEncumberedStatusEnum
        from handlers.encumbrance_events import license_encumbrance_lifted_listener

        # Set up test data
        self.test_data_generator.put_default_provider_record_in_provider_table()

        # Set up license record that is unencumbered (so privileges should be unencumbered)
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'jurisdiction': DEFAULT_LICENSE_JURISDICTION,
                'licenseType': DEFAULT_LICENSE_TYPE,
                'encumberedStatus': 'unencumbered',  # License is unencumbered
            }
        )

        # Create privilege with matching license type (should be unencumbered)
        self.test_data_generator.put_default_privilege_record_in_provider_table(
            value_overrides={
                'licenseJurisdiction': DEFAULT_LICENSE_JURISDICTION,
                'licenseType': DEFAULT_LICENSE_TYPE,
                'encumberedStatus': 'licenseEncumbered',
                'jurisdiction': 'ne',
            }
        )

        # Create privilege with different license type (should remain encumbered)
        self.test_data_generator.put_default_privilege_record_in_provider_table(
            value_overrides={
                'licenseJurisdiction': DEFAULT_LICENSE_JURISDICTION,
                'licenseType': 'audiologist',  # Different license type
                'encumberedStatus': 'licenseEncumbered',
                'jurisdiction': 'ky',
            }
        )

        message = self._generate_license_encumbrance_lifting_message()
        event = self._create_sqs_event(message)

        # Execute the handler
        license_encumbrance_lifted_listener(event, self.mock_context)

        # Verify only the matching privilege was unencumbered
        provider_records = self.config.data_client.get_provider_user_records(
            compact=DEFAULT_COMPACT,
            provider_id=DEFAULT_PROVIDER_ID,
        )

        privileges = provider_records.get_privilege_records()

        matching_privilege_after = next(p for p in privileges if p.jurisdiction == 'ne')
        different_type_privilege_after = next(p for p in privileges if p.jurisdiction == 'ky')

        # Matching privilege should be unencumbered
        self.assertEqual(PrivilegeEncumberedStatusEnum.UNENCUMBERED, matching_privilege_after.encumberedStatus)
        # Different license type privilege should remain license encumbered
        self.assertEqual(
            PrivilegeEncumberedStatusEnum.LICENSE_ENCUMBERED, different_type_privilege_after.encumberedStatus
        )

    def test_license_encumbrance_lifted_listener_does_not_unencumber_when_license_remains_encumbered(self):
        """Test that privileges are NOT unencumbered when the license itself remains encumbered."""
        from cc_common.data_model.schema.common import PrivilegeEncumberedStatusEnum
        from handlers.encumbrance_events import license_encumbrance_lifted_listener

        # Set up test data
        self.test_data_generator.put_default_provider_record_in_provider_table()

        # Set up license record that is STILL encumbered (has multiple encumbrances)
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'jurisdiction': DEFAULT_LICENSE_JURISDICTION,
                'licenseType': DEFAULT_LICENSE_TYPE,
                'encumberedStatus': 'encumbered',  # License is still encumbered
            }
        )

        # Create privileges that should NOT be unencumbered
        self.test_data_generator.put_default_privilege_record_in_provider_table(
            value_overrides={
                'licenseJurisdiction': DEFAULT_LICENSE_JURISDICTION,
                'licenseType': DEFAULT_LICENSE_TYPE,
                'encumberedStatus': 'licenseEncumbered',
                'jurisdiction': 'ne',
            }
        )

        self.test_data_generator.put_default_privilege_record_in_provider_table(
            value_overrides={
                'licenseJurisdiction': DEFAULT_LICENSE_JURISDICTION,
                'licenseType': DEFAULT_LICENSE_TYPE,
                'encumberedStatus': 'licenseEncumbered',
                'jurisdiction': 'ky',
            }
        )

        message = self._generate_license_encumbrance_lifting_message()
        event = self._create_sqs_event(message)

        # Execute the handler
        license_encumbrance_lifted_listener(event, self.mock_context)

        # Verify privileges remain license encumbered (NOT unencumbered)
        provider_records = self.config.data_client.get_provider_user_records(
            compact=DEFAULT_COMPACT,
            provider_id=DEFAULT_PROVIDER_ID,
        )

        privileges = provider_records.get_privilege_records()

        for privilege in privileges:
            if (
                privilege.licenseJurisdiction == DEFAULT_LICENSE_JURISDICTION
                and privilege.licenseType == DEFAULT_LICENSE_TYPE
            ):
                # All matching privileges should remain LICENSE_ENCUMBERED
                self.assertEqual(PrivilegeEncumberedStatusEnum.LICENSE_ENCUMBERED, privilege.encumberedStatus)

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
    @patch('cc_common.email_service_client.EmailServiceClient.send_privilege_encumbrance_provider_notification_email')
    def test_privilege_encumbrance_listener_processes_event_with_registered_provider(
        self, mock_provider_email, mock_state_email
    ):
        """Test that privilege encumbrance listener processes events for registered providers."""
        from cc_common.email_service_client import EncumbranceNotificationTemplateVariables
        from handlers.encumbrance_events import privilege_encumbrance_notification_listener

        # Set up test data with registered provider
        self.test_data_generator.put_default_provider_record_in_provider_table(
            value_overrides={'compactConnectRegisteredEmailAddress': 'provider@example.com'}
        )

        # Add the privilege that is being encumbered (in DEFAULT_PRIVILEGE_JURISDICTION = 'ne')
        self.test_data_generator.put_default_privilege_record_in_provider_table()

        # Create additional licenses and privileges for notification testing
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'jurisdiction': 'co',
                'jurisdictionUploadedLicenseStatus': 'active',
            }
        )
        self.test_data_generator.put_default_privilege_record_in_provider_table(
            value_overrides={
                'jurisdiction': 'ky',
                'administratorSetStatus': 'active',
            }
        )

        message = self._generate_privilege_encumbrance_message()
        event = self._create_sqs_event(message)

        # Execute the handler
        result = privilege_encumbrance_notification_listener(event, self.mock_context)

        # Should succeed with no batch failures
        self.assertEqual({'batchItemFailures': []}, result)

        # Verify provider notification
        mock_provider_email.assert_called_once_with(
            compact=DEFAULT_COMPACT,
            provider_email='provider@example.com',
            template_variables=EncumbranceNotificationTemplateVariables(
                provider_first_name='Björk',
                provider_last_name='Guðmundsdóttir',
                encumbered_jurisdiction='ne',
                license_type='speech-language pathologist',
                effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                provider_id=None,
            ),
        )

        # Verify state notifications (encumbered state + other states with active licenses/privileges)
        expected_template_variables_ne = EncumbranceNotificationTemplateVariables(
            provider_first_name='Björk',
            provider_last_name='Guðmundsdóttir',
            encumbered_jurisdiction='ne',
            license_type='speech-language pathologist',
            effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
            provider_id=UUID(DEFAULT_PROVIDER_ID),
        )
        expected_template_variables_co = EncumbranceNotificationTemplateVariables(
            provider_first_name='Björk',
            provider_last_name='Guðmundsdóttir',
            encumbered_jurisdiction='ne',
            license_type='speech-language pathologist',
            effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
            provider_id=UUID(DEFAULT_PROVIDER_ID),
        )
        expected_template_variables_ky = EncumbranceNotificationTemplateVariables(
            provider_first_name='Björk',
            provider_last_name='Guðmundsdóttir',
            encumbered_jurisdiction='ne',
            license_type='speech-language pathologist',
            effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
            provider_id=UUID(DEFAULT_PROVIDER_ID),
        )
        expected_state_calls = [
            # State 'ne' (encumbered jurisdiction)
            {
                'compact': DEFAULT_COMPACT,
                'jurisdiction': 'ne',
                'template_variables': expected_template_variables_ne,
            },
            # State 'co' (active license jurisdiction)
            {
                'compact': DEFAULT_COMPACT,
                'jurisdiction': 'co',
                'template_variables': expected_template_variables_co,
            },
            # State 'ky' (active privilege jurisdiction)
            {
                'compact': DEFAULT_COMPACT,
                'jurisdiction': 'ky',
                'template_variables': expected_template_variables_ky,
            },
        ]

        # Verify all state notifications were sent
        self.assertEqual(3, mock_state_email.call_count)
        actual_state_calls = [call.kwargs for call in mock_state_email.call_args_list]

        # Sort both lists for comparison
        expected_state_calls_sorted = sorted(expected_state_calls, key=lambda x: x['jurisdiction'])
        actual_state_calls_sorted = sorted(actual_state_calls, key=lambda x: x['jurisdiction'])

        self.assertEqual(expected_state_calls_sorted, actual_state_calls_sorted)

    @patch('cc_common.email_service_client.EmailServiceClient.send_privilege_encumbrance_state_notification_email')
    @patch('cc_common.email_service_client.EmailServiceClient.send_privilege_encumbrance_provider_notification_email')
    def test_privilege_encumbrance_listener_processes_event_with_unregistered_provider(
        self, mock_provider_email, mock_state_email
    ):
        """
        Test that privilege encumbrance listener handles unregistered providers.

        Note: An unregistered provider holding a privilege should not be possible in our system.
        This test is just stressing the limits of our encumbrance logic, to make sure it handles it gracefully.
        """
        from cc_common.email_service_client import EncumbranceNotificationTemplateVariables
        from handlers.encumbrance_events import privilege_encumbrance_notification_listener

        # Set up test data with unregistered provider (no email)
        self.test_data_generator.put_default_provider_record_in_provider_table(is_registered=False)

        # Add the privilege that is being encumbered (in DEFAULT_PRIVILEGE_JURISDICTION = 'ne')
        self.test_data_generator.put_default_privilege_record_in_provider_table()

        # Create additional active records for state notifications
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'jurisdiction': 'co',
                'jurisdictionUploadedLicenseStatus': 'active',
            }
        )

        message = self._generate_privilege_encumbrance_message()
        event = self._create_sqs_event(message)

        # Execute the handler
        result = privilege_encumbrance_notification_listener(event, self.mock_context)

        # Should succeed with no batch failures
        self.assertEqual({'batchItemFailures': []}, result)

        # Verify no provider notification is sent (provider not registered)
        mock_provider_email.assert_not_called()

        # Verify state notifications were sent
        self.assertEqual(2, mock_state_email.call_count)

        # Check each call individually since they have different provider_id values
        calls = mock_state_email.call_args_list
        call_jurisdictions = [call.kwargs['jurisdiction'] for call in calls]
        self.assertEqual(sorted(call_jurisdictions), ['co', 'ne'])

        # Verify all calls have the correct template_variables structure
        for call in calls:
            self.assertEqual(call.kwargs['compact'], DEFAULT_COMPACT)
            self.assertEqual(
                call.kwargs['template_variables'],
                EncumbranceNotificationTemplateVariables(
                    provider_first_name='Björk',
                    provider_last_name='Guðmundsdóttir',
                    encumbered_jurisdiction='ne',
                    license_type='speech-language pathologist',
                    effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                    provider_id=UUID(DEFAULT_PROVIDER_ID),
                ),
            )

    @patch('cc_common.email_service_client.EmailServiceClient.send_privilege_encumbrance_state_notification_email')
    @patch('cc_common.email_service_client.EmailServiceClient.send_privilege_encumbrance_provider_notification_email')
    def test_privilege_encumbrance_listener_identifies_notification_jurisdictions(
        self, mock_provider_email, mock_state_email
    ):
        """Test that privilege encumbrance listener correctly identifies states to notify."""
        from cc_common.email_service_client import EncumbranceNotificationTemplateVariables
        from handlers.encumbrance_events import privilege_encumbrance_notification_listener

        # Set up test data
        self.test_data_generator.put_default_provider_record_in_provider_table(
            value_overrides={'compactConnectRegisteredEmailAddress': 'provider@example.com'}
        )

        # Add the privilege that is being encumbered (in DEFAULT_PRIVILEGE_JURISDICTION = 'ne')
        self.test_data_generator.put_default_privilege_record_in_provider_table()

        # Create active licenses in multiple jurisdictions (excluding the encumbrance jurisdiction 'ne')
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'jurisdiction': 'co',
                'jurisdictionUploadedLicenseStatus': 'active',
            }
        )
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'jurisdiction': 'ky',
                'jurisdictionUploadedLicenseStatus': 'active',
            }
        )

        # Create active privileges in multiple jurisdictions (excluding the encumbrance jurisdiction 'ne')
        self.test_data_generator.put_default_privilege_record_in_provider_table(
            value_overrides={
                'jurisdiction': 'tx',
                'administratorSetStatus': 'active',
            }
        )

        # The encumbrance occurs in DEFAULT_PRIVILEGE_JURISDICTION ('ne')
        message = self._generate_privilege_encumbrance_message()
        event = self._create_sqs_event(message)

        # Execute the handler
        result = privilege_encumbrance_notification_listener(event, self.mock_context)

        # Should succeed with no batch failures
        self.assertEqual({'batchItemFailures': []}, result)

        # Verify provider notification
        mock_provider_email.assert_called_once_with(
            compact=DEFAULT_COMPACT,
            provider_email='provider@example.com',
            template_variables=EncumbranceNotificationTemplateVariables(
                provider_first_name='Björk',
                provider_last_name='Guðmundsdóttir',
                encumbered_jurisdiction='ne',
                license_type='speech-language pathologist',
                effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                provider_id=None,
            ),
        )

        # Verify state notifications were sent to all relevant jurisdictions
        self.assertEqual(4, mock_state_email.call_count)

        # Check each call individually since they have different provider_id values
        calls = mock_state_email.call_args_list
        call_jurisdictions = [call.kwargs['jurisdiction'] for call in calls]
        self.assertEqual(sorted(call_jurisdictions), ['co', 'ky', 'ne', 'tx'])

        # Verify all calls have the correct template_variables structure
        for call in calls:
            self.assertEqual(call.kwargs['compact'], DEFAULT_COMPACT)
            self.assertEqual(
                call.kwargs['template_variables'],
                EncumbranceNotificationTemplateVariables(
                    provider_first_name='Björk',
                    provider_last_name='Guðmundsdóttir',
                    encumbered_jurisdiction='ne',
                    license_type='speech-language pathologist',
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
        expected_failure = {'batchItemFailures': [{'itemIdentifier': '123'}]}
        self.assertEqual(expected_failure, result)

    @patch('cc_common.email_service_client.EmailServiceClient.send_privilege_encumbrance_state_notification_email')
    @patch('cc_common.email_service_client.EmailServiceClient.send_privilege_encumbrance_provider_notification_email')
    def test_privilege_encumbrance_listener_excludes_encumbered_jurisdiction_from_notifications(
        self, mock_provider_email, mock_state_email
    ):
        """Test that the jurisdiction where encumbrance occurred is not duplicated in notifications."""
        from cc_common.email_service_client import EncumbranceNotificationTemplateVariables
        from handlers.encumbrance_events import privilege_encumbrance_notification_listener

        # Set up test data
        self.test_data_generator.put_default_provider_record_in_provider_table(
            value_overrides={'compactConnectRegisteredEmailAddress': 'provider@example.com'}
        )

        # Add the privilege that is being encumbered (in DEFAULT_PRIVILEGE_JURISDICTION = 'ne')
        self.test_data_generator.put_default_privilege_record_in_provider_table()

        # Create license and privilege in different jurisdictions from the encumbrance
        # The encumbrance occurs in 'ne', so create records in other jurisdictions
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'jurisdiction': 'co',  # Different from encumbrance jurisdiction
                'jurisdictionUploadedLicenseStatus': 'active',
            }
        )
        self.test_data_generator.put_default_privilege_record_in_provider_table(
            value_overrides={
                'jurisdiction': 'ky',  # Different from encumbrance jurisdiction
                'administratorSetStatus': 'active',
            }
        )

        # Also create a license in the same jurisdiction as the encumbrance to test exclusion
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'jurisdiction': DEFAULT_PRIVILEGE_JURISDICTION,  # Same as encumbrance jurisdiction ('ne')
                'jurisdictionUploadedLicenseStatus': 'active',
            }
        )

        message = self._generate_privilege_encumbrance_message()
        event = self._create_sqs_event(message)

        # Execute the handler
        result = privilege_encumbrance_notification_listener(event, self.mock_context)

        # Should succeed with no batch failures
        self.assertEqual({'batchItemFailures': []}, result)

        # Verify provider notification
        mock_provider_email.assert_called_once_with(
            compact=DEFAULT_COMPACT,
            provider_email='provider@example.com',
            template_variables=EncumbranceNotificationTemplateVariables(
                provider_first_name='Björk',
                provider_last_name='Guðmundsdóttir',
                encumbered_jurisdiction='ne',
                license_type='speech-language pathologist',
                effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                provider_id=None,
            ),
        )

        # Verify exactly 3 notifications (ne appears only once, not duplicated)
        self.assertEqual(3, mock_state_email.call_count)

        # Check each call individually since they have different provider_id values
        calls = mock_state_email.call_args_list
        call_jurisdictions = [call.kwargs['jurisdiction'] for call in calls]
        self.assertEqual(sorted(call_jurisdictions), ['co', 'ky', 'ne'])

        # Verify all calls have the correct template_variables structure
        for call in calls:
            self.assertEqual(call.kwargs['compact'], DEFAULT_COMPACT)
            self.assertEqual(
                call.kwargs['template_variables'],
                EncumbranceNotificationTemplateVariables(
                    provider_first_name='Björk',
                    provider_last_name='Guðmundsdóttir',
                    encumbered_jurisdiction='ne',
                    license_type='speech-language pathologist',
                    effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                    provider_id=UUID(DEFAULT_PROVIDER_ID),
                ),
            )

    @patch('cc_common.email_service_client.EmailServiceClient.send_privilege_encumbrance_state_notification_email')
    @patch('cc_common.email_service_client.EmailServiceClient.send_privilege_encumbrance_provider_notification_email')
    def test_privilege_encumbrance_listener_notifies_inactive_licenses_and_privileges(
        self, mock_provider_email, mock_state_email
    ):
        """Test that inactive licenses and privileges generate notifications."""
        from cc_common.email_service_client import EncumbranceNotificationTemplateVariables
        from handlers.encumbrance_events import privilege_encumbrance_notification_listener

        # Set up test data
        self.test_data_generator.put_default_provider_record_in_provider_table(
            value_overrides={'compactConnectRegisteredEmailAddress': 'provider@example.com'}
        )

        # Add the privilege that is being encumbered (in DEFAULT_PRIVILEGE_JURISDICTION = 'ne')
        self.test_data_generator.put_default_privilege_record_in_provider_table()

        # Create inactive license (should be notified)
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'jurisdiction': 'co',
                'jurisdictionUploadedLicenseStatus': 'inactive',
            }
        )

        # Create inactive privilege (should be notified)
        self.test_data_generator.put_default_privilege_record_in_provider_table(
            value_overrides={
                'jurisdiction': 'ky',
                'administratorSetStatus': 'inactive',
            }
        )

        # Create active license (should be notified)
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'jurisdiction': 'tx',
                'jurisdictionUploadedLicenseStatus': 'active',
            }
        )

        message = self._generate_privilege_encumbrance_message()
        event = self._create_sqs_event(message)

        # Execute the handler
        result = privilege_encumbrance_notification_listener(event, self.mock_context)

        # Should succeed with no batch failures
        self.assertEqual({'batchItemFailures': []}, result)

        # Verify provider notification
        mock_provider_email.assert_called_once_with(
            compact=DEFAULT_COMPACT,
            provider_email='provider@example.com',
            template_variables=EncumbranceNotificationTemplateVariables(
                provider_first_name='Björk',
                provider_last_name='Guðmundsdóttir',
                encumbered_jurisdiction='ne',
                license_type='speech-language pathologist',
                effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                provider_id=None,
            ),
        )

        # Verify 4 notifications (to inactive 'co', 'ky', and active 'tx', 'ne')
        self.assertEqual(4, mock_state_email.call_count)

        # Check each call individually since they have different provider_id values
        calls = mock_state_email.call_args_list
        call_jurisdictions = [call.kwargs['jurisdiction'] for call in calls]
        self.assertEqual(sorted(call_jurisdictions), ['co', 'ky', 'ne', 'tx'])

        # Verify all calls have the correct template_variables structure
        for call in calls:
            self.assertEqual(call.kwargs['compact'], DEFAULT_COMPACT)
            self.assertEqual(
                call.kwargs['template_variables'],
                EncumbranceNotificationTemplateVariables(
                    provider_first_name='Björk',
                    provider_last_name='Guðmundsdóttir',
                    encumbered_jurisdiction='ne',
                    license_type='speech-language pathologist',
                    effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                    provider_id=UUID(DEFAULT_PROVIDER_ID),
                ),
            )

    @patch(
        'cc_common.email_service_client.EmailServiceClient.send_privilege_encumbrance_lifting_state_notification_email'
    )
    @patch(
        'cc_common.email_service_client.EmailServiceClient.send_privilege_encumbrance_lifting_provider_notification_email'
    )
    def test_privilege_encumbrance_lifting_notification_listener_processes_event_with_registered_provider(
        self, mock_provider_email, mock_state_email
    ):
        """Test that privilege encumbrance lifting listener processes events for registered providers."""
        from cc_common.email_service_client import EncumbranceNotificationTemplateVariables
        from handlers.encumbrance_events import privilege_encumbrance_lifting_notification_listener

        # Set up test data with registered provider
        self.test_data_generator.put_default_provider_record_in_provider_table(
            value_overrides={'compactConnectRegisteredEmailAddress': 'provider@example.com'}
        )

        # Add the privilege where encumbrance is being lifted (in DEFAULT_PRIVILEGE_JURISDICTION = 'ne')
        self.test_data_generator.put_default_privilege_record_in_provider_table()

        # Create additional licenses and privileges for notification testing
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'jurisdiction': 'co',
                'jurisdictionUploadedLicenseStatus': 'active',
            }
        )
        self.test_data_generator.put_default_privilege_record_in_provider_table(
            value_overrides={
                'jurisdiction': 'ky',
                'administratorSetStatus': 'active',
            }
        )

        message = self._generate_privilege_encumbrance_lifting_message()
        event = self._create_sqs_event(message)

        # Execute the handler
        result = privilege_encumbrance_lifting_notification_listener(event, self.mock_context)

        # Should succeed with no batch failures
        self.assertEqual({'batchItemFailures': []}, result)

        # Verify provider notification
        mock_provider_email.assert_called_once_with(
            compact=DEFAULT_COMPACT,
            provider_email='provider@example.com',
            template_variables=EncumbranceNotificationTemplateVariables(
                provider_first_name='Björk',
                provider_last_name='Guðmundsdóttir',
                encumbered_jurisdiction='ne',
                license_type='speech-language pathologist',
                effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                provider_id=None,
            ),
        )

        # Verify state notifications were sent
        self.assertEqual(3, mock_state_email.call_count)

        # Check each call individually since they have different provider_id values
        calls = mock_state_email.call_args_list
        call_jurisdictions = [call.kwargs['jurisdiction'] for call in calls]
        self.assertEqual(sorted(call_jurisdictions), ['co', 'ky', 'ne'])

        # Verify all calls have the correct template_variables structure
        for call in calls:
            self.assertEqual(call.kwargs['compact'], DEFAULT_COMPACT)
            self.assertEqual(
                call.kwargs['template_variables'],
                EncumbranceNotificationTemplateVariables(
                    provider_first_name='Björk',
                    provider_last_name='Guðmundsdóttir',
                    encumbered_jurisdiction='ne',
                    license_type='speech-language pathologist',
                    effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                    provider_id=UUID(DEFAULT_PROVIDER_ID),
                ),
            )

    @patch(
        'cc_common.email_service_client.EmailServiceClient.send_privilege_encumbrance_lifting_state_notification_email'
    )
    @patch(
        'cc_common.email_service_client.EmailServiceClient.send_privilege_encumbrance_lifting_provider_notification_email'
    )
    def test_privilege_encumbrance_lifting_notification_listener_processes_event_with_unregistered_provider(
        self, mock_provider_email, mock_state_email
    ):
        """Test that privilege encumbrance lifting listener handles unregistered providers."""
        from cc_common.email_service_client import EncumbranceNotificationTemplateVariables
        from handlers.encumbrance_events import privilege_encumbrance_lifting_notification_listener

        # Set up test data with unregistered provider (no email)
        self.test_data_generator.put_default_provider_record_in_provider_table(is_registered=False)

        # Add the privilege where encumbrance is being lifted (in DEFAULT_PRIVILEGE_JURISDICTION = 'ne')
        self.test_data_generator.put_default_privilege_record_in_provider_table()

        # Create additional active records for state notifications
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'jurisdiction': 'co',
                'jurisdictionUploadedLicenseStatus': 'active',
            }
        )

        message = self._generate_privilege_encumbrance_lifting_message()
        event = self._create_sqs_event(message)

        # Execute the handler
        result = privilege_encumbrance_lifting_notification_listener(event, self.mock_context)

        # Should succeed with no batch failures
        self.assertEqual({'batchItemFailures': []}, result)

        # Verify no provider notification is sent (provider not registered)
        mock_provider_email.assert_not_called()

        # Verify state notifications were sent
        self.assertEqual(2, mock_state_email.call_count)

        # Check each call individually since they have different provider_id values
        calls = mock_state_email.call_args_list
        call_jurisdictions = [call.kwargs['jurisdiction'] for call in calls]
        self.assertEqual(sorted(call_jurisdictions), ['co', 'ne'])

        # Verify all calls have the correct template_variables structure
        for call in calls:
            self.assertEqual(call.kwargs['compact'], DEFAULT_COMPACT)
            self.assertEqual(
                call.kwargs['template_variables'],
                EncumbranceNotificationTemplateVariables(
                    provider_first_name='Björk',
                    provider_last_name='Guðmundsdóttir',
                    encumbered_jurisdiction='ne',
                    license_type='speech-language pathologist',
                    effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                    provider_id=UUID(DEFAULT_PROVIDER_ID),
                ),
            )

    @patch(
        'cc_common.email_service_client.EmailServiceClient.send_privilege_encumbrance_lifting_state_notification_email'
    )
    @patch(
        'cc_common.email_service_client.EmailServiceClient.send_privilege_encumbrance_lifting_provider_notification_email'
    )
    def test_privilege_encumbrance_lifting_notification_listener_identifies_notification_jurisdictions(
        self, mock_provider_email, mock_state_email
    ):
        """Test that privilege encumbrance lifting listener correctly identifies states to notify."""
        from cc_common.email_service_client import EncumbranceNotificationTemplateVariables
        from handlers.encumbrance_events import privilege_encumbrance_lifting_notification_listener

        # Set up test data
        self.test_data_generator.put_default_provider_record_in_provider_table(
            value_overrides={'compactConnectRegisteredEmailAddress': 'provider@example.com'}
        )

        # Add the privilege where encumbrance is being lifted (in DEFAULT_PRIVILEGE_JURISDICTION = 'ne')
        self.test_data_generator.put_default_privilege_record_in_provider_table()

        # Create active licenses in multiple jurisdictions (excluding the lifting jurisdiction 'ne')
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'jurisdiction': 'co',
                'jurisdictionUploadedLicenseStatus': 'active',
            }
        )
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'jurisdiction': 'ky',
                'jurisdictionUploadedLicenseStatus': 'active',
            }
        )

        # Create active privileges in multiple jurisdictions (excluding the lifting jurisdiction 'ne')
        self.test_data_generator.put_default_privilege_record_in_provider_table(
            value_overrides={
                'jurisdiction': 'tx',
                'administratorSetStatus': 'active',
            }
        )

        # The encumbrance lifting occurs in DEFAULT_PRIVILEGE_JURISDICTION ('ne')
        message = self._generate_privilege_encumbrance_lifting_message()
        event = self._create_sqs_event(message)

        # Execute the handler
        result = privilege_encumbrance_lifting_notification_listener(event, self.mock_context)

        # Should succeed with no batch failures
        self.assertEqual({'batchItemFailures': []}, result)

        # Verify provider notification
        mock_provider_email.assert_called_once_with(
            compact=DEFAULT_COMPACT,
            provider_email='provider@example.com',
            template_variables=EncumbranceNotificationTemplateVariables(
                provider_first_name='Björk',
                provider_last_name='Guðmundsdóttir',
                encumbered_jurisdiction='ne',
                license_type='speech-language pathologist',
                effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                provider_id=None,
            ),
        )

        # Verify state notifications were sent to all relevant jurisdictions
        self.assertEqual(4, mock_state_email.call_count)

        # Check each call individually since they have different provider_id values
        calls = mock_state_email.call_args_list
        call_jurisdictions = [call.kwargs['jurisdiction'] for call in calls]
        self.assertEqual(sorted(call_jurisdictions), ['co', 'ky', 'ne', 'tx'])

        # Verify all calls have the correct template_variables structure
        for call in calls:
            self.assertEqual(call.kwargs['compact'], DEFAULT_COMPACT)
            self.assertEqual(
                call.kwargs['template_variables'],
                EncumbranceNotificationTemplateVariables(
                    provider_first_name='Björk',
                    provider_last_name='Guðmundsdóttir',
                    encumbered_jurisdiction='ne',
                    license_type='speech-language pathologist',
                    effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
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
        expected_failure = {'batchItemFailures': [{'itemIdentifier': '123'}]}
        self.assertEqual(expected_failure, result)

    @patch(
        'cc_common.email_service_client.EmailServiceClient.send_privilege_encumbrance_lifting_state_notification_email'
    )
    @patch(
        'cc_common.email_service_client.EmailServiceClient.send_privilege_encumbrance_lifting_provider_notification_email'
    )
    @patch('cc_common.email_service_client.EmailServiceClient.send_privilege_encumbrance_state_notification_email')
    @patch('cc_common.email_service_client.EmailServiceClient.send_privilege_encumbrance_provider_notification_email')
    def test_privilege_encumbrance_listeners_handle_no_additional_jurisdictions(
        self, mock_priv_enc_provider, mock_priv_enc_state, mock_lift_provider, mock_lift_state
    ):
        """
        Test that privilege encumbrance listeners handle case where provider has no other active licenses/privileges.
        """
        from cc_common.email_service_client import EncumbranceNotificationTemplateVariables
        from handlers.encumbrance_events import (
            privilege_encumbrance_lifting_notification_listener,
            privilege_encumbrance_notification_listener,
        )

        # Set up test data with only provider record
        self.test_data_generator.put_default_provider_record_in_provider_table(
            value_overrides={'compactConnectRegisteredEmailAddress': 'provider@example.com'}
        )

        # Add the privilege that is being encumbered/lifted (in DEFAULT_PRIVILEGE_JURISDICTION = 'ne')
        self.test_data_generator.put_default_privilege_record_in_provider_table()

        # Only create records in the same jurisdiction as the encumbrance (no other jurisdictions)
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'jurisdiction': DEFAULT_PRIVILEGE_JURISDICTION,
                'jurisdictionUploadedLicenseStatus': 'active',
            }
        )

        # Test privilege encumbrance
        message = self._generate_privilege_encumbrance_message()
        event = self._create_sqs_event(message)
        result = privilege_encumbrance_notification_listener(event, self.mock_context)

        # Should succeed with no batch failures
        self.assertEqual({'batchItemFailures': []}, result)

        # Test privilege encumbrance lifting
        message = self._generate_privilege_encumbrance_lifting_message()
        event = self._create_sqs_event(message)
        result = privilege_encumbrance_lifting_notification_listener(event, self.mock_context)

        # Should succeed with no batch failures
        self.assertEqual({'batchItemFailures': []}, result)

        # Verify privilege encumbrance notifications
        mock_priv_enc_provider.assert_called_once_with(
            compact=DEFAULT_COMPACT,
            provider_email='provider@example.com',
            template_variables=EncumbranceNotificationTemplateVariables(
                provider_first_name='Björk',
                provider_last_name='Guðmundsdóttir',
                encumbered_jurisdiction='ne',
                license_type='speech-language pathologist',
                effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                provider_id=None,
            ),
        )

        # Only state 'ne' should be notified (no other jurisdictions)
        mock_priv_enc_state.assert_called_once_with(
            compact=DEFAULT_COMPACT,
            jurisdiction='ne',
            template_variables=EncumbranceNotificationTemplateVariables(
                provider_first_name='Björk',
                provider_last_name='Guðmundsdóttir',
                encumbered_jurisdiction='ne',
                license_type='speech-language pathologist',
                effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                provider_id=UUID(DEFAULT_PROVIDER_ID),
            ),
        )

        # Verify privilege lifting notifications
        mock_lift_provider.assert_called_once_with(
            compact=DEFAULT_COMPACT,
            provider_email='provider@example.com',
            template_variables=EncumbranceNotificationTemplateVariables(
                provider_first_name='Björk',
                provider_last_name='Guðmundsdóttir',
                encumbered_jurisdiction='ne',
                license_type='speech-language pathologist',
                effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                provider_id=None,
            ),
        )

        # Only state 'ne' should be notified (no other jurisdictions)
        mock_lift_state.assert_called_once_with(
            compact=DEFAULT_COMPACT,
            jurisdiction='ne',
            template_variables=EncumbranceNotificationTemplateVariables(
                provider_first_name='Björk',
                provider_last_name='Guðmundsdóttir',
                encumbered_jurisdiction='ne',
                license_type='speech-language pathologist',
                effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                provider_id=UUID(DEFAULT_PROVIDER_ID),
            ),
        )

    @patch('cc_common.email_service_client.EmailServiceClient.send_license_encumbrance_state_notification_email')
    @patch('cc_common.email_service_client.EmailServiceClient.send_license_encumbrance_provider_notification_email')
    def test_license_encumbrance_notification_listener_processes_event_with_registered_provider(
        self, mock_provider_email, mock_state_email
    ):
        """Test that license encumbrance notification listener processes events for registered providers."""
        from cc_common.email_service_client import EncumbranceNotificationTemplateVariables
        from handlers.encumbrance_events import license_encumbrance_notification_listener

        # Set up test data with registered provider
        self.test_data_generator.put_default_provider_record_in_provider_table(
            value_overrides={'compactConnectRegisteredEmailAddress': 'provider@example.com'}
        )

        # Add the license that is being encumbered (in DEFAULT_LICENSE_JURISDICTION = 'oh')
        self.test_data_generator.put_default_license_record_in_provider_table()

        # Create additional licenses and privileges for notification testing
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'jurisdiction': 'ne',
                'jurisdictionUploadedLicenseStatus': 'active',
            }
        )
        self.test_data_generator.put_default_privilege_record_in_provider_table(
            value_overrides={
                'jurisdiction': 'ky',
                'administratorSetStatus': 'active',
            }
        )

        message = self._generate_license_encumbrance_message()
        event = self._create_sqs_event(message)

        # Execute the handler
        result = license_encumbrance_notification_listener(event, self.mock_context)

        # Should succeed with no batch failures
        self.assertEqual({'batchItemFailures': []}, result)

        # Verify provider notification
        mock_provider_email.assert_called_once_with(
            compact=DEFAULT_COMPACT,
            provider_email='provider@example.com',
            template_variables=EncumbranceNotificationTemplateVariables(
                provider_first_name='Björk',
                provider_last_name='Guðmundsdóttir',
                encumbered_jurisdiction='oh',
                license_type='speech-language pathologist',
                effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                provider_id=None,
            ),
        )

        # Verify state notifications were sent
        self.assertEqual(3, mock_state_email.call_count)

        # Check each call individually since they have different provider_id values
        calls = mock_state_email.call_args_list
        call_jurisdictions = [call.kwargs['jurisdiction'] for call in calls]
        self.assertEqual(sorted(call_jurisdictions), ['ky', 'ne', 'oh'])

        # Verify all calls have the correct template_variables structure
        for call in calls:
            self.assertEqual(call.kwargs['compact'], DEFAULT_COMPACT)
            self.assertEqual(
                call.kwargs['template_variables'],
                EncumbranceNotificationTemplateVariables(
                    provider_first_name='Björk',
                    provider_last_name='Guðmundsdóttir',
                    encumbered_jurisdiction='oh',
                    license_type='speech-language pathologist',
                    effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                    provider_id=UUID(DEFAULT_PROVIDER_ID),
                ),
            )

    @patch('cc_common.email_service_client.EmailServiceClient.send_license_encumbrance_state_notification_email')
    @patch('cc_common.email_service_client.EmailServiceClient.send_license_encumbrance_provider_notification_email')
    def test_license_encumbrance_notification_listener_processes_event_with_unregistered_provider(
        self, mock_provider_email, mock_state_email
    ):
        """Test that license encumbrance notification listener handles unregistered providers."""
        from cc_common.email_service_client import EncumbranceNotificationTemplateVariables
        from handlers.encumbrance_events import license_encumbrance_notification_listener

        # Set up test data with unregistered provider (no email)
        self.test_data_generator.put_default_provider_record_in_provider_table(is_registered=False)

        # Add the license that is being encumbered (in DEFAULT_LICENSE_JURISDICTION = 'oh')
        self.test_data_generator.put_default_license_record_in_provider_table()

        # Create additional active records for state notifications
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'jurisdiction': 'ne',
                'jurisdictionUploadedLicenseStatus': 'active',
            }
        )

        message = self._generate_license_encumbrance_message()
        event = self._create_sqs_event(message)

        # Execute the handler
        result = license_encumbrance_notification_listener(event, self.mock_context)

        # Should succeed with no batch failures
        self.assertEqual({'batchItemFailures': []}, result)

        # Verify no provider notification is sent (provider not registered)
        mock_provider_email.assert_not_called()

        # Verify state notifications were sent
        self.assertEqual(2, mock_state_email.call_count)

        # Check each call individually since they have different provider_id values
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
                    license_type='speech-language pathologist',
                    effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                    provider_id=UUID(DEFAULT_PROVIDER_ID),
                ),
            )

    @patch('cc_common.email_service_client.EmailServiceClient.send_license_encumbrance_state_notification_email')
    @patch('cc_common.email_service_client.EmailServiceClient.send_license_encumbrance_provider_notification_email')
    def test_license_encumbrance_notification_listener_identifies_notification_jurisdictions(
        self, mock_provider_email, mock_state_email
    ):
        """Test that license encumbrance notification listener correctly identifies states to notify."""
        from cc_common.email_service_client import EncumbranceNotificationTemplateVariables
        from handlers.encumbrance_events import license_encumbrance_notification_listener

        # Set up test data
        self.test_data_generator.put_default_provider_record_in_provider_table(
            value_overrides={'compactConnectRegisteredEmailAddress': 'provider@example.com'}
        )

        # Add the license that is being encumbered (in DEFAULT_LICENSE_JURISDICTION = 'oh')
        self.test_data_generator.put_default_license_record_in_provider_table()

        # Create active licenses in multiple jurisdictions (excluding the encumbrance jurisdiction 'oh')
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

        # Create active privileges in multiple jurisdictions (excluding the encumbrance jurisdiction 'oh')
        self.test_data_generator.put_default_privilege_record_in_provider_table(
            value_overrides={
                'jurisdiction': 'tx',
                'administratorSetStatus': 'active',
            }
        )

        # The encumbrance occurs in DEFAULT_LICENSE_JURISDICTION ('oh')
        message = self._generate_license_encumbrance_message()
        event = self._create_sqs_event(message)

        # Execute the handler
        result = license_encumbrance_notification_listener(event, self.mock_context)

        # Should succeed with no batch failures
        self.assertEqual({'batchItemFailures': []}, result)

        # Verify provider notification
        mock_provider_email.assert_called_once_with(
            compact=DEFAULT_COMPACT,
            provider_email='provider@example.com',
            template_variables=EncumbranceNotificationTemplateVariables(
                provider_first_name='Björk',
                provider_last_name='Guðmundsdóttir',
                encumbered_jurisdiction='oh',
                license_type='speech-language pathologist',
                effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                provider_id=None,
            ),
        )

        # Verify state notifications were sent to all relevant jurisdictions
        self.assertEqual(4, mock_state_email.call_count)

        # Check each call individually since they have different provider_id values
        calls = mock_state_email.call_args_list
        call_jurisdictions = [call.kwargs['jurisdiction'] for call in calls]
        self.assertEqual(sorted(call_jurisdictions), ['ky', 'ne', 'oh', 'tx'])

        # Verify all calls have the correct template_variables structure
        for call in calls:
            self.assertEqual(call.kwargs['compact'], DEFAULT_COMPACT)
            self.assertEqual(
                call.kwargs['template_variables'],
                EncumbranceNotificationTemplateVariables(
                    provider_first_name='Björk',
                    provider_last_name='Guðmundsdóttir',
                    encumbered_jurisdiction='oh',
                    license_type='speech-language pathologist',
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
        expected_failure = {'batchItemFailures': [{'itemIdentifier': '123'}]}
        self.assertEqual(expected_failure, result)

    @patch('cc_common.email_service_client.EmailServiceClient.send_license_encumbrance_state_notification_email')
    @patch('cc_common.email_service_client.EmailServiceClient.send_license_encumbrance_provider_notification_email')
    def test_license_encumbrance_notification_listener_excludes_encumbered_jurisdiction_from_notifications(
        self, mock_provider_email, mock_state_email
    ):
        """Test that the jurisdiction where license encumbrance occurred is not duplicated in notifications."""
        from cc_common.email_service_client import EncumbranceNotificationTemplateVariables
        from handlers.encumbrance_events import license_encumbrance_notification_listener

        # Set up test data
        self.test_data_generator.put_default_provider_record_in_provider_table(
            value_overrides={'compactConnectRegisteredEmailAddress': 'provider@example.com'}
        )

        # Add the license that is being encumbered (in DEFAULT_LICENSE_JURISDICTION = 'oh')
        self.test_data_generator.put_default_license_record_in_provider_table()

        # Create license and privilege in different jurisdictions from the encumbrance
        # The encumbrance occurs in 'oh', so create records in other jurisdictions
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'jurisdiction': 'ne',  # Different from encumbrance jurisdiction
                'jurisdictionUploadedLicenseStatus': 'active',
            }
        )
        self.test_data_generator.put_default_privilege_record_in_provider_table(
            value_overrides={
                'jurisdiction': 'ky',  # Different from encumbrance jurisdiction
                'administratorSetStatus': 'active',
            }
        )

        # Also create a privilege in the same jurisdiction as the encumbrance to test exclusion
        self.test_data_generator.put_default_privilege_record_in_provider_table(
            value_overrides={
                'jurisdiction': DEFAULT_LICENSE_JURISDICTION,  # Same as encumbrance jurisdiction ('oh')
                'administratorSetStatus': 'active',
            }
        )

        message = self._generate_license_encumbrance_message()
        event = self._create_sqs_event(message)

        # Execute the handler
        result = license_encumbrance_notification_listener(event, self.mock_context)

        # Should succeed with no batch failures
        self.assertEqual({'batchItemFailures': []}, result)

        # Verify provider notification
        mock_provider_email.assert_called_once_with(
            compact=DEFAULT_COMPACT,
            provider_email='provider@example.com',
            template_variables=EncumbranceNotificationTemplateVariables(
                provider_first_name='Björk',
                provider_last_name='Guðmundsdóttir',
                encumbered_jurisdiction='oh',
                license_type='speech-language pathologist',
                effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                provider_id=None,
            ),
        )

        # Verify exactly 3 notifications (oh appears only once, not duplicated)
        self.assertEqual(3, mock_state_email.call_count)

        # Check each call individually since they have different provider_id values
        calls = mock_state_email.call_args_list
        call_jurisdictions = [call.kwargs['jurisdiction'] for call in calls]
        self.assertEqual(sorted(call_jurisdictions), ['ky', 'ne', 'oh'])

        # Verify all calls have the correct template_variables structure
        for call in calls:
            self.assertEqual(call.kwargs['compact'], DEFAULT_COMPACT)
            self.assertEqual(
                call.kwargs['template_variables'],
                EncumbranceNotificationTemplateVariables(
                    provider_first_name='Björk',
                    provider_last_name='Guðmundsdóttir',
                    encumbered_jurisdiction='oh',
                    license_type='speech-language pathologist',
                    effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                    provider_id=UUID(DEFAULT_PROVIDER_ID),
                ),
            )

    @patch('cc_common.email_service_client.EmailServiceClient.send_license_encumbrance_state_notification_email')
    @patch('cc_common.email_service_client.EmailServiceClient.send_license_encumbrance_provider_notification_email')
    def test_license_encumbrance_notification_listener_notifies_all_licenses_and_privileges_including_inactive(
        self, mock_provider_email, mock_state_email
    ):
        """Test that all licenses and privileges generate notifications, including inactive ones."""
        from cc_common.email_service_client import EncumbranceNotificationTemplateVariables
        from handlers.encumbrance_events import license_encumbrance_notification_listener

        # Set up test data
        self.test_data_generator.put_default_provider_record_in_provider_table(
            value_overrides={'compactConnectRegisteredEmailAddress': 'provider@example.com'}
        )

        # Add the license that is being encumbered (in DEFAULT_LICENSE_JURISDICTION = 'oh')
        self.test_data_generator.put_default_license_record_in_provider_table()

        # Create inactive license (should be notified)
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'jurisdiction': 'ne',
                'jurisdictionUploadedLicenseStatus': 'inactive',
            }
        )

        # Create inactive privilege (should be notified)
        self.test_data_generator.put_default_privilege_record_in_provider_table(
            value_overrides={
                'jurisdiction': 'ky',
                'administratorSetStatus': 'inactive',
            }
        )

        # Create active license (should be notified)
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'jurisdiction': 'tx',
                'jurisdictionUploadedLicenseStatus': 'active',
            }
        )

        message = self._generate_license_encumbrance_message()
        event = self._create_sqs_event(message)

        # Execute the handler
        result = license_encumbrance_notification_listener(event, self.mock_context)

        # Should succeed with no batch failures
        self.assertEqual({'batchItemFailures': []}, result)

        # Verify provider notification
        mock_provider_email.assert_called_once_with(
            compact=DEFAULT_COMPACT,
            provider_email='provider@example.com',
            template_variables=EncumbranceNotificationTemplateVariables(
                provider_first_name='Björk',
                provider_last_name='Guðmundsdóttir',
                encumbered_jurisdiction='oh',
                license_type='speech-language pathologist',
                effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                provider_id=None,
            ),
        )

        # Verify 4 notifications (including to inactive 'ne' and 'ky')
        self.assertEqual(4, mock_state_email.call_count)

        # Check each call individually since they have different provider_id values
        calls = mock_state_email.call_args_list
        call_jurisdictions = [call.kwargs['jurisdiction'] for call in calls]
        self.assertEqual(sorted(call_jurisdictions), ['ky', 'ne', 'oh', 'tx'])

        # Verify all calls have the correct template_variables structure
        for call in calls:
            self.assertEqual(call.kwargs['compact'], DEFAULT_COMPACT)
            self.assertEqual(
                call.kwargs['template_variables'],
                EncumbranceNotificationTemplateVariables(
                    provider_first_name='Björk',
                    provider_last_name='Guðmundsdóttir',
                    encumbered_jurisdiction='oh',
                    license_type='speech-language pathologist',
                    effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                    provider_id=UUID(DEFAULT_PROVIDER_ID),
                ),
            )

    @patch(
        'cc_common.email_service_client.EmailServiceClient.send_license_encumbrance_lifting_state_notification_email'
    )
    @patch(
        'cc_common.email_service_client.EmailServiceClient.send_license_encumbrance_lifting_provider_notification_email'
    )
    def test_license_encumbrance_lifting_notification_listener_processes_event_with_registered_provider(
        self, mock_provider_email, mock_state_email
    ):
        """Test that license encumbrance lifting notification listener processes events for registered providers."""
        from cc_common.email_service_client import EncumbranceNotificationTemplateVariables
        from handlers.encumbrance_events import license_encumbrance_lifting_notification_listener

        # Set up test data with registered provider
        self.test_data_generator.put_default_provider_record_in_provider_table(
            value_overrides={'compactConnectRegisteredEmailAddress': 'provider@example.com'}
        )

        # Add the license where encumbrance is being lifted (in DEFAULT_LICENSE_JURISDICTION = 'oh')
        self.test_data_generator.put_default_license_record_in_provider_table()

        # Create additional licenses and privileges for notification testing
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'jurisdiction': 'ne',
                'jurisdictionUploadedLicenseStatus': 'active',
            }
        )
        self.test_data_generator.put_default_privilege_record_in_provider_table(
            value_overrides={
                'jurisdiction': 'ky',
                'administratorSetStatus': 'active',
            }
        )

        message = self._generate_license_encumbrance_lifting_message()
        event = self._create_sqs_event(message)

        # Execute the handler
        result = license_encumbrance_lifting_notification_listener(event, self.mock_context)

        # Should succeed with no batch failures
        self.assertEqual({'batchItemFailures': []}, result)

        # Verify provider notification
        mock_provider_email.assert_called_once_with(
            compact=DEFAULT_COMPACT,
            provider_email='provider@example.com',
            template_variables=EncumbranceNotificationTemplateVariables(
                provider_first_name='Björk',
                provider_last_name='Guðmundsdóttir',
                encumbered_jurisdiction='oh',
                license_type='speech-language pathologist',
                effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                provider_id=None,
            ),
        )

        # Verify state notifications were sent
        self.assertEqual(3, mock_state_email.call_count)

        # Check each call individually since they have different provider_id values
        calls = mock_state_email.call_args_list
        call_jurisdictions = [call.kwargs['jurisdiction'] for call in calls]
        self.assertEqual(sorted(call_jurisdictions), ['ky', 'ne', 'oh'])

        # Verify all calls have the correct template_variables structure
        for call in calls:
            self.assertEqual(call.kwargs['compact'], DEFAULT_COMPACT)
            self.assertEqual(
                call.kwargs['template_variables'],
                EncumbranceNotificationTemplateVariables(
                    provider_first_name='Björk',
                    provider_last_name='Guðmundsdóttir',
                    encumbered_jurisdiction='oh',
                    license_type='speech-language pathologist',
                    effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                    provider_id=UUID(DEFAULT_PROVIDER_ID),
                ),
            )

    @patch(
        'cc_common.email_service_client.EmailServiceClient.send_license_encumbrance_lifting_state_notification_email'
    )
    @patch(
        'cc_common.email_service_client.EmailServiceClient.send_license_encumbrance_lifting_provider_notification_email'
    )
    def test_license_encumbrance_lifting_notification_listener_processes_event_with_unregistered_provider(
        self, mock_provider_email, mock_state_email
    ):
        """Test that license encumbrance lifting notification listener handles unregistered providers."""
        from cc_common.email_service_client import EncumbranceNotificationTemplateVariables
        from handlers.encumbrance_events import license_encumbrance_lifting_notification_listener

        # Set up test data with unregistered provider (no email)
        self.test_data_generator.put_default_provider_record_in_provider_table(is_registered=False)

        # Add the license where encumbrance is being lifted (in DEFAULT_LICENSE_JURISDICTION = 'oh')
        self.test_data_generator.put_default_license_record_in_provider_table()

        # Create additional active records for state notifications
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'jurisdiction': 'ne',
                'jurisdictionUploadedLicenseStatus': 'active',
            }
        )

        message = self._generate_license_encumbrance_lifting_message()
        event = self._create_sqs_event(message)

        # Execute the handler
        result = license_encumbrance_lifting_notification_listener(event, self.mock_context)

        # Should succeed with no batch failures
        self.assertEqual({'batchItemFailures': []}, result)

        # Verify no provider notification is sent (provider not registered)
        mock_provider_email.assert_not_called()

        # Verify state notifications were sent
        self.assertEqual(2, mock_state_email.call_count)

        # Check each call individually since they have different provider_id values
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
                    license_type='speech-language pathologist',
                    effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                    provider_id=UUID(DEFAULT_PROVIDER_ID),
                ),
            )

    @patch(
        'cc_common.email_service_client.EmailServiceClient.send_license_encumbrance_lifting_state_notification_email'
    )
    @patch(
        'cc_common.email_service_client.EmailServiceClient.send_license_encumbrance_lifting_provider_notification_email'
    )
    def test_license_encumbrance_lifting_notification_listener_identifies_notification_jurisdictions(
        self, mock_provider_email, mock_state_email
    ):
        """Test that license encumbrance lifting notification listener correctly identifies states to notify."""
        from cc_common.email_service_client import EncumbranceNotificationTemplateVariables
        from handlers.encumbrance_events import license_encumbrance_lifting_notification_listener

        # Set up test data
        self.test_data_generator.put_default_provider_record_in_provider_table(
            value_overrides={'compactConnectRegisteredEmailAddress': 'provider@example.com'}
        )

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

        # Create active privileges in multiple jurisdictions (excluding the lifting jurisdiction 'oh')
        self.test_data_generator.put_default_privilege_record_in_provider_table(
            value_overrides={
                'jurisdiction': 'tx',
                'administratorSetStatus': 'active',
            }
        )

        # The encumbrance lifting occurs in DEFAULT_LICENSE_JURISDICTION ('oh')
        message = self._generate_license_encumbrance_lifting_message()
        event = self._create_sqs_event(message)

        # Execute the handler
        result = license_encumbrance_lifting_notification_listener(event, self.mock_context)

        # Should succeed with no batch failures
        self.assertEqual({'batchItemFailures': []}, result)

        # Verify provider notification
        mock_provider_email.assert_called_once_with(
            compact=DEFAULT_COMPACT,
            provider_email='provider@example.com',
            template_variables=EncumbranceNotificationTemplateVariables(
                provider_first_name='Björk',
                provider_last_name='Guðmundsdóttir',
                encumbered_jurisdiction='oh',
                license_type='speech-language pathologist',
                effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                provider_id=None,
            ),
        )

        # Verify state notifications were sent to all relevant jurisdictions
        self.assertEqual(4, mock_state_email.call_count)

        # Check each call individually since they have different provider_id values
        calls = mock_state_email.call_args_list
        call_jurisdictions = [call.kwargs['jurisdiction'] for call in calls]
        self.assertEqual(sorted(call_jurisdictions), ['ky', 'ne', 'oh', 'tx'])

        # Verify all calls have the correct template_variables structure
        for call in calls:
            self.assertEqual(call.kwargs['compact'], DEFAULT_COMPACT)
            self.assertEqual(
                call.kwargs['template_variables'],
                EncumbranceNotificationTemplateVariables(
                    provider_first_name='Björk',
                    provider_last_name='Guðmundsdóttir',
                    encumbered_jurisdiction='oh',
                    license_type='speech-language pathologist',
                    effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                    provider_id=UUID(DEFAULT_PROVIDER_ID),
                ),
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
        expected_failure = {'batchItemFailures': [{'itemIdentifier': '123'}]}
        self.assertEqual(expected_failure, result)

    @patch(
        'cc_common.email_service_client.EmailServiceClient.send_license_encumbrance_lifting_state_notification_email'
    )
    @patch(
        'cc_common.email_service_client.EmailServiceClient.send_license_encumbrance_lifting_provider_notification_email'
    )
    @patch('cc_common.email_service_client.EmailServiceClient.send_license_encumbrance_state_notification_email')
    @patch('cc_common.email_service_client.EmailServiceClient.send_license_encumbrance_provider_notification_email')
    def test_license_encumbrance_notification_listeners_handle_no_additional_jurisdictions(
        self, mock_enc_provider, mock_enc_state, mock_lift_provider, mock_lift_state
    ):
        """
        Test that license encumbrance notification listeners handle case where provider has no other active
        licenses/privileges.
        """
        from handlers.encumbrance_events import (
            license_encumbrance_lifting_notification_listener,
            license_encumbrance_notification_listener,
        )

        # Set up test data with only provider record
        self.test_data_generator.put_default_provider_record_in_provider_table(
            value_overrides={'compactConnectRegisteredEmailAddress': 'provider@example.com'}
        )

        # Add the license that is being encumbered/lifted (in DEFAULT_LICENSE_JURISDICTION = 'oh')
        self.test_data_generator.put_default_license_record_in_provider_table()

        # Only create records in the same jurisdiction as the encumbrance (no other jurisdictions)
        self.test_data_generator.put_default_privilege_record_in_provider_table(
            value_overrides={
                'jurisdiction': DEFAULT_LICENSE_JURISDICTION,
                'administratorSetStatus': 'active',
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

        # Verify license encumbrance notifications
        from cc_common.email_service_client import EncumbranceNotificationTemplateVariables

        mock_enc_provider.assert_called_once_with(
            compact=DEFAULT_COMPACT,
            provider_email='provider@example.com',
            template_variables=EncumbranceNotificationTemplateVariables(
                provider_first_name='Björk',
                provider_last_name='Guðmundsdóttir',
                encumbered_jurisdiction='oh',
                license_type='speech-language pathologist',
                effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                provider_id=None,
            ),
        )

        # Only state 'oh' should be notified (no other jurisdictions)
        mock_enc_state.assert_called_once_with(
            compact=DEFAULT_COMPACT,
            jurisdiction='oh',
            template_variables=EncumbranceNotificationTemplateVariables(
                provider_first_name='Björk',
                provider_last_name='Guðmundsdóttir',
                encumbered_jurisdiction='oh',
                license_type='speech-language pathologist',
                effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                provider_id=UUID(DEFAULT_PROVIDER_ID),
            ),
        )

        # Verify license lifting notifications
        mock_lift_provider.assert_called_once_with(
            compact=DEFAULT_COMPACT,
            provider_email='provider@example.com',
            template_variables=EncumbranceNotificationTemplateVariables(
                provider_first_name='Björk',
                provider_last_name='Guðmundsdóttir',
                encumbered_jurisdiction='oh',
                license_type='speech-language pathologist',
                effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                provider_id=None,
            ),
        )

        # Only state 'oh' should be notified (no other jurisdictions)
        mock_lift_state.assert_called_once_with(
            compact=DEFAULT_COMPACT,
            jurisdiction='oh',
            template_variables=EncumbranceNotificationTemplateVariables(
                provider_first_name='Björk',
                provider_last_name='Guðmundsdóttir',
                encumbered_jurisdiction='oh',
                license_type='speech-language pathologist',
                effective_date=date.fromisoformat(DEFAULT_EFFECTIVE_DATE),
                provider_id=UUID(DEFAULT_PROVIDER_ID),
            ),
        )
