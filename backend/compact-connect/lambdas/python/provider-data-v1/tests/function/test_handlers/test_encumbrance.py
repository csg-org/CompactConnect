import json
from decimal import Decimal

from moto import mock_aws

from . import TstFunction

PRIVILEGE_ENCUMBRANCE_ENDPOINT_RESOURCE = ('/v1/compacts/{compact}/providers/{providerId}/privileges/'
                                           'jurisdiction/{jurisdiction}/licenseType/{licenseType}/encumbrance')
LICENSE_ENCUMBRANCE_ENDPOINT_RESOURCE = ('/v1/compacts/{compact}/providers/{providerId}/licenses/'
                                        'jurisdiction/{jurisdiction}/licenseType/{licenseType}/encumbrance')


def generate_test_event(method: str, resource: str, path_parameters: dict, body: dict) -> dict:
    with open('../common/tests/resources/api-event.json') as f:
        event = json.load(f)
        event['httpMethod'] = method
        event['resource'] = resource
        event['pathParameters'] = path_parameters
        event['body'] = json.dumps(body)

    return event


@mock_aws
class TestEncumbrance(TstFunction):
    """Test suite for encumbrance endpoints."""

    def test_get_compact_jurisdictions_returns_invalid_exception_if_invalid_http_method(self):
        """Test getting an empty list if no jurisdictions configured."""
        from handlers.encumbrance import encumbrance_handler

        event = generate_test_event('POST', PRIVILEGE_ENCUMBRANCE_ENDPOINT_RESOURCE,
                                     {'compact': 'aslp', 'providerId': '123', 'jurisdiction': 'ky', 'licenseType': 'slp'},
                                     {})

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
