import json
from decimal import Decimal

from moto import mock_aws

from . import TstFunction


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
class TestGetCompactJurisdictions(TstFunction):
    """Test suite for get compact jurisdiction endpoints."""

    def test_get_compact_jurisdictions_returns_empty_list_if_no_active_jurisdictions(self):
        """Test getting an empty list if no jurisdictions configured."""
        from handlers.compact_configuration import compact_configuration_api_handler

        event = generate_test_event('GET', '/v1/compacts/{compact}/jurisdictions')

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

        event = generate_test_event('GET', '/v1/compacts/{compact}/jurisdictions')

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
