import json
from datetime import datetime
from unittest.mock import patch

from boto3.dynamodb.conditions import Key
from common_test.test_constants import (
    DEFAULT_COMPACT,
    DEFAULT_DATE_OF_UPDATE_TIMESTAMP,
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

    def test_license_encumbrance_listener_encumbers_unencumbered_privileges_successfully(self):
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
        unencumbered_privilege_after = next(p for p in privileges if p.jurisdiction == 'ne')
        already_encumbered_privilege_after = next(p for p in privileges if p.jurisdiction == 'ky')

        # Verify the unencumbered privilege is now LICENSE_ENCUMBERED
        self.assertEqual(
            PrivilegeEncumberedStatusEnum.LICENSE_ENCUMBERED, unencumbered_privilege_after.encumberedStatus
        )

        # Verify the already encumbered privilege remains ENCUMBERED (not changed)
        self.assertEqual(PrivilegeEncumberedStatusEnum.ENCUMBERED, already_encumbered_privilege_after.encumberedStatus)

    def test_license_encumbrance_listener_handles_no_matching_privileges(self):
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

    def test_license_encumbrance_listener_handles_all_privileges_already_encumbered(self):
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

    def test_license_encumbrance_lifted_listener_unencumbers_license_encumbered_privileges_successfully(self):
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
        license_encumbered_privilege_after = next(
            p for p in privileges if p.jurisdiction == DEFAULT_PRIVILEGE_JURISDICTION
        )
        self_encumbered_privilege_after = next(p for p in privileges if p.jurisdiction == 'ky')

        # Verify the LICENSE_ENCUMBERED privilege is now unencumbered
        self.assertEqual(
            PrivilegeEncumberedStatusEnum.UNENCUMBERED, license_encumbered_privilege_after.encumberedStatus
        )

        # Verify the self-encumbered privilege remains encumbered
        self.assertEqual(PrivilegeEncumberedStatusEnum.ENCUMBERED, self_encumbered_privilege_after.encumberedStatus)

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

    def test_license_encumbrance_listener_handles_multiple_matching_privileges(self):
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

        matching_privilege_after = next(p for p in privileges if p.jurisdiction == 'ne')
        different_jurisdiction_privilege_after = next(p for p in privileges if p.jurisdiction == 'tx')

        self.assertEqual(PrivilegeEncumberedStatusEnum.LICENSE_ENCUMBERED, matching_privilege_after.encumberedStatus)
        self.assertIsNone(different_jurisdiction_privilege_after.encumberedStatus)

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
            if (privilege.licenseJurisdiction == DEFAULT_LICENSE_JURISDICTION and 
                privilege.licenseType == DEFAULT_LICENSE_TYPE):
                # All matching privileges should remain LICENSE_ENCUMBERED
                self.assertEqual(
                    PrivilegeEncumberedStatusEnum.LICENSE_ENCUMBERED, 
                    privilege.encumberedStatus
                )
