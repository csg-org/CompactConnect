import json
from datetime import UTC, datetime, timedelta

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
        from cc_common.data_model.schema.common import MilitaryAuditStatus

        self.test_data_generator.put_default_provider_record_in_provider_table(
            value_overrides={
                'compact': TEST_COMPACT,
                'providerId': TEST_PROVIDER_ID,
                'militaryStatus': MilitaryAuditStatus.DECLINED,
                'militaryStatusNote': 'some declined note',
            }
        )
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

    def test_provider_user_bucket_event_handler_sets_latest_military_affiliation_to_active_and_older_to_inactive(self):
        """Test that when two military affiliation records are uploaded, the latest is set to
        active and older to inactive."""
        from cc_common.data_model.schema.military_affiliation.common import MilitaryAffiliationStatus
        from handlers.provider_s3_events import process_provider_s3_events

        # Set up provider record
        self.test_data_generator.put_default_provider_record_in_provider_table(
            value_overrides={
                'compact': TEST_COMPACT,
                'providerId': TEST_PROVIDER_ID,
            }
        )

        # Create two military affiliation records with different upload dates
        # Older record (uploaded 1 day earlier)
        older_date = datetime.now(tz=UTC) - timedelta(days=1)
        self.test_data_generator.put_default_military_affiliation_in_provider_table(
            value_overrides={
                'compact': TEST_COMPACT,
                'providerId': TEST_PROVIDER_ID,
                'dateOfUpload': older_date,
                'status': MilitaryAffiliationStatus.INITIALIZING.value,
                'fileNames': ['older_military_affiliation.pdf'],
                'documentKeys': [
                    f'compact/{TEST_COMPACT}/provider/{TEST_PROVIDER_ID}/'
                    f'document-type/military-affiliations/'
                    f'{older_date.date().isoformat()}/older_military_affiliation.pdf'
                ],
            }
        )

        # Newer record (uploaded today)
        newer_date = datetime.now(tz=UTC)
        self.test_data_generator.put_default_military_affiliation_in_provider_table(
            value_overrides={
                'compact': TEST_COMPACT,
                'providerId': TEST_PROVIDER_ID,
                'dateOfUpload': newer_date,
                'status': MilitaryAffiliationStatus.INITIALIZING.value,
                'fileNames': [MOCK_MILITARY_AFFILIATION_FILE_NAME],
                'documentKeys': [
                    f'compact/{TEST_COMPACT}/provider/{TEST_PROVIDER_ID}/'
                    f'document-type/military-affiliations/'
                    f'{newer_date.date().isoformat()}/{MOCK_MILITARY_AFFILIATION_FILE_NAME}'
                ],
            }
        )

        # Verify both records are in initializing state
        affiliation_records = self._get_military_affiliation_records()
        self.assertEqual(2, len(affiliation_records))
        for record in affiliation_records:
            self.assertEqual('initializing', record['status'])

        # Simulate the S3 bucket event for the newer file
        with open('../common/tests/resources/put-event.json') as f:
            event = json.load(f)
            event['Records'][0]['s3']['object']['key'] = (
                f'compact/{TEST_COMPACT}/provider/{TEST_PROVIDER_ID}/'
                f'document-type/military-affiliations/'
                f'{newer_date.date().isoformat()}/'
                f'{MOCK_MILITARY_AFFILIATION_FILE_NAME}'
            )

        # Process the S3 event
        process_provider_s3_events(event, self.mock_context)

        # Verify the newer record is active and the older record is inactive
        affiliation_records = self._get_military_affiliation_records()
        self.assertEqual(2, len(affiliation_records))

        # Sort records by dateOfUpload to identify which is which
        affiliation_records.sort(key=lambda r: r['dateOfUpload'])

        # Older record should be inactive
        self.assertEqual('inactive', affiliation_records[0]['status'])
        self.assertEqual(older_date.isoformat(), affiliation_records[0]['dateOfUpload'])

        # Newer record should be active
        self.assertEqual('active', affiliation_records[1]['status'])
        self.assertEqual(newer_date.isoformat(), affiliation_records[1]['dateOfUpload'])

    def test_provider_user_bucket_event_handler_updates_provider_record_with_tentative_status(self):
        """Test that processing military affiliation S3 event updates provider record with tentative
        status and empty note."""
        from handlers.provider_s3_events import process_provider_s3_events

        event = self._when_testing_military_affiliation_s3_object_create_event()

        # Verify provider record doesn't have tentative status yet
        provider_record_before = self.config.data_client.get_provider_top_level_record(
            compact=TEST_COMPACT, provider_id=TEST_PROVIDER_ID
        )
        # The default might be 'notApplicable' or might not be set, but it shouldn't be 'tentative' yet
        self.assertNotEqual('tentative', provider_record_before.militaryStatus)

        # Process the S3 event
        process_provider_s3_events(event, self.mock_context)

        # Verify provider record was updated with tentative status and empty note
        updated_provider_record = self.config.data_client.get_provider_top_level_record(
            compact=TEST_COMPACT, provider_id=TEST_PROVIDER_ID
        )

        self.assertEqual('tentative', updated_provider_record.militaryStatus)
        self.assertEqual('', updated_provider_record.militaryStatusNote)

    def test_provider_user_bucket_event_handler_creates_provider_update_record(self):
        """Test that processing military affiliation S3 event creates a provider update record with expected values."""
        from cc_common.data_model.schema.common import UpdateCategory
        from cc_common.data_model.schema.provider import ProviderUpdateData
        from handlers.provider_s3_events import process_provider_s3_events

        event = self._when_testing_military_affiliation_s3_object_create_event()

        # Get the provider record before processing to use for querying update records
        test_provider = self.config.data_client.get_provider_top_level_record(
            compact=TEST_COMPACT, provider_id=TEST_PROVIDER_ID
        )

        # Process the S3 event
        process_provider_s3_events(event, self.mock_context)

        # Query provider update records
        stored_provider_update_records = (
            self.test_data_generator.query_provider_update_records_for_given_record_from_database(test_provider)
        )

        # Verify exactly one update record was created
        self.assertEqual(1, len(stored_provider_update_records))

        # Verify the update record contents
        update_data = ProviderUpdateData.from_database_record(stored_provider_update_records[0])
        self.assertEqual(UpdateCategory.MILITARY_FILE_UPLOAD, update_data.updateType)
        self.assertEqual(TEST_PROVIDER_ID, str(update_data.providerId))
        self.assertEqual(TEST_COMPACT, update_data.compact)

        # Verify previous state was captured (should be DECLINED with note from setup)
        self.assertIsNotNone(update_data.previous)
        self.assertEqual('declined', update_data.previous.get('militaryStatus'))
        self.assertEqual('some declined note', update_data.previous.get('militaryStatusNote'))

        # Verify updated values
        self.assertEqual('tentative', update_data.updatedValues['militaryStatus'])
        self.assertEqual('', update_data.updatedValues['militaryStatusNote'])
