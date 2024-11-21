from datetime import datetime
import json

from cc_common.exceptions import CCInternalException
from moto import mock_aws
from unittest.mock import patch

from .. import TstFunction

TEST_COMPACT = 'aslp'
MOCK_SSN = '123-12-1234'
MOCK_MILITARY_AFFILIATION_FILE_NAME = 'military_affiliation.pdf'


@mock_aws
class TestGetProvider(TstFunction):
    def _create_test_provider(self):
        from cc_common.config import config

        return config.data_client.get_or_create_provider_id(compact=TEST_COMPACT, ssn=MOCK_SSN)

    def _when_testing_provider_user_event_with_custom_claims(self):
        self._load_provider_data()
        provider_id = self._create_test_provider()
        with open('../common-python/tests/resources/api-event.json') as f:
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

        with open('../common-python/tests/resources/api/provider-detail-response.json') as f:
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
        event['requestContext']['authorizer']['claims']['custom:providerId'] = 'some-provider-id'

        # calling get_provider without creating a provider first
        with self.assertRaises(CCInternalException):
            get_provider_user_me(event, self.mock_context)

@mock_aws
class TestPostProviderMilitaryAffiliation(TstFunction):
    def _create_test_provider(self):
        from cc_common.config import config

        return config.data_client.get_or_create_provider_id(compact=TEST_COMPACT, ssn=MOCK_SSN)

    def _when_testing_post_provider_user_military_affiliation_event_with_custom_claims(self):
        self._load_provider_data()
        provider_id = self._create_test_provider()
        with open('../common-python/tests/resources/api-event.json') as f:
            event = json.load(f)
            event['httpMethod'] = 'POST'
            event['requestContext']['authorizer']['claims']['custom:providerId'] = provider_id
            event['requestContext']['authorizer']['claims']['custom:compact'] = TEST_COMPACT
            event['body'] = json.dumps({
                'fileNames': [MOCK_MILITARY_AFFILIATION_FILE_NAME],
                'affiliationType': 'militaryMember',
            })

        return event

    @patch('handlers.provider_users.uuid')
    def test_post_provider_military_affiliation_returns_affiliation_information(self, mock_uuid):
        from handlers.provider_users import provider_user_me_military_affiliation
        mock_uuid.uuid4.return_value = '1234'

        event = self._when_testing_post_provider_user_military_affiliation_event_with_custom_claims()

        resp = provider_user_me_military_affiliation(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        military_affiliation_data = json.loads(resp['body'])

        #remove dynamic fields from s3 response
        del military_affiliation_data['documentUploadFields'][0]['fields']['policy']
        del military_affiliation_data['documentUploadFields'][0]['fields']['x-amz-signature']
        del military_affiliation_data['documentUploadFields'][0]['fields']['x-amz-date']
        del military_affiliation_data['documentUploadFields'][0]['fields']['x-amz-credential']

        today = datetime.now(self.config.expiration_date_resolution_timezone).date().isoformat()
        provider_id = event['requestContext']['authorizer']['claims']['custom:providerId']

        self.assertEqual(
            {
                'affiliationType': 'militaryMember',
                 'dateOfUpdate': today,
                 'dateOfUpload': today,
                 'documentUploadFields': [{'fields': {
                     'key': f'/provider/{provider_id}/document-type/military-affiliations'
                            f'/{today}/military_affiliation#1234.pdf',
                     'x-amz-algorithm': 'AWS4-HMAC-SHA256'
                 },
                 'url': 'https://provider-user-bucket.s3.amazonaws.com/'}],
                 'fileNames': ['military_affiliation.pdf'],
                 'status': 'initializing'
            }, military_affiliation_data)

    def test_post_provider_returns_400_if_api_call_made_without_proper_claims(self):
        from handlers.provider_users import provider_user_me_military_affiliation

        event = self._when_testing_post_provider_user_military_affiliation_event_with_custom_claims()

        # remove custom attributes in the cognito claims
        del event['requestContext']['authorizer']['claims']['custom:providerId']
        del event['requestContext']['authorizer']['claims']['custom:compact']

        resp = provider_user_me_military_affiliation(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])
