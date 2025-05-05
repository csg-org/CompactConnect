import json
from datetime import datetime
from unittest.mock import patch

from moto import mock_aws

from .. import TstFunction


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
class TestIngest(TstFunction):
    @staticmethod
    def _set_provider_data_to_empty_values(expected_provider: dict) -> dict:
        # The canned response resource assumes that the provider will be given a privilege, military affiliation,
        # home state selection, and one license renewal. We didn't do any of that here, so we'll reset that data
        expected_provider['privilegeJurisdictions'] = []
        expected_provider['privileges'] = []
        expected_provider['militaryAffiliations'] = []
        del expected_provider['homeJurisdictionSelection']

        # in these test cases, the provider user has not registered in the system, so these values will not be
        # present
        del expected_provider['compactConnectRegisteredEmailAddress']
        del expected_provider['cognitoSub']
        return expected_provider

    def _with_ingested_license(self, omit_email: bool = False) -> str:
        from handlers.ingest import ingest_license_message

        with open('../common/tests/resources/dynamo/provider-ssn.json') as f:
            ssn_record = json.load(f)

        self._ssn_table.put_item(Item=ssn_record)
        provider_id = ssn_record['providerId']

        with open('../common/tests/resources/ingest/event-bridge-message.json') as f:
            message = json.load(f)

        if omit_email:
            del message['detail']['emailAddress']

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
            'openid email stuff aslp/readGeneral aslp/readPrivate'
        )
        resp = get_provider(event, self.mock_context)
        self.assertEqual(resp['statusCode'], 200)
        return json.loads(resp['body'])

    def test_new_provider_ingest(self):
        from handlers.ingest import ingest_license_message

        with open('../common/tests/resources/ingest/event-bridge-message.json') as f:
            message = f.read()

        provider_id = json.loads(message)['detail']['providerId']

        event = {'Records': [{'messageId': '123', 'body': message}]}

        resp = ingest_license_message(event, self.mock_context)

        self.assertEqual({'batchItemFailures': []}, resp)

        # Now get the full provider details
        provider_data = self._get_provider_via_api(provider_id)

        with open('../common/tests/resources/api/provider-detail-response.json') as f:
            expected_provider = json.load(f)

        # Reset the expected data to match the canned response
        expected_provider = self._set_provider_data_to_empty_values(expected_provider)
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

        with open('../common/tests/resources/ingest/event-bridge-message.json') as f:
            message = json.load(f)
        # Imagine that this provider used to be licensed in ky.
        # What happens if ky uploads that inactive license?
        message['detail']['dateOfIssuance'] = '2023-01-01'
        message['detail']['familyName'] = 'Oldname'
        message['detail']['jurisdiction'] = 'ky'
        message['detail']['licenseStatus'] = 'inactive'
        message['detail']['compactEligibility'] = 'ineligible'

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

    def test_newer_active_license_and_provider_has_not_registered_in_system(self):
        from handlers.ingest import ingest_license_message

        # The test resource provider has a license in oh
        self._load_provider_data()
        with open('../common/tests/resources/dynamo/provider-ssn.json') as f:
            provider_id = json.load(f)['providerId']

        with open('../common/tests/resources/ingest/event-bridge-message.json') as f:
            message = json.load(f)
        # Imagine that this provider was just licensed in ky, but has not registered with the system (ie has not
        # picked a home state).
        # If ky uploads that new active license with a later issuance date, it should be selected as the licensee
        message['detail']['dateOfIssuance'] = '2024-08-01'
        message['detail']['familyName'] = 'Newname'
        message['detail']['jurisdiction'] = 'ky'
        message['detail']['licenseStatus'] = 'active'
        message['detail']['compactEligibility'] = 'eligible'
        # remove the home state selection for the provider which was added by the TstFunction test setup
        self.config.provider_table.delete_item(
            Key={
                'pk': f'aslp#PROVIDER#{provider_id}',
                'sk': 'aslp#PROVIDER#home-jurisdiction#',
            }
        )

        event = {'Records': [{'messageId': '123', 'body': json.dumps(message)}]}

        resp = ingest_license_message(event, self.mock_context)

        self.assertEqual({'batchItemFailures': []}, resp)

        provider_data = self._get_provider_via_api(provider_id)

        # The new name and jurisdiction should be reflected in the provider data
        self.assertEqual('Newname', provider_data['familyName'])
        self.assertEqual('ky', provider_data['licenseJurisdiction'])

        # And the second license should now be listed
        self.assertEqual(2, len(provider_data['licenses']))

    def test_newer_active_license_and_provider_is_registered_in_system(self):
        """
        The test setup creates a provider with a home state selection of 'oh'.
        This test checks that a new active license in a different jurisdiction does not override the home state
        selection.
        """
        from handlers.ingest import ingest_license_message

        # The test resource provider has a license in oh
        self._load_provider_data()
        with open('../common/tests/resources/dynamo/provider-ssn.json') as f:
            provider_id = json.load(f)['providerId']

        with open('../common/tests/resources/ingest/event-bridge-message.json') as f:
            message = json.load(f)
        # Imagine that this provider was just licensed in ky, and has registered with the system with a home state
        # selection of 'oh'.
        # If ky uploads that new active license with a later issuance date, it should NOT be set as provider's
        # license since it conflicts with their selected home state.
        message['detail']['dateOfIssuance'] = '2024-08-01'
        message['detail']['familyName'] = 'Newname'
        message['detail']['jurisdiction'] = 'ky'
        message['detail']['licenseStatus'] = 'active'
        message['detail']['compactEligibility'] = 'eligible'

        event = {'Records': [{'messageId': '123', 'body': json.dumps(message)}]}

        resp = ingest_license_message(event, self.mock_context)

        self.assertEqual({'batchItemFailures': []}, resp)

        provider_data = self._get_provider_via_api(provider_id)

        # The old name and jurisdiction should be reflected in the provider data
        self.assertEqual('Guðmundsdóttir', provider_data['familyName'])
        self.assertEqual('oh', provider_data['licenseJurisdiction'])

        # And the second license should now be listed
        self.assertEqual(2, len(provider_data['licenses']))

    @patch('handlers.ingest.EventBatchWriter', autospec=True)
    def test_existing_provider_deactivation(self, mock_event_writer):
        from handlers.ingest import ingest_license_message

        provider_id = self._with_ingested_license()

        with open('../common/tests/resources/ingest/event-bridge-message.json') as f:
            message = json.load(f)

        # What happens if their license goes inactive in a subsequent upload?
        message['detail']['licenseStatus'] = 'inactive'
        message['detail']['compactEligibility'] = 'ineligible'
        event = {'Records': [{'messageId': '123', 'body': json.dumps(message)}]}
        resp = ingest_license_message(event, self.mock_context)
        self.assertEqual({'batchItemFailures': []}, resp)

        with open('../common/tests/resources/api/provider-detail-response.json') as f:
            expected_provider = json.load(f)

        # The license status and provider should immediately be inactive
        expected_provider['jurisdictionUploadedLicenseStatus'] = 'inactive'
        expected_provider['jurisdictionUploadedCompactEligibility'] = 'ineligible'
        expected_provider['licenses'][0]['jurisdictionUploadedLicenseStatus'] = 'inactive'
        expected_provider['licenses'][0]['jurisdictionUploadedCompactEligibility'] = 'ineligible'
        # these should be calculated as inactive at record load time
        expected_provider['licenseStatus'] = 'inactive'
        expected_provider['licenses'][0]['licenseStatus'] = 'inactive'
        expected_provider['compactEligibility'] = 'ineligible'
        expected_provider['licenses'][0]['compactEligibility'] = 'ineligible'
        # ensure the privilege record is also set to inactive
        expected_provider['privileges'][0]['status'] = 'inactive'

        provider_data = self._get_provider_via_api(provider_id)

        # Reset the expected data to match the canned response
        expected_provider = self._set_provider_data_to_empty_values(expected_provider)
        for license_data in expected_provider['licenses']:
            # We uploaded a 'deactivation' by just switching 'licenseStatus' to 'inactive', so this change
            # should show up in the license history
            license_data['history'] = [
                {
                    'type': 'licenseUpdate',
                    'updateType': 'deactivation',
                    'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570',
                    'compact': 'aslp',
                    'jurisdiction': 'oh',
                    'licenseType': 'speech-language pathologist',
                    'previous': {
                        'ssnLastFour': '1234',
                        'npi': '0608337260',
                        'licenseNumber': 'A0608337260',
                        'jurisdictionUploadedLicenseStatus': 'active',
                        'licenseStatusName': 'DEFINITELY_A_HUMAN',
                        'jurisdictionUploadedCompactEligibility': 'eligible',
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
                    },
                    'updatedValues': {
                        'jurisdictionUploadedLicenseStatus': 'inactive',
                        'jurisdictionUploadedCompactEligibility': 'ineligible',
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
        # Assert that an event was sent for the deactivation
        mock_event_writer.return_value.__enter__.return_value.put_event.assert_called_once()
        call_kwargs = mock_event_writer.return_value.__enter__.return_value.put_event.call_args.kwargs
        self.assertEqual(
            call_kwargs,
            {
                'Entry': {
                    'Source': 'org.compactconnect.provider-data',
                    'DetailType': 'license.deactivation',
                    'Detail': json.dumps(
                        {
                            'eventTime': '2024-11-08T23:59:59+00:00',
                            'compact': 'aslp',
                            'jurisdiction': 'oh',
                            'providerId': provider_id,
                        }
                    ),
                    'EventBusName': 'license-data-events',
                }
            },
        )

    def test_existing_provider_renewal(self):
        from handlers.ingest import ingest_license_message

        provider_id = self._with_ingested_license()

        with open('../common/tests/resources/ingest/event-bridge-message.json') as f:
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

        # Reset the expected data to match the canned response
        expected_provider = self._set_provider_data_to_empty_values(expected_provider)

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
                    'licenseType': 'speech-language pathologist',
                    'previous': {
                        'ssnLastFour': '1234',
                        'npi': '0608337260',
                        'licenseNumber': 'A0608337260',
                        'jurisdictionUploadedLicenseStatus': 'active',
                        'licenseStatusName': 'DEFINITELY_A_HUMAN',
                        'jurisdictionUploadedCompactEligibility': 'eligible',
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

        with open('../common/tests/resources/ingest/event-bridge-message.json') as f:
            message = json.load(f)

        message['detail'].update({'familyName': 'VonSmitherton'})

        # What happens if their name changes in a subsequent upload?
        event = {'Records': [{'messageId': '123', 'body': json.dumps(message)}]}
        resp = ingest_license_message(event, self.mock_context)
        self.assertEqual({'batchItemFailures': []}, resp)

        with open('../common/tests/resources/api/provider-detail-response.json') as f:
            expected_provider = json.load(f)

        # The license status and provider should immediately reflect the new name
        expected_provider['familyName'] = 'VonSmitherton'
        expected_provider['licenses'][0]['familyName'] = 'VonSmitherton'

        provider_data = self._get_provider_via_api(provider_id)

        # Reset the expected data to match the canned response
        expected_provider = self._set_provider_data_to_empty_values(expected_provider)

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
                    'licenseType': 'speech-language pathologist',
                    'previous': {
                        'ssnLastFour': '1234',
                        'npi': '0608337260',
                        'licenseNumber': 'A0608337260',
                        'jurisdictionUploadedLicenseStatus': 'active',
                        'licenseStatusName': 'DEFINITELY_A_HUMAN',
                        'jurisdictionUploadedCompactEligibility': 'eligible',
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

        with open('../common/tests/resources/ingest/event-bridge-message.json') as f:
            message = json.load(f)

        # What happens if their license is uploaded again with no change?
        event = {'Records': [{'messageId': '123', 'body': json.dumps(message)}]}
        resp = ingest_license_message(event, self.mock_context)
        self.assertEqual({'batchItemFailures': []}, resp)

        with open('../common/tests/resources/api/provider-detail-response.json') as f:
            expected_provider = json.load(f)

        # The license status and provider should remain unchanged
        provider_data = self._get_provider_via_api(provider_id)

        # Reset the expected data to match the canned response
        expected_provider = self._set_provider_data_to_empty_values(expected_provider)
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

    def test_existing_provider_removed_email(self):
        from handlers.ingest import ingest_license_message

        provider_id = self._with_ingested_license()

        with open('../common/tests/resources/ingest/event-bridge-message.json') as f:
            message = json.load(f)

        del message['detail']['emailAddress']

        # What happens if their email is removed in a subsequent upload?
        event = {'Records': [{'messageId': '123', 'body': json.dumps(message)}]}
        resp = ingest_license_message(event, self.mock_context)
        self.assertEqual({'batchItemFailures': []}, resp)

        with open('../common/tests/resources/api/provider-detail-response.json') as f:
            expected_provider = json.load(f)

        # The license status and provider should immediately reflect the removal of the email
        provider_data = self._get_provider_via_api(provider_id)

        # Reset the expected data to match the canned response
        expected_provider = self._set_provider_data_to_empty_values(expected_provider)

        # Removing the field we just removed from the license
        del expected_provider['emailAddress']

        for license_data in expected_provider['licenses']:
            # We uploaded a license with no email by just deleting emailAddress
            # This should show up in the license history
            del license_data['emailAddress']
            license_data['history'] = [
                {
                    'type': 'licenseUpdate',
                    'updateType': 'other',
                    'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570',
                    'compact': 'aslp',
                    'jurisdiction': 'oh',
                    'licenseType': 'speech-language pathologist',
                    'previous': {
                        'ssnLastFour': '1234',
                        'npi': '0608337260',
                        'licenseNumber': 'A0608337260',
                        'jurisdictionUploadedLicenseStatus': 'active',
                        'licenseStatusName': 'DEFINITELY_A_HUMAN',
                        'jurisdictionUploadedCompactEligibility': 'eligible',
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
                    },
                    'updatedValues': {},
                    'removedValues': ['emailAddress'],
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

    def test_existing_provider_added_email(self):
        from handlers.ingest import ingest_license_message

        provider_id = self._with_ingested_license(omit_email=True)

        with open('../common/tests/resources/ingest/event-bridge-message.json') as f:
            message = json.load(f)

        # What happens if their email is added in a subsequent upload?
        event = {'Records': [{'messageId': '123', 'body': json.dumps(message)}]}
        resp = ingest_license_message(event, self.mock_context)
        self.assertEqual({'batchItemFailures': []}, resp)

        with open('../common/tests/resources/api/provider-detail-response.json') as f:
            expected_provider = json.load(f)

        # The license status and provider should immediately reflect the new email
        provider_data = self._get_provider_via_api(provider_id)

        # Reset the expected data to match the canned response
        expected_provider = self._set_provider_data_to_empty_values(expected_provider)

        for license_data in expected_provider['licenses']:
            # We added an emailAddress. This should show up in the license history
            license_data['history'] = [
                {
                    'type': 'licenseUpdate',
                    'updateType': 'other',
                    'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570',
                    'compact': 'aslp',
                    'jurisdiction': 'oh',
                    'licenseType': 'speech-language pathologist',
                    'previous': {
                        'ssnLastFour': '1234',
                        'npi': '0608337260',
                        'licenseNumber': 'A0608337260',
                        'jurisdictionUploadedLicenseStatus': 'active',
                        'licenseStatusName': 'DEFINITELY_A_HUMAN',
                        'jurisdictionUploadedCompactEligibility': 'eligible',
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
                        'phoneNumber': '+13213214321',
                    },
                    'updatedValues': {
                        'emailAddress': 'björk@example.com',
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

    def test_preprocess_license_ingest_creates_ssn_provider_record(self):
        from handlers.ingest import preprocess_license_ingest

        test_ssn = '123-12-1234'

        # Before running method under test, ensure the provider ssn record does not exist
        provider = self._ssn_table.get_item(Key={'pk': f'aslp#SSN#{test_ssn}', 'sk': f'aslp#SSN#{test_ssn}'})
        self.assertNotIn('Item', provider)

        with open('../common/tests/resources/ingest/preprocessor-sqs-message.json') as f:
            message = json.load(f)
            # set fixed ssn here to ensure we are checking the expected value
            message['ssn'] = test_ssn

        event = {'Records': [{'messageId': '123', 'body': json.dumps(message)}]}

        resp = preprocess_license_ingest(event, self.mock_context)
        self.assertEqual({'batchItemFailures': []}, resp)

        # Find the provider's id from their ssn
        provider = self._ssn_table.get_item(Key={'pk': f'aslp#SSN#{test_ssn}', 'sk': f'aslp#SSN#{test_ssn}'})['Item']
        provider_id = provider['providerId']
        # the provider_id is randomly generated, so we cannot check an exact value, just to make sure it exists
        self.assertIsNotNone(provider_id)

    def test_preprocess_license_returns_batch_item_failure_if_error_occurs(self):
        from handlers.ingest import preprocess_license_ingest

        # adding an invalid ssn here to force an exception
        test_ssn = False
        with open('../common/tests/resources/ingest/preprocessor-sqs-message.json') as f:
            message = json.load(f)
            # set fixed ssn here to ensure we are checking the expected value
            message['ssn'] = test_ssn

        event = {'Records': [{'messageId': '123', 'body': json.dumps(message)}]}

        resp = preprocess_license_ingest(event, self.mock_context)
        self.assertEqual({'batchItemFailures': [{'itemIdentifier': '123'}]}, resp)

    def test_inactive_privileges_included_in_privilege_jurisdictions(self):
        """
        Test that inactive privileges are included in the privilegeJurisdictions list.
        This test verifies that we include all jurisdictions a user has privileges in,
        regardless of whether they are active or not.
        """
        from handlers.ingest import ingest_license_message

        # The test resource provider has a license in oh and active privilege in ne
        self._load_provider_data()
        with open('../common/tests/resources/dynamo/provider-ssn.json') as f:
            provider_id = json.load(f)['providerId']

        # Add an inactive privilege record for this provider in a different jurisdiction (ky)
        inactive_privilege = {
            'pk': f'aslp#PROVIDER#{provider_id}',
            'sk': 'aslp#PROVIDER#privilege/ky#',
            'type': 'privilege',
            'providerId': provider_id,
            'compact': 'aslp',
            'jurisdiction': 'ky',
            'licenseType': 'speech-language pathologist',
            'licenseJurisdiction': 'oh',
            'dateOfIssuance': '2023-01-01',
            'dateOfRenewal': '2023-01-01',
            'dateOfExpiration': '2025-01-01',
            'dateOfUpdate': '2025-01-01T12:59:59+00:00',
            'compactTransactionId': '1234567890',
            'compactTransactionIdGSIPK': 'COMPACT#aslp#TX#1234567890#',
            'privilegeId': 'test-privilege-id',
            'administratorSetStatus': 'inactive',  # This privilege is inactive
            'attestations': [],
        }
        self.config.provider_table.put_item(Item=inactive_privilege)

        # Now ingest a new license to trigger the provider record update
        with open('../common/tests/resources/ingest/event-bridge-message.json') as f:
            message = json.load(f)

        # Make a small change to trigger an update
        message['detail']['phoneNumber'] = '+19876543210'

        event = {'Records': [{'messageId': '123', 'body': json.dumps(message)}]}
        resp = ingest_license_message(event, self.mock_context)
        self.assertEqual({'batchItemFailures': []}, resp)

        # Get the provider data and verify that the inactive privilege jurisdiction is included
        provider_data = self._get_provider_via_api(provider_id)

        # The privilegeJurisdictions should include both the active privilege from the test setup
        # and the inactive privilege we just added
        self.assertEqual({'ky', 'ne'}, set(provider_data['privilegeJurisdictions']))

    def test_multiple_license_types_same_jurisdiction(self):
        """
        Test that multiple license types in the same jurisdiction are handled correctly.

        This test:
        1. Ingests a first active license with licenseType: speech-language pathologist
        2. For the same provider, ingests a second active license with licenseType: audiologist and a newer
           dateOfIssuance
        3. Verifies that both licenses are present and that the provider data was copied from the audiologist license
        """
        from handlers.ingest import ingest_license_message

        # First, ingest a speech-language pathologist license
        provider_id = self._with_ingested_license()

        # Get the provider data after the first license ingest
        provider_data_after_first_license = self._get_provider_via_api(provider_id)

        # Verify the first license was ingested correctly
        self.assertEqual(1, len(provider_data_after_first_license['licenses']))
        self.assertEqual('speech-language pathologist', provider_data_after_first_license['licenses'][0]['licenseType'])
        self.assertEqual('oh', provider_data_after_first_license['licenseJurisdiction'])
        self.assertEqual('Björk', provider_data_after_first_license['givenName'])

        # Now ingest a second license for the same provider but with a different license type
        # and a newer issuance date
        with open('../common/tests/resources/ingest/event-bridge-message.json') as f:
            message = json.load(f)

        # Update the message to be for an audiologist license with a newer issuance date
        # and a different givenName to track which license is used for provider data
        message['detail'].update(
            {
                'licenseType': 'audiologist',
                'dateOfIssuance': '2020-06-06',  # Newer than the first license (2010-06-06)
                'licenseNumber': 'B0608337260',  # Different license number
                'givenName': 'Audrey',  # Different name to track which license is used
            }
        )

        # Ingest the second license
        event = {'Records': [{'messageId': '456', 'body': json.dumps(message)}]}
        resp = ingest_license_message(event, self.mock_context)
        self.assertEqual({'batchItemFailures': []}, resp)

        # Get the updated provider data
        provider_data = self._get_provider_via_api(provider_id)

        # Verify that both licenses are present
        self.assertEqual(2, len(provider_data['licenses']))

        # Find each license by type
        slp_license = next(
            (lic for lic in provider_data['licenses'] if lic['licenseType'] == 'speech-language pathologist'), None
        )
        aud_license = next((lic for lic in provider_data['licenses'] if lic['licenseType'] == 'audiologist'), None)

        # Verify both licenses exist
        self.assertIsNotNone(slp_license, 'Speech-language pathologist license not found')
        self.assertIsNotNone(aud_license, 'Audiologist license not found')

        # Verify license details
        self.assertEqual('A0608337260', slp_license['licenseNumber'])
        self.assertEqual('2010-06-06', slp_license['dateOfIssuance'])
        self.assertEqual('oh', slp_license['jurisdiction'])
        self.assertEqual('Björk', slp_license['givenName'])

        self.assertEqual('B0608337260', aud_license['licenseNumber'])
        self.assertEqual('2020-06-06', aud_license['dateOfIssuance'])
        self.assertEqual('oh', aud_license['jurisdiction'])
        self.assertEqual('Audrey', aud_license['givenName'])

        # Verify that the provider data was copied from the audiologist license (newer issuance date)
        # by checking the givenName
        self.assertEqual('oh', provider_data['licenseJurisdiction'])
        self.assertEqual('Audrey', provider_data['givenName'])
        self.assertEqual('Guðmundsdóttir', provider_data['familyName'])

    def test_multiple_license_types_with_home_jurisdiction(self):
        """
        Test that multiple license types with a home jurisdiction selection are handled correctly.

        This test:
        1. Ingests a first active license with licenseType: speech-language pathologist in 'oh'
        2. Sets a home jurisdiction selection for 'oh'
        3. For the same provider, ingests a second active license with licenseType: audiologist in 'ky'
           with a newer dateOfIssuance
        4. Verifies that both licenses are present but the provider data still comes from the 'oh' license
           because of the home jurisdiction selection, even though the 'ky' license is newer
        """
        from cc_common.data_model.schema.home_jurisdiction.record import ProviderHomeJurisdictionSelectionRecordSchema
        from handlers.ingest import ingest_license_message

        # First, ingest a speech-language pathologist license in 'oh'
        provider_id = self._with_ingested_license()

        # Get the provider data after the first license ingest
        provider_data_after_first_license = self._get_provider_via_api(provider_id)

        # Verify the first license was ingested correctly
        self.assertEqual(1, len(provider_data_after_first_license['licenses']))
        self.assertEqual('speech-language pathologist', provider_data_after_first_license['licenses'][0]['licenseType'])
        self.assertEqual('oh', provider_data_after_first_license['licenseJurisdiction'])
        self.assertEqual('Björk', provider_data_after_first_license['givenName'])

        # Set a home jurisdiction selection for the provider to 'oh'
        home_jurisdiction_selection = {
            'type': 'homeJurisdictionSelection',
            'compact': 'aslp',
            'providerId': provider_id,
            'jurisdiction': 'oh',
            'dateOfSelection': self.config.current_standard_datetime,
        }

        # Create the home jurisdiction selection record
        schema = ProviderHomeJurisdictionSelectionRecordSchema()
        serialized_record = schema.dump(home_jurisdiction_selection)
        self.config.provider_table.put_item(Item=serialized_record)

        # Now ingest a second license for the same provider but with a different license type
        # in a different jurisdiction (ky) and with a newer issuance date
        with open('../common/tests/resources/ingest/event-bridge-message.json') as f:
            message = json.load(f)

        # Update the message to be for an audiologist license in 'ky' with a newer issuance date
        # and a different givenName to track which license is used for provider data
        message['detail'].update(
            {
                'licenseType': 'audiologist',
                'jurisdiction': 'ky',  # Different jurisdiction from home selection (oh)
                'dateOfIssuance': '2020-06-06',  # Newer than the first license (2010-06-06)
                'licenseNumber': 'B0608337260',  # Different license number
                'givenName': 'Audrey',  # Different name to track which license is used
            }
        )

        # Ingest the second license
        event = {'Records': [{'messageId': '456', 'body': json.dumps(message)}]}
        resp = ingest_license_message(event, self.mock_context)
        self.assertEqual({'batchItemFailures': []}, resp)

        # Get the updated provider data
        provider_data = self._get_provider_via_api(provider_id)

        # Verify that both licenses are present
        self.assertEqual(2, len(provider_data['licenses']))

        # Find each license by jurisdiction
        oh_license = next((lic for lic in provider_data['licenses'] if lic['jurisdiction'] == 'oh'), None)
        ky_license = next((lic for lic in provider_data['licenses'] if lic['jurisdiction'] == 'ky'), None)

        # Verify both licenses exist
        self.assertIsNotNone(oh_license, 'Ohio license not found')
        self.assertIsNotNone(ky_license, 'Kentucky license not found')

        # Verify license details
        self.assertEqual('speech-language pathologist', oh_license['licenseType'])
        self.assertEqual('A0608337260', oh_license['licenseNumber'])
        self.assertEqual('2010-06-06', oh_license['dateOfIssuance'])
        self.assertEqual('Björk', oh_license['givenName'])

        self.assertEqual('audiologist', ky_license['licenseType'])
        self.assertEqual('B0608337260', ky_license['licenseNumber'])
        self.assertEqual('2020-06-06', ky_license['dateOfIssuance'])
        self.assertEqual('Audrey', ky_license['givenName'])

        # Verify that the provider data still comes from the Ohio license
        # because it matches the home jurisdiction selection, even though the Kentucky license
        # has a newer issuance date. We can verify this by checking the givenName.
        self.assertEqual('oh', provider_data['licenseJurisdiction'])
        self.assertEqual('Björk', provider_data['givenName'])
        self.assertEqual('Guðmundsdóttir', provider_data['familyName'])

        # Verify that the home jurisdiction selection is present in the provider data
        self.assertIn('homeJurisdictionSelection', provider_data)
        self.assertEqual('oh', provider_data['homeJurisdictionSelection']['jurisdiction'])

    def test_multiple_license_types_different_jurisdictions(self):
        """
        Test that multiple license types in different jurisdictions are handled correctly.

        This test:
        1. Ingests a first active license with licenseType: speech-language pathologist in 'oh'
        2. For the same provider, ingests a second active license with licenseType: audiologist in 'ky'
        3. Verifies that both licenses are present and the provider data is from the most recently issued license
        """
        from handlers.ingest import ingest_license_message

        # First, ingest a speech-language pathologist license in 'oh'
        provider_id = self._with_ingested_license()

        # Get the provider data after the first license ingest
        provider_data_after_first_license = self._get_provider_via_api(provider_id)

        # Verify the first license was ingested correctly
        self.assertEqual(1, len(provider_data_after_first_license['licenses']))
        self.assertEqual('speech-language pathologist', provider_data_after_first_license['licenses'][0]['licenseType'])
        self.assertEqual('oh', provider_data_after_first_license['licenseJurisdiction'])
        self.assertEqual('Björk', provider_data_after_first_license['givenName'])

        # Now ingest a second license for the same provider but with a different license type
        # in a different jurisdiction and a newer issuance date
        with open('../common/tests/resources/ingest/event-bridge-message.json') as f:
            message = json.load(f)

        # Update the message to be for an audiologist license in 'ky' with a newer issuance date
        # and a different givenName to track which license is used for provider data
        message['detail'].update(
            {
                'licenseType': 'audiologist',
                'jurisdiction': 'ky',
                'dateOfIssuance': '2020-06-06',  # Newer than the first license (2010-06-06)
                'licenseNumber': 'B0608337260',  # Different license number
                'givenName': 'Audrey',  # Different name to track which license is used
            }
        )

        # Ingest the second license
        event = {'Records': [{'messageId': '456', 'body': json.dumps(message)}]}
        resp = ingest_license_message(event, self.mock_context)
        self.assertEqual({'batchItemFailures': []}, resp)

        # Get the updated provider data
        provider_data = self._get_provider_via_api(provider_id)

        # Verify that both licenses are present
        self.assertEqual(2, len(provider_data['licenses']))

        # Find each license by jurisdiction and type
        oh_license = next((lic for lic in provider_data['licenses'] if lic['jurisdiction'] == 'oh'), None)
        ky_license = next((lic for lic in provider_data['licenses'] if lic['jurisdiction'] == 'ky'), None)

        # Verify both licenses exist
        self.assertIsNotNone(oh_license, 'Ohio license not found')
        self.assertIsNotNone(ky_license, 'Kentucky license not found')

        # Verify license details
        self.assertEqual('speech-language pathologist', oh_license['licenseType'])
        self.assertEqual('A0608337260', oh_license['licenseNumber'])
        self.assertEqual('2010-06-06', oh_license['dateOfIssuance'])
        self.assertEqual('Björk', oh_license['givenName'])

        self.assertEqual('audiologist', ky_license['licenseType'])
        self.assertEqual('B0608337260', ky_license['licenseNumber'])
        self.assertEqual('2020-06-06', ky_license['dateOfIssuance'])
        self.assertEqual('Audrey', ky_license['givenName'])

        # Verify that the provider data was copied from the audiologist license in 'ky'
        # because it has a newer issuance date. We can verify this by checking the givenName.
        self.assertEqual('ky', provider_data['licenseJurisdiction'])
        self.assertEqual('Audrey', provider_data['givenName'])
        self.assertEqual('Guðmundsdóttir', provider_data['familyName'])
