# ruff: noqa: E501 line-too-long
import json
from decimal import Decimal

from moto import mock_aws

from . import TstFunction

STAFF_USERS_COMPACT_JURISDICTION_ENDPOINT_RESOURCE = '/v1/compacts/{compact}/jurisdictions'
PUBLIC_COMPACT_JURISDICTION_ENDPOINT_RESOURCE = '/v1/public/compacts/{compact}/jurisdictions'

COMPACT_CONFIGURATION_ENDPOINT_RESOURCE = '/v1/compacts/{compact}'
JURISDICTION_CONFIGURATION_ENDPOINT_RESOURCE = '/v1/compacts/{compact}/jurisdictions/{jurisdiction}'


def generate_test_event(method: str, resource: str) -> dict:
    with open('../common/tests/resources/api-event.json') as f:
        event = json.load(f)
        event['httpMethod'] = method
        event['resource'] = resource
        event['pathParameters'] = {
            'compact': 'aslp',
        }

    return event


def load_compact_active_member_jurisdictions(postal_abbreviations: list[str], compact: str = 'aslp'):
    """Load active member jurisdictions using the TestDataGenerator."""
    from common_test.test_data_generator import TestDataGenerator

    TestDataGenerator.put_compact_active_member_jurisdictions(
        compact=compact, postal_abbreviations=postal_abbreviations
    )


@mock_aws
class TestGetStaffUsersCompactJurisdictions(TstFunction):
    """Test suite for get compact jurisdiction endpoints."""

    def test_get_compact_jurisdictions_returns_invalid_exception_if_invalid_http_method(self):
        """Test getting an empty list if no jurisdictions configured."""
        from handlers.compact_configuration import compact_configuration_api_handler

        event = generate_test_event('PATCH', STAFF_USERS_COMPACT_JURISDICTION_ENDPOINT_RESOURCE)

        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(400, response['statusCode'], msg=json.loads(response['body']))
        response_body = json.loads(response['body'])

        self.assertEqual(
            {'message': 'Invalid HTTP method'},
            response_body,
        )

    def test_get_compact_jurisdictions_returns_invalid_exception_if_invalid_compact(self):
        """Test getting an error if invalid compact is provided."""
        from handlers.compact_configuration import compact_configuration_api_handler

        event = generate_test_event('GET', STAFF_USERS_COMPACT_JURISDICTION_ENDPOINT_RESOURCE)
        event['pathParameters']['compact'] = 'invalid_compact'

        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(400, response['statusCode'], msg=json.loads(response['body']))
        response_body = json.loads(response['body'])

        self.assertEqual(
            {'message': 'Invalid compact abbreviation: invalid_compact'},
            response_body,
        )

    def test_get_compact_jurisdictions_returns_empty_list_if_no_active_jurisdictions(self):
        """Test getting an empty list if no jurisdictions configured."""
        from handlers.compact_configuration import compact_configuration_api_handler

        event = generate_test_event('GET', STAFF_USERS_COMPACT_JURISDICTION_ENDPOINT_RESOURCE)

        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))
        response_body = json.loads(response['body'])

        self.assertEqual(
            [],
            response_body,
        )

    def test_get_compact_jurisdictions_returns_list_of_configured_jurisdictions(self):
        """Test getting list of jurisdictions configured for a compact."""
        from handlers.compact_configuration import compact_configuration_api_handler

        # Load jurisdictions and active member jurisdictions
        load_compact_active_member_jurisdictions(postal_abbreviations=['ky', 'oh'])

        event = generate_test_event('GET', STAFF_USERS_COMPACT_JURISDICTION_ENDPOINT_RESOURCE)

        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))
        response_body = json.loads(response['body'])

        # Sort to ensure consistent order for comparison
        sorted_response = sorted(response_body, key=lambda x: x['postalAbbreviation'])

        self.assertEqual(
            [
                {'compact': 'aslp', 'jurisdictionName': 'Kentucky', 'postalAbbreviation': 'ky'},
                {'compact': 'aslp', 'jurisdictionName': 'Ohio', 'postalAbbreviation': 'oh'},
            ],
            sorted_response,
        )


@mock_aws
class TestGetPublicCompactJurisdictions(TstFunction):
    """Test suite for get compact jurisdiction endpoints."""

    def test_get_compact_jurisdictions_returns_invalid_exception_if_invalid_http_method(self):
        """Test getting an empty list if no jurisdictions configured."""
        from handlers.compact_configuration import compact_configuration_api_handler

        event = generate_test_event('PATCH', PUBLIC_COMPACT_JURISDICTION_ENDPOINT_RESOURCE)

        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(400, response['statusCode'], msg=json.loads(response['body']))
        response_body = json.loads(response['body'])

        self.assertEqual(
            {'message': 'Invalid HTTP method'},
            response_body,
        )

    def test_get_compact_jurisdictions_returns_invalid_exception_if_invalid_compact(self):
        """Test getting an error if invalid compact is provided."""
        from handlers.compact_configuration import compact_configuration_api_handler

        event = generate_test_event('GET', PUBLIC_COMPACT_JURISDICTION_ENDPOINT_RESOURCE)
        event['pathParameters']['compact'] = 'invalid_compact'

        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(400, response['statusCode'], msg=json.loads(response['body']))
        response_body = json.loads(response['body'])

        self.assertEqual(
            {'message': 'Invalid compact abbreviation: invalid_compact'},
            response_body,
        )

    def test_get_compact_jurisdictions_returns_empty_list_if_no_active_jurisdictions(self):
        """Test getting an empty list if no jurisdictions configured."""
        from handlers.compact_configuration import compact_configuration_api_handler

        event = generate_test_event('GET', PUBLIC_COMPACT_JURISDICTION_ENDPOINT_RESOURCE)

        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))
        response_body = json.loads(response['body'])

        self.assertEqual(
            [],
            response_body,
        )

    def test_get_compact_jurisdictions_returns_list_of_configured_jurisdictions(self):
        """Test getting list of jurisdictions configured for a compact."""
        from handlers.compact_configuration import compact_configuration_api_handler

        # Load jurisdictions and active member jurisdictions
        load_compact_active_member_jurisdictions(postal_abbreviations=['ky', 'oh'])

        event = generate_test_event('GET', PUBLIC_COMPACT_JURISDICTION_ENDPOINT_RESOURCE)

        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))
        response_body = json.loads(response['body'])

        # Sort to ensure consistent order for comparison
        sorted_response = sorted(response_body, key=lambda x: x['postalAbbreviation'])

        self.assertEqual(
            [
                {'compact': 'aslp', 'jurisdictionName': 'Kentucky', 'postalAbbreviation': 'ky'},
                {'compact': 'aslp', 'jurisdictionName': 'Ohio', 'postalAbbreviation': 'oh'},
            ],
            sorted_response,
        )


@mock_aws
class TestStaffUsersCompactConfiguration(TstFunction):
    """Test suite for managing compact configurations."""

    def _when_testing_get_compact_configuration_with_existing_compact_configuration(self):
        compact_config = self.test_data_generator.put_default_compact_configuration_in_configuration_table()
        event = generate_test_event('GET', COMPACT_CONFIGURATION_ENDPOINT_RESOURCE)
        event['pathParameters']['compact'] = compact_config['compactAbbr']
        return event, compact_config

    def _when_testing_put_compact_configuration_with_existing_configuration(
        self, set_payment_fields: bool = True, transaction_fee_zero: bool = False
    ):
        from cc_common.utils import ResponseEncoder

        value_overrides = {}
        if set_payment_fields:
            value_overrides.update(
                {'paymentProcessorPublicFields': {'publicClientKey': 'some-key', 'apiLoginId': 'some-login-id'}}
            )
        compact_config = self.test_data_generator.put_default_compact_configuration_in_configuration_table(
            value_overrides=value_overrides
        )

        event = generate_test_event('PUT', COMPACT_CONFIGURATION_ENDPOINT_RESOURCE)
        event['pathParameters']['compact'] = compact_config.compactAbbr
        # add compact admin scope to the event
        event['requestContext']['authorizer']['claims']['scope'] = f'{compact_config.compactAbbr}/admin'
        event['requestContext']['authorizer']['claims']['sub'] = 'some-admin-id'

        # we only allow the following values in the body
        event['body'] = json.dumps(
            {
                'compactCommissionFee': compact_config.compactCommissionFee,
                'licenseeRegistrationEnabled': compact_config.licenseeRegistrationEnabled,
                'compactOperationsTeamEmails': compact_config.compactOperationsTeamEmails,
                'compactAdverseActionsNotificationEmails': compact_config.compactAdverseActionsNotificationEmails,
                'compactSummaryReportNotificationEmails': compact_config.compactSummaryReportNotificationEmails,
                'transactionFeeConfiguration': compact_config.transactionFeeConfiguration
                if not transaction_fee_zero
                else {
                    'licenseeCharges': {'chargeAmount': 0.00, 'chargeType': 'FLAT_FEE_PER_PRIVILEGE', 'active': True}
                },
            },
            cls=ResponseEncoder,
        )
        return event, compact_config

    def _when_testing_put_compact_configuration(self, transaction_fee_zero: bool = False):
        from cc_common.utils import ResponseEncoder

        compact_config = self.test_data_generator.generate_default_compact_configuration(
            value_overrides={'licenseeRegistrationEnabled': False}
        )
        event = generate_test_event('PUT', COMPACT_CONFIGURATION_ENDPOINT_RESOURCE)
        event['pathParameters']['compact'] = compact_config.compactAbbr
        # add compact admin scope to the event
        event['requestContext']['authorizer']['claims']['scope'] = f'{compact_config.compactAbbr}/admin'
        event['requestContext']['authorizer']['claims']['sub'] = 'some-admin-id'

        # we only allow the following values in the body
        event['body'] = json.dumps(
            {
                'compactCommissionFee': compact_config.compactCommissionFee,
                'licenseeRegistrationEnabled': compact_config.licenseeRegistrationEnabled,
                'compactOperationsTeamEmails': compact_config.compactOperationsTeamEmails,
                'compactAdverseActionsNotificationEmails': compact_config.compactAdverseActionsNotificationEmails,
                'compactSummaryReportNotificationEmails': compact_config.compactSummaryReportNotificationEmails,
                'configuredStates': compact_config.configuredStates,
                'transactionFeeConfiguration': compact_config.transactionFeeConfiguration
                if not transaction_fee_zero
                else {
                    'licenseeCharges': {'chargeAmount': 0.00, 'chargeType': 'FLAT_FEE_PER_PRIVILEGE', 'active': True}
                },
            },
            cls=ResponseEncoder,
        )
        return event, compact_config

    def test_get_compact_configuration_returns_invalid_exception_if_invalid_http_method(self):
        """Test getting a compact configuration returns an invalid exception if the HTTP method is invalid."""
        from handlers.compact_configuration import compact_configuration_api_handler

        event = generate_test_event('PATCH', COMPACT_CONFIGURATION_ENDPOINT_RESOURCE)

        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(400, response['statusCode'], msg=json.loads(response['body']))
        response_body = json.loads(response['body'])

        self.assertEqual(
            {'message': 'Invalid HTTP method'},
            response_body,
        )

    def test_get_compact_configuration_returns_invalid_exception_if_invalid_compact(self):
        """Test getting an error if invalid compact is provided."""
        from handlers.compact_configuration import compact_configuration_api_handler

        event = generate_test_event('GET', COMPACT_CONFIGURATION_ENDPOINT_RESOURCE)
        event['pathParameters']['compact'] = 'invalid_compact'

        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(400, response['statusCode'], msg=json.loads(response['body']))
        response_body = json.loads(response['body'])

        self.assertEqual(
            {'message': 'Invalid compact abbreviation: invalid_compact'},
            response_body,
        )

    def test_get_compact_configuration_returns_empty_compact_configuration_if_no_configuration_exists(self):
        """Test getting a compact configuration returns a compact configuration."""
        from handlers.compact_configuration import compact_configuration_api_handler

        event = generate_test_event('GET', COMPACT_CONFIGURATION_ENDPOINT_RESOURCE)

        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))
        response_body = json.loads(response['body'])

        self.assertEqual(
            {
                'compactAbbr': 'aslp',
                'compactName': 'Audiology and Speech Language Pathology',
                'compactCommissionFee': {'feeType': 'FLAT_RATE', 'feeAmount': None},
                'compactOperationsTeamEmails': [],
                'compactAdverseActionsNotificationEmails': [],
                'compactSummaryReportNotificationEmails': [],
                'licenseeRegistrationEnabled': False,
                'configuredStates': [],
            },
            response_body,
        )

    def test_put_compact_configuration_rejects_invalid_compact_with_auth_error(self):
        """Test putting a compact configuration rejects an invalid compact abbreviation."""
        from handlers.compact_configuration import compact_configuration_api_handler

        event = generate_test_event('PUT', COMPACT_CONFIGURATION_ENDPOINT_RESOURCE)
        event['pathParameters']['compact'] = 'foo'
        # add compact admin scope to the event
        event['requestContext']['authorizer']['scopes'] = 'aslp/admin'

        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(403, response['statusCode'])
        self.assertIn('Access denied', json.loads(response['body'])['message'])

    def test_put_compact_configuration_rejects_state_admin_with_auth_error(self):
        """Test putting a compact configuration rejects an invalid compact abbreviation."""
        from handlers.compact_configuration import compact_configuration_api_handler

        event = generate_test_event('PUT', COMPACT_CONFIGURATION_ENDPOINT_RESOURCE)
        event['pathParameters']['compact'] = 'aslp'
        # add state admin scope to the event, but not compact admin
        event['requestContext']['authorizer']['scopes'] = 'oh/aslp.admin'

        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(403, response['statusCode'])
        self.assertIn('Access denied', json.loads(response['body'])['message'])

    def test_put_compact_configuration_stores_new_compact_configuration(self):
        """Test putting a compact configuration stores the compact configuration."""
        from cc_common.data_model.schema.compact import CompactConfigurationData
        from handlers.compact_configuration import compact_configuration_api_handler

        event, compact_config = self._when_testing_put_compact_configuration()

        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))

        # load the record from the configuration table
        serialized_compact_config = compact_config.serialize_to_database_record()
        response = self.config.compact_configuration_table.get_item(
            Key={'pk': serialized_compact_config['pk'], 'sk': serialized_compact_config['sk']}
        )

        stored_compact_data = CompactConfigurationData.from_database_record(response['Item'])

        self.assertEqual(compact_config.to_dict(), stored_compact_data.to_dict())

    def test_put_compact_configuration_preserves_payment_processor_fields_when_updating_compact_configuration(self):
        """Test putting a compact configuration preserves existing fields not set by the request body."""
        from cc_common.data_model.schema.compact import CompactConfigurationData
        from handlers.compact_configuration import compact_configuration_api_handler

        event, compact_config = self._when_testing_put_compact_configuration_with_existing_configuration()

        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))

        # load the record from the configuration table
        serialized_compact_config = compact_config.serialize_to_database_record()
        response = self.config.compact_configuration_table.get_item(
            Key={'pk': serialized_compact_config['pk'], 'sk': serialized_compact_config['sk']}
        )

        stored_compact_data = CompactConfigurationData.from_database_record(response['Item'])
        # the compact_config variable has the 'paymentProcessorPublicFields' field, which we expect to also be
        # present in the stored_compact_data
        self.assertEqual(compact_config.to_dict(), stored_compact_data.to_dict())

    def test_put_compact_configuration_removes_transaction_fee_when_zero(self):
        """Test that when a transaction fee of 0 is provided, the transaction fee configuration is removed."""
        from cc_common.data_model.schema.compact import CompactConfigurationData
        from handlers.compact_configuration import compact_configuration_api_handler

        event, expected_config = self._when_testing_put_compact_configuration(transaction_fee_zero=True)

        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))

        # load the record from the configuration table
        serialized_compact_config = expected_config.serialize_to_database_record()
        response = self.config.compact_configuration_table.get_item(
            Key={'pk': serialized_compact_config['pk'], 'sk': serialized_compact_config['sk']}
        )

        stored_compact_data = CompactConfigurationData.from_database_record(response['Item'])

        # Verify the transaction fee configuration is not present
        self.assertNotIn('transactionFeeConfiguration', stored_compact_data.to_dict())

    def test_put_compact_configuration_rejects_disabling_licensee_registration(self):
        """Test that a compact configuration update is rejected if trying to disable licensee registration after enabling it."""
        from handlers.compact_configuration import compact_configuration_api_handler

        # First, create a compact configuration with licenseeRegistrationEnabled=True
        event, _ = self._when_testing_put_compact_configuration_with_existing_configuration()

        # Now attempt to update with licenseeRegistrationEnabled=False
        body = json.loads(event['body'])
        body['licenseeRegistrationEnabled'] = False
        event['body'] = json.dumps(body)

        # Should be rejected with a 400 error
        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(400, response['statusCode'])
        response_body = json.loads(response['body'])
        self.assertIn('Once licensee registration has been enabled, it cannot be disabled', response_body['message'])

    def test_put_compact_configuration_rejects_enabling_licensee_registration_without_payment_credentials(self):
        """Test that a compact configuration update is rejected if trying to enable licensee registration without payment processor credentials."""
        from handlers.compact_configuration import compact_configuration_api_handler

        # Attempt to enable licensee registration without any existing configuration (no payment credentials)
        event, _ = self._when_testing_put_compact_configuration()
        body = json.loads(event['body'])
        body['licenseeRegistrationEnabled'] = True
        event['body'] = json.dumps(body)

        # Should be rejected with a 400 error
        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(400, response['statusCode'])
        response_body = json.loads(response['body'])
        self.assertIn(
            'Authorize.net credentials need to be uploaded before the compact can be marked as live.',
            response_body['message'],
        )

    def test_put_compact_configuration_rejects_enabling_licensee_registration_with_existing_config_without_payment_credentials(
        self,
    ):
        """Test that a compact configuration update is rejected if trying to enable licensee registration when existing config has no payment credentials."""
        from handlers.compact_configuration import compact_configuration_api_handler

        # First, create a basic compact configuration without payment credentials
        event, _ = self._when_testing_put_compact_configuration_with_existing_configuration(set_payment_fields=False)

        # Now attempt to enable licensee registration without payment credentials
        body = json.loads(event['body'])
        body['licenseeRegistrationEnabled'] = True
        event['body'] = json.dumps(body)

        # Should be rejected with a 400 error
        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(400, response['statusCode'])
        response_body = json.loads(response['body'])
        self.assertIn(
            'Authorize.net credentials not configured for compact. Please upload valid Authorize.net credentials.',
            response_body['message'],
        )

    def test_put_compact_configuration_rejects_removing_configured_states(self):
        """Test that removing states from configuredStates is rejected."""
        from handlers.compact_configuration import compact_configuration_api_handler

        # First, create a compact configuration with some configured states
        event, original_config = self._when_testing_put_compact_configuration()
        body = json.loads(event['body'])
        body['configuredStates'] = [
            {'jurisdictionName': 'Kentucky', 'postalAbbreviation': 'ky', 'isLive': False},
            {'jurisdictionName': 'Ohio', 'postalAbbreviation': 'oh', 'isLive': True},
        ]
        event['body'] = json.dumps(body)

        # Submit the configuration
        compact_configuration_api_handler(event, self.mock_context)

        # Now attempt to remove one of the states
        event, _ = self._when_testing_put_compact_configuration()
        body = json.loads(event['body'])
        body['configuredStates'] = [
            {'jurisdictionName': 'Kentucky', 'postalAbbreviation': 'ky', 'isLive': False},
            # Removed Ohio
        ]
        event['body'] = json.dumps(body)

        # Should be rejected with a 400 error
        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(400, response['statusCode'])
        response_body = json.loads(response['body'])
        self.assertIn('States cannot be removed from configuredStates', response_body['message'])
        self.assertIn('oh', response_body['message'])

    def test_put_compact_configuration_rejects_downgrading_is_live_status(self):
        """Test that changing isLive from true to false is rejected."""
        from handlers.compact_configuration import compact_configuration_api_handler

        # First, create a compact configuration with a live state
        event, original_config = self._when_testing_put_compact_configuration()
        body = json.loads(event['body'])
        body['configuredStates'] = [
            {'jurisdictionName': 'Kentucky', 'postalAbbreviation': 'ky', 'isLive': True},
            {'jurisdictionName': 'Ohio', 'postalAbbreviation': 'oh', 'isLive': False},
        ]
        event['body'] = json.dumps(body)

        # Submit the configuration
        compact_configuration_api_handler(event, self.mock_context)

        # Now attempt to change Kentucky from live to non-live
        event, _ = self._when_testing_put_compact_configuration()
        body = json.loads(event['body'])
        body['configuredStates'] = [
            {'jurisdictionName': 'Kentucky', 'postalAbbreviation': 'ky', 'isLive': False},  # Changed to false
            {'jurisdictionName': 'Ohio', 'postalAbbreviation': 'oh', 'isLive': False},
        ]
        event['body'] = json.dumps(body)

        # Should be rejected with a 400 error
        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(400, response['statusCode'])
        response_body = json.loads(response['body'])
        self.assertIn('cannot be changed from live to non-live status', response_body['message'])
        self.assertIn('ky', response_body['message'])

    def test_put_compact_configuration_allows_upgrading_is_live_status(self):
        """Test that changing isLive from false to true is allowed."""
        from handlers.compact_configuration import compact_configuration_api_handler

        # First, create a compact configuration with a non-live state
        event, original_config = self._when_testing_put_compact_configuration()
        body = json.loads(event['body'])
        body['configuredStates'] = [
            {'jurisdictionName': 'Kentucky', 'postalAbbreviation': 'ky', 'isLive': False},
        ]
        event['body'] = json.dumps(body)

        # Submit the configuration
        compact_configuration_api_handler(event, self.mock_context)

        # Now change Kentucky from non-live to live
        event, _ = self._when_testing_put_compact_configuration()
        body = json.loads(event['body'])
        body['configuredStates'] = [
            {'jurisdictionName': 'Kentucky', 'postalAbbreviation': 'ky', 'isLive': True},  # Changed to true
        ]
        event['body'] = json.dumps(body)

        # Should be accepted
        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'])

        # Verify the state was updated in the database
        stored_compact_data = self.config.compact_configuration_client.get_compact_configuration(
            original_config.compactAbbr
        )
        configured_states = stored_compact_data.configuredStates

        self.assertEqual(len(configured_states), 1)
        self.assertEqual(configured_states[0]['postalAbbreviation'], 'ky')
        self.assertTrue(configured_states[0]['isLive'])

    def test_put_compact_configuration_rejects_adding_new_states(self):
        """Test that adding new states to configuredStates is rejected."""
        from handlers.compact_configuration import compact_configuration_api_handler

        # First, create a compact configuration with one state
        event, original_config = self._when_testing_put_compact_configuration()
        body = json.loads(event['body'])
        body['configuredStates'] = [
            {'jurisdictionName': 'Kentucky', 'postalAbbreviation': 'ky', 'isLive': False},
        ]
        event['body'] = json.dumps(body)

        # Submit the configuration
        compact_configuration_api_handler(event, self.mock_context)

        # Now attempt to add a new state
        event, _ = self._when_testing_put_compact_configuration()
        body = json.loads(event['body'])
        body['configuredStates'] = [
            {'jurisdictionName': 'Kentucky', 'postalAbbreviation': 'ky', 'isLive': False},
            {'jurisdictionName': 'Ohio', 'postalAbbreviation': 'oh', 'isLive': True},  # New state
        ]
        event['body'] = json.dumps(body)

        # Should be rejected with a 400 error
        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(400, response['statusCode'])
        response_body = json.loads(response['body'])
        self.assertIn('States cannot be manually added to configuredStates', response_body['message'])
        self.assertIn('oh', response_body['message'])

    def test_put_compact_configuration_rejects_duplicate_configured_states(self):
        """Test that duplicate states in configuredStates are rejected."""
        from handlers.compact_configuration import compact_configuration_api_handler

        event, original_config = self._when_testing_put_compact_configuration()
        body = json.loads(event['body'])
        body['configuredStates'] = [
            {'jurisdictionName': 'Kentucky', 'postalAbbreviation': 'ky', 'isLive': False},
            {'jurisdictionName': 'Ohio', 'postalAbbreviation': 'oh', 'isLive': True},
            {'jurisdictionName': 'Kentucky', 'postalAbbreviation': 'ky', 'isLive': True},  # Duplicate
        ]
        event['body'] = json.dumps(body)

        # Should be rejected with a 400 error
        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(400, response['statusCode'])
        response_body = json.loads(response['body'])
        self.assertIn('Duplicate states found in configuredStates', response_body['message'])
        self.assertIn('ky', response_body['message'])
        self.assertIn('Each state can only appear once', response_body['message'])


TEST_MILITARY_RATE = Decimal('40.00')


@mock_aws
class TestStaffUsersJurisdictionConfiguration(TstFunction):
    """Test suite for managing jurisdiction configurations."""

    def _when_testing_put_jurisdiction_configuration(self):
        from cc_common.utils import ResponseEncoder

        jurisdiction_config = self.test_data_generator.generate_default_jurisdiction_configuration()
        event = generate_test_event('PUT', JURISDICTION_CONFIGURATION_ENDPOINT_RESOURCE)
        event['pathParameters']['jurisdiction'] = jurisdiction_config.postalAbbreviation
        # add compact admin scope to the event
        event['requestContext']['authorizer']['claims']['scope'] = (
            f'{jurisdiction_config.postalAbbreviation}/{jurisdiction_config.compact}.admin'
        )
        event['requestContext']['authorizer']['claims']['sub'] = 'some-admin-id'

        event['body'] = json.dumps(
            {
                'jurisdictionOperationsTeamEmails': jurisdiction_config.jurisdictionOperationsTeamEmails,
                'jurisdictionAdverseActionsNotificationEmails': jurisdiction_config.jurisdictionAdverseActionsNotificationEmails,
                'jurisdictionSummaryReportNotificationEmails': jurisdiction_config.jurisdictionSummaryReportNotificationEmails,
                'licenseeRegistrationEnabled': jurisdiction_config.licenseeRegistrationEnabled,
                'jurisprudenceRequirements': jurisdiction_config.jurisprudenceRequirements,
                'privilegeFees': jurisdiction_config.privilegeFees,
            },
            cls=ResponseEncoder,
        )

        return event, jurisdiction_config

    def _when_testing_invalid_privilege_fees(self, privilege_fees: list[dict]):
        event, jurisdiction_config = self._when_testing_put_jurisdiction_configuration()

        body = json.loads(event['body'])
        body['privilegeFees'] = privilege_fees
        event['body'] = json.dumps(body)

        return event

    def test_get_jurisdiction_configuration_returns_invalid_exception_if_invalid_http_method(self):
        """Test getting a jurisdiction configuration returns an invalid exception if the HTTP method is invalid."""
        from handlers.compact_configuration import compact_configuration_api_handler

        event = generate_test_event('PATCH', JURISDICTION_CONFIGURATION_ENDPOINT_RESOURCE)
        event['pathParameters']['jurisdiction'] = 'ky'

        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(400, response['statusCode'], msg=json.loads(response['body']))
        response_body = json.loads(response['body'])

        self.assertEqual(
            {'message': 'Invalid HTTP method'},
            response_body,
        )

    def test_get_jurisdiction_configuration_returns_invalid_exception_if_invalid_compact(self):
        """Test getting an error if invalid compact is provided."""
        from handlers.compact_configuration import compact_configuration_api_handler

        event = generate_test_event('GET', JURISDICTION_CONFIGURATION_ENDPOINT_RESOURCE)
        event['pathParameters']['compact'] = 'invalid_compact'
        event['pathParameters']['jurisdiction'] = 'ky'

        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(400, response['statusCode'], msg=json.loads(response['body']))
        response_body = json.loads(response['body'])

        self.assertEqual(
            {'message': 'Invalid compact abbreviation: invalid_compact'},
            response_body,
        )

    def test_get_jurisdiction_configuration_returns_invalid_exception_if_invalid_jurisdiction(self):
        """Test getting an error if invalid jurisdiction is provided."""
        from handlers.compact_configuration import compact_configuration_api_handler

        event = generate_test_event('GET', JURISDICTION_CONFIGURATION_ENDPOINT_RESOURCE)
        event['pathParameters']['jurisdiction'] = 'invalid_jurisdiction'

        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(400, response['statusCode'], msg=json.loads(response['body']))
        response_body = json.loads(response['body'])

        self.assertEqual(
            {'message': 'Invalid jurisdiction postal abbreviation: invalid_jurisdiction'},
            response_body,
        )

    def test_get_jurisdiction_configuration_returns_empty_jurisdiction_configuration_if_no_configuration_exists(self):
        """Test getting a jurisdiction configuration returns a default configuration if none exists."""
        from cc_common.license_util import LicenseUtility
        from handlers.compact_configuration import compact_configuration_api_handler

        event = generate_test_event('GET', JURISDICTION_CONFIGURATION_ENDPOINT_RESOURCE)
        event['pathParameters']['jurisdiction'] = 'ky'

        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))
        response_body = json.loads(response['body'])

        # Get the expected license types for this compact
        valid_license_types = LicenseUtility.get_valid_license_type_abbreviations('aslp')
        expected_privilege_fees = [
            {'licenseTypeAbbreviation': lt, 'amount': None, 'militaryRate': None} for lt in sorted(valid_license_types)
        ]

        # Sort the response privilege fees by license type for consistent comparison
        response_body['privilegeFees'] = sorted(
            response_body['privilegeFees'], key=lambda x: x['licenseTypeAbbreviation']
        )

        # Verify the jurisdiction name is set correctly from the mapping and privilege fees are created correctly
        self.assertEqual(
            {
                'compact': 'aslp',
                'jurisdictionAdverseActionsNotificationEmails': [],
                'jurisdictionName': 'Kentucky',
                'jurisdictionOperationsTeamEmails': [],
                'jurisdictionSummaryReportNotificationEmails': [],
                'jurisprudenceRequirements': {'linkToDocumentation': None, 'required': False},
                'licenseeRegistrationEnabled': False,
                'postalAbbreviation': 'ky',
                'privilegeFees': expected_privilege_fees,
            },
            response_body,
        )

    def test_get_jurisdiction_configuration_returns_configuration_if_exists(self):
        """Test getting a jurisdiction configuration returns the existing configuration."""
        from handlers.compact_configuration import compact_configuration_api_handler

        test_jurisdiction_config = (
            self.test_data_generator.put_default_jurisdiction_configuration_in_configuration_table()
        )

        # Now retrieve it
        event = generate_test_event('GET', JURISDICTION_CONFIGURATION_ENDPOINT_RESOURCE)
        event['pathParameters']['jurisdiction'] = test_jurisdiction_config.postalAbbreviation

        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))
        response_body = json.loads(response['body'])

        # Verify the returned configuration matches what we created
        self.assertEqual(
            {
                'compact': test_jurisdiction_config.compact,
                'jurisdictionName': test_jurisdiction_config.jurisdictionName,
                'jurisprudenceRequirements': test_jurisdiction_config.jurisprudenceRequirements,
                'postalAbbreviation': test_jurisdiction_config.postalAbbreviation,
                'privilegeFees': test_jurisdiction_config.privilegeFees,
                'jurisdictionOperationsTeamEmails': test_jurisdiction_config.jurisdictionOperationsTeamEmails,
                'jurisdictionAdverseActionsNotificationEmails': test_jurisdiction_config.jurisdictionAdverseActionsNotificationEmails,
                'jurisdictionSummaryReportNotificationEmails': test_jurisdiction_config.jurisdictionSummaryReportNotificationEmails,
                'licenseeRegistrationEnabled': test_jurisdiction_config.licenseeRegistrationEnabled,
            },
            response_body,
        )

    def test_put_jurisdiction_configuration_rejects_invalid_jurisdiction_with_auth_error(self):
        """Test putting a jurisdiction configuration rejects an invalid jurisdiction abbreviation."""
        from handlers.compact_configuration import compact_configuration_api_handler

        event = generate_test_event('PUT', JURISDICTION_CONFIGURATION_ENDPOINT_RESOURCE)
        # Set the jurisdiction to an invalid one
        event['pathParameters']['jurisdiction'] = 'invalid_jurisdiction'

        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(403, response['statusCode'])
        self.assertIn('Access denied', json.loads(response['body'])['message'])

    def test_put_jurisdiction_configuration_rejects_compact_admin_with_auth_error(self):
        """Test putting a jurisdiction configuration rejects an update request from a compact admin."""
        from handlers.compact_configuration import compact_configuration_api_handler

        event = generate_test_event('PUT', JURISDICTION_CONFIGURATION_ENDPOINT_RESOURCE)
        event['pathParameters'] = {'compact': 'aslp', 'jurisdiction': 'oh'}
        # add compact admin scope to the event, but not state admin
        event['requestContext']['authorizer']['claims']['scope'] = 'aslp/admin'
        event['requestContext']['authorizer']['claims']['sub'] = 'some-admin-id'

        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(403, response['statusCode'])
        self.assertIn('Access denied', json.loads(response['body'])['message'])

    def test_put_jurisdiction_configuration_stores_jurisdiction_configuration(self):
        """Test putting a jurisdiction configuration stores the jurisdiction configuration."""
        from cc_common.data_model.schema.jurisdiction import JurisdictionConfigurationData
        from handlers.compact_configuration import compact_configuration_api_handler

        event, jurisdiction_config = self._when_testing_put_jurisdiction_configuration()

        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))

        # load the record from the configuration table
        serialized_jurisdiction_config = jurisdiction_config.serialize_to_database_record()
        response = self.config.compact_configuration_table.get_item(
            Key={'pk': serialized_jurisdiction_config['pk'], 'sk': serialized_jurisdiction_config['sk']}
        )

        stored_jurisdiction_data = JurisdictionConfigurationData.from_database_record(response['Item'])

        self.assertEqual(jurisdiction_config.to_dict(), stored_jurisdiction_data.to_dict())

    def test_put_jurisdiction_configuration_accepts_null_values_for_optional_fields(self):
        """Test putting a jurisdiction configuration accepts null values for optional fields."""
        from cc_common.data_model.schema.jurisdiction import JurisdictionConfigurationData
        from cc_common.utils import ResponseEncoder
        from handlers.compact_configuration import compact_configuration_api_handler

        event, jurisdiction_config = self._when_testing_put_jurisdiction_configuration()

        # Modify the body to include null values for optional fields
        body = json.loads(event['body'])

        # Set linkToDocumentation to null
        body['jurisprudenceRequirements'] = {'required': True, 'linkToDocumentation': None}

        # Set militaryRate to null for the first privilege fee
        body['privilegeFees'][0]['militaryRate'] = None

        event['body'] = json.dumps(body, cls=ResponseEncoder)

        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))

        # Verify the configuration was stored with null values
        serialized_jurisdiction_config = jurisdiction_config.serialize_to_database_record()
        db_response = self.config.compact_configuration_table.get_item(
            Key={'pk': serialized_jurisdiction_config['pk'], 'sk': serialized_jurisdiction_config['sk']}
        )

        stored_jurisdiction_data = JurisdictionConfigurationData.from_database_record(db_response['Item'])
        stored_dict = stored_jurisdiction_data.to_dict()

        # Verify the optional fields have null values
        self.assertIsNone(stored_dict['jurisprudenceRequirements']['linkToDocumentation'])

        # Find the privilege fee that should have null militaryRate
        self.assertIsNone(stored_dict['privilegeFees'][0]['militaryRate'])

    def test_put_jurisdiction_configuration_rejects_invalid_license_type_abbreviation(self):
        """Test putting a jurisdiction configuration with an invalid license type abbreviation is rejected."""
        from handlers.compact_configuration import compact_configuration_api_handler

        event = self._when_testing_invalid_privilege_fees(
            privilege_fees=[{'licenseTypeAbbreviation': 'INVALID_LICENSE_TYPE', 'amount': 100.00}]
        )

        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(400, response['statusCode'])
        response_body = json.loads(response['body'])
        self.assertIn(
            'Invalid jurisdiction configuration: '
            "{'privilegeFees': ['Invalid license type abbreviation(s): INVALID_LICENSE_TYPE.",
            response_body['message'],
        )

    def test_put_jurisdiction_configuration_rejects_duplicate_license_type_abbreviation(self):
        """Test putting a jurisdiction configuration with a duplicate license type is rejected."""
        from handlers.compact_configuration import compact_configuration_api_handler

        event = self._when_testing_invalid_privilege_fees(
            privilege_fees=[
                {'licenseTypeAbbreviation': 'slp', 'amount': 100.00},
                {'licenseTypeAbbreviation': 'aud', 'amount': 100.00},
                {'licenseTypeAbbreviation': 'slp', 'amount': 50.00},
            ]
        )

        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(400, response['statusCode'])
        response_body = json.loads(response['body'])
        self.assertIn(
            'Invalid jurisdiction configuration: '
            "{'privilegeFees': ['Duplicate privilege fees found for same license type abbreviation(s).",
            response_body['message'],
        )

    def test_put_jurisdiction_configuration_rejects_missing_license_type_abbreviation(self):
        """Test putting a jurisdiction configuration with a missing license type abbreviation is rejected."""
        from handlers.compact_configuration import compact_configuration_api_handler

        event = self._when_testing_invalid_privilege_fees(
            privilege_fees=[{'licenseTypeAbbreviation': 'slp', 'amount': 100.00}]
        )

        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(400, response['statusCode'])
        response_body = json.loads(response['body'])
        self.assertIn(
            "Invalid jurisdiction configuration: {'privilegeFees': "
            "['Missing privilege fee(s) for required license type(s): aud. "
            'All valid license types for aslp must be included',
            response_body['message'],
        )

    def test_put_jurisdiction_configuration_rejects_disabling_licensee_registration(self):
        """Test that a jurisdiction configuration update is rejected if trying to disable licensee registration after enabling it."""
        from handlers.compact_configuration import compact_configuration_api_handler

        # First, create a jurisdiction configuration with licenseeRegistrationEnabled=True
        event, jurisdiction_config = self._when_testing_put_jurisdiction_configuration()
        # Set licenseeRegistrationEnabled to True in the request body
        body = json.loads(event['body'])
        body['licenseeRegistrationEnabled'] = True
        event['body'] = json.dumps(body)

        # Submit the configuration
        compact_configuration_api_handler(event, self.mock_context)

        # Now attempt to update with licenseeRegistrationEnabled=False
        event, _ = self._when_testing_put_jurisdiction_configuration()
        body = json.loads(event['body'])
        body['licenseeRegistrationEnabled'] = False
        event['body'] = json.dumps(body)

        # Should be rejected with a 400 error
        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(400, response['statusCode'])
        response_body = json.loads(response['body'])
        self.assertIn('Once licensee registration has been enabled, it cannot be disabled', response_body['message'])
