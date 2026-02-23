import json
from datetime import datetime
from unittest.mock import patch
from uuid import UUID

from cc_common.data_model.update_tier_enum import UpdateTierEnum
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
            'clinicalPrivilegeActionCategories': [ClinicalPrivilegeActionCategory.UNSAFE_PRACTICE.value],
        },
    }


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat(DEFAULT_DATE_OF_UPDATE_TIMESTAMP))
class TestPostPrivilegeInvestigation(TstFunction):
    """Test suite for privilege investigation endpoints."""

    def setUp(self):
        super().setUp()
        self.set_live_compact_jurisdictions_for_test({'cosm': ['ne']})

    def _load_privilege_data(self):
        """Load privilege test data from JSON file"""
        # Load provider record first (needed for encumbrance creation)
        self.test_data_generator.put_default_provider_record_in_provider_table()
        # License needed so runtime privilege generation returns a privilege for get_provider
        self.test_data_generator.put_default_license_record_in_provider_table()
        privilege = self.test_data_generator.generate_default_privilege()
        self.test_data_generator.store_record_in_provider_table(privilege.serialize_to_database_record())
        return privilege

    def _when_testing_privilege_investigation(self):
        test_privilege_record = self._load_privilege_data()

        test_event = self.test_data_generator.generate_test_api_event(
            sub_override=DEFAULT_AA_SUBMITTING_USER_ID,
            scope_override=f'openid email {test_privilege_record.jurisdiction}/cosm.admin',
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

    @patch('cc_common.event_bus_client.EventBusClient._publish_event')
    def test_privilege_investigation_handler(self, mock_publish_event):
        from cc_common.data_model.schema.common import InvestigationStatusEnum
        from handlers.investigation import investigation_handler
        from handlers.providers import get_provider

        event, test_privilege_record = self._when_testing_privilege_investigation()

        response = investigation_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))
        response_body = json.loads(response['body'])

        self.assertEqual(
            {'message': 'OK'},
            response_body,
        )

        # Verify that the investigation record was added to the provider data table
        provider_user_records = self.config.data_client.get_provider_user_records(
            compact=test_privilege_record.compact,
            provider_id=test_privilege_record.providerId,
        )
        investigation_records = provider_user_records.get_investigation_records_for_privilege(
            privilege_jurisdiction=test_privilege_record.jurisdiction,
            privilege_license_type_abbreviation=test_privilege_record.licenseTypeAbbreviation,
        )
        self.assertEqual(1, len(investigation_records))
        investigation = investigation_records[0]

        # Verify the investigation record fields
        expected_investigation = {
            'type': 'investigation',
            'compact': test_privilege_record.compact,
            'providerId': test_privilege_record.providerId,
            'jurisdiction': test_privilege_record.jurisdiction,
            'licenseType': test_privilege_record.licenseType,
            'investigationAgainst': 'privilege',
            'submittingUser': UUID(DEFAULT_AA_SUBMITTING_USER_ID),
            'creationDate': datetime.fromisoformat(DEFAULT_DATE_OF_UPDATE_TIMESTAMP),
            'dateOfUpdate': datetime.fromisoformat(DEFAULT_DATE_OF_UPDATE_TIMESTAMP),
            'investigationId': investigation.investigationId,
        }
        self.assertEqual(expected_investigation, investigation.to_dict())

        # Verify that the privilege record was updated to be under investigation
        updated_privilege_record = provider_user_records.get_privilege_records()[0]

        self.assertEqual(InvestigationStatusEnum.UNDER_INVESTIGATION, updated_privilege_record.investigationStatus)

        # Verify that investigation objects are included in the API response
        api_event = self.test_data_generator.generate_test_api_event(
            scope_override=f'openid email {test_privilege_record.jurisdiction}/cosm.readGeneral',
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

        expected_privilege = {
            'providerId': str(test_privilege_record.providerId),
            'investigationStatus': 'underInvestigation',
            'investigations': [
                {
                    'type': 'investigation',
                    'compact': test_privilege_record.compact,
                    'providerId': str(test_privilege_record.providerId),
                    'jurisdiction': test_privilege_record.jurisdiction,
                    'licenseType': test_privilege_record.licenseType,
                    'submittingUser': DEFAULT_AA_SUBMITTING_USER_ID,
                    'creationDate': DEFAULT_DATE_OF_UPDATE_TIMESTAMP,
                    'dateOfUpdate': DEFAULT_DATE_OF_UPDATE_TIMESTAMP,
                    'investigationId': privilege['investigations'][0]['investigationId'],  # Dynamic field
                }
            ],
        }

        self.assertDictPartialMatch(expected_privilege, privilege)

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
                'investigationId': call_args['detail']['investigationId'],  # Dynamic field
            },
        }
        self.assertEqual(expected_event_args, call_args)

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

        # Load provider record first (needed for encumbrance creation)
        self.test_data_generator.put_default_provider_record_in_provider_table()
        license_data = self.test_data_generator.generate_default_license()
        self.test_data_generator.store_record_in_provider_table(license_data.serialize_to_database_record())
        return license_data

    def _when_testing_valid_license_investigation(self, body_overrides: dict | None = None):
        test_license_record = self._load_license_data()
        test_body = {}
        if body_overrides:
            test_body.update(body_overrides)

        test_event = self.test_data_generator.generate_test_api_event(
            sub_override=DEFAULT_AA_SUBMITTING_USER_ID,
            scope_override=f'openid email {test_license_record.jurisdiction}/cosm.admin',
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

    @patch('cc_common.event_bus_client.EventBusClient._publish_event')
    def test_license_investigation_handler(self, mock_publish_event):
        from cc_common.data_model.schema.common import InvestigationStatusEnum
        from handlers.investigation import investigation_handler
        from handlers.providers import get_provider

        event, test_license_record = self._when_testing_valid_license_investigation()

        response = investigation_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))
        response_body = json.loads(response['body'])

        self.assertEqual(
            {'message': 'OK'},
            response_body,
        )

        # Verify that the investigation record was added to the provider data table
        # Perform a query to list all investigations for the provider using the starts_with key condition
        provider_user_records = self.config.data_client.get_provider_user_records(
            compact=test_license_record.compact,
            provider_id=test_license_record.providerId,
        )
        investigation_records = provider_user_records.get_investigation_records_for_license(
            license_jurisdiction=test_license_record.jurisdiction,
            license_type_abbreviation=test_license_record.licenseTypeAbbreviation,
        )
        self.assertEqual(1, len(investigation_records))
        investigation = investigation_records[0]

        # Verify the investigation record fields
        expected_investigation = {
            'type': 'investigation',
            'compact': test_license_record.compact,
            'providerId': test_license_record.providerId,
            'jurisdiction': test_license_record.jurisdiction,
            'licenseType': test_license_record.licenseType,
            'investigationAgainst': 'license',
            'submittingUser': UUID(DEFAULT_AA_SUBMITTING_USER_ID),
            'creationDate': datetime.fromisoformat(DEFAULT_DATE_OF_UPDATE_TIMESTAMP),
            'dateOfUpdate': datetime.fromisoformat(DEFAULT_DATE_OF_UPDATE_TIMESTAMP),
            'investigationId': investigation.investigationId,
        }
        self.assertEqual(expected_investigation, investigation.to_dict())

        # Verify that the license record was updated to be under investigation
        updated_license_record = provider_user_records.get_license_records()[0]

        self.assertEqual(InvestigationStatusEnum.UNDER_INVESTIGATION, updated_license_record.investigationStatus)

        # Verify that investigation objects are included in the API response
        api_event = self.test_data_generator.generate_test_api_event(
            scope_override=f'openid email {test_license_record.jurisdiction}/cosm.readGeneral',
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

        expected_license = {
            'providerId': str(test_license_record.providerId),
            'investigationStatus': 'underInvestigation',
            'investigations': [
                {
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
            ],
        }

        self.assertDictPartialMatch(expected_license, license_obj)

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
                'investigationId': call_args['detail']['investigationId'],  # Dynamic field
            },
        }
        self.assertEqual(expected_event_args, call_args)

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

    def setUp(self):
        super().setUp()
        self.set_live_compact_jurisdictions_for_test({'cosm': ['ne']})

    def _load_privilege_data(self):
        """Load privilege test data using test data generator"""
        # Load provider record first (needed for encumbrance creation)
        self.test_data_generator.put_default_provider_record_in_provider_table()
        # License needed so runtime privilege generation returns a privilege for get_provider
        self.test_data_generator.put_default_license_record_in_provider_table()
        privilege = self.test_data_generator.generate_default_privilege()
        self.test_data_generator.store_record_in_provider_table(privilege.serialize_to_database_record())
        return privilege

    def _when_testing_privilege_investigation_close(self, body_overrides: dict | None = None):
        test_privilege_record = self._load_privilege_data()
        test_body = {}
        if body_overrides:
            test_body.update(body_overrides)

        # First create an investigation
        create_event = self.test_data_generator.generate_test_api_event(
            sub_override=DEFAULT_AA_SUBMITTING_USER_ID,
            scope_override=f'openid email {test_privilege_record.jurisdiction}/cosm.admin',
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

        # Get the investigation ID using the data client
        provider_user_records = self.config.data_client.get_provider_user_records(
            compact=test_privilege_record.compact,
            provider_id=test_privilege_record.providerId,
        )
        investigation_records = provider_user_records.get_investigation_records_for_privilege(
            privilege_jurisdiction=test_privilege_record.jurisdiction,
            privilege_license_type_abbreviation=test_privilege_record.licenseTypeAbbreviation,
        )
        self.assertEqual(1, len(investigation_records))
        investigation_id = investigation_records[0].investigationId

        # Now create the close event
        test_event = self.test_data_generator.generate_test_api_event(
            sub_override=DEFAULT_AA_SUBMITTING_USER_ID,
            scope_override=f'openid email {test_privilege_record.jurisdiction}/cosm.admin',
            value_overrides={
                'httpMethod': 'PATCH',
                'resource': PRIVILEGE_INVESTIGATION_ID_ENDPOINT_RESOURCE,
                'pathParameters': {
                    'compact': test_privilege_record.compact,
                    'providerId': str(test_privilege_record.providerId),
                    'jurisdiction': test_privilege_record.jurisdiction,
                    'licenseType': test_privilege_record.licenseTypeAbbreviation,
                    'investigationId': str(investigation_id),
                },
                'body': json.dumps(test_body),
            },
        )

        return test_event, test_privilege_record, investigation_id

    @patch('cc_common.event_bus_client.EventBusClient._publish_event')
    def test_privilege_investigation_close_handler(self, mock_publish_event):
        from handlers.investigation import investigation_handler
        from handlers.providers import get_provider

        event, test_privilege_record, investigation_id = self._when_testing_privilege_investigation_close()

        response = investigation_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))
        response_body = json.loads(response['body'])

        self.assertEqual(
            {'message': 'OK'},
            response_body,
        )

        # Verify that the investigation record was updated
        provider_user_records = self.config.data_client.get_provider_user_records(
            compact=test_privilege_record.compact,
            provider_id=test_privilege_record.providerId,
        )
        # Get all investigation records (including closed ones)
        all_investigations = provider_user_records.get_investigation_records_for_privilege(
            privilege_jurisdiction=test_privilege_record.jurisdiction,
            privilege_license_type_abbreviation=test_privilege_record.licenseTypeAbbreviation,
            filter_condition=lambda inv: inv.investigationId == investigation_id,
            include_closed=True,
        )
        self.assertEqual(1, len(all_investigations))
        investigation = all_investigations[0]

        expected_investigation = {
            'type': 'investigation',
            'compact': test_privilege_record.compact,
            'providerId': test_privilege_record.providerId,
            'jurisdiction': test_privilege_record.jurisdiction,
            'licenseType': test_privilege_record.licenseType,
            'investigationAgainst': 'privilege',
            'investigationId': investigation_id,
            'submittingUser': UUID(DEFAULT_AA_SUBMITTING_USER_ID),
            'creationDate': datetime.fromisoformat(DEFAULT_DATE_OF_UPDATE_TIMESTAMP),
            'closeDate': datetime.fromisoformat(DEFAULT_DATE_OF_UPDATE_TIMESTAMP),
            'closingUser': UUID(DEFAULT_AA_SUBMITTING_USER_ID),
            'dateOfUpdate': datetime.fromisoformat(DEFAULT_DATE_OF_UPDATE_TIMESTAMP),
        }

        self.assertEqual(expected_investigation, investigation.to_dict())

        # Verify that the privilege record no longer has investigation status
        updated_privilege_record = provider_user_records.get_privilege_records()[0]

        self.assertIsNone(updated_privilege_record.investigationStatus)

        # Verify that investigation objects are removed from the API response
        api_event = self.test_data_generator.generate_test_api_event(
            scope_override=f'openid email {test_privilege_record.jurisdiction}/cosm.readGeneral',
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
                'investigationId': call_args['detail']['investigationId'],  # Dynamic field
            },
        }
        self.assertEqual(expected_event_args, call_args)

    def test_privilege_investigation_close_with_encumbrance_creates_encumbrance(self):
        from handlers.investigation import investigation_handler

        event, test_privilege_record, investigation_id = self._when_testing_privilege_investigation_close(
            body_overrides=_generate_test_investigation_close_with_encumbrance_body()
        )

        response = investigation_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))

        # Verify that an encumbrance was created
        provider_user_records = self.config.data_client.get_provider_user_records(
            compact=test_privilege_record.compact,
            provider_id=test_privilege_record.providerId,
        )
        encumbrance_records = provider_user_records.get_adverse_action_records_for_privilege(
            privilege_jurisdiction=test_privilege_record.jurisdiction,
            privilege_license_type_abbreviation=test_privilege_record.licenseTypeAbbreviation,
        )
        self.assertEqual(1, len(encumbrance_records))

        # Verify that the investigation record has the resulting encumbrance ID
        all_investigations = provider_user_records.get_investigation_records_for_privilege(
            privilege_jurisdiction=test_privilege_record.jurisdiction,
            privilege_license_type_abbreviation=test_privilege_record.licenseTypeAbbreviation,
            filter_condition=lambda inv: inv.investigationId == investigation_id,
            include_closed=True,
        )
        self.assertEqual(1, len(all_investigations))
        investigation = all_investigations[0]

        self.assertIsNotNone(investigation.resultingEncumbranceId)


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat(DEFAULT_DATE_OF_UPDATE_TIMESTAMP))
class TestPatchLicenseInvestigationClose(TstFunction):
    """Test suite for license investigation close endpoints."""

    def _load_license_data(self):
        """Load license test data using test data generator"""
        # Load provider record first (needed for encumbrance creation)
        self.test_data_generator.put_default_provider_record_in_provider_table()
        license_data = self.test_data_generator.generate_default_license()
        self.test_data_generator.store_record_in_provider_table(license_data.serialize_to_database_record())
        return license_data

    def _when_testing_license_investigation_close(self, body_overrides: dict | None = None):
        test_license_record = self._load_license_data()
        test_body = {}
        if body_overrides:
            test_body.update(body_overrides)

        # First create an investigation
        create_event = self.test_data_generator.generate_test_api_event(
            sub_override=DEFAULT_AA_SUBMITTING_USER_ID,
            scope_override=f'openid email {test_license_record.jurisdiction}/cosm.admin',
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

        # Get the investigation ID using the data client
        provider_user_records = self.config.data_client.get_provider_user_records(
            compact=test_license_record.compact,
            provider_id=test_license_record.providerId,
        )
        investigation_records = provider_user_records.get_investigation_records_for_license(
            license_jurisdiction=test_license_record.jurisdiction,
            license_type_abbreviation=test_license_record.licenseTypeAbbreviation,
        )
        self.assertEqual(1, len(investigation_records))
        investigation_id = investigation_records[0].investigationId

        # Now create the close event
        test_event = self.test_data_generator.generate_test_api_event(
            sub_override=DEFAULT_AA_SUBMITTING_USER_ID,
            scope_override=f'openid email {test_license_record.jurisdiction}/cosm.admin',
            value_overrides={
                'httpMethod': 'PATCH',
                'resource': LICENSE_INVESTIGATION_ID_ENDPOINT_RESOURCE,
                'pathParameters': {
                    'compact': test_license_record.compact,
                    'providerId': str(test_license_record.providerId),
                    'jurisdiction': test_license_record.jurisdiction,
                    'licenseType': test_license_record.licenseTypeAbbreviation,
                    'investigationId': str(investigation_id),
                },
                'body': json.dumps(test_body),
            },
        )

        return test_event, test_license_record, investigation_id

    @patch('cc_common.event_bus_client.EventBusClient._publish_event')
    def test_license_investigation_close_handler(self, mock_publish_event):
        from handlers.investigation import investigation_handler
        from handlers.providers import get_provider

        event, test_license_record, investigation_id = self._when_testing_license_investigation_close()

        response = investigation_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))
        response_body = json.loads(response['body'])

        self.assertEqual(
            {'message': 'OK'},
            response_body,
        )

        # Verify that the investigation record was updated
        provider_user_records = self.config.data_client.get_provider_user_records(
            compact=test_license_record.compact,
            provider_id=test_license_record.providerId,
        )
        # Get all investigation records (including closed ones)
        all_investigations = provider_user_records.get_investigation_records_for_license(
            license_jurisdiction=test_license_record.jurisdiction,
            license_type_abbreviation=test_license_record.licenseTypeAbbreviation,
            filter_condition=lambda inv: inv.investigationId == investigation_id,
            include_closed=True,
        )
        self.assertEqual(1, len(all_investigations))
        investigation = all_investigations[0]

        expected_investigation = {
            'type': 'investigation',
            'compact': test_license_record.compact,
            'providerId': test_license_record.providerId,
            'jurisdiction': test_license_record.jurisdiction,
            'licenseType': test_license_record.licenseType,
            'investigationAgainst': 'license',
            'investigationId': investigation_id,
            'submittingUser': UUID(DEFAULT_AA_SUBMITTING_USER_ID),
            'creationDate': datetime.fromisoformat(DEFAULT_DATE_OF_UPDATE_TIMESTAMP),
            'closeDate': datetime.fromisoformat(DEFAULT_DATE_OF_UPDATE_TIMESTAMP),
            'closingUser': UUID(DEFAULT_AA_SUBMITTING_USER_ID),
            'dateOfUpdate': datetime.fromisoformat(DEFAULT_DATE_OF_UPDATE_TIMESTAMP),
        }

        self.assertEqual(expected_investigation, investigation.to_dict())

        # Verify that the license record no longer has investigation status
        updated_license_record = provider_user_records.get_license_records()[0]

        self.assertIsNone(updated_license_record.investigationStatus)

        # Verify that investigation objects are removed from the API response
        api_event = self.test_data_generator.generate_test_api_event(
            scope_override=f'openid email {test_license_record.jurisdiction}/cosm.readGeneral',
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
                'investigationId': call_args['detail']['investigationId'],  # Dynamic field
            },
        }
        self.assertEqual(expected_event_args, call_args)

    def test_license_investigation_close_with_encumbrance_creates_encumbrance(self):
        from handlers.investigation import investigation_handler

        event, test_license_record, investigation_id = self._when_testing_license_investigation_close(
            body_overrides=_generate_test_investigation_close_with_encumbrance_body()
        )

        response = investigation_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))

        # Verify that an encumbrance was created
        provider_user_records = self.config.data_client.get_provider_user_records(
            compact=test_license_record.compact,
            provider_id=test_license_record.providerId,
        )
        encumbrance_records = provider_user_records.get_adverse_action_records_for_license(
            license_jurisdiction=test_license_record.jurisdiction,
            license_type_abbreviation=test_license_record.licenseTypeAbbreviation,
        )
        self.assertEqual(1, len(encumbrance_records))

        # Verify that the investigation record has the resulting encumbrance ID
        all_investigations = provider_user_records.get_investigation_records_for_license(
            license_jurisdiction=test_license_record.jurisdiction,
            license_type_abbreviation=test_license_record.licenseTypeAbbreviation,
            filter_condition=lambda inv: inv.investigationId == investigation_id,
            include_closed=True,
        )
        self.assertEqual(1, len(all_investigations))
        investigation = all_investigations[0]

        self.assertIsNotNone(investigation.resultingEncumbranceId)


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat(DEFAULT_DATE_OF_UPDATE_TIMESTAMP))
class TestMultipleSimultaneousPrivilegeInvestigations(TstFunction):
    """Test suite for multiple simultaneous privilege investigations."""

    def setUp(self):
        super().setUp()
        self.set_live_compact_jurisdictions_for_test({'cosm': ['ne']})

    def _load_privilege_data(self):
        """Load privilege test data using test data generator"""
        # Load provider record first
        self.test_data_generator.put_default_provider_record_in_provider_table()
        # License needed so runtime privilege generation returns a privilege for get_provider
        self.test_data_generator.put_default_license_record_in_provider_table()
        privilege = self.test_data_generator.generate_default_privilege()
        self.test_data_generator.store_record_in_provider_table(privilege.serialize_to_database_record())
        return privilege

    @patch('cc_common.event_bus_client.EventBusClient._publish_event')
    def test_closing_one_of_multiple_investigations_maintains_investigation_status(self, mock_publish_event):
        """Test that closing one investigation while another is open maintains investigation status."""
        from cc_common.data_model.schema.common import InvestigationStatusEnum, UpdateCategory
        from handlers.investigation import investigation_handler
        from handlers.providers import get_provider

        test_privilege_record = self._load_privilege_data()

        # Create first investigation
        first_investigation_event = self.test_data_generator.generate_test_api_event(
            sub_override=DEFAULT_AA_SUBMITTING_USER_ID,
            scope_override=f'openid email {test_privilege_record.jurisdiction}/cosm.admin',
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

        response = investigation_handler(first_investigation_event, self.mock_context)
        self.assertEqual(200, response['statusCode'])

        # Get the first investigation ID
        provider_user_records = self.config.data_client.get_provider_user_records(
            compact=test_privilege_record.compact,
            provider_id=test_privilege_record.providerId,
        )
        investigation_records = provider_user_records.get_investigation_records_for_privilege(
            privilege_jurisdiction=test_privilege_record.jurisdiction,
            privilege_license_type_abbreviation=test_privilege_record.licenseTypeAbbreviation,
        )
        self.assertEqual(1, len(investigation_records))
        first_investigation_id = investigation_records[0].investigationId

        # Create second investigation
        second_investigation_event = self.test_data_generator.generate_test_api_event(
            sub_override=DEFAULT_AA_SUBMITTING_USER_ID,
            scope_override=f'openid email {test_privilege_record.jurisdiction}/cosm.admin',
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

        response = investigation_handler(second_investigation_event, self.mock_context)
        self.assertEqual(200, response['statusCode'])

        # Get the second investigation ID
        provider_user_records = self.config.data_client.get_provider_user_records(
            compact=test_privilege_record.compact,
            provider_id=test_privilege_record.providerId,
        )
        investigation_records = provider_user_records.get_investigation_records_for_privilege(
            privilege_jurisdiction=test_privilege_record.jurisdiction,
            privilege_license_type_abbreviation=test_privilege_record.licenseTypeAbbreviation,
        )
        self.assertEqual(2, len(investigation_records))
        second_investigation_id = [
            inv.investigationId for inv in investigation_records if inv.investigationId != first_investigation_id
        ][0]

        # Close the second investigation
        close_second_event = self.test_data_generator.generate_test_api_event(
            sub_override=DEFAULT_AA_SUBMITTING_USER_ID,
            scope_override=f'openid email {test_privilege_record.jurisdiction}/cosm.admin',
            value_overrides={
                'httpMethod': 'PATCH',
                'resource': PRIVILEGE_INVESTIGATION_ID_ENDPOINT_RESOURCE,
                'pathParameters': {
                    'compact': test_privilege_record.compact,
                    'providerId': str(test_privilege_record.providerId),
                    'jurisdiction': test_privilege_record.jurisdiction,
                    'licenseType': test_privilege_record.licenseTypeAbbreviation,
                    'investigationId': str(second_investigation_id),
                },
                'body': json.dumps({}),
            },
        )

        response = investigation_handler(close_second_event, self.mock_context)
        self.assertEqual(200, response['statusCode'])

        # Verify that the privilege record still shows under investigation
        provider_user_records = self.config.data_client.get_provider_user_records(
            compact=test_privilege_record.compact,
            provider_id=test_privilege_record.providerId,
        )
        updated_privilege_record = provider_user_records.get_privilege_records()[0]

        self.assertEqual(
            InvestigationStatusEnum.UNDER_INVESTIGATION,
            updated_privilege_record.investigationStatus,
        )

        # Verify that one investigation is still visible in the API response
        api_event = self.test_data_generator.generate_test_api_event(
            scope_override=f'openid email {test_privilege_record.jurisdiction}/cosm.readGeneral',
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
        privilege = provider_data['privileges'][0]

        self.assertEqual(1, len(privilege['investigations']))
        self.assertEqual(str(first_investigation_id), privilege['investigations'][0]['investigationId'])

        # Verify that there are two INVESTIGATION update records
        provider_user_records = self.config.data_client.get_provider_user_records(
            compact=test_privilege_record.compact,
            provider_id=test_privilege_record.providerId,
            include_update_tier=UpdateTierEnum.TIER_THREE,
        )
        update_records = provider_user_records.get_update_records_for_privilege(
            jurisdiction=test_privilege_record.jurisdiction,
            license_type=test_privilege_record.licenseType,
        )

        investigation_update_records = [
            record for record in update_records if record.updateType == UpdateCategory.INVESTIGATION
        ]
        self.assertEqual(2, len(investigation_update_records))

        # Verify that there are no CLOSING_INVESTIGATION update records
        closing_update_records = [
            record for record in update_records if record.updateType == UpdateCategory.CLOSING_INVESTIGATION
        ]
        self.assertEqual(0, len(closing_update_records))

        # Verify that investigation closed event WAS published (should be 3 calls: 2 creation + 1 closure)
        self.assertEqual(3, mock_publish_event.call_count)
        call_types = [call[1]['detail_type'] for call in mock_publish_event.call_args_list]
        self.assertEqual(2, call_types.count('privilege.investigation'))
        self.assertEqual(1, call_types.count('privilege.investigationClosed'))

        # Now close the first investigation
        close_first_event = self.test_data_generator.generate_test_api_event(
            sub_override=DEFAULT_AA_SUBMITTING_USER_ID,
            scope_override=f'openid email {test_privilege_record.jurisdiction}/cosm.admin',
            value_overrides={
                'httpMethod': 'PATCH',
                'resource': PRIVILEGE_INVESTIGATION_ID_ENDPOINT_RESOURCE,
                'pathParameters': {
                    'compact': test_privilege_record.compact,
                    'providerId': str(test_privilege_record.providerId),
                    'jurisdiction': test_privilege_record.jurisdiction,
                    'licenseType': test_privilege_record.licenseTypeAbbreviation,
                    'investigationId': str(first_investigation_id),
                },
                'body': json.dumps({}),
            },
        )

        response = investigation_handler(close_first_event, self.mock_context)
        self.assertEqual(200, response['statusCode'])

        # Verify that the privilege record no longer has investigation status
        provider_user_records = self.config.data_client.get_provider_user_records(
            compact=test_privilege_record.compact,
            provider_id=test_privilege_record.providerId,
            include_update_tier=UpdateTierEnum.TIER_THREE,
        )
        updated_privilege_record = provider_user_records.get_privilege_records()[0]

        self.assertIsNone(updated_privilege_record.investigationStatus)

        # Verify that there are no investigations visible in the API response
        api_response = get_provider(api_event, self.mock_context)
        self.assertEqual(200, api_response['statusCode'])

        provider_data = json.loads(api_response['body'])
        privilege = provider_data['privileges'][0]

        self.assertEqual(0, len(privilege['investigations']))

        # Verify that there are still two INVESTIGATION update records
        provider_user_records = self.config.data_client.get_provider_user_records(
            compact=test_privilege_record.compact,
            provider_id=test_privilege_record.providerId,
            include_update_tier=UpdateTierEnum.TIER_THREE,
        )
        update_records = provider_user_records.get_update_records_for_privilege(
            jurisdiction=test_privilege_record.jurisdiction, license_type=test_privilege_record.licenseType
        )

        investigation_update_records = [
            record for record in update_records if record.updateType == UpdateCategory.INVESTIGATION
        ]
        self.assertEqual(2, len(investigation_update_records))

        # Verify that there is one CLOSING_INVESTIGATION update record
        closing_update_records = [
            record for record in update_records if record.updateType == UpdateCategory.CLOSING_INVESTIGATION
        ]
        self.assertEqual(1, len(closing_update_records))

        # Verify that investigation closed events were published (should be 4 calls total: 2 creation + 2 closure)
        self.assertEqual(4, mock_publish_event.call_count)
        call_types = [call[1]['detail_type'] for call in mock_publish_event.call_args_list]
        self.assertEqual(2, call_types.count('privilege.investigation'))
        self.assertEqual(2, call_types.count('privilege.investigationClosed'))


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat(DEFAULT_DATE_OF_UPDATE_TIMESTAMP))
class TestMultipleSimultaneousLicenseInvestigations(TstFunction):
    """Test suite for multiple simultaneous license investigations."""

    def _load_license_data(self):
        """Load license test data using test data generator"""
        # Load provider record first
        self.test_data_generator.put_default_provider_record_in_provider_table()
        license_data = self.test_data_generator.generate_default_license()
        self.test_data_generator.store_record_in_provider_table(license_data.serialize_to_database_record())
        return license_data

    @patch('cc_common.event_bus_client.EventBusClient._publish_event')
    def test_closing_one_of_multiple_investigations_maintains_investigation_status(self, mock_publish_event):
        """Test that closing one investigation while another is open maintains investigation status."""
        from cc_common.data_model.schema.common import InvestigationStatusEnum, UpdateCategory
        from handlers.investigation import investigation_handler
        from handlers.providers import get_provider

        test_license_record = self._load_license_data()

        # Create first investigation
        first_investigation_event = self.test_data_generator.generate_test_api_event(
            sub_override=DEFAULT_AA_SUBMITTING_USER_ID,
            scope_override=f'openid email {test_license_record.jurisdiction}/cosm.admin',
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

        response = investigation_handler(first_investigation_event, self.mock_context)
        self.assertEqual(200, response['statusCode'])

        # Get the first investigation ID
        provider_user_records = self.config.data_client.get_provider_user_records(
            compact=test_license_record.compact,
            provider_id=test_license_record.providerId,
            include_update_tier=UpdateTierEnum.TIER_THREE,
        )
        investigation_records = provider_user_records.get_investigation_records_for_license(
            license_jurisdiction=test_license_record.jurisdiction,
            license_type_abbreviation=test_license_record.licenseTypeAbbreviation,
        )
        self.assertEqual(1, len(investigation_records))
        first_investigation_id = investigation_records[0].investigationId

        # Create second investigation
        second_investigation_event = self.test_data_generator.generate_test_api_event(
            sub_override=DEFAULT_AA_SUBMITTING_USER_ID,
            scope_override=f'openid email {test_license_record.jurisdiction}/cosm.admin',
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

        response = investigation_handler(second_investigation_event, self.mock_context)
        self.assertEqual(200, response['statusCode'])

        # Get the second investigation ID
        provider_user_records = self.config.data_client.get_provider_user_records(
            compact=test_license_record.compact,
            provider_id=test_license_record.providerId,
            include_update_tier=UpdateTierEnum.TIER_THREE,
        )
        investigation_records = provider_user_records.get_investigation_records_for_license(
            license_jurisdiction=test_license_record.jurisdiction,
            license_type_abbreviation=test_license_record.licenseTypeAbbreviation,
        )
        self.assertEqual(2, len(investigation_records))
        second_investigation_id = [
            inv.investigationId for inv in investigation_records if inv.investigationId != first_investigation_id
        ][0]

        # Close the second investigation
        close_second_event = self.test_data_generator.generate_test_api_event(
            sub_override=DEFAULT_AA_SUBMITTING_USER_ID,
            scope_override=f'openid email {test_license_record.jurisdiction}/cosm.admin',
            value_overrides={
                'httpMethod': 'PATCH',
                'resource': LICENSE_INVESTIGATION_ID_ENDPOINT_RESOURCE,
                'pathParameters': {
                    'compact': test_license_record.compact,
                    'providerId': str(test_license_record.providerId),
                    'jurisdiction': test_license_record.jurisdiction,
                    'licenseType': test_license_record.licenseTypeAbbreviation,
                    'investigationId': str(second_investigation_id),
                },
                'body': json.dumps({}),
            },
        )

        response = investigation_handler(close_second_event, self.mock_context)
        self.assertEqual(200, response['statusCode'])

        # Verify that the license record still shows under investigation
        provider_user_records = self.config.data_client.get_provider_user_records(
            compact=test_license_record.compact,
            provider_id=test_license_record.providerId,
            include_update_tier=UpdateTierEnum.TIER_THREE,
        )
        updated_license_record = provider_user_records.get_license_records()[0]

        self.assertEqual(
            InvestigationStatusEnum.UNDER_INVESTIGATION,
            updated_license_record.investigationStatus,
        )

        # Verify that one investigation is still visible in the API response
        api_event = self.test_data_generator.generate_test_api_event(
            scope_override=f'openid email {test_license_record.jurisdiction}/cosm.readGeneral',
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
        license_obj = provider_data['licenses'][0]

        self.assertEqual(1, len(license_obj['investigations']))
        self.assertEqual(str(first_investigation_id), license_obj['investigations'][0]['investigationId'])

        # Verify that there are two INVESTIGATION update records
        provider_user_records = self.config.data_client.get_provider_user_records(
            compact=test_license_record.compact,
            provider_id=test_license_record.providerId,
            include_update_tier=UpdateTierEnum.TIER_THREE,
        )
        update_records = provider_user_records.get_update_records_for_license(
            jurisdiction=test_license_record.jurisdiction, license_type=test_license_record.licenseType
        )

        investigation_update_records = [
            record for record in update_records if record.updateType == UpdateCategory.INVESTIGATION
        ]
        self.assertEqual(2, len(investigation_update_records))

        # Verify that there are no CLOSING_INVESTIGATION update records
        closing_update_records = [
            record for record in update_records if record.updateType == UpdateCategory.CLOSING_INVESTIGATION
        ]
        self.assertEqual(0, len(closing_update_records))

        # Verify that investigation closed event WAS published (should be 3 calls: 2 creation + 1 closure)
        self.assertEqual(3, mock_publish_event.call_count)
        call_types = [call[1]['detail_type'] for call in mock_publish_event.call_args_list]
        self.assertEqual(2, call_types.count('license.investigation'))
        self.assertEqual(1, call_types.count('license.investigationClosed'))

        # Now close the first investigation
        close_first_event = self.test_data_generator.generate_test_api_event(
            sub_override=DEFAULT_AA_SUBMITTING_USER_ID,
            scope_override=f'openid email {test_license_record.jurisdiction}/cosm.admin',
            value_overrides={
                'httpMethod': 'PATCH',
                'resource': LICENSE_INVESTIGATION_ID_ENDPOINT_RESOURCE,
                'pathParameters': {
                    'compact': test_license_record.compact,
                    'providerId': str(test_license_record.providerId),
                    'jurisdiction': test_license_record.jurisdiction,
                    'licenseType': test_license_record.licenseTypeAbbreviation,
                    'investigationId': str(first_investigation_id),
                },
                'body': json.dumps({}),
            },
        )

        response = investigation_handler(close_first_event, self.mock_context)
        self.assertEqual(200, response['statusCode'])

        # Verify that the license record no longer has investigation status
        provider_user_records = self.config.data_client.get_provider_user_records(
            compact=test_license_record.compact,
            provider_id=test_license_record.providerId,
            include_update_tier=UpdateTierEnum.TIER_THREE,
        )
        updated_license_record = provider_user_records.get_license_records()[0]

        self.assertIsNone(updated_license_record.investigationStatus)

        # Verify that there are no investigations visible in the API response
        api_response = get_provider(api_event, self.mock_context)
        self.assertEqual(200, api_response['statusCode'])

        provider_data = json.loads(api_response['body'])
        license_obj = provider_data['licenses'][0]

        self.assertEqual(0, len(license_obj['investigations']))

        # Verify that there are still two INVESTIGATION update records
        provider_user_records = self.config.data_client.get_provider_user_records(
            compact=test_license_record.compact,
            provider_id=test_license_record.providerId,
            include_update_tier=UpdateTierEnum.TIER_THREE,
        )
        update_records = provider_user_records.get_update_records_for_license(
            jurisdiction=test_license_record.jurisdiction, license_type=test_license_record.licenseType
        )

        investigation_update_records = [
            record for record in update_records if record.updateType == UpdateCategory.INVESTIGATION
        ]
        self.assertEqual(2, len(investigation_update_records))

        # Verify that there is one CLOSING_INVESTIGATION update record
        closing_update_records = [
            record for record in update_records if record.updateType == UpdateCategory.CLOSING_INVESTIGATION
        ]
        self.assertEqual(1, len(closing_update_records))

        # Verify that investigation closed events were published (should be 4 calls total: 2 creation + 2 closure)
        self.assertEqual(4, mock_publish_event.call_count)
        call_types = [call[1]['detail_type'] for call in mock_publish_event.call_args_list]
        self.assertEqual(2, call_types.count('license.investigation'))
        self.assertEqual(2, call_types.count('license.investigationClosed'))
