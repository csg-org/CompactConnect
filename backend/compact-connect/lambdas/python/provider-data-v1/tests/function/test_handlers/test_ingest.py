import json

from moto import mock_aws

from .. import TstFunction


@mock_aws
class TestIngest(TstFunction):
    def _with_ingested_license(self) -> str:
        from handlers.ingest import ingest_license_message

        with open('../common/tests/resources/dynamo/provider-ssn.json') as f:
            ssn_record = json.load(f)

        self._ssn_table.put_item(Item=ssn_record)
        provider_id = ssn_record['providerId']

        with open('../common/tests/resources/ingest/message.json') as f:
            message = json.load(f)

        # Upload a new license
        event = {'Records': [{'messageId': '123', 'body': json.dumps(message)}]}
        resp = ingest_license_message(event, self.mock_context)
        self.assertEqual({'batchItemFailures': []}, resp)

        return provider_id

    def _get_provider_via_api(self, provider_id: str) -> dict:
        from handlers.providers import get_provider

        # To test full internal consistency, we'll also pull this new license record out
        # via the API to make sure it shows up as expected.
        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        event['pathParameters'] = {'compact': 'aslp', 'providerId': provider_id}
        event['requestContext']['authorizer']['claims']['scope'] = (
            'openid email stuff aslp/readGeneral aslp/aslp.readPrivate'
        )
        resp = get_provider(event, self.mock_context)
        self.assertEqual(resp['statusCode'], 200)
        return json.loads(resp['body'])

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

        # Find the provider's id from their ssn
        resp = query_providers(event, self.mock_context)
        self.assertEqual(resp['statusCode'], 200)
        provider_id = json.loads(resp['body'])['providers'][0]['providerId']

        # Now get the full provider details
        provider_data = self._get_provider_via_api(provider_id)

        with open('../common/tests/resources/api/provider-detail-response.json') as f:
            expected_provider = json.load(f)

        # The canned response resource assumes that the provider will be given a privilege, military affiliation, and
        # one license renewal. We didn't do any of that here, so we'll reset that data
        expected_provider['privilegeJurisdictions'] = []
        expected_provider['privileges'] = []
        expected_provider['militaryAffiliations'] = []
        for license_data in expected_provider['licenses']:
            license_data['history'] = []

        # Removing/setting dynamic fields for comparison
        del expected_provider['dateOfUpdate']
        del provider_data['dateOfUpdate']
        expected_provider['providerId'] = provider_id
        for license_data in expected_provider['licenses']:
            del license_data['dateOfUpdate']
            license_data['providerId'] = provider_id
        for license_data in provider_data['licenses']:
            del license_data['dateOfUpdate']

        self.assertEqual(expected_provider, provider_data)

    def test_old_inactive_license(self):
        from handlers.ingest import ingest_license_message

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

        with open('../common/tests/resources/api/provider-detail-response.json') as f:
            expected_provider = json.load(f)

        provider_data = self._get_provider_via_api(provider_id)

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

        provider_data = self._get_provider_via_api(provider_id)

        # The new name and jurisdiction should be reflected in the provider data
        self.assertEqual('Newname', provider_data['familyName'])
        self.assertEqual('ky', provider_data['licenseJurisdiction'])

        # And the second license should now be listed
        self.assertEqual(2, len(provider_data['licenses']))

    def test_existing_provider_deactivation(self):
        from handlers.ingest import ingest_license_message

        provider_id = self._with_ingested_license()

        with open('../common/tests/resources/ingest/message.json') as f:
            message = json.load(f)

        # What happens if their license goes inactive in a subsequent upload?
        message['detail']['status'] = 'inactive'
        event = {'Records': [{'messageId': '123', 'body': json.dumps(message)}]}
        resp = ingest_license_message(event, self.mock_context)
        self.assertEqual({'batchItemFailures': []}, resp)

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

        provider_data = self._get_provider_via_api(provider_id)

        # The canned response resource assumes that the provider will be given a privilege, military affiliation, and
        # one license renewal. We didn't do any of that here, so we'll reset that data
        expected_provider['privilegeJurisdictions'] = []
        expected_provider['privileges'] = []
        expected_provider['militaryAffiliations'] = []
        for license_data in expected_provider['licenses']:
            # We uploaded a 'deactivation' by just switching 'status' to 'inactive', so this change
            # should show up in the license history
            license_data['history'] = [
                {
                    'type': 'licenseUpdate',
                    'updateType': 'deactivation',
                    'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570',
                    'compact': 'aslp',
                    'jurisdiction': 'oh',
                    'previous': {
                        'ssn': '123-12-1234',
                        'npi': '0608337260',
                        'licenseType': 'speech-language pathologist',
                        'jurisdictionStatus': 'active',
                        'givenName': 'Björk',
                        'middleName': 'Gunnar',
                        'familyName': 'Guðmundsdóttir',
                        'dateOfIssuance': '2010-06-06',
                        'dateOfBirth': '1985-06-06',
                        'dateOfExpiration': '2025-04-04',
                        'dateOfRenewal': '2020-04-04',
                        'homeAddressStreet1': '123 A St.',
                        'homeAddressStreet2': 'Apt 321',
                        'homeAddressCity': 'Columbus',
                        'homeAddressState': 'oh',
                        'homeAddressPostalCode': '43004',
                        'emailAddress': 'björk@example.com',
                        'phoneNumber': '+13213214321',
                        'militaryWaiver': False,
                    },
                    'updatedValues': {'jurisdictionStatus': 'inactive'},
                }
            ]

        # Removing/setting dynamic fields for comparison
        del expected_provider['dateOfUpdate']
        del provider_data['dateOfUpdate']
        expected_provider['providerId'] = provider_id
        for license_data in expected_provider['licenses']:
            del license_data['dateOfUpdate']
            license_data['providerId'] = provider_id
        for license_data in provider_data['licenses']:
            del license_data['dateOfUpdate']
            for hist in license_data['history']:
                del hist['dateOfUpdate']
                del hist['previous']['dateOfUpdate']

        self.assertEqual(expected_provider, provider_data)

    def test_existing_provider_renewal(self):
        from handlers.ingest import ingest_license_message

        provider_id = self._with_ingested_license()

        with open('../common/tests/resources/ingest/message.json') as f:
            message = json.load(f)

        message['detail'].update({'dateOfRenewal': '2025-03-03', 'dateOfExpiration': '2030-03-03'})

        # What happens if their license is renewed in a subsequent upload?
        event = {'Records': [{'messageId': '123', 'body': json.dumps(message)}]}
        resp = ingest_license_message(event, self.mock_context)
        self.assertEqual({'batchItemFailures': []}, resp)

        with open('../common/tests/resources/api/provider-detail-response.json') as f:
            expected_provider = json.load(f)

        # The license status and provider should immediately reflect the new dates
        expected_provider['dateOfExpiration'] = '2030-03-03'
        expected_provider['licenses'][0]['dateOfExpiration'] = '2030-03-03'
        expected_provider['licenses'][0]['dateOfRenewal'] = '2025-03-03'

        provider_data = self._get_provider_via_api(provider_id)

        # The canned response resource assumes that the provider will be given a privilege, military affiliation, and
        # one license renewal. We didn't do any of that here, so we'll reset that data
        expected_provider['privilegeJurisdictions'] = []
        expected_provider['privileges'] = []
        expected_provider['militaryAffiliations'] = []
        for license_data in expected_provider['licenses']:
            # We uploaded a 'renewal' by just updating the dateOfRenewal and dateOfExpiration
            # This should show up in the license history
            license_data['history'] = [
                {
                    'type': 'licenseUpdate',
                    'updateType': 'renewal',
                    'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570',
                    'compact': 'aslp',
                    'jurisdiction': 'oh',
                    'previous': {
                        'ssn': '123-12-1234',
                        'npi': '0608337260',
                        'licenseType': 'speech-language pathologist',
                        'jurisdictionStatus': 'active',
                        'givenName': 'Björk',
                        'middleName': 'Gunnar',
                        'familyName': 'Guðmundsdóttir',
                        'dateOfIssuance': '2010-06-06',
                        'dateOfBirth': '1985-06-06',
                        'dateOfExpiration': '2025-04-04',
                        'dateOfRenewal': '2020-04-04',
                        'homeAddressStreet1': '123 A St.',
                        'homeAddressStreet2': 'Apt 321',
                        'homeAddressCity': 'Columbus',
                        'homeAddressState': 'oh',
                        'homeAddressPostalCode': '43004',
                        'emailAddress': 'björk@example.com',
                        'phoneNumber': '+13213214321',
                        'militaryWaiver': False,
                    },
                    'updatedValues': {
                        'dateOfRenewal': '2025-03-03',
                        'dateOfExpiration': '2030-03-03',
                    },
                }
            ]

        # Removing/setting dynamic fields for comparison
        del expected_provider['dateOfUpdate']
        del provider_data['dateOfUpdate']
        expected_provider['providerId'] = provider_id
        for license_data in expected_provider['licenses']:
            del license_data['dateOfUpdate']
            license_data['providerId'] = provider_id
        for license_data in provider_data['licenses']:
            del license_data['dateOfUpdate']
            for hist in license_data['history']:
                del hist['dateOfUpdate']
                del hist['previous']['dateOfUpdate']

        self.assertEqual(expected_provider, provider_data)

    def test_existing_provider_name_change(self):
        from handlers.ingest import ingest_license_message

        provider_id = self._with_ingested_license()

        with open('../common/tests/resources/ingest/message.json') as f:
            message = json.load(f)

        message['detail'].update({'familyName': 'VonSmitherton'})

        # What happens if their license is renewed in a subsequent upload?
        event = {'Records': [{'messageId': '123', 'body': json.dumps(message)}]}
        resp = ingest_license_message(event, self.mock_context)
        self.assertEqual({'batchItemFailures': []}, resp)

        with open('../common/tests/resources/api/provider-detail-response.json') as f:
            expected_provider = json.load(f)

        # The license status and provider should immediately reflect the new name
        expected_provider['familyName'] = 'VonSmitherton'
        expected_provider['licenses'][0]['familyName'] = 'VonSmitherton'

        provider_data = self._get_provider_via_api(provider_id)

        # The canned response resource assumes that the provider will be given a privilege, military affiliation, and
        # one license renewal. We didn't do any of that here, so we'll reset that data
        expected_provider['privilegeJurisdictions'] = []
        expected_provider['privileges'] = []
        expected_provider['militaryAffiliations'] = []
        for license_data in expected_provider['licenses']:
            # We uploaded a 'name change' by just updating the familyName
            # This should show up in the license history
            license_data['history'] = [
                {
                    'type': 'licenseUpdate',
                    'updateType': 'other',
                    'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570',
                    'compact': 'aslp',
                    'jurisdiction': 'oh',
                    'previous': {
                        'ssn': '123-12-1234',
                        'npi': '0608337260',
                        'licenseType': 'speech-language pathologist',
                        'jurisdictionStatus': 'active',
                        'givenName': 'Björk',
                        'middleName': 'Gunnar',
                        'familyName': 'Guðmundsdóttir',
                        'dateOfIssuance': '2010-06-06',
                        'dateOfBirth': '1985-06-06',
                        'dateOfExpiration': '2025-04-04',
                        'dateOfRenewal': '2020-04-04',
                        'homeAddressStreet1': '123 A St.',
                        'homeAddressStreet2': 'Apt 321',
                        'homeAddressCity': 'Columbus',
                        'homeAddressState': 'oh',
                        'homeAddressPostalCode': '43004',
                        'emailAddress': 'björk@example.com',
                        'phoneNumber': '+13213214321',
                        'militaryWaiver': False,
                    },
                    'updatedValues': {
                        'familyName': 'VonSmitherton',
                    },
                }
            ]

        # Removing/setting dynamic fields for comparison
        del expected_provider['dateOfUpdate']
        del provider_data['dateOfUpdate']
        expected_provider['providerId'] = provider_id
        for license_data in expected_provider['licenses']:
            del license_data['dateOfUpdate']
            license_data['providerId'] = provider_id
        for license_data in provider_data['licenses']:
            del license_data['dateOfUpdate']
            for hist in license_data['history']:
                del hist['dateOfUpdate']
                del hist['previous']['dateOfUpdate']

        self.assertEqual(expected_provider, provider_data)

    def test_existing_provider_no_change(self):
        from handlers.ingest import ingest_license_message

        provider_id = self._with_ingested_license()

        with open('../common/tests/resources/ingest/message.json') as f:
            message = json.load(f)

        # What happens if their license is uploaded again with no change?
        event = {'Records': [{'messageId': '123', 'body': json.dumps(message)}]}
        resp = ingest_license_message(event, self.mock_context)
        self.assertEqual({'batchItemFailures': []}, resp)

        with open('../common/tests/resources/api/provider-detail-response.json') as f:
            expected_provider = json.load(f)

        # The license status and provider should remain unchanged
        provider_data = self._get_provider_via_api(provider_id)

        # The canned response resource assumes that the provider will be given a privilege, military affiliation, and
        # one license renewal. We didn't do any of that here, so we'll reset that data
        expected_provider['privilegeJurisdictions'] = []
        expected_provider['privileges'] = []
        expected_provider['militaryAffiliations'] = []
        for license_data in expected_provider['licenses']:
            # No changes should show up in the license history
            license_data['history'] = []

        # Removing/setting dynamic fields for comparison
        del expected_provider['dateOfUpdate']
        del provider_data['dateOfUpdate']
        expected_provider['providerId'] = provider_id
        for license_data in expected_provider['licenses']:
            del license_data['dateOfUpdate']
            license_data['providerId'] = provider_id
        for license_data in provider_data['licenses']:
            del license_data['dateOfUpdate']
            for hist in license_data['history']:
                del hist['dateOfUpdate']
                del hist['previous']['dateOfUpdate']

        self.assertEqual(expected_provider, provider_data)
