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


def load_test_jurisdiction(compact_configuration_table, jurisdiction_overrides: dict):
    with open('../common/tests/resources/dynamo/jurisdiction.json') as f:
        record = json.load(f, parse_float=Decimal)

    record.update(jurisdiction_overrides)
    compact_configuration_table.put_item(Item=record)

    # return record for optional usage in tests
    return record


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

        # load jurisdictions
        load_test_jurisdiction(
            self.config.compact_configuration_table,
            {
                'pk': 'aslp#CONFIGURATION',
                'sk': 'aslp#JURISDICTION#ky',
                'jurisdictionName': 'Kentucky',
                'postalAbbreviation': 'ky',
                'compact': 'aslp',
            },
        )
        load_test_jurisdiction(
            self.config.compact_configuration_table,
            {
                'pk': 'aslp#CONFIGURATION',
                'sk': 'aslp#JURISDICTION#oh',
                'jurisdictionName': 'Ohio',
                'postalAbbreviation': 'oh',
                'compact': 'aslp',
            },
        )

        event = generate_test_event('GET', STAFF_USERS_COMPACT_JURISDICTION_ENDPOINT_RESOURCE)

        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))
        response_body = json.loads(response['body'])

        self.assertEqual(
            [
                {'compact': 'aslp', 'jurisdictionName': 'Kentucky', 'postalAbbreviation': 'ky'},
                {'compact': 'aslp', 'jurisdictionName': 'Ohio', 'postalAbbreviation': 'oh'},
            ],
            response_body,
        )


@mock_aws
class TestGetPublicCompactJurisdictions(TstFunction):
    """Test suite for get compact jurisdiction endpoints."""

    def test_get_compact_jurisdictions_returns_invalid_exception_if_invalid_http_methog(self):
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

        # load jurisdictions
        load_test_jurisdiction(
            self.config.compact_configuration_table,
            {
                'pk': 'aslp#CONFIGURATION',
                'sk': 'aslp#JURISDICTION#ky',
                'jurisdictionName': 'Kentucky',
                'postalAbbreviation': 'ky',
                'compact': 'aslp',
            },
        )
        load_test_jurisdiction(
            self.config.compact_configuration_table,
            {
                'pk': 'aslp#CONFIGURATION',
                'sk': 'aslp#JURISDICTION#oh',
                'jurisdictionName': 'Ohio',
                'postalAbbreviation': 'oh',
                'compact': 'aslp',
            },
        )

        event = generate_test_event('GET', PUBLIC_COMPACT_JURISDICTION_ENDPOINT_RESOURCE)

        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))
        response_body = json.loads(response['body'])

        self.assertEqual(
            [
                {'compact': 'aslp', 'jurisdictionName': 'Kentucky', 'postalAbbreviation': 'ky'},
                {'compact': 'aslp', 'jurisdictionName': 'Ohio', 'postalAbbreviation': 'oh'},
            ],
            response_body,
        )


@mock_aws
class TestStaffUsersCompactConfiguration(TstFunction):
    """Test suite for managing compact configurations."""

    def _when_testing_get_compact_configuration_with_existing_compact_configuration(self):
        compact_config = self.test_data_generator.put_default_compact_configuration_in_configuration_table()
        event = generate_test_event('GET', COMPACT_CONFIGURATION_ENDPOINT_RESOURCE)
        event['pathParameters']['compact'] = compact_config['compactAbbr']
        return event, compact_config

    def _when_testing_post_compact_configuration(self):
        from cc_common.utils import ResponseEncoder
        compact_config = self.test_data_generator.generate_default_compact_configuration()
        event = generate_test_event('POST', COMPACT_CONFIGURATION_ENDPOINT_RESOURCE)
        event['pathParameters']['compact'] = compact_config.compactAbbr
        # add compact admin scope to the event
        event['requestContext']['authorizer']['claims']['scope'] = f'{compact_config.compactAbbr}/admin'
        event['requestContext']['authorizer']['claims']['sub'] = 'some-admin-id'

        # we only allow the following values in the body
        event['body'] = json.dumps({
            'compactCommissionFee': compact_config.compactCommissionFee,
            'licenseeRegistrationEnabled': compact_config.licenseeRegistrationEnabled,
            'compactOperationsTeamEmails': compact_config.compactOperationsTeamEmails,
            'compactAdverseActionsNotificationEmails': compact_config.compactAdverseActionsNotificationEmails,
            'compactSummaryReportNotificationEmails': compact_config.compactSummaryReportNotificationEmails,
            'transactionFeeConfiguration': compact_config.transactionFeeConfiguration,
        }, cls=ResponseEncoder)
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
                'compactCommissionFee': {'commissionFee': None, 'commissionFeeType': 'FLAT_RATE'},
                'operationsTeamEmails': [],
                'adverseActionsNotificationEmails': [],
                'summaryReportNotificationEmails': [],
                'licenseeRegistrationEnabled': False,
            },
            response_body,
        )

    def test_post_compact_configuration_rejects_invalid_compact_with_auth_error(self):
        """Test posting a compact configuration rejects an invalid compact abbreviation."""
        from handlers.compact_configuration import compact_configuration_api_handler

        event = generate_test_event('POST', COMPACT_CONFIGURATION_ENDPOINT_RESOURCE)
        event['pathParameters']['compact'] = 'foo'
        # add compact admin scope to the event
        event['requestContext']['authorizer']['scopes'] = f'aslp/admin'

        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(403, response['statusCode'])
        self.assertIn('Access denied', json.loads(response['body'])['message'])

    def test_post_compact_configuration_stores_compact_configuration(self):
        """Test posting a compact configuration stores the compact configuration."""
        from handlers.compact_configuration import compact_configuration_api_handler
        from cc_common.data_model.schema.compact import CompactConfigurationData

        event, compact_config = self._when_testing_post_compact_configuration()

        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))

        # load the record from the configuration table
        serialized_compact_config = compact_config.serialize_to_database_record()
        response = self.config.compact_configuration_table.get_item(Key={
            'pk': serialized_compact_config['pk'],
            'sk': serialized_compact_config['sk']
            }
        )

        stored_compact_data = CompactConfigurationData.from_database_record(response['Item'])

        self.assertEqual(compact_config.to_dict(), stored_compact_data.to_dict())



@mock_aws
class TestStaffUsersJurisdictionConfiguration(TstFunction):
    """Test suite for managing jurisdiction configurations."""

    def _when_testing_post_jurisdiction_configuration(self):
        from cc_common.utils import ResponseEncoder

        jurisdiction_config = self.test_data_generator.generate_default_jurisdiction_configuration()
        event = generate_test_event('POST', JURISDICTION_CONFIGURATION_ENDPOINT_RESOURCE)
        event['pathParameters']['jurisdiction'] = jurisdiction_config.postalAbbreviation
        # add compact admin scope to the event
        event['requestContext']['authorizer']['claims']['scope'] = f'{jurisdiction_config.postalAbbreviation}/{jurisdiction_config.compact}.admin'
        event['requestContext']['authorizer']['claims']['sub'] = 'some-admin-id'

        event['body'] = json.dumps(
            {
                'jurisdictionOperationsTeamEmails': jurisdiction_config.jurisdictionOperationsTeamEmails,
                'jurisdictionAdverseActionsNotificationEmails': jurisdiction_config.jurisdictionAdverseActionsNotificationEmails,
                'jurisdictionSummaryReportNotificationEmails': jurisdiction_config.jurisdictionSummaryReportNotificationEmails,
                'licenseeRegistrationEnabled': jurisdiction_config.licenseeRegistrationEnabled,
                'jurisprudenceRequirements': jurisdiction_config.jurisprudenceRequirements,
                'militaryDiscount': jurisdiction_config.militaryDiscount,
                'privilegeFees': jurisdiction_config.privilegeFees,
            }, cls=ResponseEncoder
        )

        return event, jurisdiction_config

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

    def test_get_jurisdiction_configuration_returns_empty_jurisdiction_configuration_if_no_configuration_exists(self):
        """Test getting a jurisdiction configuration returns a default configuration if none exists."""
        from handlers.compact_configuration import compact_configuration_api_handler

        event = generate_test_event('GET', JURISDICTION_CONFIGURATION_ENDPOINT_RESOURCE)
        event['pathParameters']['jurisdiction'] = 'ky'

        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))
        response_body = json.loads(response['body'])

        # Verify the jurisdiction name is set correctly from the mapping
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
                'privilegeFees': [],
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
                'militaryDiscount': test_jurisdiction_config.militaryDiscount,
                'postalAbbreviation': test_jurisdiction_config.postalAbbreviation,
                'privilegeFees': test_jurisdiction_config.privilegeFees,
            },
            response_body,
        )

    def test_post_jurisdiction_configuration_rejects_invalid_jurisdiction_with_auth_error(self):
        """Test posting a jurisdiction configuration rejects an invalid jurisdiction abbreviation."""
        from handlers.compact_configuration import compact_configuration_api_handler

        event = generate_test_event('POST', JURISDICTION_CONFIGURATION_ENDPOINT_RESOURCE)
        # Set the jurisdiction to an invalid one
        event['pathParameters']['jurisdiction'] = 'invalid_jurisdiction'

        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(403, response['statusCode'])
        self.assertIn('Access denied', json.loads(response['body'])['message'])


    def test_post_jurisdiction_configuration_returns_invalid_jurisdiction_with_auth_error(self):
        """Test posting a jurisdiction configuration rejects an invalid jurisdiction abbreviation."""
        from handlers.compact_configuration import compact_configuration_api_handler

        event = generate_test_event('POST', JURISDICTION_CONFIGURATION_ENDPOINT_RESOURCE)
        # Set the jurisdiction to an invalid one
        event['pathParameters']['jurisdiction'] = 'invalid_jurisdiction'

        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(403, response['statusCode'])
        self.assertIn('Access denied', json.loads(response['body'])['message'])

    def test_post_jurisdiction_configuration_stores_jurisdiction_configuration(self):
        """Test posting a jurisdiction configuration stores the jurisdiction configuration."""
        from handlers.compact_configuration import compact_configuration_api_handler
        from cc_common.data_model.schema.jurisdiction import JurisdictionConfigurationData

        event, jurisdiction_config = self._when_testing_post_jurisdiction_configuration()

        response = compact_configuration_api_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'], msg=json.loads(response['body']))

        # load the record from the configuration table
        serialized_jurisdiction_config = jurisdiction_config.serialize_to_database_record()
        response = self.config.compact_configuration_table.get_item(Key={
            'pk': serialized_jurisdiction_config['pk'],
            'sk': serialized_jurisdiction_config['sk']
            }
        )

        stored_jurisdiction_data = JurisdictionConfigurationData.from_database_record(response['Item'])

        self.assertEqual(jurisdiction_config.to_dict(), stored_jurisdiction_data.to_dict())





