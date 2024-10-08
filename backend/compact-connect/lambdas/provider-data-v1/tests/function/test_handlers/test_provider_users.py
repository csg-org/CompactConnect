import json

from moto import mock_aws
from tests.function import TstFunction
from exceptions import CCInternalException

TEST_COMPACT = "aslp"
MOCK_SSN = "123-12-1234"
@mock_aws
class TestGetProvider(TstFunction):

    def _create_test_provider(self):
        from config import config
        provider_id = config.data_client.get_or_create_provider_id(compact=TEST_COMPACT, ssn=MOCK_SSN)

        return provider_id

    def _when_testing_provider_user_event_with_custom_claims(self):
        self._load_provider_data()
        provider_id = self._create_test_provider()
        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)
            event['requestContext']['authorizer']['claims']['custom:providerId'] = provider_id
            event['requestContext']['authorizer']['claims']['custom:compact'] = TEST_COMPACT

        return event

    def test_get_provider_returns_provider_information(self):
        from handlers.provider_users import get_provider_user_me
        event = self._when_testing_provider_user_event_with_custom_claims()

        resp = get_provider_user_me(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        provider_data = json.loads(resp['body'])

        with open('tests/resources/api/provider-detail-response.json', 'r') as f:
            expected_provider = json.load(f)
        self.assertEqual(expected_provider, provider_data)


    def test_get_provider_returns_400_if_api_call_made_without_proper_claims(self):
        from handlers.provider_users import get_provider_user_me

        event = self._when_testing_provider_user_event_with_custom_claims()

        # remove custom attributes in the cognito claims
        del event['requestContext']['authorizer']['claims']['custom:providerId']
        del event['requestContext']['authorizer']['claims']['custom:compact']

        resp = get_provider_user_me(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])

    def test_get_provider_raises_exception_if_user_claims_do_not_match_any_provider_in_database(self):
        from handlers.provider_users import get_provider_user_me

        event = self._when_testing_provider_user_event_with_custom_claims()
        event['requestContext']['authorizer']['claims']['custom:providerId'] = "some-provider-id"

        # calling get_provider without creating a provider first
        with self.assertRaises(CCInternalException):
            get_provider_user_me(event, self.mock_context)
