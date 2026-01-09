import json
from datetime import UTC, datetime

from boto3.dynamodb.conditions import Key
from moto import mock_aws

from .. import TstFunction

TEST_COMPACT = 'aslp'
TEST_PROVIDER_ID = '89a6377e-c3a5-40e5-bca5-317ec854c570'
MOCK_SSN = '123-12-1234'
MOCK_MILITARY_AFFILIATION_FILE_NAME = 'military_affiliation.pdf'


@mock_aws
class TestProviderUserBucketS3Events(TstFunction):
    def _call_post_military_affiliation_endpoint(self):
        from handlers.provider_users import provider_users_api_handler

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)
            event['httpMethod'] = 'POST'
            event['resource'] = '/v1/provider-users/me/military-affiliation'
            event['requestContext']['authorizer']['claims']['custom:providerId'] = TEST_PROVIDER_ID
            event['requestContext']['authorizer']['claims']['custom:compact'] = TEST_COMPACT
            event['body'] = json.dumps(
                {
                    'fileNames': [MOCK_MILITARY_AFFILIATION_FILE_NAME],
                    'affiliationType': 'militaryMember',
                }
            )

        return provider_users_api_handler(event, self.mock_context)

    def _when_testing_military_affiliation_s3_object_create_event(self):
        # make mock call to POST endpoint to create a military affiliation record in an initializing state
        post_resp = self._call_post_military_affiliation_endpoint()
        # make sure the post was successful
        self.assertEqual(200, post_resp['statusCode'])

        # Simulate the s3 bucket event
        with open('../common/tests/resources/put-event.json') as f:
            event = json.load(f)
            event['Records'][0]['s3']['object']['key'] = (
                f'compact/{TEST_COMPACT}/provider/{TEST_PROVIDER_ID}/'
                f'document-type/military-affiliations/'
                f'{datetime.now(tz=UTC).date().isoformat()}/'
                f'{MOCK_MILITARY_AFFILIATION_FILE_NAME}'
            )

        return event

    def _get_military_affiliation_records(self):
        return self.config.provider_table.query(
            KeyConditionExpression=Key('pk').eq(f'{TEST_COMPACT}#PROVIDER#{TEST_PROVIDER_ID}')
            & Key('sk').begins_with(
                f'{TEST_COMPACT}#PROVIDER#military-affiliation#',
            )
        )['Items']

    def test_provider_user_bucket_event_handler_sets_military_affiliation_status_to_active(self):
        from handlers.provider_s3_events import process_provider_s3_events

        event = self._when_testing_military_affiliation_s3_object_create_event()
        # ensure the military affiliation record is in the initializing state
        affiliation_record = self._get_military_affiliation_records()
        self.assertEqual(1, len(affiliation_record))
        self.assertEqual('initializing', affiliation_record[0]['status'])

        process_provider_s3_events(event, self.mock_context)

        # now confirm the status has been updated to active
        affiliation_record = self._get_military_affiliation_records()
        self.assertEqual(1, len(affiliation_record))
        self.assertEqual('active', affiliation_record[0]['status'])
