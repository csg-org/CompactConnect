import json
from datetime import datetime
from unittest.mock import patch

from boto3.dynamodb.conditions import Key
from common_test.test_constants import (
    DEFAULT_AA_SUBMITTING_USER_ID,
    DEFAULT_DATE_OF_UPDATE_TIMESTAMP,
)
from moto import mock_aws

from .. import TstFunction

PRIVILEGE_INVESTIGATION_ENDPOINT_RESOURCE = (
    '/v1/compacts/{compact}/providers/{providerId}/privileges/'
    'jurisdiction/{jurisdiction}/licenseType/{licenseType}/investigation'
)
LICENSE_INVESTIGATION_ENDPOINT_RESOURCE = (
    '/v1/compacts/{compact}/providers/{providerId}/licenses/'
    'jurisdiction/{jurisdiction}/licenseType/{licenseType}/investigation'
)
PRIVILEGE_INVESTIGATION_ID_ENDPOINT_RESOURCE = (
    '/v1/compacts/{compact}/providers/{providerId}/privileges/'
    'jurisdiction/{jurisdiction}/licenseType/{licenseType}/investigation/{investigationId}'
)
LICENSE_INVESTIGATION_ID_ENDPOINT_RESOURCE = (
    '/v1/compacts/{compact}/providers/{providerId}/licenses/'
    'jurisdiction/{jurisdiction}/licenseType/{licenseType}/investigation/{investigationId}'
)

TEST_INVESTIGATION_START_DATE = '2023-01-15'
TEST_INVESTIGATION_CLOSE_DATE = '2023-02-15'
TEST_ENCUMBRANCE_EFFECTIVE_DATE = '2023-01-15'


def _generate_test_investigation_close_with_encumbrance_body():
    from cc_common.data_model.schema.common import ClinicalPrivilegeActionCategory, EncumbranceType

    return {
        'encumbrance': {
            'encumbranceEffectiveDate': TEST_ENCUMBRANCE_EFFECTIVE_DATE,
            # These Enums are expected to be `str` type, so we'll directly access their .value
            'encumbranceType': EncumbranceType.SUSPENSION.value,
            'clinicalPrivilegeActionCategory': ClinicalPrivilegeActionCategory.UNSAFE_PRACTICE.value,
        },
    }


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat(DEFAULT_DATE_OF_UPDATE_TIMESTAMP))
class TestPostPrivilegeInvestigation(TstFunction):
    """Test suite for privilege investigation endpoints."""

    def _load_privilege_data(self):
        """Load privilege test data from JSON file"""
        import json
        from decimal import Decimal

        # Load provider record first (needed for encumbrance creation)
        with open('../common/tests/resources/dynamo/provider.json') as f:
            provider_record = json.load(f, parse_float=Decimal)
        self._provider_table.put_item(Item=provider_record)

        # Load privilege record
        with open('../common/tests/resources/dynamo/privilege.json') as f:
            privilege_record = json.load(f, parse_float=Decimal)
        self._provider_table.put_item(Item=privilege_record)

        # Return the privilege data as a data class
        from cc_common.data_model.schema.privilege import PrivilegeData

        return PrivilegeData.from_database_record(privilege_record)

    def _when_testing_privilege_investigation(self):
        test_privilege_record = self._load_privilege_data()

        test_event = self.test_data_generator.generate_test_api_event(
            sub_override=DEFAULT_AA_SUBMITTING_USER_ID,
            scope_override=f'openid email {test_privilege_record.jurisdiction}/aslp.admin',
            value_overrides={
                'httpMethod': 'POST',
                'resource': PRIVILEGE_INVESTIGATION_ENDPOINT_RESOURCE,
                'pathParameters': {
                    'compact': test_privilege_record.compact,
                    'providerId': str(test_privilege_record.providerId),
                    'jurisdiction': test_privilege_record.jurisdiction,
                    'licenseType': test_privilege_record.licenseTypeAbbreviation,
                },
            },
        )

        # return both the test event and the test privilege record
        return test_event, test_privilege_record

    def test_privilege_investigation_handler_returns_ok_message_with_valid_body(self):
        from handlers.investigation import investigation_handler

        event = self._when_testing_privilege_investigation()[0]

        response = investigation_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))
        response_body = json.loads(response['body'])

        self.assertEqual(
            {'message': 'OK'},
            response_body,
        )

    def test_privilege_investigation_handler_adds_investigation_record_in_provider_data_table(self):
        from handlers.investigation import investigation_handler

        event, test_privilege_record = self._when_testing_privilege_investigation()

        response = investigation_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))

        # Verify that the investigation record was added to the provider data table
        # Perform a query to list all investigations for the provider using the starts_with key condition
        investigation_records = self._provider_table.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('pk').eq(test_privilege_record.serialize_to_database_record()['pk'])
            & Key('sk').begins_with(
                f'{test_privilege_record.compact}#PROVIDER#privilege/{test_privilege_record.jurisdiction}/slp#INVESTIGATION'
            ),
        )
        self.assertEqual(1, len(investigation_records['Items']))
        item = investigation_records['Items'][0]

        # Verify the investigation record fields
        expected_investigation = {
            'type': 'investigation',
            'compact': test_privilege_record.compact,
            'providerId': str(test_privilege_record.providerId),
            'jurisdiction': test_privilege_record.jurisdiction,
            'licenseType': test_privilege_record.licenseType,
            'investigationAgainst': 'privilege',
            'submittingUser': DEFAULT_AA_SUBMITTING_USER_ID,
            'creationDate': DEFAULT_DATE_OF_UPDATE_TIMESTAMP,
            'dateOfUpdate': DEFAULT_DATE_OF_UPDATE_TIMESTAMP,
            'pk': test_privilege_record.serialize_to_database_record()['pk'],
            'sk': (
                f'{test_privilege_record.compact}#PROVIDER#privilege/'
                f'{test_privilege_record.jurisdiction}/slp#INVESTIGATION#{item["investigationId"]}'
            ),
            'investigationId': item['investigationId'],
        }
        self.assertEqual(expected_investigation, item)

    def test_privilege_investigation_handler_sets_provider_record_to_under_investigation_in_provider_data_table(self):
        from cc_common.data_model.schema.common import InvestigationStatusEnum
        from handlers.investigation import investigation_handler
        from handlers.providers import get_provider

        event, test_privilege_record = self._when_testing_privilege_investigation()

        response = investigation_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))

        # Verify that the privilege record was updated to be under investigation
        updated_privilege_record = self._provider_table.get_item(
            Key={
                'pk': test_privilege_record.serialize_to_database_record()['pk'],
                'sk': test_privilege_record.serialize_to_database_record()['sk'],
            }
        )['Item']

        self.assertEqual(
            InvestigationStatusEnum.UNDER_INVESTIGATION.value, updated_privilege_record['investigationStatus']
        )

        # Verify that investigation objects are included in the API response
        api_event = self.test_data_generator.generate_test_api_event(
            scope_override=f'openid email {test_privilege_record.jurisdiction}/aslp.readGeneral',
            value_overrides={
                'httpMethod': 'GET',
                'resource': '/v1/compacts/{compact}/providers/{providerId}',
                'pathParameters': {
                    'compact': test_privilege_record.compact,
                    'providerId': str(test_privilege_record.providerId),
                },
            },
        )

        api_response = get_provider(api_event, self.mock_context)
        self.assertEqual(200, api_response['statusCode'])

        provider_data = json.loads(api_response['body'])

        # Verify that the privilege has investigation objects
        privilege = provider_data['privileges'][0]
        investigation = privilege['investigations'][0]

        expected_investigation = {
            'type': 'investigation',
            'compact': test_privilege_record.compact,
            'providerId': str(test_privilege_record.providerId),
            'jurisdiction': test_privilege_record.jurisdiction,
            'licenseType': test_privilege_record.licenseType,
            'submittingUser': DEFAULT_AA_SUBMITTING_USER_ID,
            'creationDate': DEFAULT_DATE_OF_UPDATE_TIMESTAMP,
            'dateOfUpdate': DEFAULT_DATE_OF_UPDATE_TIMESTAMP,
            'investigationId': investigation['investigationId'],  # Dynamic field
        }

        self.assertEqual(expected_investigation, investigation)

    def test_privilege_investigation_handler_returns_access_denied_if_compact_admin(self):
        """Verifying that only state admins are allowed to create privilege investigations"""
        from handlers.investigation import investigation_handler

        event, test_privilege_record = self._when_testing_privilege_investigation()

        event['requestContext']['authorizer']['claims']['scope'] = f'openid email {test_privilege_record.compact}/admin'

        response = investigation_handler(event, self.mock_context)
        self.assertEqual(403, response['statusCode'], msg=json.loads(response['body']))
        response_body = json.loads(response['body'])

        self.assertEqual(
            {'message': 'Access denied'},
            response_body,
        )

    @patch('cc_common.event_bus_client.EventBusClient._publish_event')
    def test_privilege_investigation_handler_publishes_event(self, mock_publish_event):
        """Test that privilege investigation handler publishes the correct event."""
        from handlers.investigation import investigation_handler

        event, test_privilege_record = self._when_testing_privilege_investigation()

        response = investigation_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'])

        # Verify event was published with correct details
        mock_publish_event.assert_called_once()
        call_args = mock_publish_event.call_args[1]

        expected_event_args = {
            'source': 'org.compactconnect.provider-data',
            'detail_type': 'privilege.investigation',
            'event_batch_writer': None,
            'detail': {
                'compact': test_privilege_record.compact,
                'providerId': str(test_privilege_record.providerId),
                'jurisdiction': test_privilege_record.jurisdiction,
                'licenseTypeAbbreviation': test_privilege_record.licenseTypeAbbreviation,
                'eventTime': DEFAULT_DATE_OF_UPDATE_TIMESTAMP,
                'investigationAgainst': 'privilege',
            },
        }
        self.assertEqual(expected_event_args, call_args)

    @patch('cc_common.event_bus_client.EventBusClient._publish_event')
    def test_privilege_investigation_handler_handles_event_publishing_failure(self, mock_publish_event):
        """Test that privilege investigation handler fails when event publishing fails."""
        from handlers.investigation import investigation_handler

        event, _ = self._when_testing_privilege_investigation()
        mock_publish_event.side_effect = Exception('Event publishing failed')

        with self.assertRaises(Exception) as context:
            investigation_handler(event, self.mock_context)
        self.assertEqual('Event publishing failed', str(context.exception))


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat(DEFAULT_DATE_OF_UPDATE_TIMESTAMP))
class TestPostLicenseInvestigation(TstFunction):
    """Test suite for license investigation endpoints."""

    def _load_license_data(self):
        """Load license test data from JSON file"""
        import json
        from decimal import Decimal

        # Load provider record first (needed for encumbrance creation)
        with open('../common/tests/resources/dynamo/provider.json') as f:
            provider_record = json.load(f, parse_float=Decimal)
        self._provider_table.put_item(Item=provider_record)

        # Load license record
        with open('../common/tests/resources/dynamo/license.json') as f:
            license_record = json.load(f, parse_float=Decimal)
        self._provider_table.put_item(Item=license_record)

        # Return the license data as a data class
        from cc_common.data_model.schema.license import LicenseData

        return LicenseData.from_database_record(license_record)

    def _when_testing_valid_license_investigation(self, body_overrides: dict | None = None):
        test_license_record = self._load_license_data()
        test_body = {}
        if body_overrides:
            test_body.update(body_overrides)

        test_event = self.test_data_generator.generate_test_api_event(
            sub_override=DEFAULT_AA_SUBMITTING_USER_ID,
            scope_override=f'openid email {test_license_record.jurisdiction}/aslp.admin',
            value_overrides={
                'httpMethod': 'POST',
                'resource': LICENSE_INVESTIGATION_ENDPOINT_RESOURCE,
                'pathParameters': {
                    'compact': test_license_record.compact,
                    'providerId': str(test_license_record.providerId),
                    'jurisdiction': test_license_record.jurisdiction,
                    'licenseType': test_license_record.licenseTypeAbbreviation,
                },
                'body': json.dumps(test_body),
            },
        )

        # return both the event and test license record
        return test_event, test_license_record

    def test_license_investigation_handler_returns_ok_message_with_valid_body(self):
        from handlers.investigation import investigation_handler

        event = self._when_testing_valid_license_investigation()[0]

        response = investigation_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))
        response_body = json.loads(response['body'])

        self.assertEqual(
            {'message': 'OK'},
            response_body,
        )

    def test_license_investigation_handler_adds_investigation_record_in_provider_data_table(self):
        from handlers.investigation import investigation_handler

        event, test_license_record = self._when_testing_valid_license_investigation()

        response = investigation_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))

        # Verify that the investigation record was added to the provider data table
        # Perform a query to list all investigations for the provider using the starts_with key condition
        investigation_records = self._provider_table.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('pk').eq(test_license_record.serialize_to_database_record()['pk'])
            & Key('sk').begins_with(
                f'{test_license_record.compact}#PROVIDER#license/{test_license_record.jurisdiction}/slp#INVESTIGATION'
            ),
        )
        self.assertEqual(1, len(investigation_records['Items']))
        item = investigation_records['Items'][0]

        # Verify the investigation record fields
        expected_investigation = {
            'type': 'investigation',
            'compact': test_license_record.compact,
            'providerId': str(test_license_record.providerId),
            'jurisdiction': test_license_record.jurisdiction,
            'licenseType': test_license_record.licenseType,
            'investigationAgainst': 'license',
            'submittingUser': DEFAULT_AA_SUBMITTING_USER_ID,
            'creationDate': DEFAULT_DATE_OF_UPDATE_TIMESTAMP,
            'dateOfUpdate': DEFAULT_DATE_OF_UPDATE_TIMESTAMP,
            'pk': test_license_record.serialize_to_database_record()['pk'],
            'sk': (
                f'{test_license_record.compact}#PROVIDER#license/'
                f'{test_license_record.jurisdiction}/slp#INVESTIGATION#{item["investigationId"]}'
            ),
            'investigationId': item['investigationId'],
        }
        self.assertEqual(expected_investigation, item)

    def test_license_investigation_handler_sets_provider_record_to_under_investigation_in_provider_data_table(self):
        from cc_common.data_model.schema.common import InvestigationStatusEnum
        from handlers.investigation import investigation_handler
        from handlers.providers import get_provider

        event, test_license_record = self._when_testing_valid_license_investigation()

        response = investigation_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))

        # Verify that the license record was updated to be under investigation
        updated_license_record = self._provider_table.get_item(
            Key={
                'pk': test_license_record.serialize_to_database_record()['pk'],
                'sk': test_license_record.serialize_to_database_record()['sk'],
            }
        )['Item']

        self.assertEqual(
            InvestigationStatusEnum.UNDER_INVESTIGATION.value, updated_license_record['investigationStatus']
        )

        # Verify that investigation objects are included in the API response
        api_event = self.test_data_generator.generate_test_api_event(
            scope_override=f'openid email {test_license_record.jurisdiction}/aslp.readGeneral',
            value_overrides={
                'httpMethod': 'GET',
                'resource': '/v1/compacts/{compact}/providers/{providerId}',
                'pathParameters': {
                    'compact': test_license_record.compact,
                    'providerId': str(test_license_record.providerId),
                },
            },
        )

        api_response = get_provider(api_event, self.mock_context)
        self.assertEqual(200, api_response['statusCode'])

        provider_data = json.loads(api_response['body'])

        # Verify that the license has investigation objects
        license_obj = provider_data['licenses'][0]
        investigation = license_obj['investigations'][0]

        expected_investigation = {
            'type': 'investigation',
            'compact': test_license_record.compact,
            'providerId': str(test_license_record.providerId),
            'jurisdiction': test_license_record.jurisdiction,
            'licenseType': test_license_record.licenseType,
            'submittingUser': DEFAULT_AA_SUBMITTING_USER_ID,
            'creationDate': DEFAULT_DATE_OF_UPDATE_TIMESTAMP,
            'dateOfUpdate': DEFAULT_DATE_OF_UPDATE_TIMESTAMP,
            'investigationId': investigation['investigationId'],  # Dynamic field
        }

        self.assertEqual(expected_investigation, investigation)

    def test_license_investigation_handler_returns_access_denied_if_compact_admin(self):
        """Verifying that only state admins are allowed to create license investigations"""
        from handlers.investigation import investigation_handler

        event, test_license_record = self._when_testing_valid_license_investigation()

        event['requestContext']['authorizer']['claims']['scope'] = f'openid email {test_license_record.compact}/admin'

        response = investigation_handler(event, self.mock_context)
        self.assertEqual(403, response['statusCode'], msg=json.loads(response['body']))
        response_body = json.loads(response['body'])

        self.assertEqual(
            {'message': 'Access denied'},
            response_body,
        )

    @patch('cc_common.event_bus_client.EventBusClient._publish_event')
    def test_license_investigation_handler_publishes_event(self, mock_publish_event):
        """Test that license investigation handler publishes the correct event."""
        from handlers.investigation import investigation_handler

        event, test_license_record = self._when_testing_valid_license_investigation()

        response = investigation_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'])

        # Verify event was published with correct details
        mock_publish_event.assert_called_once()
        call_args = mock_publish_event.call_args[1]

        expected_event_args = {
            'source': 'org.compactconnect.provider-data',
            'detail_type': 'license.investigation',
            'event_batch_writer': None,
            'detail': {
                'compact': test_license_record.compact,
                'providerId': str(test_license_record.providerId),
                'jurisdiction': test_license_record.jurisdiction,
                'licenseTypeAbbreviation': test_license_record.licenseTypeAbbreviation,
                'eventTime': DEFAULT_DATE_OF_UPDATE_TIMESTAMP,
                'investigationAgainst': 'license',
                'investigationId': call_args['detail']['investigationId'],
            },
        }
        self.assertEqual(expected_event_args, call_args)

    @patch('cc_common.event_bus_client.EventBusClient._publish_event')
    def test_license_investigation_handler_handles_event_publishing_failure(self, mock_publish_event):
        """Test that license investigation handler fails when event publishing fails."""
        from handlers.investigation import investigation_handler

        event, _ = self._when_testing_valid_license_investigation()
        mock_publish_event.side_effect = Exception('Event publishing failed')

        with self.assertRaises(Exception) as context:
            investigation_handler(event, self.mock_context)
        self.assertEqual('Event publishing failed', str(context.exception))


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat(DEFAULT_DATE_OF_UPDATE_TIMESTAMP))
class TestPatchPrivilegeInvestigationClose(TstFunction):
    """Test suite for privilege investigation close endpoints."""

    def _load_privilege_data(self):
        """Load privilege test data from JSON file"""
        import json
        from decimal import Decimal

        # Load provider record first (needed for encumbrance creation)
        with open('../common/tests/resources/dynamo/provider.json') as f:
            provider_record = json.load(f, parse_float=Decimal)
        self._provider_table.put_item(Item=provider_record)

        # Load privilege record
        with open('../common/tests/resources/dynamo/privilege.json') as f:
            privilege_record = json.load(f, parse_float=Decimal)
        self._provider_table.put_item(Item=privilege_record)

        # Return the privilege data as a data class
        from cc_common.data_model.schema.privilege import PrivilegeData

        return PrivilegeData.from_database_record(privilege_record)

    def _when_testing_privilege_investigation_close(self, body_overrides: dict | None = None):
        test_privilege_record = self._load_privilege_data()
        test_body = {}
        if body_overrides:
            test_body.update(body_overrides)

        # First create an investigation
        create_event = self.test_data_generator.generate_test_api_event(
            sub_override=DEFAULT_AA_SUBMITTING_USER_ID,
            scope_override=f'openid email {test_privilege_record.jurisdiction}/aslp.admin',
            value_overrides={
                'httpMethod': 'POST',
                'resource': PRIVILEGE_INVESTIGATION_ENDPOINT_RESOURCE,
                'pathParameters': {
                    'compact': test_privilege_record.compact,
                    'providerId': str(test_privilege_record.providerId),
                    'jurisdiction': test_privilege_record.jurisdiction,
                    'licenseType': test_privilege_record.licenseTypeAbbreviation,
                },
            },
        )

        from handlers.investigation import investigation_handler

        investigation_handler(create_event, self.mock_context)

        # Get the investigation ID from the database
        investigation_records = self._provider_table.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('pk').eq(test_privilege_record.serialize_to_database_record()['pk'])
            & Key('sk').begins_with(
                f'{test_privilege_record.compact}#PROVIDER#privilege/{test_privilege_record.jurisdiction}/slp#INVESTIGATION'
            ),
        )
        investigation_id = investigation_records['Items'][0]['investigationId']

        # Now create the close event
        test_event = self.test_data_generator.generate_test_api_event(
            sub_override=DEFAULT_AA_SUBMITTING_USER_ID,
            scope_override=f'openid email {test_privilege_record.jurisdiction}/aslp.admin',
            value_overrides={
                'httpMethod': 'PATCH',
                'resource': PRIVILEGE_INVESTIGATION_ID_ENDPOINT_RESOURCE,
                'pathParameters': {
                    'compact': test_privilege_record.compact,
                    'providerId': str(test_privilege_record.providerId),
                    'jurisdiction': test_privilege_record.jurisdiction,
                    'licenseType': test_privilege_record.licenseTypeAbbreviation,
                    'investigationId': investigation_id,
                },
                'body': json.dumps(test_body),
            },
        )

        return test_event, test_privilege_record, investigation_id

    def test_privilege_investigation_close_handler_returns_ok_message_with_valid_body(self):
        from handlers.investigation import investigation_handler

        event = self._when_testing_privilege_investigation_close()[0]

        response = investigation_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))
        response_body = json.loads(response['body'])

        self.assertEqual(
            {'message': 'OK'},
            response_body,
        )

    def test_privilege_investigation_close_handler_updates_investigation_record(self):
        from handlers.investigation import investigation_handler

        event, test_privilege_record, investigation_id = self._when_testing_privilege_investigation_close()

        response = investigation_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))

        # Verify that the investigation record was updated
        investigation_record = self._provider_table.get_item(
            Key={
                'pk': test_privilege_record.serialize_to_database_record()['pk'],
                'sk': (
                    f'{test_privilege_record.compact}#PROVIDER#privilege/'
                    f'{test_privilege_record.jurisdiction}/slp#INVESTIGATION#{investigation_id}'
                ),
            }
        )['Item']

        expected_investigation = {
            'pk': test_privilege_record.serialize_to_database_record()['pk'],
            'sk': (
                f'{test_privilege_record.compact}#PROVIDER#privilege/'
                f'{test_privilege_record.jurisdiction}/slp#INVESTIGATION#{investigation_id}'
            ),
            'type': 'investigation',
            'compact': test_privilege_record.compact,
            'providerId': str(test_privilege_record.providerId),
            'jurisdiction': test_privilege_record.jurisdiction,
            'licenseType': test_privilege_record.licenseType,
            'investigationAgainst': 'privilege',
            'investigationId': investigation_id,
            'submittingUser': DEFAULT_AA_SUBMITTING_USER_ID,
            'creationDate': DEFAULT_DATE_OF_UPDATE_TIMESTAMP,
            'closeDate': DEFAULT_DATE_OF_UPDATE_TIMESTAMP,
            'closingUser': DEFAULT_AA_SUBMITTING_USER_ID,
            'dateOfUpdate': DEFAULT_DATE_OF_UPDATE_TIMESTAMP,
        }

        self.assertEqual(expected_investigation, investigation_record)

    def test_privilege_investigation_close_handler_removes_investigation_status_from_privilege(self):
        from handlers.investigation import investigation_handler
        from handlers.providers import get_provider

        event, test_privilege_record, investigation_id = self._when_testing_privilege_investigation_close()

        response = investigation_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))

        # Verify that the privilege record no longer has investigation status
        updated_privilege_record = self._provider_table.get_item(
            Key={
                'pk': test_privilege_record.serialize_to_database_record()['pk'],
                'sk': test_privilege_record.serialize_to_database_record()['sk'],
            }
        )['Item']

        self.assertNotIn('investigationStatus', updated_privilege_record)

        # Verify that investigation objects are removed from the API response
        api_event = self.test_data_generator.generate_test_api_event(
            scope_override=f'openid email {test_privilege_record.jurisdiction}/aslp.readGeneral',
            value_overrides={
                'httpMethod': 'GET',
                'resource': '/v1/compacts/{compact}/providers/{providerId}',
                'pathParameters': {
                    'compact': test_privilege_record.compact,
                    'providerId': str(test_privilege_record.providerId),
                },
            },
        )

        api_response = get_provider(api_event, self.mock_context)
        self.assertEqual(200, api_response['statusCode'])

        provider_data = json.loads(api_response['body'])

        # Verify that the privilege has no investigation objects
        privilege = provider_data['privileges'][0]
        expected_privilege = {
            'investigations': [],
        }

        self.assertEqual(expected_privilege['investigations'], privilege['investigations'])

    def test_privilege_investigation_close_with_encumbrance_creates_encumbrance(self):
        from handlers.investigation import investigation_handler

        event, test_privilege_record, investigation_id = self._when_testing_privilege_investigation_close(
            body_overrides=_generate_test_investigation_close_with_encumbrance_body()
        )

        response = investigation_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))

        # Verify that an encumbrance was created
        encumbrance_records = self._provider_table.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('pk').eq(test_privilege_record.serialize_to_database_record()['pk'])
            & Key('sk').begins_with(
                f'{test_privilege_record.compact}#PROVIDER#privilege/{test_privilege_record.jurisdiction}/slp#ADVERSE_ACTION'
            ),
        )
        self.assertEqual(1, len(encumbrance_records['Items']))

        # Verify that the investigation record has the resulting encumbrance ID
        investigation_record = self._provider_table.get_item(
            Key={
                'pk': test_privilege_record.serialize_to_database_record()['pk'],
                'sk': (
                    f'{test_privilege_record.compact}#PROVIDER#privilege/'
                    f'{test_privilege_record.jurisdiction}/slp#INVESTIGATION#{investigation_id}'
                ),
            }
        )['Item']

        self.assertIn('resultingEncumbranceId', investigation_record)

    @patch('cc_common.event_bus_client.EventBusClient._publish_event')
    def test_privilege_investigation_close_handler_publishes_event(self, mock_publish_event):
        """Test that privilege investigation close handler publishes the correct event."""
        from handlers.investigation import investigation_handler

        event, test_privilege_record, investigation_id = self._when_testing_privilege_investigation_close()

        response = investigation_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'])

        # Verify event was published with correct details (should be called twice: creation + closure)
        self.assertEqual(2, mock_publish_event.call_count)
        call_args = mock_publish_event.call_args[1]

        expected_event_args = {
            'source': 'org.compactconnect.provider-data',
            'detail_type': 'privilege.investigationClosed',
            'event_batch_writer': None,
            'detail': {
                'compact': test_privilege_record.compact,
                'providerId': str(test_privilege_record.providerId),
                'jurisdiction': test_privilege_record.jurisdiction,
                'licenseTypeAbbreviation': test_privilege_record.licenseTypeAbbreviation,
                'eventTime': DEFAULT_DATE_OF_UPDATE_TIMESTAMP,
                'investigationAgainst': 'privilege',
                'effectiveDate': '2024-11-08',  # Date portion of DEFAULT_DATE_OF_UPDATE_TIMESTAMP
            },
        }
        self.assertEqual(expected_event_args, call_args)


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat(DEFAULT_DATE_OF_UPDATE_TIMESTAMP))
class TestPatchLicenseInvestigationClose(TstFunction):
    """Test suite for license investigation close endpoints."""

    def _load_license_data(self):
        """Load license test data from JSON file"""
        import json
        from decimal import Decimal

        # Load provider record first (needed for encumbrance creation)
        with open('../common/tests/resources/dynamo/provider.json') as f:
            provider_record = json.load(f, parse_float=Decimal)
        self._provider_table.put_item(Item=provider_record)

        # Load license record
        with open('../common/tests/resources/dynamo/license.json') as f:
            license_record = json.load(f, parse_float=Decimal)
        self._provider_table.put_item(Item=license_record)

        # Return the license data as a data class
        from cc_common.data_model.schema.license import LicenseData

        return LicenseData.from_database_record(license_record)

    def _when_testing_license_investigation_close(self, body_overrides: dict | None = None):
        test_license_record = self._load_license_data()
        test_body = {}
        if body_overrides:
            test_body.update(body_overrides)

        # First create an investigation
        create_event = self.test_data_generator.generate_test_api_event(
            sub_override=DEFAULT_AA_SUBMITTING_USER_ID,
            scope_override=f'openid email {test_license_record.jurisdiction}/aslp.admin',
            value_overrides={
                'httpMethod': 'POST',
                'resource': LICENSE_INVESTIGATION_ENDPOINT_RESOURCE,
                'pathParameters': {
                    'compact': test_license_record.compact,
                    'providerId': str(test_license_record.providerId),
                    'jurisdiction': test_license_record.jurisdiction,
                    'licenseType': test_license_record.licenseTypeAbbreviation,
                },
            },
        )

        from handlers.investigation import investigation_handler

        investigation_handler(create_event, self.mock_context)

        # Get the investigation ID from the database
        investigation_records = self._provider_table.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('pk').eq(test_license_record.serialize_to_database_record()['pk'])
            & Key('sk').begins_with(
                f'{test_license_record.compact}#PROVIDER#license/{test_license_record.jurisdiction}/slp#INVESTIGATION'
            ),
        )
        investigation_id = investigation_records['Items'][0]['investigationId']

        # Now create the close event
        test_event = self.test_data_generator.generate_test_api_event(
            sub_override=DEFAULT_AA_SUBMITTING_USER_ID,
            scope_override=f'openid email {test_license_record.jurisdiction}/aslp.admin',
            value_overrides={
                'httpMethod': 'PATCH',
                'resource': LICENSE_INVESTIGATION_ID_ENDPOINT_RESOURCE,
                'pathParameters': {
                    'compact': test_license_record.compact,
                    'providerId': str(test_license_record.providerId),
                    'jurisdiction': test_license_record.jurisdiction,
                    'licenseType': test_license_record.licenseTypeAbbreviation,
                    'investigationId': investigation_id,
                },
                'body': json.dumps(test_body),
            },
        )

        return test_event, test_license_record, investigation_id

    def test_license_investigation_close_handler_returns_ok_message_with_valid_body(self):
        from handlers.investigation import investigation_handler

        event = self._when_testing_license_investigation_close()[0]

        response = investigation_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))
        response_body = json.loads(response['body'])

        self.assertEqual(
            {'message': 'OK'},
            response_body,
        )

    def test_license_investigation_close_handler_updates_investigation_record(self):
        from handlers.investigation import investigation_handler

        event, test_license_record, investigation_id = self._when_testing_license_investigation_close()

        response = investigation_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))

        # Verify that the investigation record was updated
        investigation_record = self._provider_table.get_item(
            Key={
                'pk': test_license_record.serialize_to_database_record()['pk'],
                'sk': (
                    f'{test_license_record.compact}#PROVIDER#license/'
                    f'{test_license_record.jurisdiction}/slp#INVESTIGATION#{investigation_id}'
                ),
            }
        )['Item']

        expected_investigation = {
            'pk': test_license_record.serialize_to_database_record()['pk'],
            'sk': (
                f'{test_license_record.compact}#PROVIDER#license/'
                f'{test_license_record.jurisdiction}/slp#INVESTIGATION#{investigation_id}'
            ),
            'type': 'investigation',
            'compact': test_license_record.compact,
            'providerId': str(test_license_record.providerId),
            'jurisdiction': test_license_record.jurisdiction,
            'licenseType': test_license_record.licenseType,
            'investigationAgainst': 'license',
            'investigationId': investigation_id,
            'submittingUser': DEFAULT_AA_SUBMITTING_USER_ID,
            'creationDate': DEFAULT_DATE_OF_UPDATE_TIMESTAMP,
            'closeDate': DEFAULT_DATE_OF_UPDATE_TIMESTAMP,
            'closingUser': DEFAULT_AA_SUBMITTING_USER_ID,
            'dateOfUpdate': DEFAULT_DATE_OF_UPDATE_TIMESTAMP,
        }

        self.assertEqual(expected_investigation, investigation_record)

    def test_license_investigation_close_handler_removes_investigation_status_from_license(self):
        from handlers.investigation import investigation_handler
        from handlers.providers import get_provider

        event, test_license_record, investigation_id = self._when_testing_license_investigation_close()

        response = investigation_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))

        # Verify that the license record no longer has investigation status
        updated_license_record = self._provider_table.get_item(
            Key={
                'pk': test_license_record.serialize_to_database_record()['pk'],
                'sk': test_license_record.serialize_to_database_record()['sk'],
            }
        )['Item']

        self.assertNotIn('investigationStatus', updated_license_record)

        # Verify that investigation objects are removed from the API response
        api_event = self.test_data_generator.generate_test_api_event(
            scope_override=f'openid email {test_license_record.jurisdiction}/aslp.readGeneral',
            value_overrides={
                'httpMethod': 'GET',
                'resource': '/v1/compacts/{compact}/providers/{providerId}',
                'pathParameters': {
                    'compact': test_license_record.compact,
                    'providerId': str(test_license_record.providerId),
                },
            },
        )

        api_response = get_provider(api_event, self.mock_context)
        self.assertEqual(200, api_response['statusCode'])

        provider_data = json.loads(api_response['body'])

        # Verify that the license has no investigation objects
        license_obj = provider_data['licenses'][0]
        expected_license = {
            'investigations': [],
        }

        self.assertEqual(expected_license['investigations'], license_obj['investigations'])

    def test_license_investigation_close_with_encumbrance_creates_encumbrance(self):
        from handlers.investigation import investigation_handler

        event, test_license_record, investigation_id = self._when_testing_license_investigation_close(
            body_overrides=_generate_test_investigation_close_with_encumbrance_body()
        )

        response = investigation_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))

        # Verify that an encumbrance was created
        encumbrance_records = self._provider_table.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('pk').eq(test_license_record.serialize_to_database_record()['pk'])
            & Key('sk').begins_with(
                f'{test_license_record.compact}#PROVIDER#license/{test_license_record.jurisdiction}/slp#ADVERSE_ACTION'
            ),
        )
        self.assertEqual(1, len(encumbrance_records['Items']))

        # Verify that the investigation record has the resulting encumbrance ID
        investigation_record = self._provider_table.get_item(
            Key={
                'pk': test_license_record.serialize_to_database_record()['pk'],
                'sk': (
                    f'{test_license_record.compact}#PROVIDER#license/'
                    f'{test_license_record.jurisdiction}/slp#INVESTIGATION#{investigation_id}'
                ),
            }
        )['Item']

        self.assertIn('resultingEncumbranceId', investigation_record)

    @patch('cc_common.event_bus_client.EventBusClient._publish_event')
    def test_license_investigation_close_handler_publishes_event(self, mock_publish_event):
        """Test that license investigation close handler publishes the correct event."""
        from handlers.investigation import investigation_handler

        event, test_license_record, investigation_id = self._when_testing_license_investigation_close()

        response = investigation_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'])

        # Verify event was published with correct details (should be called twice: creation + closure)
        self.assertEqual(2, mock_publish_event.call_count)
        call_args = mock_publish_event.call_args[1]

        expected_event_args = {
            'source': 'org.compactconnect.provider-data',
            'detail_type': 'license.investigationClosed',
            'event_batch_writer': None,
            'detail': {
                'compact': test_license_record.compact,
                'providerId': str(test_license_record.providerId),
                'jurisdiction': test_license_record.jurisdiction,
                'licenseTypeAbbreviation': test_license_record.licenseTypeAbbreviation,
                'eventTime': DEFAULT_DATE_OF_UPDATE_TIMESTAMP,
                'investigationAgainst': 'license',
                'effectiveDate': '2024-11-08',  # Date portion of DEFAULT_DATE_OF_UPDATE_TIMESTAMP
            },
        }
        self.assertEqual(expected_event_args, call_args)
