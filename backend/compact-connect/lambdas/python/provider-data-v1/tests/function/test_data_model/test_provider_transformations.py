import json
from datetime import date, datetime
from unittest.mock import patch

from boto3.dynamodb.conditions import Key
from moto import mock_aws

from .. import TstFunction


@mock_aws
class TestTransformations(TstFunction):
    # Yes, this is an excessively long method. We're going with it for sake of a single illustrative test.
    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
    @patch('cc_common.config._Config.license_preprocessing_queue')
    def test_transformations(self, mock_license_preprocessing_queue):
        """Provider data undergoes several transformations from when a license is first posted, stored into the
        database, then returned via the API. We will specifically test that chain, end to end, to make sure the
        transformations all happen as expected.
        """
        # Before we get started, we'll pre-set the SSN/providerId association we expect
        with open('../common/tests/resources/dynamo/provider-ssn.json') as f:
            provider_ssn = json.load(f)

        self._ssn_table.put_item(Item=provider_ssn)
        expected_provider_id = provider_ssn['providerId']

        # license data as it comes in from a board, in this case, as POSTed through the API
        with open('../common/tests/resources/api/license-post.json') as f:
            license_post = json.load(f)
        license_ssn = license_post['ssn']

        # The API Gateway event, as it is presented to the API lambda
        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # Pack an array of one license into the request body
        event['body'] = json.dumps([license_post])

        # Compact and jurisdiction are provided via path parameters
        event['pathParameters'] = {'compact': 'aslp', 'jurisdiction': 'oh'}
        # Authorize ourselves to write the license
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email oh/aslp.write'

        from handlers.licenses import post_licenses

        # POST the license via the API
        post_licenses(event, self.mock_context)

        # Capture the message sent to the preprocessing queue
        preprocessing_message = json.loads(
            mock_license_preprocessing_queue.send_messages.call_args.kwargs['Entries'][0]['MessageBody']
        )

        # Now we need to simulate the preprocessing step
        # Mock EventBatchWriter so we can intercept the EventBridge event
        with patch('handlers.ingest.config.events_client', autospec=True) as mock_event_client:
            from handlers.ingest import preprocess_license_ingest

            # Create an SQS event with our preprocessing message
            preprocess_event = {'Records': [{'messageId': '123', 'body': json.dumps(preprocessing_message)}]}

            # Run the preprocessing step
            preprocess_license_ingest(preprocess_event, self.mock_context)

            # Capture the event the preprocessor will produce for the event bus
            event_bridge_event = json.loads(mock_event_client.put_events.call_args.kwargs['Entries'][0]['Detail'])

        # A sample SQS message from EventBridge
        with open('../common/tests/resources/ingest/event-bridge-message.json') as f:
            message = json.load(f)

        # Pack our license.ingest event into the sample message
        message['detail'] = event_bridge_event
        event = {'Records': [{'messageId': '123', 'body': json.dumps(message)}]}

        from handlers.ingest import ingest_license_message

        # This should fully ingest the license, which will result in it being written to the DB
        ingest_license_message(event, self.mock_context)

        from cc_common.data_model.data_client import DataClient

        # We'll fetch the provider id from the ssn table
        client = DataClient(self.config)
        provider_id = self._ssn_table.get_item(Key={'pk': f'aslp#SSN#{license_ssn}', 'sk': f'aslp#SSN#{license_ssn}'})[
            'Item'
        ]['providerId']
        self.assertEqual(expected_provider_id, provider_id)
        provider_record = client.get_provider(compact='aslp', provider_id=provider_id, detail=False)['items'][0]

        # Expected representation of each record in the database
        with open('../common/tests/resources/dynamo/provider.json') as f:
            expected_provider = json.load(f)

        # register the provider in the system
        client.process_registration_values(
            compact='aslp',
            provider_id=provider_id,
            cognito_sub=expected_provider['cognitoSub'],
            jurisdiction='oh',
            email_address=expected_provider['compactConnectRegisteredEmailAddress'],
        )

        # Add a privilege to practice in Nebraska
        client.create_provider_privileges(
            compact='aslp',
            provider_id=provider_id,
            provider_record=provider_record,
            # using values in expected privilege json file
            jurisdiction_postal_abbreviations=['ne'],
            license_expiration_date=date(2025, 4, 4),
            compact_transaction_id='1234567890',
            existing_privileges_for_license=[],
            license_type='speech-language pathologist',
            attestations=[{'attestationId': 'jurisprudence-confirmation', 'version': '1'}],
        )

        from cc_common.data_model.schema.military_affiliation.common import MilitaryAffiliationType

        # Add a military affiliation
        client.create_military_affiliation(
            compact='aslp',
            provider_id=provider_id,
            affiliation_type=MilitaryAffiliationType.MILITARY_MEMBER,
            file_names=['military-waiver.pdf'],
            document_keys=[
                f'/provider/{provider_id}/document-type/military-affiliations/2024-07-08/1234#military-waiver.pdf'
            ],
        )

        # Get the provider straight from the table, to inspect them
        resp = self._provider_table.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('pk').eq(f'aslp#PROVIDER#{provider_id}')
            & Key('sk').begins_with('aslp#PROVIDER'),
        )
        # One record for each of: provider, license, privilege, militaryAffiliation, and homeJurisdictionSelection
        self.assertEqual(5, len(resp['Items']))
        records = {item['type']: item for item in resp['Items']}

        # Convert this to the data type expected from DynamoDB
        expected_provider['privilegeJurisdictions'] = set(expected_provider['privilegeJurisdictions'])

        with open('../common/tests/resources/dynamo/license.json') as f:
            expected_license = json.load(f)
        with open('../common/tests/resources/dynamo/privilege.json') as f:
            expected_privilege = json.load(f)
        with open('../common/tests/resources/dynamo/military-affiliation.json') as f:
            expected_military_affiliation = json.load(f)
            # in this case, the status will be initializing, since it is not set to active until
            # the military affiliation document is uploaded
            expected_military_affiliation['status'] = 'initializing'

        # each record has a dynamic dateOfUpdate field that we'll remove for comparison
        for record in [
            expected_provider,
            expected_license,
            expected_privilege,
            expected_military_affiliation,
            *records.values(),
        ]:
            # Drop dynamic field
            del record['dateOfUpdate']
        # These fields will be dynamic, so we'll remove them from comparison
        del expected_provider['providerDateOfUpdate']
        del records['provider']['providerDateOfUpdate']
        del expected_privilege['dateOfIssuance']
        del expected_privilege['dateOfRenewal']
        del expected_military_affiliation['dateOfUpload']
        # removing dynamic fields
        del records['privilege']['dateOfIssuance']
        del records['privilege']['dateOfRenewal']
        del records['militaryAffiliation']['dateOfUpload']

        # Make sure each is represented the way we expect, in the db
        self.assertEqual(expected_provider, records['provider'])
        self.assertEqual(expected_license, records['license'])
        self.assertEqual(expected_privilege, records['privilege'])
        self.assertEqual(expected_military_affiliation, records['militaryAffiliation'])

        from handlers.providers import get_provider

        # Get a fresh API Gateway event
        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        event['pathParameters'] = {'compact': 'aslp', 'providerId': provider_id}
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/readGeneral aslp/readPrivate'

        resp = get_provider(event, self.mock_context)

        # If we get a 200, our full ingest chain was successful
        self.assertEqual(200, resp['statusCode'])

        provider_data = json.loads(resp['body'])

        # Expected representation of our provider coming _out_ via the API
        with open('../common/tests/resources/api/provider-detail-response.json') as f:
            expected_provider = json.load(f)
            # in this case, the military affiliation status will be initializing, since it is not set to active until
            # the military affiliation document is uploaded to s3
            expected_provider['militaryAffiliations'][0]['status'] = 'initializing'

        # Force the provider id to match
        expected_provider['providerId'] = provider_id

        # Drop dynamic fields from comparison
        del provider_data['dateOfUpdate']
        del provider_data['licenses'][0]['dateOfUpdate']
        del provider_data['privileges'][0]['dateOfUpdate']
        del provider_data['privileges'][0]['dateOfIssuance']
        del provider_data['privileges'][0]['dateOfRenewal']
        del provider_data['militaryAffiliations'][0]['dateOfUpload']
        del provider_data['militaryAffiliations'][0]['dateOfUpdate']
        del provider_data['homeJurisdictionSelection']['dateOfSelection']
        del provider_data['homeJurisdictionSelection']['dateOfUpdate']
        del expected_provider['dateOfUpdate']
        del expected_provider['licenses'][0]['dateOfUpdate']
        del expected_provider['privileges'][0]['dateOfUpdate']
        del expected_provider['privileges'][0]['dateOfIssuance']
        del expected_provider['privileges'][0]['dateOfRenewal']
        del expected_provider['militaryAffiliations'][0]['dateOfUpload']
        del expected_provider['militaryAffiliations'][0]['dateOfUpdate']
        del expected_provider['homeJurisdictionSelection']['dateOfUpdate']
        del expected_provider['homeJurisdictionSelection']['dateOfSelection']

        # This lengthy test does not include change records for licenses or privileges, so we'll blank out the
        # sample history from our expected_provider
        expected_provider['licenses'][0]['history'] = []
        expected_provider['privileges'][0]['history'] = []

        # Phew! We've loaded the data all the way in via the ingest chain and back out via the API!
        self.maxDiff = None
        self.assertEqual(expected_provider, provider_data)
