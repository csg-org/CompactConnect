import json
from datetime import datetime
from unittest.mock import patch

from boto3.dynamodb.conditions import Key
from common_test.test_constants import (
    DEFAULT_COMPACT,
    DEFAULT_DATE_OF_UPDATE_TIMESTAMP,
    DEFAULT_LICENSE_JURISDICTION,
    DEFAULT_LICENSE_TYPE,
    DEFAULT_PROVIDER_ID,
)
from moto import mock_aws

from . import TstFunction


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat(DEFAULT_DATE_OF_UPDATE_TIMESTAMP))
class TestLicenseDeactivationEvents(TstFunction):
    """Test suite for license deactivation event handlers."""

    def _generate_license_deactivation_message(self, message_overrides=None):
        """Generate a test SQS message for license deactivation events."""
        message = {
            'detail': {
                'compact': DEFAULT_COMPACT,
                'providerId': DEFAULT_PROVIDER_ID,
                'jurisdiction': DEFAULT_LICENSE_JURISDICTION,
                'licenseType': DEFAULT_LICENSE_TYPE,
                'eventTime': DEFAULT_DATE_OF_UPDATE_TIMESTAMP,
            }
        }
        if message_overrides:
            message['detail'].update(message_overrides)
        return message

    def _create_sqs_event(self, message):
        """Create a proper SQS event structure with the message in the body."""
        return {'Records': [{'messageId': '123', 'body': json.dumps(message)}]}

    def test_license_deactivation_listener_deactivates_active_privileges_successfully(self):
        """Test that license deactivation event successfully deactivates associated active privileges."""
        from cc_common.data_model.schema.common import LicenseDeactivatedStatusEnum
        from handlers.license_deactivation_events import license_deactivation_listener

        # Set up test data
        self.test_data_generator.put_default_provider_record_in_provider_table()

        # Create privileges with matching license jurisdiction and type - one active,
        # another already license-deactivated
        self.test_data_generator.put_default_privilege_record_in_provider_table(
            value_overrides={
                'licenseJurisdiction': DEFAULT_LICENSE_JURISDICTION,
                'licenseType': DEFAULT_LICENSE_TYPE,
                # licenseDeactivatedStatus is None (active)
                'jurisdiction': 'ne',
            }
        )

        self.test_data_generator.put_default_privilege_record_in_provider_table(
            value_overrides={
                'licenseJurisdiction': DEFAULT_LICENSE_JURISDICTION,
                'licenseType': DEFAULT_LICENSE_TYPE,
                'licenseDeactivatedStatus': 'licenseDeactivated',  # Already license-deactivated
                'jurisdiction': 'ky',  # Different jurisdiction to distinguish
            }
        )

        message = self._generate_license_deactivation_message()
        event = self._create_sqs_event(message)

        # Execute the handler
        license_deactivation_listener(event, self.mock_context)

        # Verify that only the active privilege was deactivated
        provider_records = self.config.data_client.get_provider_user_records(
            compact=DEFAULT_COMPACT,
            provider_id=DEFAULT_PROVIDER_ID,
        )

        privileges = provider_records.get_privilege_records()

        # Find the privileges by jurisdiction
        previously_active_privilege = next(p for p in privileges if p.jurisdiction == 'ne')
        previously_deactivated_privilege = next(p for p in privileges if p.jurisdiction == 'ky')

        # Verify the active privilege is now LICENSE_DEACTIVATED
        self.assertEqual(
            LicenseDeactivatedStatusEnum.LICENSE_DEACTIVATED, previously_active_privilege.licenseDeactivatedStatus
        )

        # Verify the already deactivated privilege remains LICENSE_DEACTIVATED (not changed)
        self.assertEqual(
            LicenseDeactivatedStatusEnum.LICENSE_DEACTIVATED, previously_deactivated_privilege.licenseDeactivatedStatus
        )

    def test_license_deactivation_listener_handles_no_matching_privileges(self):
        """Test that license deactivation event handles case where no matching privileges exist."""
        from handlers.license_deactivation_events import license_deactivation_listener

        # Set up test data with no matching privileges
        self.test_data_generator.put_default_provider_record_in_provider_table()

        # Create privilege with different license jurisdiction/type
        self.test_data_generator.put_default_privilege_record_in_provider_table(
            value_overrides={
                'licenseJurisdiction': 'ky',  # Different jurisdiction
                'licenseType': 'audiologist',  # Different license type
                # note there is no licenseDeactivatedStatus present
            }
        )

        message = self._generate_license_deactivation_message()
        event = self._create_sqs_event(message)

        # Execute the handler - should not raise any exceptions
        license_deactivation_listener(event, self.mock_context)

        # Verify no privileges were modified
        provider_records = self.config.data_client.get_provider_user_records(
            compact=DEFAULT_COMPACT,
            provider_id=DEFAULT_PROVIDER_ID,
        )

        privileges = provider_records.get_privilege_records()
        self.assertEqual(1, len(privileges))
        self.assertIsNone(privileges[0].licenseDeactivatedStatus)

    def test_license_deactivation_listener_handles_multiple_matching_privileges(self):
        """Test that license deactivation event handles multiple matching privileges correctly."""
        from cc_common.data_model.schema.common import LicenseDeactivatedStatusEnum
        from handlers.license_deactivation_events import license_deactivation_listener

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

        message = self._generate_license_deactivation_message()
        event = self._create_sqs_event(message)

        # Execute the handler
        license_deactivation_listener(event, self.mock_context)

        # Verify both privileges were deactivated
        provider_records = self.config.data_client.get_provider_user_records(
            compact=DEFAULT_COMPACT,
            provider_id=DEFAULT_PROVIDER_ID,
        )

        privileges = provider_records.get_privilege_records()
        self.assertEqual(2, len(privileges))

        for privilege in privileges:
            self.assertEqual(LicenseDeactivatedStatusEnum.LICENSE_DEACTIVATED, privilege.licenseDeactivatedStatus)

    def test_license_deactivation_listener_handles_mixed_license_types(self):
        """Test that license deactivation event only affects privileges with matching license type."""
        from cc_common.data_model.schema.common import LicenseDeactivatedStatusEnum
        from handlers.license_deactivation_events import license_deactivation_listener

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

        message = self._generate_license_deactivation_message()
        event = self._create_sqs_event(message)

        # Execute the handler
        license_deactivation_listener(event, self.mock_context)

        # Verify only the matching privilege was deactivated
        provider_records = self.config.data_client.get_provider_user_records(
            compact=DEFAULT_COMPACT,
            provider_id=DEFAULT_PROVIDER_ID,
        )

        privileges = provider_records.get_privilege_records()

        matching_privilege_after = next(p for p in privileges if p.jurisdiction == 'ne')
        different_type_privilege_after = next(p for p in privileges if p.jurisdiction == 'ky')

        self.assertEqual(
            LicenseDeactivatedStatusEnum.LICENSE_DEACTIVATED, matching_privilege_after.licenseDeactivatedStatus
        )
        self.assertIsNone(
            different_type_privilege_after.licenseDeactivatedStatus,
            f'licenseDeactivatedStatus is not None: {different_type_privilege_after.licenseDeactivatedStatus}',
        )

    def test_license_deactivation_listener_handles_mixed_license_jurisdictions(self):
        """Test that license deactivation event only affects privileges with matching license jurisdiction."""
        from cc_common.data_model.schema.common import LicenseDeactivatedStatusEnum
        from handlers.license_deactivation_events import license_deactivation_listener

        # Set up test data
        self.test_data_generator.put_default_provider_record_in_provider_table()

        # Create privilege with matching license jurisdiction
        self.test_data_generator.put_default_privilege_record_in_provider_table(
            value_overrides={
                'licenseJurisdiction': DEFAULT_LICENSE_JURISDICTION,
                'licenseType': DEFAULT_LICENSE_TYPE,
                'jurisdiction': 'ne',
            }
        )

        # Create privilege with different license jurisdiction
        self.test_data_generator.put_default_privilege_record_in_provider_table(
            value_overrides={
                'licenseJurisdiction': 'ky',  # Different license jurisdiction
                'licenseType': DEFAULT_LICENSE_TYPE,
                'jurisdiction': 'tx',
            }
        )

        message = self._generate_license_deactivation_message()
        event = self._create_sqs_event(message)

        # Execute the handler
        license_deactivation_listener(event, self.mock_context)

        # Verify only the matching privilege was deactivated
        provider_records = self.config.data_client.get_provider_user_records(
            compact=DEFAULT_COMPACT,
            provider_id=DEFAULT_PROVIDER_ID,
        )

        privileges = provider_records.get_privilege_records()

        matching_privilege = next(p for p in privileges if p.jurisdiction == 'ne')
        different_jurisdiction_privilege = next(p for p in privileges if p.jurisdiction == 'tx')

        self.assertEqual(LicenseDeactivatedStatusEnum.LICENSE_DEACTIVATED, matching_privilege.licenseDeactivatedStatus)
        self.assertIsNone(different_jurisdiction_privilege.licenseDeactivatedStatus)

    def test_license_deactivation_listener_creates_update_records_for_all_affected_privileges(self):
        """Test that license deactivation event creates privilege update records for all affected privileges."""
        from handlers.license_deactivation_events import license_deactivation_listener

        # Set up test data
        self.test_data_generator.put_default_provider_record_in_provider_table()

        # Create multiple privileges
        privilege1 = self.test_data_generator.put_default_privilege_record_in_provider_table(
            value_overrides={
                'licenseJurisdiction': DEFAULT_LICENSE_JURISDICTION,
                'licenseType': DEFAULT_LICENSE_TYPE,
                'jurisdiction': 'ne',
            }
        )

        privilege2 = self.test_data_generator.put_default_privilege_record_in_provider_table(
            value_overrides={
                'licenseJurisdiction': DEFAULT_LICENSE_JURISDICTION,
                'licenseType': DEFAULT_LICENSE_TYPE,
                'jurisdiction': 'ky',
            }
        )

        message = self._generate_license_deactivation_message()
        event = self._create_sqs_event(message)

        # Execute the handler
        license_deactivation_listener(event, self.mock_context)

        # Verify privilege update records were created for both privileges
        for privilege in [privilege1, privilege2]:
            privilege_update_records = self._provider_table.query(
                Select='ALL_ATTRIBUTES',
                KeyConditionExpression=Key('pk').eq(privilege.serialize_to_database_record()['pk'])
                & Key('sk').begins_with(f'{privilege.compact}#PROVIDER#privilege/{privilege.jurisdiction}/slp#UPDATE'),
            )

            self.assertEqual(1, len(privilege_update_records['Items']))
            update_record = privilege_update_records['Items'][0]
            self.assertEqual('licenseDeactivation', update_record['updateType'])
            self.assertEqual({'licenseDeactivatedStatus': 'licenseDeactivated'}, update_record['updatedValues'])

    def test_license_deactivation_listener_fails_with_missing_required_fields(self):
        """Test that license deactivation event handler fails when required fields are missing."""
        from handlers.license_deactivation_events import license_deactivation_listener

        # Create message missing required licenseType field
        message = {
            'detail': {
                'compact': DEFAULT_COMPACT,
                'providerId': DEFAULT_PROVIDER_ID,
                'jurisdiction': DEFAULT_LICENSE_JURISDICTION,
                'eventTime': DEFAULT_DATE_OF_UPDATE_TIMESTAMP,
                # Missing 'licenseType' field
            }
        }
        event = self._create_sqs_event(message)

        # Execute the handler and expect error
        resp = license_deactivation_listener(event, self.mock_context)

        self.assertEqual({'batchItemFailures': [{'itemIdentifier': '123'}]}, resp)
