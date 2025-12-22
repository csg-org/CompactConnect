import json
from datetime import datetime
from unittest.mock import patch

from common_test.test_constants import (
    DEFAULT_COMPACT,
    DEFAULT_DATE_OF_UPDATE_TIMESTAMP,
)
from moto import mock_aws

from .. import TstFunction

MILITARY_AUDIT_ENDPOINT_RESOURCE = '/v1/compacts/{compact}/providers/{providerId}/militaryAudit'


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat(DEFAULT_DATE_OF_UPDATE_TIMESTAMP))
class TestMilitaryAudit(TstFunction):
    """Test suite for military audit endpoint."""

    def _when_testing_military_audit(
        self, military_status: str, military_status_note: str | None = None, test_provider=None
    ):
        """Set up test data and generate test event for military audit."""
        # Create provider and military affiliation records
        if test_provider is None:
            test_provider = self.test_data_generator.put_default_provider_record_in_provider_table()
            self.test_data_generator.put_default_military_affiliation_in_provider_table()

        body = {'militaryStatus': military_status}
        if military_status_note:
            body['militaryStatusNote'] = military_status_note

        test_event = self.test_data_generator.generate_test_api_event(
            scope_override=f'openid email {DEFAULT_COMPACT}/admin',
            value_overrides={
                'httpMethod': 'PATCH',
                'resource': MILITARY_AUDIT_ENDPOINT_RESOURCE,
                'pathParameters': {
                    'compact': test_provider.compact,
                    'providerId': str(test_provider.providerId),
                },
                'body': json.dumps(body),
            },
        )
        return test_event, test_provider

    def test_military_audit_approved_returns_ok(self):
        """Test that approving military audit returns OK message."""
        from handlers.military_audit import military_audit_handler

        event, _ = self._when_testing_military_audit('approved')

        response = military_audit_handler(event, self.mock_context)

        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))
        response_body = json.loads(response['body'])
        self.assertEqual({'message': 'OK'}, response_body)

    def test_military_audit_declined_with_note_returns_ok(self):
        """Test that declining military audit with a note returns OK message."""
        from handlers.military_audit import military_audit_handler

        event, _ = self._when_testing_military_audit('declined', 'Documentation was unclear')

        response = military_audit_handler(event, self.mock_context)

        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))
        response_body = json.loads(response['body'])
        self.assertEqual({'message': 'OK'}, response_body)

    def test_military_audit_updates_provider_record(self):
        """Test that military audit updates the provider record with audit status."""
        from handlers.military_audit import military_audit_handler

        event, test_provider = self._when_testing_military_audit('approved')

        response = military_audit_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))

        # Verify provider record was updated
        updated_provider_record = self.config.data_client.get_provider_top_level_record(
            compact=test_provider.compact, provider_id=test_provider.providerId
        )

        self.assertEqual('approved', updated_provider_record.militaryStatus)
        self.assertEqual('', updated_provider_record.militaryStatusNote)

    def test_military_audit_declined_updates_with_note(self):
        """Test that declining military audit updates provider and affiliation with note."""
        from handlers.military_audit import military_audit_handler

        event, test_provider = self._when_testing_military_audit('declined', 'Invalid documentation')

        response = military_audit_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))

        # Verify provider record was updated
        updated_provider_record = self.config.data_client.get_provider_top_level_record(
            compact=test_provider.compact, provider_id=test_provider.providerId
        )

        self.assertEqual('declined', updated_provider_record.militaryStatus)
        self.assertEqual('Invalid documentation', updated_provider_record.militaryStatusNote)

    def test_military_audit_invalid_status_returns_400(self):
        """Test that an invalid military status returns 400 error."""
        from handlers.military_audit import military_audit_handler

        event, _ = self._when_testing_military_audit(
            'foo',
            'Documentation verified',
        )

        response = military_audit_handler(event, self.mock_context)

        self.assertEqual(400, response['statusCode'])
        self.assertEqual(
            {'message': "Invalid request body: {'militaryStatus': ['Must be one of: approved, declined.']}"},
            json.loads(response['body']),
        )

    def test_military_audit_missing_status_returns_400(self):
        """Test that missing military status returns 400 error."""
        from handlers.military_audit import military_audit_handler

        test_provider = self.test_data_generator.put_default_provider_record_in_provider_table()
        self.test_data_generator.put_default_military_affiliation_in_provider_table()

        test_event = self.test_data_generator.generate_test_api_event(
            scope_override=f'openid email {DEFAULT_COMPACT}/admin',
            value_overrides={
                'httpMethod': 'PATCH',
                'resource': MILITARY_AUDIT_ENDPOINT_RESOURCE,
                'pathParameters': {
                    'compact': test_provider.compact,
                    'providerId': str(test_provider.providerId),
                },
                'body': json.dumps({}),
            },
        )

        response = military_audit_handler(test_event, self.mock_context)

        self.assertEqual(400, response['statusCode'])

    def test_military_audit_no_affiliation_returns_404(self):
        """Test that audit fails when provider has no military affiliation records."""
        from handlers.military_audit import military_audit_handler

        # Only create provider, no military affiliation
        test_provider = self.test_data_generator.put_default_provider_record_in_provider_table()

        event, _ = self._when_testing_military_audit('approved', 'Documentation verified', test_provider=test_provider)

        response = military_audit_handler(event, self.mock_context)

        self.assertEqual(404, response['statusCode'])

    def test_military_audit_unauthorized_returns_403(self):
        """Test that non-admin users receive 403 Forbidden."""
        from handlers.military_audit import military_audit_handler

        test_provider = self.test_data_generator.put_default_provider_record_in_provider_table()
        self.test_data_generator.put_default_military_affiliation_in_provider_table()

        # Use a non-admin scope
        test_event = self.test_data_generator.generate_test_api_event(
            scope_override=f'openid email {DEFAULT_COMPACT}/readGeneral',
            value_overrides={
                'httpMethod': 'PATCH',
                'resource': MILITARY_AUDIT_ENDPOINT_RESOURCE,
                'pathParameters': {
                    'compact': test_provider.compact,
                    'providerId': str(test_provider.providerId),
                },
                'body': json.dumps({'militaryStatus': 'approved'}),
            },
        )

        response = military_audit_handler(test_event, self.mock_context)

        self.assertEqual(403, response['statusCode'])

    def test_military_audit_creates_provider_update_record(self):
        """Test that military audit creates a provider update record with expected values."""
        from cc_common.data_model.schema.common import UpdateCategory
        from cc_common.data_model.schema.provider import ProviderUpdateData
        from handlers.military_audit import military_audit_handler

        # Create provider with initial military status
        test_provider = self.test_data_generator.put_default_provider_record_in_provider_table(
            value_overrides={'militaryStatus': 'tentative', 'militaryStatusNote': ''}
        )
        self.test_data_generator.put_default_military_affiliation_in_provider_table()

        event, _ = self._when_testing_military_audit('approved', 'Documentation verified', test_provider=test_provider)

        response = military_audit_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))

        # Query provider update records
        stored_provider_update_records = (
            self.test_data_generator.query_provider_update_records_for_given_record_from_database(test_provider)
        )

        # Verify exactly one update record was created
        self.assertEqual(1, len(stored_provider_update_records))

        # Verify the update record contents
        update_data = ProviderUpdateData.from_database_record(stored_provider_update_records[0])
        self.assertEqual(UpdateCategory.MILITARY_AUDIT, update_data.updateType)
        self.assertEqual(test_provider.providerId, update_data.providerId)
        self.assertEqual(test_provider.compact, update_data.compact)

        # Verify previous state was captured
        self.assertIsNotNone(update_data.previous)
        self.assertEqual('tentative', update_data.previous.get('militaryStatus'))
        self.assertEqual('', update_data.previous.get('militaryStatusNote'))

        # Verify updated values
        self.assertEqual('approved', update_data.updatedValues['militaryStatus'])
        self.assertEqual('Documentation verified', update_data.updatedValues['militaryStatusNote'])
