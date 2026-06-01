import json
from datetime import date, datetime
from unittest.mock import MagicMock, patch

from boto3.dynamodb.conditions import Key
from moto import mock_aws

from .. import TstFunction


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
class TestIngest(TstFunction):
    @staticmethod
    def _set_provider_data_to_empty_values(expected_provider: dict) -> dict:
        # Ingest tests upload a single-state OH license only; the canned fixture also
        # includes a multi-state license used by _load_provider_data() tests.
        expected_provider['privileges'] = []
        expected_provider['licenses'] = [
            license_record
            for license_record in expected_provider['licenses']
            if license_record.get('licenseScope') == 'single-state'
        ]

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

        event['pathParameters'] = {'compact': 'socw', 'providerId': provider_id}
        event['requestContext']['authorizer']['claims']['scope'] = (
            'openid email stuff socw/readGeneral socw/readPrivate'
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

        # So get_provider returns one privilege (ne) to match expected fixture
        self.set_live_compact_jurisdictions_for_test({'socw': ['ne']})

        # The test resource provider has a license in oh
        self._load_provider_data()
        with open('../common/tests/resources/dynamo/provider-ssn.json') as f:
            provider_id = json.load(f)['providerId']

        with open('../common/tests/resources/ingest/event-bridge-message.json') as f:
            message = json.load(f)
        # Imagine that this provider used to be licensed in ky.
        # What happens if ky uploads that inactive license?
        message['detail']['dateOfIssuance'] = '2006-01-01'
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

        # The original provider data is preferred over the posted license data in our test case
        self.assertEqual(expected_provider, provider_data)

        # OH single-state and multi-state licenses plus the ingested KY license
        self.assertEqual(3, len(licenses))

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

        expected_provider = self._set_provider_data_to_empty_values(expected_provider)

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

        provider_data = self._get_provider_via_api(provider_id)

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
                            'compact': 'socw',
                            'jurisdiction': 'oh',
                            'eventTime': '2024-11-08T23:59:59+00:00',
                            'providerId': provider_id,
                            'licenseType': 'licensed clinical social worker',
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

        expected_provider = self._set_provider_data_to_empty_values(expected_provider)

        # The license status and provider should immediately reflect the new dates
        expected_provider['dateOfExpiration'] = '2030-03-03'
        expected_provider['licenses'][0]['dateOfExpiration'] = '2030-03-03'
        if omit_date_of_renewal:
            del expected_provider['licenses'][0]['dateOfRenewal']
        else:
            expected_provider['licenses'][0]['dateOfRenewal'] = '2025-03-03'

        provider_data = self._get_provider_via_api(provider_id)

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

        expected_provider = self._set_provider_data_to_empty_values(expected_provider)

        # The license status and provider should immediately reflect the new name
        expected_provider['familyName'] = 'VonSmitherton'
        expected_provider['licenses'][0]['familyName'] = 'VonSmitherton'

        provider_data = self._get_provider_via_api(provider_id)

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
        provider = self._ssn_table.get_item(Key={'pk': f'socw#SSN#{test_ssn}', 'sk': f'socw#SSN#{test_ssn}'})
        self.assertNotIn('Item', provider)

        with open('../common/tests/resources/ingest/preprocessor-sqs-message.json') as f:
            message = json.load(f)
            # set fixed ssn here to ensure we are checking the expected value
            message['ssn'] = test_ssn

        event = {'Records': [{'messageId': '123', 'body': json.dumps(message)}]}

        resp = preprocess_license_ingest(event, self.mock_context)
        self.assertEqual({'batchItemFailures': []}, resp)

        # Find the provider's id from their ssn
        provider = self._ssn_table.get_item(Key={'pk': f'socw#SSN#{test_ssn}', 'sk': f'socw#SSN#{test_ssn}'})['Item']
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

    def test_multiple_license_types_same_jurisdiction(self):
        """
        Test that multiple license types in the same jurisdiction are handled correctly.

        This test:
        1. Ingests a first active license with licenseType: licensed clinical social worker
        2. For the same provider, ingests a second active license with licenseType: licensed master social worker and a
        newer dateOfIssuance
        3. Verifies that both licenses are present and that the provider data was copied from the
        licensed master social worker license
        """
        from handlers.ingest import ingest_license_message

        # First, ingest a licensed clinical social worker license
        provider_id = self._with_ingested_license()

        # Get the provider data after the first license ingest
        provider_data_after_first_license = self._get_provider_via_api(provider_id)

        # Verify the first license was ingested correctly
        self.assertEqual(1, len(provider_data_after_first_license['licenses']))
        self.assertEqual(
            'licensed clinical social worker', provider_data_after_first_license['licenses'][0]['licenseType']
        )
        self.assertEqual('oh', provider_data_after_first_license['licenseJurisdiction'])
        self.assertEqual('Björk', provider_data_after_first_license['givenName'])

        # Now ingest a second license for the same provider but with a different license type
        # and a newer issuance date
        with open('../common/tests/resources/ingest/event-bridge-message.json') as f:
            message = json.load(f)

        # Update the message to be for an licensed master social worker license with a newer issuance date
        # and a different givenName to track which license is used for provider data
        message['detail'].update(
            {
                'licenseType': 'licensed master social worker',
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
        lcsw_license = next(
            (lic for lic in provider_data['licenses'] if lic['licenseType'] == 'licensed clinical social worker'), None
        )
        lmsw_license = next(
            (lic for lic in provider_data['licenses'] if lic['licenseType'] == 'licensed master social worker'), None
        )

        # Verify both licenses exist
        self.assertIsNotNone(lcsw_license, 'licensed clinical social worker license not found')
        self.assertIsNotNone(lmsw_license, 'licensed master social worker license not found')

        # Verify license details
        self.assertEqual('A0608337260', lcsw_license['licenseNumber'])
        self.assertEqual('2010-06-06', lcsw_license['dateOfIssuance'])
        self.assertEqual('oh', lcsw_license['jurisdiction'])
        self.assertEqual('Björk', lcsw_license['givenName'])

        self.assertEqual('B0608337260', lmsw_license['licenseNumber'])
        self.assertEqual('2020-06-06', lmsw_license['dateOfIssuance'])
        self.assertEqual('oh', lmsw_license['jurisdiction'])
        self.assertEqual('Audrey', lmsw_license['givenName'])

        # Verify that the provider data was copied from the licensed master social worker license (newer issuance date)
        # by checking the givenName
        self.assertEqual('oh', provider_data['licenseJurisdiction'])
        self.assertEqual('Audrey', provider_data['givenName'])
        self.assertEqual('Guðmundsdóttir', provider_data['familyName'])

    def test_licenses_with_different_jurisdictions_updates_provider_data_when_single_and_multi_state_licenses_uploaded(
        self,
    ):
        """
        Test that multiple license types in different jurisdictions are handled correctly.

        This test:
        1. Ingests a first active single-state license with licenseType: licensed clinical social worker in 'oh'
        2. For the same provider, ingests a second active single-state licensed master social worker license  in 'ky'
        3. Verifies that both licenses are present and the provider data is NOT updated to the most recently issued
        license.
        4. ingest an active multi-state licensed master social worker license  in 'ky'
        5. Verifies that all licenses are present and the provider data is updated to the data from the new jurisdiction
         since both single and multi state licenses have been uploaded.
        """
        from handlers.ingest import ingest_license_message

        # First, ingest a licensed clinical social worker license in 'oh'
        provider_id = self._with_ingested_license()

        # Get the provider data after the first license ingest
        provider_data_after_first_license = self._get_provider_via_api(provider_id)

        # Verify the first license was ingested correctly
        self.assertEqual(1, len(provider_data_after_first_license['licenses']))
        self.assertEqual(
            'licensed clinical social worker', provider_data_after_first_license['licenses'][0]['licenseType']
        )
        self.assertEqual('oh', provider_data_after_first_license['licenseJurisdiction'])
        self.assertEqual('Björk', provider_data_after_first_license['givenName'])

        # Now ingest a second license for the same provider but with a different license type
        # in a different jurisdiction and a newer issuance date
        with open('../common/tests/resources/ingest/event-bridge-message.json') as f:
            message = json.load(f)

        # Update the message to be for an licensed master social worker license in 'ky' with a newer issuance date
        # and a different givenName to track which license is used for provider data
        message['detail'].update(
            {
                'licenseType': 'licensed master social worker',
                'licenseScope': 'single-state',
                'jurisdiction': 'ky',
                'dateOfIssuance': '2020-06-06',
                'licenseNumber': 'B0608337260',
                'givenName': 'Audrey',
            }
        )

        # Ingest the second license
        event = {'Records': [{'messageId': '456', 'body': json.dumps(message)}]}
        resp = ingest_license_message(event, self.mock_context)
        self.assertEqual({'batchItemFailures': []}, resp)

        # Get the updated provider data
        provider_data_after_ky_single_state = self._get_provider_via_api(provider_id)

        # Verify that both licenses are present
        self.assertEqual(2, len(provider_data_after_ky_single_state['licenses']))

        # Find each license by jurisdiction and type
        oh_license = next(
            (lic for lic in provider_data_after_ky_single_state['licenses'] if lic['jurisdiction'] == 'oh'), None
        )
        ky_license = next(
            (lic for lic in provider_data_after_ky_single_state['licenses'] if lic['jurisdiction'] == 'ky'), None
        )

        # Verify both licenses exist
        self.assertIsNotNone(oh_license, 'Ohio license not found')
        self.assertIsNotNone(ky_license, 'Kentucky license not found')

        # Verify license details
        self.assertEqual('licensed clinical social worker', oh_license['licenseType'])
        self.assertEqual('A0608337260', oh_license['licenseNumber'])
        self.assertEqual('2010-06-06', oh_license['dateOfIssuance'])
        self.assertEqual('Björk', oh_license['givenName'])

        self.assertEqual('licensed master social worker', ky_license['licenseType'])
        self.assertEqual('single-state', ky_license['licenseScope'])
        self.assertEqual('B0608337260', ky_license['licenseNumber'])
        self.assertEqual('2020-06-06', ky_license['dateOfIssuance'])
        self.assertEqual('Audrey', ky_license['givenName'])

        # verify that the provider data is not updated to the Kentucky license
        self.assertEqual('oh', provider_data_after_ky_single_state['licenseJurisdiction'])
        self.assertEqual('Björk', provider_data_after_ky_single_state['givenName'])

        with open('../common/tests/resources/ingest/event-bridge-message.json') as f:
            message = json.load(f)

        message['detail'].update(
            {
                'licenseType': 'licensed master social worker',
                'licenseScope': 'multi-state',
                'jurisdiction': 'ky',
                'dateOfIssuance': '2021-06-06',
                'licenseNumber': 'C0608337260',
                'givenName': 'Audrey',
            }
        )

        event = {'Records': [{'messageId': '789', 'body': json.dumps(message)}]}
        resp = ingest_license_message(event, self.mock_context)
        self.assertEqual({'batchItemFailures': []}, resp)

        provider_data = self._get_provider_via_api(provider_id)

        self.assertEqual(3, len(provider_data['licenses']))
        ky_multi_state = next(
            (
                lic
                for lic in provider_data['licenses']
                if lic['jurisdiction'] == 'ky' and lic['licenseScope'] == 'multi-state'
            ),
            None,
        )

        self.assertIsNotNone(ky_multi_state, 'Kentucky multi-state license not found')
        self.assertEqual('licensed master social worker', ky_multi_state['licenseType'])
        self.assertEqual('C0608337260', ky_multi_state['licenseNumber'])
        self.assertEqual('2021-06-06', ky_multi_state['dateOfIssuance'])
        self.assertEqual('Audrey', ky_multi_state['givenName'])

        # Verify that the provider data was updated from the multi-state licensed master social worker
        # license in 'ky' because it has a newer issuance date and there is a paired single-state license.
        # We verify this by checking the givenName and jurisdiction.
        self.assertEqual('ky', provider_data['licenseJurisdiction'])
        self.assertEqual('Audrey', provider_data['givenName'])
        self.assertEqual('Guðmundsdóttir', provider_data['familyName'])

    def test_home_jurisdiction_change_triggered_by_multi_state_licenses_when_single_and_multi_state_licenses_uploaded(
        self,
    ):
        """
        Test that home jurisdiction changes are only triggered by multi-state license upload after single-state
        license has been uploaded.

        This test:
        1. Ingests a first active single-state license with licenseType: licensed clinical social worker in 'oh'
        2. For the same provider, ingests a second active multi-state licensed master social worker license  in 'ky'
        3. Verifies that both licenses are present and the provider data is NOT updated to the most recently issued
        license.
        4. Ingest an active single-state licensed master social worker license  in 'ky'
        5. Verifies that all licenses are present and the provider data is still not updated.
        6. Ingest multi-state license from ky again.
        7. Verifies that provider data updated to the data from the new jurisdiction
         since both single and multi state licenses have been uploaded.
        """
        from handlers.ingest import ingest_license_message

        # First, ingest a licensed clinical social worker license in 'oh'
        provider_id = self._with_ingested_license()

        # Get the provider data after the first license ingest
        provider_data_after_first_license = self._get_provider_via_api(provider_id)

        # Verify the first license was ingested correctly
        self.assertEqual(1, len(provider_data_after_first_license['licenses']))
        self.assertEqual(
            'licensed clinical social worker', provider_data_after_first_license['licenses'][0]['licenseType']
        )
        self.assertEqual('oh', provider_data_after_first_license['licenseJurisdiction'])
        self.assertEqual('Björk', provider_data_after_first_license['givenName'])

        # Now ingest a second license for the same provider but with a different license type
        # in a different jurisdiction and a newer issuance date
        with open('../common/tests/resources/ingest/event-bridge-message.json') as f:
            message = json.load(f)

        # Update the message to be for an licensed master social worker multi-state license in 'ky'
        # with a newer issuance date and a different givenName to track which license is used for provider data
        message['detail'].update(
            {
                'licenseType': 'licensed master social worker',
                'licenseScope': 'multi-state',
                'jurisdiction': 'ky',
                'dateOfIssuance': '2020-06-06',
                'licenseNumber': 'B0608337260',
                'givenName': 'Audrey',
            }
        )

        # Ingest the second license
        event = {'Records': [{'messageId': '456', 'body': json.dumps(message)}]}
        resp = ingest_license_message(event, self.mock_context)
        self.assertEqual({'batchItemFailures': []}, resp)

        # Get the updated provider data
        provider_data_after_ky_single_state = self._get_provider_via_api(provider_id)

        # Verify that both licenses are present
        self.assertEqual(2, len(provider_data_after_ky_single_state['licenses']))

        # Find each license by jurisdiction and type
        oh_license = next(
            (lic for lic in provider_data_after_ky_single_state['licenses'] if lic['jurisdiction'] == 'oh'), None
        )
        ky_license = next(
            (lic for lic in provider_data_after_ky_single_state['licenses'] if lic['jurisdiction'] == 'ky'), None
        )

        # Verify both licenses exist
        self.assertIsNotNone(oh_license, 'Ohio license not found')
        self.assertIsNotNone(ky_license, 'Kentucky license not found')

        # Verify license details
        self.assertEqual('licensed clinical social worker', oh_license['licenseType'])
        self.assertEqual('A0608337260', oh_license['licenseNumber'])
        self.assertEqual('2010-06-06', oh_license['dateOfIssuance'])
        self.assertEqual('Björk', oh_license['givenName'])

        self.assertEqual('licensed master social worker', ky_license['licenseType'])
        self.assertEqual('multi-state', ky_license['licenseScope'])
        self.assertEqual('B0608337260', ky_license['licenseNumber'])
        self.assertEqual('2020-06-06', ky_license['dateOfIssuance'])
        self.assertEqual('Audrey', ky_license['givenName'])

        # verify that the provider data is not updated to the Kentucky license
        self.assertEqual('oh', provider_data_after_ky_single_state['licenseJurisdiction'])
        self.assertEqual('Björk', provider_data_after_ky_single_state['givenName'])

        with open('../common/tests/resources/ingest/event-bridge-message.json') as f:
            message = json.load(f)

        message['detail'].update(
            {
                'licenseType': 'licensed master social worker',
                'licenseScope': 'single-state',
                'jurisdiction': 'ky',
                'dateOfIssuance': '2021-06-06',
                'licenseNumber': 'C0608337260',
                'givenName': 'Audrey',
            }
        )

        event = {'Records': [{'messageId': '789', 'body': json.dumps(message)}]}
        resp = ingest_license_message(event, self.mock_context)
        self.assertEqual({'batchItemFailures': []}, resp)

        provider_data = self._get_provider_via_api(provider_id)

        self.assertEqual(3, len(provider_data['licenses']))
        ky_single_state = next(
            (
                lic
                for lic in provider_data['licenses']
                if lic['jurisdiction'] == 'ky' and lic['licenseScope'] == 'single-state'
            ),
            None,
        )

        self.assertIsNotNone(ky_single_state, 'Kentucky single-state license not found')
        self.assertEqual('licensed master social worker', ky_single_state['licenseType'])
        self.assertEqual('C0608337260', ky_single_state['licenseNumber'])
        self.assertEqual('2021-06-06', ky_single_state['dateOfIssuance'])
        self.assertEqual('Audrey', ky_single_state['givenName'])

        # verify that the provider data is not updated to the Kentucky license yet
        # (only multi-state uploads trigger change)
        self.assertEqual('oh', provider_data_after_ky_single_state['licenseJurisdiction'])
        self.assertEqual('Björk', provider_data_after_ky_single_state['givenName'])

        # re-upload multi-state license in ky, which should trigger the home-state change
        with open('../common/tests/resources/ingest/event-bridge-message.json') as f:
            message = json.load(f)

        message['detail'].update(
            {
                'licenseType': 'licensed master social worker',
                'licenseScope': 'multi-state',
                'jurisdiction': 'ky',
                'dateOfIssuance': '2020-06-06',
                'licenseNumber': 'B0608337260',
                'givenName': 'Audrey',
            }
        )

        event = {'Records': [{'messageId': '789', 'body': json.dumps(message)}]}
        resp = ingest_license_message(event, self.mock_context)
        self.assertEqual({'batchItemFailures': []}, resp)

        provider_data = self._get_provider_via_api(provider_id)

        self.assertEqual(3, len(provider_data['licenses']))

        # Verify that the provider data was updated from the multi-state licensed master social worker
        # license in 'ky' because it has a newer issuance date and there is a paired single-state license.
        # We verify this by checking the givenName and jurisdiction.
        self.assertEqual('ky', provider_data['licenseJurisdiction'])
        self.assertEqual('Audrey', provider_data['givenName'])
        self.assertEqual('Guðmundsdóttir', provider_data['familyName'])

    def test_same_license_types_different_jurisdictions_triggers_home_jurisdiction_change_event_bridge_notification(
        self,
    ):
        """
        Same license type (licensed clinical social worker) in two jurisdictions: a newer multi-state issuance from KY
        replaces OH as the best license and ingest emits ``provider.homeStateChange`` with former OH and new KY.
        A KY single-state license of the same type must exist before the KY multi-state upload so the pairing rule
        is satisfied.
        """
        import handlers.ingest as ingest_handler
        from handlers.ingest import ingest_license_message

        with open('../common/tests/resources/dynamo/provider-ssn.json') as f:
            ssn_record = json.load(f)

        self._ssn_table.put_item(Item=ssn_record)
        provider_id = ssn_record['providerId']

        with open('../common/tests/resources/ingest/event-bridge-message.json') as f:
            message = json.load(f)

        message['detail']['licenseScope'] = 'multi-state'
        event = {'Records': [{'messageId': '123', 'body': json.dumps(message)}]}
        resp = ingest_license_message(event, self.mock_context)
        self.assertEqual({'batchItemFailures': []}, resp)

        provider_data_after_first_license = self._get_provider_via_api(provider_id)

        # Verify the first license was ingested correctly
        self.assertEqual(1, len(provider_data_after_first_license['licenses']))
        self.assertEqual(
            'licensed clinical social worker', provider_data_after_first_license['licenses'][0]['licenseType']
        )
        self.assertEqual('multi-state', provider_data_after_first_license['licenses'][0]['licenseScope'])
        self.assertEqual('oh', provider_data_after_first_license['licenseJurisdiction'])
        self.assertEqual('Björk', provider_data_after_first_license['givenName'])

        with open('../common/tests/resources/ingest/event-bridge-message.json') as f:
            message = json.load(f)

        # Paired single-state in KY is required before a KY multi-state upload can trigger home jurisdiction change.
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'providerId': provider_id,
                'licenseType': 'licensed clinical social worker',
                'licenseScope': 'single-state',
                'jurisdiction': 'ky',
                'dateOfIssuance': date.fromisoformat('2019-06-06'),
            }
        )

        # Same license type as OH, but KY multi-state upload with a newer issuance date → new home jurisdiction
        message['detail'].update(
            {
                'licenseType': 'licensed clinical social worker',
                'licenseScope': 'multi-state',
                'jurisdiction': 'ky',
                'dateOfIssuance': '2020-06-06',
                'licenseNumber': 'B0608337260',
                'givenName': 'Audrey',
            }
        )

        mock_put_events = MagicMock(return_value={'FailedEntryCount': 0, 'Entries': [{'EventId': 'evt-1'}]})
        # Patch the EventBridge client bound on this lambda's config (setUp replaces the global singleton each test).
        with patch.object(ingest_handler.config.events_client, 'put_events', mock_put_events):
            event = {'Records': [{'messageId': '456', 'body': json.dumps(message)}]}
            resp = ingest_license_message(event, self.mock_context)
            self.assertEqual({'batchItemFailures': []}, resp)

        mock_put_events.assert_called_once()
        entries = mock_put_events.call_args.kwargs['Entries']
        self.assertEqual(1, len(entries))
        home_change_entry = entries[0]
        self.assertEqual(
            {
                'Detail': json.dumps(
                    {
                        'compact': 'socw',
                        'jurisdiction': 'ky',
                        'eventTime': '2024-11-08T23:59:59+00:00',
                        'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570',
                        'licenseType': 'licensed clinical social worker',
                        'formerHomeJurisdiction': 'oh',
                    }
                ),
                'DetailType': 'provider.homeStateChange',
                'EventBusName': 'license-data-events',
                'Source': 'org.compactconnect.provider-data',
            },
            home_change_entry,
        )

        provider_data = self._get_provider_via_api(provider_id)

        self.assertEqual(3, len(provider_data['licenses']))
        oh_license = next(
            (
                lic
                for lic in provider_data['licenses']
                if lic['jurisdiction'] == 'oh' and lic['licenseScope'] == 'multi-state'
            ),
            None,
        )
        ky_single_state = next(
            (
                lic
                for lic in provider_data['licenses']
                if lic['jurisdiction'] == 'ky' and lic['licenseScope'] == 'single-state'
            ),
            None,
        )
        ky_multi_state = next(
            (
                lic
                for lic in provider_data['licenses']
                if lic['jurisdiction'] == 'ky' and lic['licenseScope'] == 'multi-state'
            ),
            None,
        )

        self.assertIsNotNone(oh_license, 'Ohio multi-state license not found')
        self.assertIsNotNone(ky_single_state, 'Kentucky single-state license not found')
        self.assertIsNotNone(ky_multi_state, 'Kentucky multi-state license not found')

        # Verify license details
        self.assertEqual('licensed clinical social worker', oh_license['licenseType'])
        self.assertEqual('A0608337260', oh_license['licenseNumber'])
        self.assertEqual('2010-06-06', oh_license['dateOfIssuance'])
        self.assertEqual('Björk', oh_license['givenName'])

        self.assertEqual('licensed clinical social worker', ky_multi_state['licenseType'])
        self.assertEqual('B0608337260', ky_multi_state['licenseNumber'])
        self.assertEqual('2020-06-06', ky_multi_state['dateOfIssuance'])
        self.assertEqual('Audrey', ky_multi_state['givenName'])

        self.assertEqual('ky', provider_data['licenseJurisdiction'])
        self.assertEqual('Audrey', provider_data['givenName'])

    def test_multiple_license_types_different_jurisdictions_does_not_trigger_home_jurisdiction_change(
        self,
    ):
        """
        Practitioner has two license types in OH (no multi-state/single-state pairs). A KY licensed master social
        worker single-state upload is ingested without a paired KY multi-state license. Even though KY lmsw is newer
        than the OH lmsw of the same type, home jurisdiction change must not fire because the pairing rule is not met.
        """
        import handlers.ingest as ingest_handler
        from handlers.ingest import ingest_license_message

        provider_id = self._with_ingested_license()
        # add a new license type,
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'providerId': provider_id,
                'licenseType': 'licensed master social worker',
                'dateOfIssuance': date.fromisoformat('2024-05-06'),
                'jurisdiction': 'oh',
            }
        )
        # update the original to later date
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'providerId': provider_id,
                'licenseType': 'licensed clinical social worker',
                'jurisdiction': 'oh',
                'dateOfRenewal': date.fromisoformat('2026-06-06'),
            }
        )

        with open('../common/tests/resources/ingest/event-bridge-message.json') as f:
            message = json.load(f)

        # KY lmsw single-state only (default scope from event-bridge-message.json); no KY multi-state pair exists.
        message['detail'].update(
            {
                'licenseType': 'licensed master social worker',
                'licenseScope': 'single-state',
                'jurisdiction': 'ky',
                'dateOfIssuance': '2025-06-06',
                'licenseNumber': 'B0608337260',
                'givenName': 'Audrey',
            }
        )

        mock_put_events = MagicMock(return_value={'FailedEntryCount': 0, 'Entries': [{'EventId': 'evt-1'}]})
        # Patch the EventBridge client bound on this lambda's config (setUp replaces the global singleton each test).
        with patch.object(ingest_handler.config.events_client, 'put_events', mock_put_events):
            event = {'Records': [{'messageId': '456', 'body': json.dumps(message)}]}
            resp = ingest_license_message(event, self.mock_context)
            self.assertEqual({'batchItemFailures': []}, resp)

        mock_put_events.assert_not_called()

        # Verify provider record remains the same
        provider_data = self._get_provider_via_api(provider_id)
        self.assertEqual('oh', provider_data['licenseJurisdiction'])
        self.assertEqual('Björk', provider_data['givenName'])

    def test_multi_state_license_preferred_over_newer_single_state_for_provider_record(self):
        """
        When a practitioner has both single-state and multi-state licenses, the multi-state license is selected as
        the best license for populating the provider record even when a single-state license was renewed more recently.
        """
        from handlers.ingest import ingest_license_message

        with open('../common/tests/resources/dynamo/provider-ssn.json') as f:
            ssn_record = json.load(f)

        self._ssn_table.put_item(Item=ssn_record)
        provider_id = ssn_record['providerId']

        with open('../common/tests/resources/ingest/event-bridge-message.json') as f:
            message = json.load(f)

        message['detail'].update(
            {
                'licenseScope': 'single-state',
                'givenName': 'Audrey',
                'dateOfRenewal': '2026-06-06',
                'dateOfExpiration': '2030-04-04',
            }
        )

        event = {'Records': [{'messageId': '123', 'body': json.dumps(message)}]}
        resp = ingest_license_message(event, self.mock_context)
        self.assertEqual({'batchItemFailures': []}, resp)

        provider_data_after_single_state = self._get_provider_via_api(provider_id)
        self.assertEqual('Audrey', provider_data_after_single_state['givenName'])
        self.assertEqual(1, len(provider_data_after_single_state['licenses']))

        with open('../common/tests/resources/ingest/event-bridge-message.json') as f:
            message = json.load(f)

        message['detail'].update(
            {
                'licenseScope': 'multi-state',
                'licenseNumber': 'B0608337260',
                'givenName': 'Björk',
                'dateOfIssuance': '2010-06-06',
                'dateOfRenewal': '2020-04-04',
                'dateOfExpiration': '2025-04-04',
            }
        )

        event = {'Records': [{'messageId': '456', 'body': json.dumps(message)}]}
        resp = ingest_license_message(event, self.mock_context)
        self.assertEqual({'batchItemFailures': []}, resp)

        provider_data = self._get_provider_via_api(provider_id)
        self.assertEqual(2, len(provider_data['licenses']))
        self.assertEqual('Björk', provider_data['givenName'])
        self.assertEqual('oh', provider_data['licenseJurisdiction'])

        single_state_license = next(
            (lic for lic in provider_data['licenses'] if lic['licenseScope'] == 'single-state'), None
        )
        multi_state_license = next(
            (lic for lic in provider_data['licenses'] if lic['licenseScope'] == 'multi-state'), None
        )
        self.assertIsNotNone(single_state_license)
        self.assertIsNotNone(multi_state_license)
        self.assertEqual('Audrey', single_state_license['givenName'])
        self.assertEqual('Björk', multi_state_license['givenName'])

        provider_records = self._provider_table.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('pk').eq(f'socw#PROVIDER#{provider_id}'),
        )['Items']
        provider_record = next(record for record in provider_records if record['type'] == 'provider')
        self.assertEqual('Björk', provider_record['givenName'])
        self.assertEqual('oh', provider_record['licenseJurisdiction'])

    def test_multi_state_license_does_not_overwrite_existing_single_state_license(self):
        """
        Test that ingesting a multi-state license creates a distinct record when the provider already has a
        single-state license of the same license type in the same jurisdiction.

        A single-state and a multi-state license are uniquely different records (a multi-state license grants a
        practitioner privileges across the compact, while a single-state license does not). Ingesting the
        multi-state license must therefore NOT overwrite or update the existing single-state license - both must be
        persisted as separate records.
        """
        from handlers.ingest import ingest_license_message

        # First, ingest a single-state licensed clinical social worker license in 'oh'
        provider_id = self._with_ingested_license()

        provider_data_after_first_license = self._get_provider_via_api(provider_id)
        self.assertEqual(1, len(provider_data_after_first_license['licenses']))
        self.assertEqual('single-state', provider_data_after_first_license['licenses'][0]['licenseScope'])

        # Now ingest a multi-state license for the same provider, same license type and jurisdiction
        with open('../common/tests/resources/ingest/event-bridge-message.json') as f:
            message = json.load(f)

        message['detail'].update(
            {
                'licenseScope': 'multi-state',
                'licenseNumber': 'B0608337260',  # Different license number than the single-state license
            }
        )

        event = {'Records': [{'messageId': '456', 'body': json.dumps(message)}]}
        resp = ingest_license_message(event, self.mock_context)
        self.assertEqual({'batchItemFailures': []}, resp)

        # Both the single-state and multi-state licenses should be present as distinct records
        provider_data = self._get_provider_via_api(provider_id)
        self.assertEqual(2, len(provider_data['licenses']))

        single_state_license = next(
            (lic for lic in provider_data['licenses'] if lic['licenseScope'] == 'single-state'), None
        )
        multi_state_license = next(
            (lic for lic in provider_data['licenses'] if lic['licenseScope'] == 'multi-state'), None
        )
        self.assertIsNotNone(single_state_license, 'single-state license not found')
        self.assertIsNotNone(multi_state_license, 'multi-state license not found')

        # Both licenses share the same type and jurisdiction, but are distinguished by scope and license number
        for license_record in (single_state_license, multi_state_license):
            self.assertEqual('licensed clinical social worker', license_record['licenseType'])
            self.assertEqual('oh', license_record['jurisdiction'])

        # The original single-state license must be untouched by the multi-state ingest
        self.assertEqual('A0608337260', single_state_license['licenseNumber'])
        self.assertEqual('B0608337260', multi_state_license['licenseNumber'])

        # Ingesting the multi-state license creates a new license record rather than updating the existing
        # single-state license, so exactly two license records exist and no licenseUpdate record was written.
        provider_records = self._provider_table.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('pk').eq(f'socw#PROVIDER#{provider_id}'),
        )['Items']
        license_records = [record for record in provider_records if record['type'] == 'license']
        license_update_records = [record for record in provider_records if record['type'] == 'licenseUpdate']
        self.assertEqual(2, len(license_records))
        self.assertEqual(0, len(license_update_records))


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
class TestMultiStateSingleStateValidationError(TstFunction):
    """license.validation-error when multi-state upload is eligible but paired single-state is ineligible."""

    def _ingest_license(self, detail_overrides: dict | None = None, *, message_id: str = '123') -> dict:
        from handlers.ingest import ingest_license_message

        with open('../common/tests/resources/ingest/event-bridge-message.json') as f:
            message = json.load(f)
        if detail_overrides:
            message['detail'].update(detail_overrides)
        event = {'Records': [{'messageId': message_id, 'body': json.dumps(message)}]}
        resp = ingest_license_message(event, self.mock_context)
        self.assertEqual({'batchItemFailures': []}, resp)
        return message

    def _setup_provider_ssn(self) -> str:
        with open('../common/tests/resources/dynamo/provider-ssn.json') as f:
            ssn_record = json.load(f)
        self._ssn_table.put_item(Item=ssn_record)
        return ssn_record['providerId']

    @patch('handlers.ingest.EventBatchWriter', autospec=True)
    def test_eligible_multi_state_with_ineligible_single_state_emits_validation_error(self, mock_event_writer):
        from handlers.ingest import ingest_license_message

        self._setup_provider_ssn()

        self._ingest_license(
            {
                'licenseScope': 'single-state',
                'licenseStatus': 'inactive',
                'compactEligibility': 'ineligible',
            },
            message_id='100',
        )

        with open('../common/tests/resources/ingest/event-bridge-message.json') as f:
            message = json.load(f)
        message['detail'].update(
            {
                'licenseScope': 'multi-state',
                'licenseNumber': 'B0608337260',
                'licenseStatus': 'active',
                'compactEligibility': 'eligible',
            }
        )
        event = {'Records': [{'messageId': '101', 'body': json.dumps(message)}]}
        resp = ingest_license_message(event, self.mock_context)
        self.assertEqual({'batchItemFailures': []}, resp)

        mock_event_writer.return_value.__enter__.return_value.put_event.assert_called_once()
        entry = mock_event_writer.return_value.__enter__.return_value.put_event.call_args.kwargs['Entry']
        self.assertEqual('license.validation-error', entry['DetailType'])
        self.assertEqual('org.compactconnect.provider-data', entry['Source'])
        self.assertEqual('license-data-events', entry['EventBusName'])

        detail = json.loads(entry['Detail'])
        self.assertEqual('socw', detail['compact'])
        self.assertEqual('oh', detail['jurisdiction'])
        self.assertEqual('2024-11-08T23:59:59+00:00', detail['eventTime'])
        self.assertNotIn('recordNumber', detail)
        self.assertIn('validData', detail)
        self.assertIn('errors', detail)
        self.assertEqual('multi-state', detail['validData']['licenseScope'])
        self.assertEqual('eligible', detail['validData']['compactEligibility'])

        provider_records = self._provider_table.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('pk').eq(f'socw#PROVIDER#{message["detail"]["providerId"]}'),
        )['Items']
        multi_state_license = next(
            record
            for record in provider_records
            if record['type'] == 'license' and record['licenseScope'] == 'multi-state'
        )
        self.assertEqual('B0608337260', multi_state_license['licenseNumber'])

    @patch('handlers.ingest.EventBatchWriter', autospec=True)
    def test_eligible_multi_state_with_eligible_single_state_does_not_emit_validation_error(self, mock_event_writer):
        self._setup_provider_ssn()

        self._ingest_license(
            {
                'licenseScope': 'single-state',
                'licenseStatus': 'active',
                'compactEligibility': 'eligible',
            },
            message_id='200',
        )

        self._ingest_license(
            {
                'licenseScope': 'multi-state',
                'licenseNumber': 'B0608337260',
                'licenseStatus': 'active',
                'compactEligibility': 'eligible',
            },
            message_id='201',
        )

        mock_event_writer.return_value.__enter__.return_value.put_event.assert_not_called()

    @patch('handlers.ingest.EventBatchWriter', autospec=True)
    def test_eligible_multi_state_without_single_state_does_not_emit_validation_error(self, mock_event_writer):
        from handlers.ingest import ingest_license_message

        with open('../common/tests/resources/ingest/event-bridge-message.json') as f:
            message = json.load(f)

        message['detail'].update(
            {
                'licenseScope': 'multi-state',
                'licenseNumber': 'B0608337260',
                'licenseStatus': 'active',
                'compactEligibility': 'eligible',
            }
        )

        event = {'Records': [{'messageId': '300', 'body': json.dumps(message)}]}
        resp = ingest_license_message(event, self.mock_context)
        self.assertEqual({'batchItemFailures': []}, resp)

        mock_event_writer.return_value.__enter__.return_value.put_event.assert_not_called()

        provider_records = self._provider_table.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('pk').eq(f'socw#PROVIDER#{message["detail"]["providerId"]}'),
        )['Items']
        license_records = [record for record in provider_records if record['type'] == 'license']
        self.assertEqual(1, len(license_records))
        self.assertEqual('multi-state', license_records[0]['licenseScope'])
