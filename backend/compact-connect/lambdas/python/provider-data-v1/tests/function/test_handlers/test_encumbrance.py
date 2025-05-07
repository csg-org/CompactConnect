import json
from datetime import date, datetime
from unittest.mock import patch

from boto3.dynamodb.conditions import Key
from common_test.test_constants import (
    DEFAULT_AA_SUBMITTING_USER_ID,
    DEFAULT_DATE_OF_UPDATE_TIMESTAMP,
    DEFAULT_LICENSE_JURISDICTION,
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

    def _when_testing_valid_privilege_encumbrance(self):
        self.test_data_generator.put_default_provider_record_in_provider_table()
        test_privilege_record = self.test_data_generator.put_default_privilege_record_in_provider_table()

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
                'body': json.dumps(_generate_test_body()),
            },
        )
        # return both the test event and the test privilege record
        return test_event, test_privilege_record

    def test_privilege_encumbrance_handler_returns_ok_message_with_valid_body(self):
        from handlers.encumbrance import encumbrance_handler

        event = self._when_testing_valid_privilege_encumbrance()[0]

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

        event, test_privilege_record = self._when_testing_valid_privilege_encumbrance()

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

        event, test_privilege_record = self._when_testing_valid_privilege_encumbrance()

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

    def test_privilege_encumbrance_handler_sets_privilege_record_to_inactive_in_provider_data_table(self):
        from cc_common.data_model.schema.common import PrivilegeEncumberedStatusEnum
        from cc_common.data_model.schema.privilege import PrivilegeData
        from handlers.encumbrance import encumbrance_handler

        event, test_privilege_record = self._when_testing_valid_privilege_encumbrance()

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

        event, test_license_record = self._when_testing_valid_privilege_encumbrance()
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

        event, test_privilege_record = self._when_testing_valid_privilege_encumbrance()

        event['requestContext']['authorizer']['claims']['scope'] = f'openid email {test_privilege_record.compact}/admin'

        response = encumbrance_handler(event, self.mock_context)
        self.assertEqual(403, response['statusCode'], msg=json.loads(response['body']))
        response_body = json.loads(response['body'])

        self.assertEqual(
            {'message': 'Access denied'},
            response_body,
        )


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat(DEFAULT_DATE_OF_UPDATE_TIMESTAMP))
class TestPostLicenseEncumbrance(TstFunction):
    """Test suite for license encumbrance endpoints."""

    def _when_testing_valid_license_encumbrance(self):
        self.test_data_generator.put_default_provider_record_in_provider_table()
        test_license_record = self.test_data_generator.put_default_license_record_in_provider_table()

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
                'body': json.dumps(_generate_test_body()),
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
