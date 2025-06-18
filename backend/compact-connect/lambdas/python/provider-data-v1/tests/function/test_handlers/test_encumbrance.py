import json
from datetime import UTC, date, datetime, timedelta
from unittest.mock import patch

from boto3.dynamodb.conditions import Key
from cc_common.exceptions import CCInternalException
from common_test.test_constants import (
    DEFAULT_AA_SUBMITTING_USER_ID,
    DEFAULT_DATE_OF_UPDATE_TIMESTAMP,
    DEFAULT_LICENSE_JURISDICTION,
    DEFAULT_LICENSE_TYPE_ABBREVIATION,
    DEFAULT_PRIVILEGE_JURISDICTION,
)
from moto import mock_aws

from .. import TstFunction

PRIVILEGE_ENCUMBRANCE_ENDPOINT_RESOURCE = (
    '/v1/compacts/{compact}/providers/{providerId}/privileges/'
    'jurisdiction/{jurisdiction}/licenseType/{licenseType}/encumbrance'
)
LICENSE_ENCUMBRANCE_ENDPOINT_RESOURCE = (
    '/v1/compacts/{compact}/providers/{providerId}/licenses/'
    'jurisdiction/{jurisdiction}/licenseType/{licenseType}/encumbrance'
)
PRIVILEGE_ENCUMBRANCE_ID_ENDPOINT_RESOURCE = (
    '/v1/compacts/{compact}/providers/{providerId}/privileges/'
    'jurisdiction/{jurisdiction}/licenseType/{licenseType}/encumbrance/{encumbranceId}'
)
LICENSE_ENCUMBRANCE_ID_ENDPOINT_RESOURCE = (
    '/v1/compacts/{compact}/providers/{providerId}/licenses/'
    'jurisdiction/{jurisdiction}/licenseType/{licenseType}/encumbrance/{encumbranceId}'
)

TEST_ENCUMBRANCE_EFFECTIVE_DATE = '2023-01-15'


def _generate_test_body():
    from cc_common.data_model.schema.common import ClinicalPrivilegeActionCategory

    return {
        'encumbranceEffectiveDate': TEST_ENCUMBRANCE_EFFECTIVE_DATE,
        'clinicalPrivilegeActionCategory': ClinicalPrivilegeActionCategory.UNSAFE_PRACTICE,
    }


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat(DEFAULT_DATE_OF_UPDATE_TIMESTAMP))
class TestPostPrivilegeEncumbrance(TstFunction):
    """Test suite for privilege encumbrance endpoints."""

    def _when_testing_privilege_encumbrance(self, body_overrides: dict | None = None):
        self.test_data_generator.put_default_provider_record_in_provider_table()
        test_privilege_record = self.test_data_generator.put_default_privilege_record_in_provider_table()

        body = _generate_test_body()
        if body_overrides:
            body.update(body_overrides)

        test_event = self.test_data_generator.generate_test_api_event(
            sub_override=DEFAULT_AA_SUBMITTING_USER_ID,
            scope_override=f'openid email {test_privilege_record.jurisdiction}/aslp.admin',
            value_overrides={
                'httpMethod': 'POST',
                'resource': PRIVILEGE_ENCUMBRANCE_ENDPOINT_RESOURCE,
                'pathParameters': {
                    'compact': test_privilege_record.compact,
                    'providerId': test_privilege_record.providerId,
                    'jurisdiction': test_privilege_record.jurisdiction,
                    'licenseType': self.test_data_generator.get_license_type_abbr_for_license_type(
                        compact=test_privilege_record.compact, license_type=test_privilege_record.licenseType
                    ),
                },
                'body': json.dumps(body),
            },
        )
        # return both the test event and the test privilege record
        return test_event, test_privilege_record

    def test_privilege_encumbrance_handler_returns_ok_message_with_valid_body(self):
        from handlers.encumbrance import encumbrance_handler

        event = self._when_testing_privilege_encumbrance()[0]

        response = encumbrance_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))
        response_body = json.loads(response['body'])

        self.assertEqual(
            {'message': 'OK'},
            response_body,
        )

    def test_privilege_encumbrance_handler_adds_adverse_action_record_in_provider_data_table(self):
        from cc_common.data_model.schema.adverse_action import AdverseActionData
        from handlers.encumbrance import encumbrance_handler

        event, test_privilege_record = self._when_testing_privilege_encumbrance()

        response = encumbrance_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))

        # Verify that the encumbrance record was added to the provider data table
        # Perform a query to list all encumbrances for the provider using the starts_with key condition
        adverse_action_encumbrances = self._provider_table.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('pk').eq(test_privilege_record.serialize_to_database_record()['pk'])
            & Key('sk').begins_with(
                f'{test_privilege_record.compact}#PROVIDER#privilege/{test_privilege_record.jurisdiction}/slp#ADVERSE_ACTION'
            ),
        )
        self.assertEqual(1, len(adverse_action_encumbrances['Items']))
        item = adverse_action_encumbrances['Items'][0]

        default_adverse_action_encumbrance = self.test_data_generator.generate_default_adverse_action(
            value_overrides={
                'adverseActionId': item['adverseActionId'],
                'effectiveStartDate': date.fromisoformat(TEST_ENCUMBRANCE_EFFECTIVE_DATE),
                'jurisdiction': DEFAULT_PRIVILEGE_JURISDICTION,
            }
        )
        loaded_adverse_action = AdverseActionData.from_database_record(item)

        self.assertEqual(
            default_adverse_action_encumbrance.to_dict(),
            loaded_adverse_action.to_dict(),
        )

    def test_privilege_encumbrance_handler_adds_privilege_update_record_in_provider_data_table(self):
        from cc_common.data_model.schema.privilege import PrivilegeUpdateData
        from handlers.encumbrance import encumbrance_handler

        event, test_privilege_record = self._when_testing_privilege_encumbrance()

        response = encumbrance_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))

        # Verify that the encumbrance record was added to the provider data table
        # Perform a query to list all encumbrances for the provider using the starts_with key condition
        privilege_update_records = self._provider_table.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('pk').eq(test_privilege_record.serialize_to_database_record()['pk'])
            & Key('sk').begins_with(
                f'{test_privilege_record.compact}#PROVIDER#privilege/{test_privilege_record.jurisdiction}/slp#UPDATE'
            ),
        )
        self.assertEqual(1, len(privilege_update_records['Items']))
        item = privilege_update_records['Items'][0]

        expected_privilege_update_data = self.test_data_generator.generate_default_privilege_update(
            value_overrides={
                'updateType': 'encumbrance',
                'updatedValues': {'encumberedStatus': 'encumbered'},
            }
        )
        loaded_privilege_update_data = PrivilegeUpdateData.from_database_record(item)

        self.assertEqual(
            expected_privilege_update_data.to_dict(),
            loaded_privilege_update_data.to_dict(),
        )
        self.assertEqual({'encumberedStatus': 'encumbered'}, loaded_privilege_update_data.updatedValues)

    def test_privilege_encumbrance_handler_sets_privilege_record_to_inactive_in_provider_data_table(self):
        from cc_common.data_model.schema.common import PrivilegeEncumberedStatusEnum
        from cc_common.data_model.schema.privilege import PrivilegeData
        from handlers.encumbrance import encumbrance_handler

        event, test_privilege_record = self._when_testing_privilege_encumbrance()

        response = encumbrance_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))

        # Verify that the encumbrance record was added to the provider data table
        # Perform a query to get the privilege that matches the expected pk/sk
        privilege_serialized_record = test_privilege_record.serialize_to_database_record()
        privilege_records = self._provider_table.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('pk').eq(privilege_serialized_record['pk'])
            & Key('sk').eq(privilege_serialized_record['sk']),
        )
        self.assertEqual(1, len(privilege_records['Items']))
        item = privilege_records['Items'][0]

        expected_privilege_data = self.test_data_generator.generate_default_privilege(
            value_overrides={'dateOfUpdate': DEFAULT_DATE_OF_UPDATE_TIMESTAMP, 'encumberedStatus': 'encumbered'}
        )
        loaded_privilege_data = PrivilegeData.from_database_record(item)

        self.assertEqual(PrivilegeEncumberedStatusEnum.ENCUMBERED, loaded_privilege_data.encumberedStatus)

        self.assertEqual(
            expected_privilege_data.to_dict(),
            loaded_privilege_data.to_dict(),
        )

    def test_privilege_encumbrance_handler_sets_provider_record_to_encumbered_in_provider_data_table(self):
        from cc_common.data_model.schema.common import LicenseEncumberedStatusEnum
        from cc_common.data_model.schema.provider import ProviderData
        from handlers.encumbrance import encumbrance_handler

        event, test_privilege_record = self._when_testing_privilege_encumbrance()
        test_provider_record = self.test_data_generator.generate_default_provider()

        response = encumbrance_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))

        # Verify that the encumbrance status was added to the provider record
        provider_serialized_record = test_provider_record.serialize_to_database_record()
        provider_records = self._provider_table.get_item(
            Key={'pk': provider_serialized_record['pk'], 'sk': provider_serialized_record['sk']}
        )
        item = provider_records['Item']

        expected_provider_data = self.test_data_generator.generate_default_provider(
            value_overrides={'dateOfUpdate': DEFAULT_DATE_OF_UPDATE_TIMESTAMP, 'encumberedStatus': 'encumbered'}
        )
        loaded_provider_data = ProviderData.from_database_record(item)

        self.assertEqual(LicenseEncumberedStatusEnum.ENCUMBERED, loaded_provider_data.encumberedStatus)

        self.assertEqual(
            expected_provider_data.to_dict(),
            loaded_provider_data.to_dict(),
        )

    def test_privilege_encumbrance_handler_returns_access_denied_if_compact_admin(self):
        from handlers.encumbrance import encumbrance_handler

        event, test_privilege_record = self._when_testing_privilege_encumbrance()

        event['requestContext']['authorizer']['claims']['scope'] = f'openid email {test_privilege_record.compact}/admin'

        response = encumbrance_handler(event, self.mock_context)
        self.assertEqual(403, response['statusCode'], msg=json.loads(response['body']))
        response_body = json.loads(response['body'])

        self.assertEqual(
            {'message': 'Access denied'},
            response_body,
        )

    def test_privilege_encumbrance_handler_returns_400_if_encumbrance_date_in_future(self):
        """Verifying that encumbrance dates cannot be set in the future"""
        from handlers.encumbrance import encumbrance_handler

        future_date = (datetime.now(tz=UTC) + timedelta(days=2)).strftime('%Y-%m-%d')
        event, test_privilege_record = self._when_testing_privilege_encumbrance(
            body_overrides={'encumbranceEffectiveDate': future_date}
        )

        response = encumbrance_handler(event, self.mock_context)
        self.assertEqual(400, response['statusCode'], msg=json.loads(response['body']))
        response_body = json.loads(response['body'])

        self.assertEqual(
            {'message': 'The encumbrance date must not be a future date'},
            response_body,
        )

    @patch('cc_common.event_bus_client.EventBusClient._publish_event')
    def test_privilege_encumbrance_handler_publishes_event(self, mock_publish_event):
        """Test that privilege encumbrance handler publishes the correct event."""
        from handlers.encumbrance import encumbrance_handler

        event, test_privilege_record = self._when_testing_privilege_encumbrance()

        response = encumbrance_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'])

        # Verify event was published with correct details
        mock_publish_event.assert_called_once()
        call_args = mock_publish_event.call_args[1]
        self.assertEqual('org.compactconnect.provider-data', call_args['source'])
        self.assertEqual('privilege.encumbrance', call_args['detail_type'])
        self.assertEqual(test_privilege_record.compact, call_args['detail']['compact'])
        self.assertEqual(str(test_privilege_record.providerId), call_args['detail']['providerId'])
        self.assertEqual(test_privilege_record.jurisdiction, call_args['detail']['jurisdiction'])
        self.assertEqual(test_privilege_record.licenseTypeAbbreviation, call_args['detail']['licenseTypeAbbreviation'])
        self.assertEqual(DEFAULT_DATE_OF_UPDATE_TIMESTAMP, call_args['detail']['eventTime'])

    @patch('cc_common.event_bus_client.EventBusClient._publish_event')
    def test_privilege_encumbrance_handler_handles_event_publishing_failure(self, mock_publish_event):
        """Test that privilege encumbrance handler fails when event publishing fails."""
        from handlers.encumbrance import encumbrance_handler

        event, _ = self._when_testing_privilege_encumbrance()
        mock_publish_event.side_effect = Exception('Event publishing failed')

        with self.assertRaises(Exception) as context:
            encumbrance_handler(event, self.mock_context)
        self.assertEqual('Event publishing failed', str(context.exception))


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat(DEFAULT_DATE_OF_UPDATE_TIMESTAMP))
class TestPostLicenseEncumbrance(TstFunction):
    """Test suite for license encumbrance endpoints."""

    def _when_testing_valid_license_encumbrance(self, body_overrides: dict | None = None):
        self.test_data_generator.put_default_provider_record_in_provider_table()
        test_license_record = self.test_data_generator.put_default_license_record_in_provider_table()

        body = _generate_test_body()
        if body_overrides:
            body.update(body_overrides)

        test_event = self.test_data_generator.generate_test_api_event(
            sub_override=DEFAULT_AA_SUBMITTING_USER_ID,
            scope_override=f'openid email {test_license_record.jurisdiction}/aslp.admin',
            value_overrides={
                'httpMethod': 'POST',
                'resource': LICENSE_ENCUMBRANCE_ENDPOINT_RESOURCE,
                'pathParameters': {
                    'compact': test_license_record.compact,
                    'providerId': test_license_record.providerId,
                    'jurisdiction': test_license_record.jurisdiction,
                    'licenseType': self.test_data_generator.get_license_type_abbr_for_license_type(
                        compact=test_license_record.compact, license_type=test_license_record.licenseType
                    ),
                },
                'body': json.dumps(body),
            },
        )

        # return both the event and test license record
        return test_event, test_license_record

    def test_license_encumbrance_handler_returns_ok_message_with_valid_body(self):
        from handlers.encumbrance import encumbrance_handler

        event = self._when_testing_valid_license_encumbrance()[0]

        response = encumbrance_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))
        response_body = json.loads(response['body'])

        self.assertEqual(
            {'message': 'OK'},
            response_body,
        )

    def test_license_encumbrance_handler_adds_adverse_action_record_in_provider_data_table(self):
        from cc_common.data_model.schema.adverse_action import AdverseActionData
        from handlers.encumbrance import encumbrance_handler

        event, test_license_record = self._when_testing_valid_license_encumbrance()

        response = encumbrance_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))

        # Verify that the encumbrance record was added to the provider data table
        # Perform a query to list all encumbrances for the provider using the starts_with key condition
        adverse_action_encumbrances = self._provider_table.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('pk').eq(test_license_record.serialize_to_database_record()['pk'])
            & Key('sk').begins_with(
                f'{test_license_record.compact}#PROVIDER#license/{test_license_record.jurisdiction}/slp#ADVERSE_ACTION'
            ),
        )
        self.assertEqual(1, len(adverse_action_encumbrances['Items']))
        item = adverse_action_encumbrances['Items'][0]

        expected_adverse_action_encumbrance = self.test_data_generator.generate_default_adverse_action(
            value_overrides={
                'actionAgainst': 'license',
                'adverseActionId': item['adverseActionId'],
                'effectiveStartDate': date.fromisoformat(TEST_ENCUMBRANCE_EFFECTIVE_DATE),
                'jurisdiction': DEFAULT_LICENSE_JURISDICTION,
            }
        )
        loaded_adverse_action = AdverseActionData.from_database_record(item)

        self.assertEqual(
            expected_adverse_action_encumbrance.to_dict(),
            loaded_adverse_action.to_dict(),
        )

    def test_license_encumbrance_handler_adds_license_update_record_in_provider_data_table(self):
        from cc_common.data_model.schema.license import LicenseUpdateData
        from handlers.encumbrance import encumbrance_handler

        event, test_license_record = self._when_testing_valid_license_encumbrance()

        response = encumbrance_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))

        # Verify that the update record was added for the license
        license_update_records = self._provider_table.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('pk').eq(test_license_record.serialize_to_database_record()['pk'])
            & Key('sk').begins_with(
                f'{test_license_record.compact}#PROVIDER#license/{test_license_record.jurisdiction}/slp#UPDATE'
            ),
        )
        self.assertEqual(1, len(license_update_records['Items']))
        item = license_update_records['Items'][0]

        expected_license_update_data = self.test_data_generator.generate_default_license_update(
            value_overrides={
                'updateType': 'encumbrance',
                'updatedValues': {'encumberedStatus': 'encumbered'},
            }
        )
        loaded_license_update_data = LicenseUpdateData.from_database_record(item)

        self.assertEqual(
            expected_license_update_data.to_dict(),
            loaded_license_update_data.to_dict(),
        )

    def test_license_encumbrance_handler_sets_license_record_to_encumbered_in_provider_data_table(self):
        from cc_common.data_model.schema.common import LicenseEncumberedStatusEnum
        from cc_common.data_model.schema.license import LicenseData
        from handlers.encumbrance import encumbrance_handler

        event, test_license_record = self._when_testing_valid_license_encumbrance()

        response = encumbrance_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))

        # Verify that the encumbrance status was added to the license record
        license_serialized_record = test_license_record.serialize_to_database_record()
        license_records = self._provider_table.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('pk').eq(license_serialized_record['pk'])
            & Key('sk').eq(license_serialized_record['sk']),
        )
        self.assertEqual(1, len(license_records['Items']))
        item = license_records['Items'][0]

        expected_license_data = self.test_data_generator.generate_default_license(
            value_overrides={'dateOfUpdate': DEFAULT_DATE_OF_UPDATE_TIMESTAMP, 'encumberedStatus': 'encumbered'}
        )
        loaded_license_data = LicenseData.from_database_record(item)

        self.assertEqual(LicenseEncumberedStatusEnum.ENCUMBERED, loaded_license_data.encumberedStatus)

        self.assertEqual(
            expected_license_data.to_dict(),
            loaded_license_data.to_dict(),
        )

    def test_license_encumbrance_handler_sets_provider_record_to_encumbered_in_provider_data_table(self):
        from cc_common.data_model.schema.common import LicenseEncumberedStatusEnum
        from cc_common.data_model.schema.provider import ProviderData
        from handlers.encumbrance import encumbrance_handler

        event, test_license_record = self._when_testing_valid_license_encumbrance()
        test_provider_record = self.test_data_generator.generate_default_provider()

        response = encumbrance_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))

        # Verify that the encumbrance status was added to the provider record
        provider_serialized_record = test_provider_record.serialize_to_database_record()
        provider_records = self._provider_table.get_item(
            Key={'pk': provider_serialized_record['pk'], 'sk': provider_serialized_record['sk']}
        )
        item = provider_records['Item']

        expected_provider_data = self.test_data_generator.generate_default_provider(
            value_overrides={'dateOfUpdate': DEFAULT_DATE_OF_UPDATE_TIMESTAMP, 'encumberedStatus': 'encumbered'}
        )
        loaded_provider_data = ProviderData.from_database_record(item)

        self.assertEqual(LicenseEncumberedStatusEnum.ENCUMBERED, loaded_provider_data.encumberedStatus)

        self.assertEqual(
            expected_provider_data.to_dict(),
            loaded_provider_data.to_dict(),
        )

    def test_license_encumbrance_handler_returns_access_denied_if_compact_admin(self):
        """Verifying that only state admins are allowed to encumber licenses"""
        from handlers.encumbrance import encumbrance_handler

        event, test_license_record = self._when_testing_valid_license_encumbrance()

        event['requestContext']['authorizer']['claims']['scope'] = f'openid email {test_license_record.compact}/admin'

        response = encumbrance_handler(event, self.mock_context)
        self.assertEqual(403, response['statusCode'], msg=json.loads(response['body']))
        response_body = json.loads(response['body'])

        self.assertEqual(
            {'message': 'Access denied'},
            response_body,
        )

    def test_license_encumbrance_handler_returns_400_if_encumbrance_date_in_future(self):
        """Verifying that license encumbrances cannot have future effective dates"""
        from handlers.encumbrance import encumbrance_handler

        future_date = (datetime.now(tz=UTC) + timedelta(days=2)).strftime('%Y-%m-%d')

        event, test_license_record = self._when_testing_valid_license_encumbrance(
            body_overrides={'encumbranceEffectiveDate': future_date}
        )

        response = encumbrance_handler(event, self.mock_context)
        self.assertEqual(400, response['statusCode'], msg=json.loads(response['body']))
        response_body = json.loads(response['body'])

        self.assertEqual(
            {'message': 'The encumbrance date must not be a future date'},
            response_body,
        )


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat(DEFAULT_DATE_OF_UPDATE_TIMESTAMP))
class TestPatchPrivilegeEncumbranceLifting(TstFunction):
    """Test suite for privilege encumbrance lifting endpoints."""

    def _setup_privilege_with_adverse_action(self, adverse_action_overrides=None, privilege_overrides=None):
        """Helper method to set up a privilege with an adverse action for testing."""
        self.test_data_generator.put_default_provider_record_in_provider_table(
            value_overrides={'encumberedStatus': 'encumbered'}
        )
        test_privilege_record = self.test_data_generator.put_default_privilege_record_in_provider_table(
            value_overrides=privilege_overrides or {'encumberedStatus': 'encumbered'}
        )
        test_adverse_action = self.test_data_generator.put_default_adverse_action_record_in_provider_table(
            value_overrides={
                'actionAgainst': 'privilege',
                'jurisdiction': test_privilege_record.jurisdiction,
                'licenseType': test_privilege_record.licenseType,
                **(adverse_action_overrides or {}),
            }
        )
        return test_privilege_record, test_adverse_action

    def _generate_lift_encumbrance_event(self, privilege_record, adverse_action, body_overrides=None):
        """Helper method to generate a test event for lifting privilege encumbrance."""
        body = {
            'effectiveLiftDate': '2024-01-15',
            **(body_overrides or {}),
        }

        return self.test_data_generator.generate_test_api_event(
            sub_override=DEFAULT_AA_SUBMITTING_USER_ID,
            scope_override=f'openid email {privilege_record.jurisdiction}/aslp.admin',
            value_overrides={
                'httpMethod': 'PATCH',
                'resource': PRIVILEGE_ENCUMBRANCE_ID_ENDPOINT_RESOURCE,
                'pathParameters': {
                    'compact': privilege_record.compact,
                    'providerId': str(privilege_record.providerId),
                    'jurisdiction': privilege_record.jurisdiction,
                    'licenseType': DEFAULT_LICENSE_TYPE_ABBREVIATION,
                    'encumbranceId': str(adverse_action.adverseActionId),
                },
                'body': json.dumps(body),
            },
        )

    def test_should_raise_cc_invalid_exception_if_lift_date_in_future(self):
        from handlers.encumbrance import encumbrance_handler

        privilege_record, adverse_action = self._setup_privilege_with_adverse_action()

        # Set lift date to future
        future_date = (datetime.now(UTC) + timedelta(days=2)).strftime('%Y-%m-%d')
        event = self._generate_lift_encumbrance_event(
            privilege_record, adverse_action, body_overrides={'effectiveLiftDate': future_date}
        )

        response = encumbrance_handler(event, self.mock_context)
        self.assertEqual(400, response['statusCode'])
        response_body = json.loads(response['body'])
        self.assertIn('future date', response_body['message'])

    def test_should_raise_cc_invalid_exception_if_lift_date_is_invalid_date(self):
        from handlers.encumbrance import encumbrance_handler

        privilege_record, adverse_action = self._setup_privilege_with_adverse_action()

        event = self._generate_lift_encumbrance_event(
            privilege_record, adverse_action, body_overrides={'effectiveLiftDate': 'invalid-date'}
        )

        response = encumbrance_handler(event, self.mock_context)
        self.assertEqual(400, response['statusCode'])
        response_body = json.loads(response['body'])
        self.assertEqual("Invalid request body: {'effectiveLiftDate': ['Not a valid date.']}", response_body['message'])

    def test_should_raise_cc_not_found_exception_if_adverse_action_not_found(self):
        from handlers.encumbrance import encumbrance_handler

        privilege_record, _ = self._setup_privilege_with_adverse_action()

        # Use a non-existent adverse action ID
        event = self._generate_lift_encumbrance_event(
            privilege_record, type('MockAdverseAction', (), {'adverseActionId': 'non-existent-id'})()
        )

        response = encumbrance_handler(event, self.mock_context)
        self.assertEqual(404, response['statusCode'])
        response_body = json.loads(response['body'])
        self.assertIn('Encumbrance record not found', response_body['message'])

    def test_should_raise_cc_invalid_exception_if_adverse_action_is_already_lifted(self):
        from handlers.encumbrance import encumbrance_handler

        privilege_record, adverse_action = self._setup_privilege_with_adverse_action(
            adverse_action_overrides={'effectiveLiftDate': date(2024, 1, 10)}
        )

        event = self._generate_lift_encumbrance_event(privilege_record, adverse_action)

        response = encumbrance_handler(event, self.mock_context)
        self.assertEqual(400, response['statusCode'])
        response_body = json.loads(response['body'])
        self.assertIn('already been lifted', response_body['message'])

    def test_should_return_ok_message_if_successful(self):
        from handlers.encumbrance import encumbrance_handler

        privilege_record, adverse_action = self._setup_privilege_with_adverse_action()
        event = self._generate_lift_encumbrance_event(privilege_record, adverse_action)

        response = encumbrance_handler(event, self.mock_context)

        self.assertEqual(200, response['statusCode'])
        response_body = json.loads(response['body'])
        self.assertEqual({'message': 'OK'}, response_body)

    def test_should_raise_cc_internal_exception_if_privilege_record_not_found(self):
        from handlers.encumbrance import encumbrance_handler

        # Set up adverse action without corresponding privilege record
        self.test_data_generator.put_default_provider_record_in_provider_table()
        adverse_action = self.test_data_generator.put_default_adverse_action_record_in_provider_table(
            value_overrides={'actionAgainst': 'privilege'}
        )

        event = self.test_data_generator.generate_test_api_event(
            sub_override=DEFAULT_AA_SUBMITTING_USER_ID,
            scope_override=f'openid email {adverse_action.jurisdiction}/aslp.admin',
            value_overrides={
                'httpMethod': 'PATCH',
                'resource': PRIVILEGE_ENCUMBRANCE_ID_ENDPOINT_RESOURCE,
                'pathParameters': {
                    'compact': adverse_action.compact,
                    'providerId': str(adverse_action.providerId),
                    'jurisdiction': adverse_action.jurisdiction,
                    'licenseType': adverse_action.licenseTypeAbbreviation,
                    'encumbranceId': str(adverse_action.adverseActionId),
                },
                'body': json.dumps(
                    {
                        'effectiveLiftDate': '2024-01-15',
                    }
                ),
            },
        )

        with self.assertRaises(CCInternalException) as context:
            encumbrance_handler(event, self.mock_context)

        self.assertIn('Privilege record not found', str(context.exception))

    def test_should_update_encumbrance_status_on_privilege_record_if_last_encumbrance_lifted(self):
        from cc_common.data_model.schema.common import PrivilegeEncumberedStatusEnum
        from handlers.encumbrance import encumbrance_handler

        privilege_record, adverse_action = self._setup_privilege_with_adverse_action(
            privilege_overrides={'encumberedStatus': 'encumbered'}
        )
        event = self._generate_lift_encumbrance_event(privilege_record, adverse_action)

        response = encumbrance_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'])

        # Verify privilege record is now unencumbered
        provider_records = self.config.data_client.get_provider_user_records(
            compact=privilege_record.compact, provider_id=str(privilege_record.providerId)
        )

        privilege_records = provider_records.get_privilege_records(
            filter_condition=lambda p: (
                p.jurisdiction == privilege_record.jurisdiction and p.licenseType == privilege_record.licenseType
            )
        )

        self.assertEqual(1, len(privilege_records))
        self.assertEqual(PrivilegeEncumberedStatusEnum.UNENCUMBERED, privilege_records[0].encumberedStatus)

    def test_should_update_adverse_action_to_set_lifted_fields_when_privilege_encumbrance_is_lifted(self):
        from handlers.encumbrance import encumbrance_handler

        privilege_record, adverse_action = self._setup_privilege_with_adverse_action()
        event = self._generate_lift_encumbrance_event(privilege_record, adverse_action)

        response = encumbrance_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'])

        # Verify adverse action has lift information
        provider_records = self.config.data_client.get_provider_user_records(
            compact=privilege_record.compact, provider_id=str(privilege_record.providerId)
        )

        adverse_actions = provider_records.get_adverse_action_records_for_privilege(
            privilege_jurisdiction=privilege_record.jurisdiction,
            privilege_license_type_abbreviation=adverse_action.licenseTypeAbbreviation,
        )

        self.assertEqual(1, len(adverse_actions))
        lifted_adverse_action = adverse_actions[0]
        self.assertEqual(date(2024, 1, 15), lifted_adverse_action.effectiveLiftDate)
        self.assertEqual(DEFAULT_AA_SUBMITTING_USER_ID, str(lifted_adverse_action.liftingUser))

    def test_should_update_provider_record_to_unencumbered_when_last_privilege_encumbrance_is_lifted(self):
        from cc_common.data_model.provider_record_util import ProviderUserRecords
        from cc_common.data_model.schema.common import LicenseEncumberedStatusEnum
        from handlers.encumbrance import encumbrance_handler

        privilege_record, adverse_action = self._setup_privilege_with_adverse_action(
            privilege_overrides={'encumberedStatus': 'encumbered'}
        )
        event = self._generate_lift_encumbrance_event(privilege_record, adverse_action)

        response = encumbrance_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'])

        # Verify provider record is now unencumbered
        provider_records: ProviderUserRecords = self.config.data_client.get_provider_user_records(
            compact=privilege_record.compact, provider_id=str(privilege_record.providerId)
        )

        loaded_provider_data = provider_records.get_provider_record()
        self.assertEqual(LicenseEncumberedStatusEnum.UNENCUMBERED, loaded_provider_data.encumberedStatus)

    def test_should_not_update_provider_record_when_other_privilege_encumbrances_exist(self):
        from cc_common.data_model.provider_record_util import ProviderUserRecords
        from cc_common.data_model.schema.common import LicenseEncumberedStatusEnum
        from handlers.encumbrance import encumbrance_handler

        # Set up first privilege with adverse action
        privilege_record, adverse_action = self._setup_privilege_with_adverse_action()

        # Set up second privilege with encumbered status (different jurisdiction)
        self.test_data_generator.put_default_privilege_record_in_provider_table(
            value_overrides={
                'encumberedStatus': 'encumbered',
                'jurisdiction': 'ky',  # Different jurisdiction
                'providerId': privilege_record.providerId,
                'compact': privilege_record.compact,
            }
        )

        event = self._generate_lift_encumbrance_event(privilege_record, adverse_action)

        response = encumbrance_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'])

        # Verify provider record remains encumbered
        provider_records: ProviderUserRecords = self.config.data_client.get_provider_user_records(
            compact=privilege_record.compact, provider_id=str(privilege_record.providerId)
        )

        loaded_provider_data = provider_records.get_provider_record()
        self.assertEqual(LicenseEncumberedStatusEnum.ENCUMBERED, loaded_provider_data.encumberedStatus)

    def test_should_not_update_provider_record_when_encumbered_license_exists(self):
        from cc_common.data_model.provider_record_util import ProviderUserRecords
        from cc_common.data_model.schema.common import LicenseEncumberedStatusEnum
        from handlers.encumbrance import encumbrance_handler

        # Set up privilege with adverse action
        privilege_record, adverse_action = self._setup_privilege_with_adverse_action()

        # Set up license with encumbered status
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'encumberedStatus': 'encumbered',
                'providerId': privilege_record.providerId,
                'compact': privilege_record.compact,
            }
        )

        event = self._generate_lift_encumbrance_event(privilege_record, adverse_action)

        response = encumbrance_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'])

        # Verify provider record remains encumbered
        provider_records: ProviderUserRecords = self.config.data_client.get_provider_user_records(
            compact=privilege_record.compact, provider_id=str(privilege_record.providerId)
        )

        loaded_provider_data = provider_records.get_provider_record()
        self.assertEqual(LicenseEncumberedStatusEnum.ENCUMBERED, loaded_provider_data.encumberedStatus)

    def test_should_return_access_denied_if_compact_admin_attempts_to_lift_privilege_encumbrance(self):
        """Verifying that only state admins are allowed to lift privilege encumbrances"""
        from handlers.encumbrance import encumbrance_handler

        privilege_record, adverse_action = self._setup_privilege_with_adverse_action()
        event = self._generate_lift_encumbrance_event(privilege_record, adverse_action)

        # Change scope to compact admin instead of state admin
        event['requestContext']['authorizer']['claims']['scope'] = f'openid email {privilege_record.compact}/admin'

        response = encumbrance_handler(event, self.mock_context)
        self.assertEqual(403, response['statusCode'])
        response_body = json.loads(response['body'])

        self.assertEqual(
            {'message': 'Access denied'},
            response_body,
        )

    @patch('cc_common.event_bus_client.EventBusClient._publish_event')
    def test_privilege_encumbrance_lifting_handler_publishes_event(self, mock_publish_event):
        """Test that privilege encumbrance lifting handler publishes the correct event."""
        from handlers.encumbrance import encumbrance_handler

        privilege_record, adverse_action = self._setup_privilege_with_adverse_action()
        event = self._generate_lift_encumbrance_event(privilege_record, adverse_action)

        response = encumbrance_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'])

        # Verify event was published with correct details
        mock_publish_event.assert_called_once()
        call_args = mock_publish_event.call_args[1]
        self.assertEqual('org.compactconnect.provider-data', call_args['source'])
        self.assertEqual('privilege.encumbranceLifted', call_args['detail_type'])
        self.assertEqual(privilege_record.compact, call_args['detail']['compact'])
        self.assertEqual(str(privilege_record.providerId), call_args['detail']['providerId'])
        self.assertEqual(privilege_record.jurisdiction, call_args['detail']['jurisdiction'])
        self.assertEqual(privilege_record.licenseTypeAbbreviation, call_args['detail']['licenseTypeAbbreviation'])
        self.assertEqual(DEFAULT_DATE_OF_UPDATE_TIMESTAMP, call_args['detail']['eventTime'])

    @patch('cc_common.event_bus_client.EventBusClient._publish_event')
    def test_privilege_encumbrance_lifting_handler_handles_event_publishing_failure(self, mock_publish_event):
        """Test that privilege encumbrance lifting handler fails when event publishing fails."""
        from handlers.encumbrance import encumbrance_handler

        privilege_record, adverse_action = self._setup_privilege_with_adverse_action()
        event = self._generate_lift_encumbrance_event(privilege_record, adverse_action)
        mock_publish_event.side_effect = Exception('Event publishing failed')

        with self.assertRaises(Exception) as context:
            encumbrance_handler(event, self.mock_context)
        self.assertEqual('Event publishing failed', str(context.exception))


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat(DEFAULT_DATE_OF_UPDATE_TIMESTAMP))
class TestPatchLicenseEncumbranceLifting(TstFunction):
    """Test suite for license encumbrance lifting endpoints."""

    def _setup_license_with_adverse_action(self, adverse_action_overrides=None, license_overrides=None):
        """Helper method to set up a license with an adverse action for testing."""
        self.test_data_generator.put_default_provider_record_in_provider_table(
            value_overrides={'encumberedStatus': 'encumbered'}
        )
        test_license_record = self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides=license_overrides or {'encumberedStatus': 'encumbered'}
        )
        test_adverse_action = self.test_data_generator.put_default_adverse_action_record_in_provider_table(
            value_overrides={
                'actionAgainst': 'license',
                'jurisdiction': test_license_record.jurisdiction,
                **(adverse_action_overrides or {}),
            }
        )
        return test_license_record, test_adverse_action

    def _generate_lift_encumbrance_event(self, license_record, adverse_action, body_overrides=None):
        """Helper method to generate a test event for lifting license encumbrance."""
        body = {
            'effectiveLiftDate': '2024-01-15',
            **(body_overrides or {}),
        }

        return self.test_data_generator.generate_test_api_event(
            sub_override=DEFAULT_AA_SUBMITTING_USER_ID,
            scope_override=f'openid email {license_record.jurisdiction}/aslp.admin',
            value_overrides={
                'httpMethod': 'PATCH',
                'resource': LICENSE_ENCUMBRANCE_ID_ENDPOINT_RESOURCE,
                'pathParameters': {
                    'compact': license_record.compact,
                    'providerId': str(license_record.providerId),
                    'jurisdiction': license_record.jurisdiction,
                    'licenseType': DEFAULT_LICENSE_TYPE_ABBREVIATION,
                    'encumbranceId': str(adverse_action.adverseActionId),
                },
                'body': json.dumps(body),
            },
        )

    def test_should_raise_cc_invalid_exception_if_lift_date_in_future(self):
        from handlers.encumbrance import encumbrance_handler

        license_record, adverse_action = self._setup_license_with_adverse_action()

        # Set lift date to future
        future_date = (datetime.now(tz=UTC) + timedelta(days=2)).strftime('%Y-%m-%d')
        event = self._generate_lift_encumbrance_event(
            license_record, adverse_action, body_overrides={'effectiveLiftDate': future_date}
        )

        response = encumbrance_handler(event, self.mock_context)
        self.assertEqual(400, response['statusCode'])
        response_body = json.loads(response['body'])
        self.assertIn('future date', response_body['message'])

    def test_should_raise_cc_invalid_exception_if_lift_date_is_invalid_date(self):
        from handlers.encumbrance import encumbrance_handler

        license_record, adverse_action = self._setup_license_with_adverse_action()

        event = self._generate_lift_encumbrance_event(
            license_record, adverse_action, body_overrides={'effectiveLiftDate': 'invalid-date'}
        )

        response = encumbrance_handler(event, self.mock_context)
        self.assertEqual(400, response['statusCode'])
        response_body = json.loads(response['body'])
        self.assertEqual("Invalid request body: {'effectiveLiftDate': ['Not a valid date.']}", response_body['message'])

    def test_should_raise_cc_not_found_exception_if_adverse_action_not_found(self):
        from handlers.encumbrance import encumbrance_handler

        license_record, _ = self._setup_license_with_adverse_action()

        # Use a non-existent adverse action ID
        event = self._generate_lift_encumbrance_event(
            license_record, type('MockAdverseAction', (), {'adverseActionId': 'non-existent-id'})()
        )

        response = encumbrance_handler(event, self.mock_context)
        self.assertEqual(404, response['statusCode'])
        response_body = json.loads(response['body'])
        self.assertIn('Encumbrance record not found', response_body['message'])

    def test_should_raise_cc_invalid_exception_if_adverse_action_is_already_lifted(self):
        from handlers.encumbrance import encumbrance_handler

        license_record, adverse_action = self._setup_license_with_adverse_action(
            adverse_action_overrides={'effectiveLiftDate': date(2024, 1, 10)}
        )

        event = self._generate_lift_encumbrance_event(license_record, adverse_action)

        response = encumbrance_handler(event, self.mock_context)
        self.assertEqual(400, response['statusCode'])
        response_body = json.loads(response['body'])
        self.assertIn('already been lifted', response_body['message'])

    def test_should_return_ok_message_if_successful(self):
        from handlers.encumbrance import encumbrance_handler

        license_record, adverse_action = self._setup_license_with_adverse_action()
        event = self._generate_lift_encumbrance_event(license_record, adverse_action)

        response = encumbrance_handler(event, self.mock_context)

        self.assertEqual(200, response['statusCode'])
        response_body = json.loads(response['body'])
        self.assertEqual({'message': 'OK'}, response_body)

    def test_should_raise_cc_internal_exception_if_license_record_not_found(self):
        from handlers.encumbrance import encumbrance_handler

        # Set up adverse action without corresponding license record
        self.test_data_generator.put_default_provider_record_in_provider_table()
        adverse_action = self.test_data_generator.put_default_adverse_action_record_in_provider_table(
            value_overrides={'actionAgainst': 'license'}
        )

        event = self.test_data_generator.generate_test_api_event(
            sub_override=DEFAULT_AA_SUBMITTING_USER_ID,
            scope_override=f'openid email {adverse_action.jurisdiction}/aslp.admin',
            value_overrides={
                'httpMethod': 'PATCH',
                'resource': LICENSE_ENCUMBRANCE_ID_ENDPOINT_RESOURCE,
                'pathParameters': {
                    'compact': adverse_action.compact,
                    'providerId': str(adverse_action.providerId),
                    'jurisdiction': adverse_action.jurisdiction,
                    'licenseType': adverse_action.licenseTypeAbbreviation,
                    'encumbranceId': str(adverse_action.adverseActionId),
                },
                'body': json.dumps(
                    {
                        'effectiveLiftDate': '2024-01-15',
                    }
                ),
            },
        )

        with self.assertRaises(CCInternalException) as context:
            encumbrance_handler(event, self.mock_context)

        self.assertIn('License record not found', str(context.exception))

    def test_should_update_encumbrance_status_on_license_record_if_last_encumbrance_lifted(self):
        from cc_common.data_model.schema.common import LicenseEncumberedStatusEnum
        from handlers.encumbrance import encumbrance_handler

        license_record, adverse_action = self._setup_license_with_adverse_action(
            license_overrides={'encumberedStatus': 'encumbered'}
        )
        event = self._generate_lift_encumbrance_event(license_record, adverse_action)

        response = encumbrance_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'])

        # Verify license record is now unencumbered
        provider_records = self.config.data_client.get_provider_user_records(
            compact=license_record.compact, provider_id=str(license_record.providerId)
        )

        license_records = provider_records.get_license_records(
            filter_condition=lambda record: (
                record.jurisdiction == license_record.jurisdiction and record.licenseType == license_record.licenseType
            )
        )

        self.assertEqual(1, len(license_records))
        self.assertEqual(LicenseEncumberedStatusEnum.UNENCUMBERED, license_records[0].encumberedStatus)

    def test_should_update_adverse_action_to_set_lifted_fields_when_license_encumbrance_is_lifted(self):
        from handlers.encumbrance import encumbrance_handler

        license_record, adverse_action = self._setup_license_with_adverse_action()
        event = self._generate_lift_encumbrance_event(license_record, adverse_action)

        response = encumbrance_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'])

        # Verify adverse action has lift information
        provider_records = self.config.data_client.get_provider_user_records(
            compact=license_record.compact, provider_id=str(license_record.providerId)
        )

        adverse_actions = provider_records.get_adverse_action_records_for_license(
            license_jurisdiction=license_record.jurisdiction,
            license_type_abbreviation=adverse_action.licenseTypeAbbreviation,
        )

        self.assertEqual(1, len(adverse_actions))
        lifted_adverse_action = adverse_actions[0]
        self.assertEqual(date(2024, 1, 15), lifted_adverse_action.effectiveLiftDate)
        self.assertEqual(DEFAULT_AA_SUBMITTING_USER_ID, str(lifted_adverse_action.liftingUser))

    def test_should_update_provider_record_to_unencumbered_when_last_license_encumbrance_is_lifted(self):
        from cc_common.data_model.provider_record_util import ProviderUserRecords
        from cc_common.data_model.schema.common import LicenseEncumberedStatusEnum
        from handlers.encumbrance import encumbrance_handler

        license_record, adverse_action = self._setup_license_with_adverse_action(
            license_overrides={'encumberedStatus': 'encumbered'}
        )
        event = self._generate_lift_encumbrance_event(license_record, adverse_action)

        response = encumbrance_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'])

        # Verify provider record is now unencumbered
        provider_records: ProviderUserRecords = self.config.data_client.get_provider_user_records(
            compact=license_record.compact, provider_id=str(license_record.providerId)
        )

        loaded_provider_data = provider_records.get_provider_record()
        self.assertEqual(LicenseEncumberedStatusEnum.UNENCUMBERED, loaded_provider_data.encumberedStatus)

    def test_should_not_update_provider_record_when_other_license_encumbrances_exist(self):
        from cc_common.data_model.provider_record_util import ProviderUserRecords
        from cc_common.data_model.schema.common import LicenseEncumberedStatusEnum
        from handlers.encumbrance import encumbrance_handler

        # Set up first license with adverse action
        license_record, adverse_action = self._setup_license_with_adverse_action()

        # Set up second license with encumbered status (different jurisdiction)
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'encumberedStatus': 'encumbered',
                'jurisdiction': 'ne',  # Different jurisdiction
                'providerId': license_record.providerId,
                'compact': license_record.compact,
            }
        )

        event = self._generate_lift_encumbrance_event(license_record, adverse_action)

        response = encumbrance_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'])

        # Verify provider record remains encumbered
        provider_records: ProviderUserRecords = self.config.data_client.get_provider_user_records(
            compact=license_record.compact, provider_id=str(license_record.providerId)
        )

        loaded_provider_data = provider_records.get_provider_record()
        self.assertEqual(LicenseEncumberedStatusEnum.ENCUMBERED, loaded_provider_data.encumberedStatus)

    def test_should_not_update_provider_record_when_encumbered_privilege_exists(self):
        from cc_common.data_model.provider_record_util import ProviderUserRecords
        from cc_common.data_model.schema.common import LicenseEncumberedStatusEnum
        from handlers.encumbrance import encumbrance_handler

        # Set up license with adverse action
        license_record, adverse_action = self._setup_license_with_adverse_action()

        # Set up privilege with encumbered status
        self.test_data_generator.put_default_privilege_record_in_provider_table(
            value_overrides={
                'encumberedStatus': 'encumbered',
                'providerId': license_record.providerId,
                'compact': license_record.compact,
            }
        )

        event = self._generate_lift_encumbrance_event(license_record, adverse_action)

        response = encumbrance_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'])

        # Verify provider record remains encumbered
        provider_records: ProviderUserRecords = self.config.data_client.get_provider_user_records(
            compact=license_record.compact, provider_id=str(license_record.providerId)
        )

        loaded_provider_data = provider_records.get_provider_record()
        self.assertEqual(LicenseEncumberedStatusEnum.ENCUMBERED, loaded_provider_data.encumberedStatus)

    def test_should_return_access_denied_if_compact_admin_attempts_to_lift_license_encumbrance(self):
        """Verifying that only state admins are allowed to lift license encumbrances"""
        from handlers.encumbrance import encumbrance_handler

        license_record, adverse_action = self._setup_license_with_adverse_action()
        event = self._generate_lift_encumbrance_event(license_record, adverse_action)

        # Change scope to compact admin instead of state admin
        event['requestContext']['authorizer']['claims']['scope'] = f'openid email {license_record.compact}/admin'

        response = encumbrance_handler(event, self.mock_context)
        self.assertEqual(403, response['statusCode'])
        response_body = json.loads(response['body'])

        self.assertEqual(
            {'message': 'Access denied'},
            response_body,
        )
