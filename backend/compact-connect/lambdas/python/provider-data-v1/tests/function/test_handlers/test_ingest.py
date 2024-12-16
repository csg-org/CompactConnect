import json

from moto import mock_aws

from .. import TstFunction


@mock_aws
class TestIngest(TstFunction):
    def test_new_provider_ingest(self):
        from handlers.ingest import ingest_license_message
        from handlers.providers import query_providers

        with open('../common/tests/resources/ingest/message.json') as f:
            message = f.read()

        event = {'Records': [{'messageId': '123', 'body': message}]}

        resp = ingest_license_message(event, self.mock_context)

        self.assertEqual({'batchItemFailures': []}, resp)

        # To test full internal consistency, we'll also pull this new license record out
        # via the API to make sure it shows up as expected.
        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        event['pathParameters'] = {'compact': 'aslp'}
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email stuff aslp/readGeneral'
        event['body'] = json.dumps({'query': {'ssn': '123-12-1234'}})
        resp = query_providers(event, self.mock_context)
        self.assertEqual(resp['statusCode'], 200)

        with open('../common/tests/resources/api/provider-response.json') as f:
            expected_provider = json.load(f)
        # The canned response resource assumes that the provider will be given a privilege in NE. We didn't do that,
        # so we'll reset the privilege array.
        expected_provider['privilegeJurisdictions'] = []

        provider_data = json.loads(resp['body'])['providers'][0]
        # Removing dynamic fields from comparison
        del expected_provider['providerId']
        del provider_data['providerId']
        del expected_provider['dateOfUpdate']
        del provider_data['dateOfUpdate']

        self.assertEqual(expected_provider, provider_data)

    def test_existing_provider_ingest(self):
        from handlers.ingest import ingest_license_message
        from handlers.providers import get_provider

        self._load_provider_data()
        with open('../common/tests/resources/dynamo/provider-ssn.json') as f:
            provider_id = json.load(f)['providerId']

        with open('../common/tests/resources/ingest/message.json') as f:
            message = json.load(f)
        # What happens if their license goes inactive?
        message['detail']['status'] = 'inactive'

        event = {'Records': [{'messageId': '123', 'body': json.dumps(message)}]}

        resp = ingest_license_message(event, self.mock_context)

        self.assertEqual({'batchItemFailures': []}, resp)

        # To test full internal consistency, we'll also pull this new license record out
        # via the API to make sure it shows up as expected.
        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        event['pathParameters'] = {'compact': 'aslp', 'providerId': provider_id}
        event['requestContext']['authorizer']['claims']['scope'] = (
            'openid email stuff aslp/readGeneral ' 'aslp/aslp.readPrivate'
        )
        resp = get_provider(event, self.mock_context)
        self.assertEqual(resp['statusCode'], 200)

        with open('../common/tests/resources/api/provider-detail-response.json') as f:
            expected_provider = json.load(f)
        # The license status and provider should immediately be inactive
        expected_provider['jurisdictionStatus'] = 'inactive'
        expected_provider['licenses'][0]['jurisdictionStatus'] = 'inactive'
        # these should be calculated as inactive at record load time
        expected_provider['status'] = 'inactive'
        expected_provider['licenses'][0]['status'] = 'inactive'
        # NOTE: when we are supporting privilege applications officially, they should also be set inactive. That will
        # be captured in the relevant feature work - this is just to help us remember, since it's pretty important.
        # expected_provider['privileges'][0]['status'] = 'inactive'

        # add expected compactTransactionId to the expected provider
        expected_provider['privileges'][0]['compactTransactionId'] = '1234567890'

        provider_data = json.loads(resp['body'])
        # Removing dynamic fields from comparison
        del expected_provider['providerId']
        del provider_data['providerId']
        del expected_provider['dateOfUpdate']
        del provider_data['dateOfUpdate']
        del expected_provider['licenses'][0]['dateOfUpdate']
        del provider_data['licenses'][0]['dateOfUpdate']

        self.assertEqual(expected_provider, provider_data)

    def test_old_inactive_license(self):
        from handlers.ingest import ingest_license_message
        from handlers.providers import get_provider

        # The test resource provider has a license in oh
        self._load_provider_data()
        with open('../common/tests/resources/dynamo/provider-ssn.json') as f:
            provider_id = json.load(f)['providerId']

        with open('../common/tests/resources/ingest/message.json') as f:
            message = json.load(f)
        # Imagine that this provider used to be licensed in ky.
        # What happens if ky uploads that inactive license?
        message['detail']['dateOfIssuance'] = '2023-01-01'
        message['detail']['familyName'] = 'Oldname'
        message['detail']['jurisdiction'] = 'ky'
        message['detail']['status'] = 'inactive'

        event = {'Records': [{'messageId': '123', 'body': json.dumps(message)}]}

        resp = ingest_license_message(event, self.mock_context)

        self.assertEqual({'batchItemFailures': []}, resp)

        # To test full internal consistency, we'll also pull this new license record out
        # via the API to make sure it shows up as expected.
        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        event['pathParameters'] = {'compact': 'aslp', 'providerId': provider_id}
        event['requestContext']['authorizer']['claims']['scope'] = (
            'openid email stuff aslp/readGeneral ' 'aslp/aslp.readPrivate'
        )
        resp = get_provider(event, self.mock_context)
        self.assertEqual(resp['statusCode'], 200)

        with open('../common/tests/resources/api/provider-detail-response.json') as f:
            expected_provider = json.load(f)

        provider_data = json.loads(resp['body'])

        # Removing dynamic fields from comparison
        del expected_provider['providerId']
        del provider_data['providerId']
        del expected_provider['dateOfUpdate']
        del provider_data['dateOfUpdate']

        # We will look at the licenses separately
        del expected_provider['licenses']
        licenses = provider_data.pop('licenses')
        # add expected compactTransactionId to the expected provider
        expected_provider['privileges'][0]['compactTransactionId'] = '1234567890'

        # The original provider data is preferred over the posted license data in our test case
        self.assertEqual(expected_provider, provider_data)

        # But the second license should now be listed
        self.assertEqual(2, len(licenses))

    def test_newer_active_license(self):
        from handlers.ingest import ingest_license_message
        from handlers.providers import get_provider

        # The test resource provider has a license in oh
        self._load_provider_data()
        with open('../common/tests/resources/dynamo/provider-ssn.json') as f:
            provider_id = json.load(f)['providerId']

        with open('../common/tests/resources/ingest/message.json') as f:
            message = json.load(f)
        # Imagine that this provider was just licensed in ky.
        # What happens if ky uploads that new license?
        message['detail']['dateOfIssuance'] = '2024-08-01'
        message['detail']['familyName'] = 'Newname'
        message['detail']['jurisdiction'] = 'ky'
        message['detail']['status'] = 'active'

        event = {'Records': [{'messageId': '123', 'body': json.dumps(message)}]}

        resp = ingest_license_message(event, self.mock_context)

        self.assertEqual({'batchItemFailures': []}, resp)

        # To test full internal consistency, we'll also pull this new license record out
        # via the API to make sure it shows up as expected.
        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        event['pathParameters'] = {'compact': 'aslp', 'providerId': provider_id}
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email stuff aslp/readGeneral'
        resp = get_provider(event, self.mock_context)
        self.assertEqual(resp['statusCode'], 200)

        provider_data = json.loads(resp['body'])

        # The new name and jurisdiction should be reflected in the provider data
        self.assertEqual('Newname', provider_data['familyName'])
        self.assertEqual('ky', provider_data['licenseJurisdiction'])

        # And the second license should now be listed
        self.assertEqual(2, len(provider_data['licenses']))
