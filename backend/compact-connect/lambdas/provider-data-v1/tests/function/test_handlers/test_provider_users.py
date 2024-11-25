import json
from datetime import datetime
from unittest.mock import patch

from boto3.dynamodb.conditions import Key
from cc_common.exceptions import CCInternalException
from moto import mock_aws

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

    def _get_military_affiliation_records(self, event):
        provider_id = event['requestContext']['authorizer']['claims']['custom:providerId']
        return self.config.provider_table.query(
            KeyConditionExpression=Key('pk').eq(f'{TEST_COMPACT}#PROVIDER#{provider_id}')
            & Key('sk').begins_with(
                f'{TEST_COMPACT}#PROVIDER#military-affiliation#',
            )
        )['Items']

    def _when_testing_post_provider_user_military_affiliation_event_with_custom_claims(self):
        self._load_provider_data()
        provider_id = self._create_test_provider()
        with open('../common-python/tests/resources/api-event.json') as f:
            event = json.load(f)
            event['httpMethod'] = 'POST'
            event['requestContext']['authorizer']['claims']['custom:providerId'] = provider_id
            event['requestContext']['authorizer']['claims']['custom:compact'] = TEST_COMPACT
            event['body'] = json.dumps(
                {
                    'fileNames': [MOCK_MILITARY_AFFILIATION_FILE_NAME],
                    'affiliationType': 'militaryMember',
                }
            )

        return event

    @patch('handlers.provider_users.uuid')
    def test_post_provider_military_affiliation_returns_affiliation_information(self, mock_uuid):
        from handlers.provider_users import provider_user_me_military_affiliation

        mock_uuid.uuid4.return_value = '1234'

        event = self._when_testing_post_provider_user_military_affiliation_event_with_custom_claims()

        resp = provider_user_me_military_affiliation(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        military_affiliation_data = json.loads(resp['body'])

        # remove dynamic fields from s3 response
        del military_affiliation_data['documentUploadFields'][0]['fields']['policy']
        del military_affiliation_data['documentUploadFields'][0]['fields']['x-amz-signature']
        del military_affiliation_data['documentUploadFields'][0]['fields']['x-amz-date']
        del military_affiliation_data['documentUploadFields'][0]['fields']['x-amz-credential']

        today = datetime.now(self.config.expiration_date_resolution_timezone).date().isoformat()
        provider_id = event['requestContext']['authorizer']['claims']['custom:providerId']

        # remove the dynamic dateOfUpload field
        military_affiliation_data.pop('dateOfUpload')

        self.assertEqual(
            {
                'affiliationType': 'militaryMember',
                'dateOfUpdate': today,
                'documentUploadFields': [
                    {
                        'fields': {
                            'key': f'compact/{TEST_COMPACT}/provider/{provider_id}/document-type/military-affiliations'
                            f'/{today}/military_affiliation#1234.pdf',
                            'x-amz-algorithm': 'AWS4-HMAC-SHA256',
                        },
                        'url': 'https://provider-user-bucket.s3.amazonaws.com/',
                    }
                ],
                'fileNames': ['military_affiliation.pdf'],
                'status': 'initializing',
            },
            military_affiliation_data,
        )

    def test_post_provider_military_affiliation_sets_previous_record_status_to_inactive(self):
        from handlers.provider_users import provider_user_me_military_affiliation

        event = self._when_testing_post_provider_user_military_affiliation_event_with_custom_claims()

        resp = provider_user_me_military_affiliation(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        # get the military affiliation record
        military_affiliation_records = self._get_military_affiliation_records(event)
        # There should have been another record loaded previously with an 'active' status by the
        # test setup, so now we check to see if it has been set to 'inactive'
        self.assertEqual(2, len(military_affiliation_records))
        # record with the oldest upload date should be inactive, the other should be initializing
        affiliations_sorted_by_date = sorted(military_affiliation_records, key=lambda x: x['dateOfUpload'])
        self.assertEqual('inactive', affiliations_sorted_by_date[0]['status'])
        self.assertEqual('initializing', affiliations_sorted_by_date[1]['status'])

    def test_post_provider_returns_400_if_api_call_made_without_proper_claims(self):
        from handlers.provider_users import provider_user_me_military_affiliation

        event = self._when_testing_post_provider_user_military_affiliation_event_with_custom_claims()

        # remove custom attributes in the cognito claims
        del event['requestContext']['authorizer']['claims']['custom:providerId']
        del event['requestContext']['authorizer']['claims']['custom:compact']

        resp = provider_user_me_military_affiliation(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])

    def _when_testing_file_names(self, file_names: list[str]):
        from handlers.provider_users import provider_user_me_military_affiliation

        event = self._when_testing_post_provider_user_military_affiliation_event_with_custom_claims()
        event['body'] = json.dumps(
            {
                'fileNames': file_names,
                'affiliationType': 'militaryMember',
            }
        )

        return provider_user_me_military_affiliation(event, self.mock_context)

    def test_post_provider_returns_400_if_file_name_using_unsupported_file_extension(self):
        resp = self._when_testing_file_names(['military_affiliation.guff'])

        self.assertEqual(400, resp['statusCode'])
        message = json.loads(resp['body'])['message']

        self.assertEqual(
            """Invalid file type "guff" The following file types are supported: ('pdf', 'jpg', 'jpeg', 'png', 'docx')""",
            message,
        )

    def test_post_provider_returns_200_if_file_extensions_valid(self):
        resp = self._when_testing_file_names(['file.pdf', 'file.jpg', 'file.jpeg', 'file.png', 'file.docx'])

        self.assertEqual(200, resp['statusCode'])


@mock_aws
class TestPatchProviderMilitaryAffiliation(TstFunction):
    def _create_test_provider(self):
        from cc_common.config import config

        return config.data_client.get_or_create_provider_id(compact=TEST_COMPACT, ssn=MOCK_SSN)

    def _when_testing_patch_provider_user_military_affiliation_event_with_custom_claims(self):
        self._load_provider_data()
        provider_id = self._create_test_provider()
        with open('../common-python/tests/resources/api-event.json') as f:
            event = json.load(f)
            event['httpMethod'] = 'PATCH'
            event['requestContext']['authorizer']['claims']['custom:providerId'] = provider_id
            event['requestContext']['authorizer']['claims']['custom:compact'] = TEST_COMPACT
            event['body'] = json.dumps({'status': 'inactive'})

        return event

    def _get_military_affiliation_records(self, event):
        provider_id = event['requestContext']['authorizer']['claims']['custom:providerId']
        return self.config.provider_table.query(
            KeyConditionExpression=Key('pk').eq(f'{TEST_COMPACT}#PROVIDER#{provider_id}')
            & Key('sk').begins_with(
                f'{TEST_COMPACT}#PROVIDER#military-affiliation#',
            )
        )['Items']

    def test_patch_provider_military_affiliation_returns_message(self):
        from handlers.provider_users import provider_user_me_military_affiliation

        event = self._when_testing_patch_provider_user_military_affiliation_event_with_custom_claims()

        resp = provider_user_me_military_affiliation(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        resp_body = json.loads(resp['body'])

        self.assertEqual({'message': 'Military affiliation updated successfully'}, resp_body)

    def test_patch_provider_military_affiliation_returs_400_if_invalid_body(self):
        from handlers.provider_users import provider_user_me_military_affiliation

        event = self._when_testing_patch_provider_user_military_affiliation_event_with_custom_claims()

        event['body'] = json.dumps({'status': 'active'})

        resp = provider_user_me_military_affiliation(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])
        message = json.loads(resp['body'])['message']

        self.assertEqual('Invalid status value. Only "inactive" is allowed.', message)

    def test_patch_provider_military_affiliation_updates_status(self):
        from handlers.provider_users import provider_user_me_military_affiliation

        event = self._when_testing_patch_provider_user_military_affiliation_event_with_custom_claims()

        # get the military affiliation record loaded in the test setup and confirm it is active
        affiliation_record = self._get_military_affiliation_records(event)
        self.assertEqual(1, len(affiliation_record))
        self.assertEqual('active', affiliation_record[0]['status'])

        resp = provider_user_me_military_affiliation(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        # now confirm the status has been updated to inactive
        affiliation_record = self._get_military_affiliation_records(event)

        self.assertEqual(1, len(affiliation_record))
        self.assertEqual('inactive', affiliation_record[0]['status'])
