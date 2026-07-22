import json
from datetime import date, datetime
from unittest.mock import MagicMock, patch

from cc_common.data_model.update_tier_enum import UpdateTierEnum
from common_test.test_constants import DEFAULT_PROVIDER_ID
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
        expected_provider['currentHomeJurisdiction'] = 'unknown'
        # if the home jurisdiction is unknown, the user has not registered in the system, and
        # is ineligible to purchase privileges until they register in the system.
        expected_provider['compactEligibility'] = 'ineligible'

        # in these test cases, the provider user has not registered in the system, so these values will not be
        # present
        del expected_provider['compactConnectRegisteredEmailAddress']
        return expected_provider

    def _with_ingested_license(self, omit_email: bool = False, omit_date_of_renewal: bool = False) -> str:
        from handlers.ingest import ingest_license_message

        with open('../common/tests/resources/dynamo/provider-ssn.json') as f:
            ssn_record = json.load(f)

        self._ssn_table.put_item(Item=ssn_record)
        provider_id = ssn_record['providerId']

        with open('../common/tests/resources/ingest/event-bridge-message.json') as f:
            message = json.load(f)

        if omit_email:
            del message['detail']['emailAddress']
        if omit_date_of_renewal:
            del message['detail']['dateOfRenewal']

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
        test_provider = self.test_data_generator.put_default_provider_record_in_provider_table(is_registered=False)
        self.test_data_generator.put_default_license_record_in_provider_table()

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

        event = {'Records': [{'messageId': '123', 'body': json.dumps(message)}]}

        resp = ingest_license_message(event, self.mock_context)

        self.assertEqual({'batchItemFailures': []}, resp)

        provider_data = self._get_provider_via_api(test_provider.providerId)

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
        # Assert that an event was sent for the deactivation
        mock_event_writer.return_value.__enter__.return_value.put_event.assert_called_once()
        call_kwargs = mock_event_writer.return_value.__enter__.return_value.put_event.call_args.kwargs
        self.assertEqual(
            {
                'Entry': {
                    'Source': 'org.compactconnect.provider-data',
                    'DetailType': 'license.deactivation',
                    'Detail': json.dumps(
                        {
                            'compact': 'aslp',
                            'jurisdiction': 'oh',
                            'eventTime': '2024-11-08T23:59:59+00:00',
                            'providerId': provider_id,
                            'licenseType': 'speech-language pathologist',
                        }
                    ),
                    'EventBusName': 'license-data-events',
                }
            },
            call_kwargs,
        )

    @patch('handlers.ingest.EventBatchWriter', autospec=True)
    def test_expired_license_deactivation_does_not_send_event(self, mock_event_writer):
        """Test that license deactivation event is NOT sent when the license is expired."""
        from common_test.test_constants import (
            DEFAULT_COMPACT,
            DEFAULT_LICENSE_JURISDICTION,
            DEFAULT_LICENSE_TYPE,
            DEFAULT_PROVIDER_ID,
        )
        from handlers.ingest import ingest_license_message

        # Set up test data with an expired license that gets deactivated
        self.test_data_generator.put_default_provider_record_in_provider_table()

        # Create a license that is expired (dateOfExpiration before current date)
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'providerId': DEFAULT_PROVIDER_ID,
                'jurisdiction': DEFAULT_LICENSE_JURISDICTION,
                'licenseType': DEFAULT_LICENSE_TYPE,
                'dateOfExpiration': date.fromisoformat(
                    '2024-11-05'
                ),  # expired compared to mock test date of 2024-11-08
                'jurisdictionUploadedLicenseStatus': 'active',  # Currently active, will be deactivated
                'jurisdictionUploadedCompactEligibility': 'eligible',
            }
        )

        # Create the ingest message to deactivate the expired license
        with open('../common/tests/resources/ingest/event-bridge-message.json') as f:
            message = json.load(f)

        message['detail'].update(
            {
                'compact': DEFAULT_COMPACT,
                'jurisdiction': DEFAULT_LICENSE_JURISDICTION,
                'licenseType': DEFAULT_LICENSE_TYPE,
                'providerId': DEFAULT_PROVIDER_ID,
                'dateOfExpiration': '2024-11-05',  # expired compared to mock test date of 2024-11-08
                'licenseStatus': 'inactive',  # Being deactivated by jurisdiction
                'compactEligibility': 'ineligible',
            }
        )

        event = {'Records': [{'messageId': '123', 'body': json.dumps(message)}]}

        # Execute the ingest
        resp = ingest_license_message(event, self.mock_context)
        self.assertEqual({'batchItemFailures': []}, resp)

        # Verify that NO license deactivation event was sent because the license is expired
        mock_event_writer.return_value.__enter__.return_value.put_event.assert_not_called()

    def _when_test_existing_provider_renewal(self, message_detail: dict, omit_date_of_renewal: bool = False):
        from handlers.ingest import ingest_license_message

        provider_id = self._with_ingested_license(omit_date_of_renewal=omit_date_of_renewal)

        with open('../common/tests/resources/ingest/event-bridge-message.json') as f:
            message = json.load(f)

        message['detail'].update(message_detail)
        if omit_date_of_renewal:
            del message['detail']['dateOfRenewal']

        # What happens if their license is renewed in a subsequent upload?
        event = {'Records': [{'messageId': '123', 'body': json.dumps(message)}]}
        resp = ingest_license_message(event, self.mock_context)
        self.assertEqual({'batchItemFailures': []}, resp)

        with open('../common/tests/resources/api/provider-detail-response.json') as f:
            expected_provider = json.load(f)

        # The license status and provider should immediately reflect the new dates
        expected_provider['dateOfExpiration'] = '2030-03-03'
        expected_provider['licenses'][0]['dateOfExpiration'] = '2030-03-03'
        if omit_date_of_renewal:
            del expected_provider['licenses'][0]['dateOfRenewal']
        else:
            expected_provider['licenses'][0]['dateOfRenewal'] = '2025-03-03'

        provider_data = self._get_provider_via_api(provider_id)

        # Reset the expected data to match the canned response
        expected_provider = self._set_provider_data_to_empty_values(expected_provider)

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

    def test_existing_provider_renewal(self):
        self._when_test_existing_provider_renewal(
            message_detail={'dateOfRenewal': '2025-03-03', 'dateOfExpiration': '2030-03-03'}, omit_date_of_renewal=False
        )

    def test_existing_provider_renewal_without_date_of_renewal_field(self):
        self._when_test_existing_provider_renewal(
            message_detail={'dateOfExpiration': '2030-03-03'}, omit_date_of_renewal=True
        )

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

        # verify that no update record was created
        provider_user_records = self.config.data_client.get_provider_user_records(
            compact=provider_data['compact'], provider_id=provider_id, include_update_tier=UpdateTierEnum.TIER_THREE
        )
        self.assertEqual(0, len(provider_user_records._license_update_records))  # noqa SLF001

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

        for license_data in expected_provider['licenses']:
            # We uploaded a license with no email by just deleting emailAddress
            # This should show up in the license history
            del license_data['emailAddress']

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

        # verify that update record was created
        provider_user_records = self.config.data_client.get_provider_user_records(
            compact=provider_data['compact'], provider_id=provider_id, include_update_tier=UpdateTierEnum.TIER_THREE
        )
        self.assertEqual(1, len(provider_user_records._license_update_records))  # noqa SLF001
        self.assertEqual(['emailAddress'], provider_user_records._license_update_records[0].removedValues)  # noqa SLF001

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

        # Set the current home jurisdiction on the provider to simulate them registering in the system
        self.test_data_generator.put_default_provider_record_in_provider_table(
            value_overrides={'providerId': provider_id, 'currentHomeJurisdiction': 'oh'}, is_registered=True
        )

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
        self.assertEqual('oh', provider_data['currentHomeJurisdiction'])

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


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
class TestIngestSsnCorrection(TstFunction):
    """Function tests for the SSN-correction migration orchestration in ingest_license_message.

    The old (incorrect-SSN) provider uses the test-data-generator default provider id; the corrected SSN
    resolves to NEW_PROVIDER_ID.
    """

    OLD_PROVIDER_ID = DEFAULT_PROVIDER_ID
    NEW_PROVIDER_ID = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
    NEW_SSN_LAST_FOUR = '6789'
    OLD_REGISTERED_EMAIL = 'old-provider@example.com'
    # firstUploadDate tracks when a license was first uploaded; migration must carry it forward unchanged
    LICENSE_FIRST_UPLOAD_DATE = datetime.fromisoformat('2020-01-01T00:00:00+00:00')

    def setUp(self):
        super().setUp()
        # patch the email client method at class level: the handler module may hold a config instance from an
        # earlier test module import, so instance-level mocking would not be seen
        email_patcher = patch(
            'cc_common.email_service_client.EmailServiceClient.send_provider_ssn_correction_reregistration_email',
            MagicMock(return_value={'message': 'Email message sent'}),
        )
        self._mock_send_reregistration_email = email_patcher.start()
        self.addCleanup(email_patcher.stop)

    def build_resources(self):
        import os

        import boto3

        super().build_resources()
        self._provider_user_bucket = boto3.resource('s3').create_bucket(Bucket=os.environ['PROVIDER_USER_BUCKET_NAME'])

    def delete_resources(self):
        self._provider_user_bucket.objects.delete()
        self._provider_user_bucket.delete()
        super().delete_resources()

    def _put_old_provider_records(self, *, with_second_license: bool = False) -> list:
        """Store the old provider's records and return the stored data class instances."""
        stored_records = [
            self.test_data_generator.put_default_provider_record_in_provider_table(
                {'compactConnectRegisteredEmailAddress': self.OLD_REGISTERED_EMAIL}
            ),
            self.test_data_generator.put_default_license_record_in_provider_table(
                {'firstUploadDate': self.LICENSE_FIRST_UPLOAD_DATE}
            ),
            self.test_data_generator.put_default_privilege_record_in_provider_table(),
            self.test_data_generator.put_default_military_affiliation_in_provider_table(),
        ]
        if with_second_license:
            stored_records.append(
                self.test_data_generator.put_default_license_record_in_provider_table({'licenseType': 'audiologist'})
            )
        return stored_records

    def _create_old_cognito_user(self):
        self.config.cognito_client.admin_create_user(
            UserPoolId=self.config.provider_user_pool_id,
            Username=self.OLD_REGISTERED_EMAIL,
            UserAttributes=[{'Name': 'email', 'Value': self.OLD_REGISTERED_EMAIL}],
        )

    def _does_old_cognito_user_exist(self) -> bool:
        from botocore.exceptions import ClientError

        try:
            self.config.cognito_client.admin_get_user(
                UserPoolId=self.config.provider_user_pool_id,
                Username=self.OLD_REGISTERED_EMAIL,
            )
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'UserNotFoundException':
                return False
            raise

    def _run_ingest_with_previous_provider_id(self):
        from handlers.ingest import ingest_license_message

        with open('../common/tests/resources/ingest/event-bridge-message.json') as f:
            message = json.load(f)

        message['detail']['providerId'] = self.NEW_PROVIDER_ID
        message['detail']['previousProviderId'] = self.OLD_PROVIDER_ID
        message['detail']['ssnLastFour'] = self.NEW_SSN_LAST_FOUR

        event = {'Records': [{'messageId': '123', 'body': json.dumps(message)}]}
        return ingest_license_message(event, self.mock_context)

    def _get_provider_records(self, provider_id: str) -> list[dict]:
        from boto3.dynamodb.conditions import Key

        return self.config.provider_table.query(KeyConditionExpression=Key('pk').eq(f'aslp#PROVIDER#{provider_id}'))[
            'Items'
        ]

    def _get_api_response_snapshot_for_provider(self, provider_id: str) -> dict:
        """Load a provider's records and JSON-cast their api response object, matching the format of the
        expected snapshots built by generate_default_provider_detail_response.
        """
        from cc_common.utils import ResponseEncoder

        provider_user_records = self.config.data_client.get_provider_user_records(
            compact='aslp',
            provider_id=provider_id,
        )
        return json.loads(json.dumps(provider_user_records.generate_api_response_object(), cls=ResponseEncoder))

    def test_full_migration_moves_records_under_new_provider_id(self):
        old_provider_record_items = self._put_old_provider_records()
        self._create_old_cognito_user()

        # snapshot the old provider's full state before the migration runs
        expected_old_provider_snapshot = self.test_data_generator.generate_default_provider_detail_response(
            old_provider_record_items
        )
        self.assertEqual(
            expected_old_provider_snapshot,
            self._get_api_response_snapshot_for_provider(self.OLD_PROVIDER_ID),
        )

        resp = self._run_ingest_with_previous_provider_id()
        self.assertEqual({'batchItemFailures': []}, resp)

        # the migrated license (refreshed by the ingested upload, carrying the corrected ssnLastFour), its
        # privilege, and the person-level military affiliation record now live under the new provider id, with
        # a newly-created provider record. The new provider is not registered: the practitioner must register
        # again under the corrected account
        default_military_affiliation = self.test_data_generator.generate_default_military_affiliation()
        expected_new_provider_snapshot = self.test_data_generator.generate_default_provider_detail_response(
            [
                self.test_data_generator.generate_default_provider(
                    value_overrides={
                        'providerId': self.NEW_PROVIDER_ID,
                        'ssnLastFour': self.NEW_SSN_LAST_FOUR,
                    },
                    is_registered=False,
                ),
                self.test_data_generator.generate_default_license(
                    value_overrides={
                        'providerId': self.NEW_PROVIDER_ID,
                        'ssnLastFour': self.NEW_SSN_LAST_FOUR,
                        'firstUploadDate': self.LICENSE_FIRST_UPLOAD_DATE,
                    }
                ),
                self.test_data_generator.generate_default_privilege(
                    value_overrides={'providerId': self.NEW_PROVIDER_ID}
                ),
                self.test_data_generator.generate_default_military_affiliation(
                    value_overrides={
                        'providerId': self.NEW_PROVIDER_ID,
                        # the migration re-points document keys at the new provider id's keyspace
                        'documentKeys': [
                            document_key.replace(self.OLD_PROVIDER_ID, self.NEW_PROVIDER_ID)
                            for document_key in default_military_affiliation.documentKeys
                        ],
                    }
                ),
            ]
        )
        self.assertEqual(
            expected_new_provider_snapshot,
            self._get_api_response_snapshot_for_provider(self.NEW_PROVIDER_ID),
        )

    def test_full_migration_deletes_cognito_user(self):
        self._put_old_provider_records()
        self._create_old_cognito_user()

        resp = self._run_ingest_with_previous_provider_id()
        self.assertEqual({'batchItemFailures': []}, resp)

        self.assertFalse(self._does_old_cognito_user_exist())

    def test_full_migration_sends_reregistration_email(self):
        self._put_old_provider_records()
        self._create_old_cognito_user()

        resp = self._run_ingest_with_previous_provider_id()
        self.assertEqual({'batchItemFailures': []}, resp)

        self._mock_send_reregistration_email.assert_called_once_with(
            compact='aslp',
            provider_email=self.OLD_REGISTERED_EMAIL,
        )

    def test_partial_migration_keeps_cognito_user_and_sends_no_email(self):
        self._put_old_provider_records(with_second_license=True)
        self._create_old_cognito_user()

        resp = self._run_ingest_with_previous_provider_id()
        self.assertEqual({'batchItemFailures': []}, resp)

        # the old provider still exists with its remaining license and its person-level records
        old_records = self._get_provider_records(self.OLD_PROVIDER_ID)
        old_record_types = {record['type'] for record in old_records}
        self.assertIn('provider', old_record_types)
        self.assertIn('license', old_record_types)
        self.assertIn('militaryAffiliation', old_record_types)

        # person-level records are not copied to the new provider
        new_record_types = {record['type'] for record in self._get_provider_records(self.NEW_PROVIDER_ID)}
        self.assertNotIn('militaryAffiliation', new_record_types)

        # the old Cognito user remains and no re-registration email was sent
        self.assertTrue(self._does_old_cognito_user_exist())
        self._mock_send_reregistration_email.assert_not_called()

    def test_no_op_migration_still_ingests_license_normally(self):
        # the previousSSN resolved to a provider id with no records at all
        resp = self._run_ingest_with_previous_provider_id()
        self.assertEqual({'batchItemFailures': []}, resp)

        new_records = self._get_provider_records(self.NEW_PROVIDER_ID)
        new_record_types = {record['type'] for record in new_records}
        self.assertEqual({'license', 'provider'}, new_record_types)

        # previousProviderId is transient migration routing data and must never be persisted
        for record in new_records:
            self.assertNotIn('previousProviderId', record)

        self._mock_send_reregistration_email.assert_not_called()

    def test_full_migration_with_unregistered_old_provider_sends_no_email(self):
        # the old provider never registered: no Cognito user, no registered email on the provider record
        self.test_data_generator.put_default_provider_record_in_provider_table(is_registered=False)
        self.test_data_generator.put_default_license_record_in_provider_table()

        resp = self._run_ingest_with_previous_provider_id()
        self.assertEqual({'batchItemFailures': []}, resp)

        self.assertEqual([], self._get_provider_records(self.OLD_PROVIDER_ID))
        self._mock_send_reregistration_email.assert_not_called()

    def _s3_object_body(self, key: str) -> bytes | None:
        """Return the body of an object in the provider user bucket, or None if it does not exist."""
        from botocore.exceptions import ClientError

        try:
            return self._provider_user_bucket.Object(key).get()['Body'].read()
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return None
            raise

    def test_full_migration_moves_military_documents_to_new_provider_keyspace(self):
        # the old provider has two military affiliation records, each with a document stored under the old
        # provider id's keyspace in the provider user bucket
        self.test_data_generator.put_default_provider_record_in_provider_table(
            {'compactConnectRegisteredEmailAddress': self.OLD_REGISTERED_EMAIL}
        )
        self.test_data_generator.put_default_license_record_in_provider_table()

        old_documents = {
            f'compact/aslp/provider/{self.OLD_PROVIDER_ID}/document-type/military-affiliations'
            f'/2024-07-08T23:59:59+00:00/1234#military-waiver.pdf': b'waiver-document-content',
            f'compact/aslp/provider/{self.OLD_PROVIDER_ID}/document-type/military-affiliations'
            f'/2024-08-08T23:59:59+00:00/5678#military-orders.pdf': b'orders-document-content',
        }
        for date_of_upload, (document_key, document_body) in zip(
            ['2024-07-08T23:59:59+00:00', '2024-08-08T23:59:59+00:00'], old_documents.items(), strict=True
        ):
            self.test_data_generator.put_default_military_affiliation_in_provider_table(
                {
                    'dateOfUpload': datetime.fromisoformat(date_of_upload),
                    'documentKeys': [document_key],
                }
            )
            self._provider_user_bucket.put_object(Key=document_key, Body=document_body)

        resp = self._run_ingest_with_previous_provider_id()
        self.assertEqual({'batchItemFailures': []}, resp)

        # the old partition is gone; both military affiliation records now live under the new provider id,
        # with their document keys re-pointed at the new provider's keyspace
        self.assertEqual([], self._get_provider_records(self.OLD_PROVIDER_ID))
        new_military_records = [
            record
            for record in self._get_provider_records(self.NEW_PROVIDER_ID)
            if record['type'] == 'militaryAffiliation'
        ]
        self.assertEqual(2, len(new_military_records))
        for record in new_military_records:
            self.assertEqual(self.NEW_PROVIDER_ID, record['providerId'])
        self.assertEqual(
            sorted(key.replace(self.OLD_PROVIDER_ID, self.NEW_PROVIDER_ID) for key in old_documents),
            sorted(key for record in new_military_records for key in record['documentKeys']),
        )

        # the documents were moved in S3: old objects deleted, new objects present with the same content
        for old_key, document_body in old_documents.items():
            self.assertIsNone(self._s3_object_body(old_key))
            new_key = old_key.replace(self.OLD_PROVIDER_ID, self.NEW_PROVIDER_ID)
            self.assertEqual(document_body, self._s3_object_body(new_key))

    def test_full_migration_moves_all_objects_under_old_provider_keyspace(self):
        """The S3 move must be driven by listing the old provider id's keyspace directly, not by walking
        DynamoDB records for known document types. This way any file under a provider's keyspace is carried
        over on a full migration, including document types the migration logic doesn't know about.
        """
        self.test_data_generator.put_default_provider_record_in_provider_table(
            {'compactConnectRegisteredEmailAddress': self.OLD_REGISTERED_EMAIL}
        )
        self.test_data_generator.put_default_license_record_in_provider_table()

        # an object under the old provider's keyspace with no corresponding DynamoDB record referencing it
        # (e.g. a future/unsupported document type)
        untracked_key = f'compact/aslp/provider/{self.OLD_PROVIDER_ID}/document-type/some-future-type/file.pdf'
        self._provider_user_bucket.put_object(Key=untracked_key, Body=b'untracked-document-content')

        resp = self._run_ingest_with_previous_provider_id()
        self.assertEqual({'batchItemFailures': []}, resp)

        # only the provider id segment of the keyspace changes; everything after it is preserved verbatim
        new_key = f'compact/aslp/provider/{self.NEW_PROVIDER_ID}/document-type/some-future-type/file.pdf'
        self.assertIsNone(self._s3_object_body(untracked_key))
        self.assertEqual(b'untracked-document-content', self._s3_object_body(new_key))
