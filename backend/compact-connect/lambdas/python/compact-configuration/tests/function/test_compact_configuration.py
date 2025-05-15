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
    """
    Creates a mock API Gateway event for testing with specified HTTP method and resource.
    
    Args:
        method: The HTTP method to set in the event (e.g., 'GET', 'POST').
        resource: The API resource path to set in the event.
    
    Returns:
        A dictionary representing the API Gateway event with the given method, resource, and a default 'compact' path parameter.
    """
    with open('../common/tests/resources/api-event.json') as f:
        event = json.load(f)
        event['httpMethod'] = method
        event['resource'] = resource
        event['pathParameters'] = {
            'compact': 'aslp',
        }

    return event


def load_compact_active_member_jurisdictions(postal_abbreviations: list[str], compact: str = 'aslp'):
    """
    Inserts active member jurisdictions for a specified compact using provided postal abbreviations.
    
    Args:
        postal_abbreviations: List of jurisdiction postal abbreviations to add as active members.
        compact: Compact abbreviation to associate with the jurisdictions. Defaults to 'aslp'.
    """
    from common_test.test_data_generator import TestDataGenerator

    TestDataGenerator.put_compact_active_member_jurisdictions(
        compact=compact, postal_abbreviations=postal_abbreviations
    )


@mock_aws
class TestGetStaffUsersCompactJurisdictions(TstFunction):
    """Test suite for get compact jurisdiction endpoints."""

    def test_get_compact_jurisdictions_returns_invalid_exception_if_invalid_http_method(self):
        """
        Tests that a PATCH request to the staff users compact jurisdictions endpoint returns a 400 error with an 'Invalid HTTP method' message when the HTTP method is not allowed.
        """
        from handlers.compact_configuration import compact_configuration_api_handler

        event = generate_test_event('PATCH', STAFF_USERS_COMPACT_JURISDICTION_ENDPOINT_RESOURCE)

        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(400, response['statusCode'], msg=json.loads(response['body']))
        response_body = json.loads(response['body'])

        self.assertEqual(
            {'message': 'Invalid HTTP method'},
            response_body,
        )

    def test_get_compact_jurisdictions_returns_empty_list_if_no_active_jurisdictions(self):
        """
        Verifies that the API returns an empty list when no active jurisdictions are configured.
        
        Sends a GET request to the staff users compact jurisdictions endpoint and asserts that the response is 200 with an empty list in the body.
        """
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
        """
        Verifies that the API returns a sorted list of configured jurisdictions for a compact.
        
        This test loads active member jurisdictions, sends a GET request to the staff users compact jurisdictions endpoint, and asserts that the response contains the expected list of jurisdictions sorted by postal abbreviation.
        """
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

    def test_get_compact_jurisdictions_returns_invalid_exception_if_invalid_http_methog(self):
        """
        Tests that a PATCH request to the public compact jurisdictions endpoint returns a 400 error with an 'Invalid HTTP method' message.
        """
        from handlers.compact_configuration import compact_configuration_api_handler

        event = generate_test_event('PATCH', PUBLIC_COMPACT_JURISDICTION_ENDPOINT_RESOURCE)

        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(400, response['statusCode'], msg=json.loads(response['body']))
        response_body = json.loads(response['body'])

        self.assertEqual(
            {'message': 'Invalid HTTP method'},
            response_body,
        )

    def test_get_compact_jurisdictions_returns_empty_list_if_no_active_jurisdictions(self):
        """
        Tests that the API returns an empty list when no active jurisdictions are configured.
        """
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
        """
        Verifies that the API returns a sorted list of configured jurisdictions for a compact.
        
        This test loads active member jurisdictions, sends a GET request to the public compact jurisdictions endpoint, and asserts that the response contains the expected jurisdictions sorted by postal abbreviation.
        """
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
        """
        Prepares a GET event and inserts a default compact configuration for testing.
        
        Returns:
            A tuple containing the generated GET event with the compact abbreviation set in path parameters, and the inserted compact configuration dictionary.
        """
        compact_config = self.test_data_generator.put_default_compact_configuration_in_configuration_table()
        event = generate_test_event('GET', COMPACT_CONFIGURATION_ENDPOINT_RESOURCE)
        event['pathParameters']['compact'] = compact_config['compactAbbr']
        return event, compact_config

    def _when_testing_put_compact_configuration(self, transaction_fee_zero: bool = False):
        """
        Prepares a mock API Gateway PUT event and default compact configuration for testing.
        
        If `transaction_fee_zero` is True, sets the transaction fee amount to zero in the event body. Returns the event dictionary and the generated compact configuration object.
        """
        from cc_common.utils import ResponseEncoder

        compact_config = self.test_data_generator.generate_default_compact_configuration()
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

    def test_get_compact_configuration_returns_invalid_exception_if_invalid_http_method(self):
        """
        Verifies that a PATCH request to the compact configuration endpoint returns a 400 error with an 'Invalid HTTP method' message.
        """
        from handlers.compact_configuration import compact_configuration_api_handler

        event = generate_test_event('PATCH', COMPACT_CONFIGURATION_ENDPOINT_RESOURCE)

        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(400, response['statusCode'], msg=json.loads(response['body']))
        response_body = json.loads(response['body'])

        self.assertEqual(
            {'message': 'Invalid HTTP method'},
            response_body,
        )

    def test_get_compact_configuration_returns_empty_compact_configuration_if_no_configuration_exists(self):
        """
        Verifies that retrieving a compact configuration with no existing data returns default values.
        
        Sends a GET request to the compact configuration endpoint and asserts that the response contains the default compact configuration fields with empty lists and null fee amount.
        """
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
            },
            response_body,
        )

    def test_put_compact_configuration_rejects_invalid_compact_with_auth_error(self):
        """
        Tests that a PUT request to update a compact configuration with an invalid compact abbreviation returns a 403 error with an "Access denied" message.
        """
        from handlers.compact_configuration import compact_configuration_api_handler

        event = generate_test_event('PUT', COMPACT_CONFIGURATION_ENDPOINT_RESOURCE)
        event['pathParameters']['compact'] = 'foo'
        # add compact admin scope to the event
        event['requestContext']['authorizer']['scopes'] = 'aslp/admin'

        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(403, response['statusCode'])
        self.assertIn('Access denied', json.loads(response['body'])['message'])

    def test_put_compact_configuration_rejects_state_admin_with_auth_error(self):
        """
        Tests that a state admin without compact admin privileges is denied access when attempting to update a compact configuration.
        
        Verifies that a PUT request with only state admin scope returns a 403 status code and an "Access denied" message.
        """
        from handlers.compact_configuration import compact_configuration_api_handler

        event = generate_test_event('PUT', COMPACT_CONFIGURATION_ENDPOINT_RESOURCE)
        event['pathParameters']['compact'] = 'aslp'
        # add state admin scope to the event, but not compact admin
        event['requestContext']['authorizer']['scopes'] = 'oh/aslp.admin'

        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(403, response['statusCode'])
        self.assertIn('Access denied', json.loads(response['body'])['message'])

    def test_put_compact_configuration_stores_compact_configuration(self):
        """
        Verifies that a PUT request to the compact configuration endpoint stores the configuration data.
        
        This test submits a compact configuration via the API handler, retrieves the stored record from the database, and asserts that the stored data matches the submitted configuration.
        """
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

    def test_put_compact_configuration_removes_transaction_fee_when_zero(self):
        """
        Verifies that providing a transaction fee of zero removes the transaction fee configuration from the stored compact configuration.
        """
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
        """
        Verifies that disabling licensee registration after it has been enabled in a compact configuration is rejected with a 400 error.
        """
        from handlers.compact_configuration import compact_configuration_api_handler

        # First, create a compact configuration with licenseeRegistrationEnabled=True
        event, original_config = self._when_testing_put_compact_configuration()
        # Set licenseeRegistrationEnabled to True in the request body
        body = json.loads(event['body'])
        body['licenseeRegistrationEnabled'] = True
        event['body'] = json.dumps(body)

        # Submit the configuration
        compact_configuration_api_handler(event, self.mock_context)

        # Now attempt to update with licenseeRegistrationEnabled=False
        event, _ = self._when_testing_put_compact_configuration()
        body = json.loads(event['body'])
        body['licenseeRegistrationEnabled'] = False
        event['body'] = json.dumps(body)

        # Should be rejected with a 400 error
        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(400, response['statusCode'])
        response_body = json.loads(response['body'])
        self.assertIn('Once licensee registration has been enabled, it cannot be disabled', response_body['message'])


TEST_MILITARY_RATE = Decimal('40.00')


@mock_aws
class TestStaffUsersJurisdictionConfiguration(TstFunction):
    """Test suite for managing jurisdiction configurations."""

    def _when_testing_put_jurisdiction_configuration(self):
        """
        Prepares a mock API Gateway PUT event and default jurisdiction configuration for testing.
        
        Returns:
            A tuple containing the prepared event dictionary and the generated jurisdiction configuration object.
        """
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
        """
        Prepares a PUT event for jurisdiction configuration with specified invalid privilege fees.
        
        Args:
            privilege_fees: A list of privilege fee dictionaries to include in the event body.
        
        Returns:
            The modified event dictionary with the provided privilege fees.
        """
        event, jurisdiction_config = self._when_testing_put_jurisdiction_configuration()

        body = json.loads(event['body'])
        body['privilegeFees'] = privilege_fees
        event['body'] = json.dumps(body)

        return event

    def test_get_jurisdiction_configuration_returns_invalid_exception_if_invalid_http_method(self):
        """
        Tests that a PATCH request to the jurisdiction configuration endpoint returns a 400 error with an 'Invalid HTTP method' message.
        """
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

    def test_get_jurisdiction_configuration_returns_empty_jurisdiction_configuration_if_no_configuration_exists(self):
        """
        Tests that retrieving a jurisdiction configuration with no existing data returns a default configuration.
        
        Verifies that the response includes the correct jurisdiction name, empty email lists, default privilege fees for all valid license types with null amounts, and other default values.
        """
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
        """
        Verifies that retrieving a jurisdiction configuration returns the stored configuration.
        
        This test inserts a default jurisdiction configuration, sends a GET request for that jurisdiction, and asserts that the response contains the expected configuration data.
        """
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
        """
        Tests that attempting to update a jurisdiction configuration with an invalid jurisdiction abbreviation returns a 403 error with an access denied message.
        """
        from handlers.compact_configuration import compact_configuration_api_handler

        event = generate_test_event('PUT', JURISDICTION_CONFIGURATION_ENDPOINT_RESOURCE)
        # Set the jurisdiction to an invalid one
        event['pathParameters']['jurisdiction'] = 'invalid_jurisdiction'

        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(403, response['statusCode'])
        self.assertIn('Access denied', json.loads(response['body'])['message'])

    def test_put_jurisdiction_configuration_rejects_compact_admin_with_auth_error(self):
        """
        Tests that a compact admin cannot update a jurisdiction configuration and receives a 403 error.
        """
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
        """
        Verifies that submitting a jurisdiction configuration via PUT stores the configuration correctly.
        
        This test sends a PUT request to the jurisdiction configuration endpoint and asserts that the stored configuration in the database matches the submitted data.
        """
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
        """
        Tests that a jurisdiction configuration can be stored with null values for optional fields.
        
        This test verifies that the API accepts and persists null values for optional fields such as
        'linkToDocumentation' in 'jurisprudenceRequirements' and 'militaryRate' in 'privilegeFees'
        when updating a jurisdiction configuration.
        """
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
        """
        Tests that submitting a jurisdiction configuration with an invalid license type abbreviation returns a 400 error with an appropriate validation message.
        """
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
        """
        Tests that submitting a jurisdiction configuration with duplicate license type abbreviations in privilege fees is rejected with a 400 error.
        """
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
        """
        Tests that a jurisdiction configuration PUT request missing required license type abbreviations in privilege fees is rejected with a 400 error.
        """
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
        """
        Verifies that disabling licensee registration after it has been enabled in a jurisdiction configuration is rejected with a 400 error.
        """
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
