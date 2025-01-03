import json
from datetime import UTC, date, datetime
from unittest.mock import MagicMock, patch

from cc_common.config import config
from cc_common.exceptions import CCAwsServiceException, CCFailedTransactionException, CCInternalException
from moto import mock_aws

from .. import TstFunction

TEST_COMPACT = 'aslp'
# this value is defined in the provider.json file
TEST_PROVIDER_ID = '89a6377e-c3a5-40e5-bca5-317ec854c570'

MOCK_TRANSACTION_ID = '1234'
JURISPRUDENCE_CONFIRMATION_ATTESTATION_ID = 'jurisprudence-confirmation'
REQUIRED_ATTESTATION_IDS = [JURISPRUDENCE_CONFIRMATION_ATTESTATION_ID]


def _generate_test_request_body(selected_jurisdictions: list[str] = None, attestations: list[dict] = None):
    if not selected_jurisdictions:
        selected_jurisdictions = ['ky']
    if attestations is None:
        attestations = [{'attestationId': JURISPRUDENCE_CONFIRMATION_ATTESTATION_ID, 'version': '1'}]

    return json.dumps(
        {
            'selectedJurisdictions': selected_jurisdictions,
            'orderInformation': {
                'card': {'number': '<card number>', 'expiration': '<expiration date>', 'cvv': '<cvv>'},
                'billing': {
                    'firstName': 'testFirstName',
                    'lastName': 'testLastName',
                    'streetAddress': '123 Test St',
                    'streetAddress2': '',  # optional
                    'state': 'OH',
                    'zip': '12345',
                },
            },
            'attestations': attestations,
        }
    )


@mock_aws
class TestPostPurchasePrivileges(TstFunction):
    """
    In this test setup, we simulate having a licensee that has a license in ohio and is
    purchasing a privilege in kentucky.
    """

    def setUp(self):
        super().setUp()
        # Load test attestation data
        with open('../common/tests/resources/dynamo/attestation.json') as f:
            test_attestation = json.load(f)
            # put in one attestation records for each required attestation type
            for attestation_id in REQUIRED_ATTESTATION_IDS:
                test_attestation['attestationId'] = attestation_id
                self.config.compact_configuration_table.put_item(Item=test_attestation)

    def _load_test_jurisdiction(self):
        with open('../common/tests/resources/dynamo/jurisdiction.json') as f:
            jurisdiction = json.load(f)
            # swap out the jurisdiction postal abbreviation for ky
            jurisdiction['postalAbbreviation'] = 'ky'
            jurisdiction['jurisdictionName'] = 'Kentucky'
            jurisdiction['pk'] = 'aslp#CONFIGURATION'
            jurisdiction['sk'] = 'aslp#JURISDICTION#ky'
            self.config.compact_configuration_table.put_item(Item=jurisdiction)

    def _when_testing_provider_user_event_with_custom_claims(
        self,
        test_compact=TEST_COMPACT,
        license_status: str = 'active',
        license_expiration_date: str = '2050-01-01',
    ):
        self._load_compact_configuration_data()
        self._load_provider_data()
        self._load_test_jurisdiction()
        self._load_license_data(status=license_status, expiration_date=license_expiration_date)
        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)
            event['requestContext']['authorizer']['claims']['custom:providerId'] = TEST_PROVIDER_ID
            event['requestContext']['authorizer']['claims']['custom:compact'] = test_compact

        return event

    def _when_purchase_client_successfully_processes_request(self, mock_purchase_client_constructor):
        mock_purchase_client = MagicMock()
        mock_purchase_client_constructor.return_value = mock_purchase_client
        mock_purchase_client.process_charge_for_licensee_privileges.return_value = {
            'transactionId': MOCK_TRANSACTION_ID
        }

        return mock_purchase_client

    def _when_purchase_client_raises_transaction_exception(self, mock_purchase_client_constructor):
        mock_purchase_client = MagicMock()
        mock_purchase_client_constructor.return_value = mock_purchase_client
        mock_purchase_client.process_charge_for_licensee_privileges.side_effect = CCFailedTransactionException(
            'cvv invalid'
        )

        return mock_purchase_client

    @patch('handlers.privileges.PurchaseClient')
    def test_post_purchase_privileges_calls_purchase_client_with_expected_parameters(
        self, mock_purchase_client_constructor
    ):
        from handlers.privileges import post_purchase_privileges

        mock_purchase_client = self._when_purchase_client_successfully_processes_request(
            mock_purchase_client_constructor
        )
        event = self._when_testing_provider_user_event_with_custom_claims()
        event['body'] = _generate_test_request_body()

        resp = post_purchase_privileges(event, self.mock_context)
        self.assertEqual(200, resp['statusCode'])

        purchase_client_call_kwargs = mock_purchase_client.process_charge_for_licensee_privileges.call_args.kwargs

        self.assertEqual(
            json.loads(event['body'])['orderInformation'], purchase_client_call_kwargs['order_information']
        )
        self.assertEqual(TEST_COMPACT, purchase_client_call_kwargs['compact_configuration'].compact_name)
        self.assertEqual(
            ['ky'],
            [
                jurisdiction.postal_abbreviation
                for jurisdiction in purchase_client_call_kwargs['selected_jurisdictions']
            ],
        )
        # in this test, the user had an empty list of military affiliations, so this should be false
        self.assertEqual(False, purchase_client_call_kwargs['user_active_military'])

    def _when_testing_military_affiliation_status(
        self,
        mock_purchase_client_constructor: MagicMock,
        military_affiliation_status: str,
        expected_military_parameter: bool,
    ):
        from handlers.privileges import post_purchase_privileges

        mock_purchase_client = self._when_purchase_client_successfully_processes_request(
            mock_purchase_client_constructor
        )
        event = self._when_testing_provider_user_event_with_custom_claims()
        self._load_military_affiliation_record_data(status=military_affiliation_status)
        event['body'] = _generate_test_request_body()

        resp = post_purchase_privileges(event, self.mock_context)
        self.assertEqual(200, resp['statusCode'])

        purchase_client_call_kwargs = mock_purchase_client.process_charge_for_licensee_privileges.call_args.kwargs
        self.assertEqual(expected_military_parameter, purchase_client_call_kwargs['user_active_military'])

    @patch('handlers.privileges.PurchaseClient')
    def test_post_purchase_privileges_calls_purchase_client_with_active_military_status(
        self, mock_purchase_client_constructor
    ):
        self._when_testing_military_affiliation_status(mock_purchase_client_constructor, 'active', True)

    @patch('handlers.privileges.PurchaseClient')
    def test_post_purchase_privileges_calls_purchase_client_with_inactive_military_status(
        self, mock_purchase_client_constructor
    ):
        self._when_testing_military_affiliation_status(mock_purchase_client_constructor, 'inactive', False)

    @patch('handlers.privileges.PurchaseClient')
    def test_post_purchase_privileges_raises_exception_when_military_affiliation_in_initializing_status(
        self, mock_purchase_client_constructor
    ):
        from handlers.privileges import post_purchase_privileges

        self._when_purchase_client_successfully_processes_request(mock_purchase_client_constructor)
        event = self._when_testing_provider_user_event_with_custom_claims()
        self._load_military_affiliation_record_data(status='initializing')
        event['body'] = _generate_test_request_body()

        resp = post_purchase_privileges(event, self.mock_context)
        self.assertEqual(400, resp['statusCode'])
        response_body = json.loads(resp['body'])

        self.assertEqual(
            {
                'message': 'Your proof of military affiliation documentation was not successfully'
                ' processed. Please return to the Military Status page and re-upload your military'
                ' affiliation documentation or end your military affiliation.'
            },
            response_body,
        )

    @patch('handlers.privileges.PurchaseClient')
    def test_post_purchase_privileges_returns_transaction_id(self, mock_purchase_client_constructor):
        from handlers.privileges import post_purchase_privileges

        self._when_purchase_client_successfully_processes_request(mock_purchase_client_constructor)

        event = self._when_testing_provider_user_event_with_custom_claims()
        event['body'] = _generate_test_request_body()

        resp = post_purchase_privileges(event, self.mock_context)
        self.assertEqual(200, resp['statusCode'])
        response_body = json.loads(resp['body'])

        self.assertEqual({'transactionId': MOCK_TRANSACTION_ID}, response_body)

    @patch('handlers.privileges.PurchaseClient')
    def test_post_purchase_privileges_returns_error_message_if_transaction_failure(
        self, mock_purchase_client_constructor
    ):
        from handlers.privileges import post_purchase_privileges

        self._when_purchase_client_raises_transaction_exception(mock_purchase_client_constructor)

        event = self._when_testing_provider_user_event_with_custom_claims()
        event['body'] = _generate_test_request_body()

        resp = post_purchase_privileges(event, self.mock_context)
        self.assertEqual(400, resp['statusCode'])
        response_body = json.loads(resp['body'])

        self.assertEqual({'message': 'Error: cvv invalid'}, response_body)

    @patch('handlers.privileges.PurchaseClient')
    def test_post_purchase_privileges_returns_400_if_selected_jurisdiction_invalid(
        self, mock_purchase_client_constructor
    ):
        from handlers.privileges import post_purchase_privileges

        self._when_purchase_client_successfully_processes_request(mock_purchase_client_constructor)

        event = self._when_testing_provider_user_event_with_custom_claims()
        event['body'] = _generate_test_request_body(['oh', 'foobar'])

        resp = post_purchase_privileges(event, self.mock_context)
        self.assertEqual(400, resp['statusCode'])
        response_body = json.loads(resp['body'])

        self.assertEqual({'message': 'Invalid jurisdiction postal abbreviation'}, response_body)

    @patch('handlers.privileges.PurchaseClient')
    def test_post_purchase_privileges_returns_400_if_selected_jurisdiction_matches_existing_license(
        self, mock_purchase_client_constructor
    ):
        """
        In this case, the user is attempting to purchase a privilege in ohio, but they already have a license in ohio.
        So the request should be rejected.
        """
        from handlers.privileges import post_purchase_privileges

        self._when_purchase_client_successfully_processes_request(mock_purchase_client_constructor)

        event = self._when_testing_provider_user_event_with_custom_claims()
        event['body'] = _generate_test_request_body(['oh'])

        resp = post_purchase_privileges(event, self.mock_context)
        self.assertEqual(400, resp['statusCode'])
        response_body = json.loads(resp['body'])

        self.assertEqual(
            {'message': "Selected privilege jurisdiction 'oh' matches license jurisdiction"}, response_body
        )

    @patch('handlers.privileges.PurchaseClient')
    def test_purchase_privileges_invalid_if_existing_privilege_expiration_matches_license_expiration(
        self, mock_purchase_client_constructor
    ):
        """
        In this case, the user is attempting to purchase a privilege in kentucky twice and the license expiration
        date has not been updated since the last renewal. We reject the request in this case.
        """
        from handlers.privileges import post_purchase_privileges

        self._when_purchase_client_successfully_processes_request(mock_purchase_client_constructor)

        event = self._when_testing_provider_user_event_with_custom_claims()
        event['body'] = _generate_test_request_body()

        resp = post_purchase_privileges(event, self.mock_context)
        self.assertEqual(200, resp['statusCode'])

        # now make the same call with the same jurisdiction
        resp = post_purchase_privileges(event, self.mock_context)
        self.assertEqual(400, resp['statusCode'])
        response_body = json.loads(resp['body'])

        self.assertEqual(
            {'message': "Selected privilege jurisdiction 'ky' matches existing privilege jurisdiction"}, response_body
        )

    @patch('handlers.privileges.PurchaseClient')
    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-10-05T23:59:59+00:00'))
    def test_purchase_privileges_allows_existing_privilege_purchase_if_license_expiration_does_not_match(
        self, mock_purchase_client_constructor
    ):
        """
        In this case, the user is attempting to purchase a privilege in kentucky twice, but the license expiration
        date is different. We allow the user to renew their privilege so the expiration date is updated.
        """
        from handlers.privileges import post_purchase_privileges

        self._when_purchase_client_successfully_processes_request(mock_purchase_client_constructor)
        test_expiration_date = date(2024, 10, 8).isoformat()
        event = self._when_testing_provider_user_event_with_custom_claims(license_expiration_date=test_expiration_date)
        event['body'] = _generate_test_request_body()
        test_issuance_date = datetime(2023, 10, 8, hour=5, tzinfo=UTC).isoformat()

        # create an existing privilege record for the kentucky jurisdiction, simulating a previous purchase
        with open('../common/tests/resources/dynamo/privilege.json') as f:
            privilege_record = json.load(f)
            privilege_record['pk'] = f'{TEST_COMPACT}#PROVIDER#{TEST_PROVIDER_ID}'
            privilege_record['sk'] = f'{TEST_COMPACT}#PROVIDER#privilege/ky#2023-10-08'
            # in this case, the user is purchasing the privilege for the first time
            # so the date of renewal is the same as the date of issuance
            privilege_record['dateOfRenewal'] = test_issuance_date
            privilege_record['dateOfIssuance'] = test_issuance_date
            privilege_record['dateOfExpiration'] = test_expiration_date
            privilege_record['compact'] = TEST_COMPACT
            privilege_record['jurisdiction'] = 'ky'
            privilege_record['providerId'] = TEST_PROVIDER_ID
            self.config.provider_table.put_item(Item=privilege_record)

        # update the license expiration date to be different
        updated_expiration_date = '2050-01-01'
        self._load_license_data(expiration_date=updated_expiration_date)

        # now make the same call with the same jurisdiction
        resp = post_purchase_privileges(event, self.mock_context)
        self.assertEqual(200, resp['statusCode'])
        response_body = json.loads(resp['body'])

        self.assertEqual({'transactionId': MOCK_TRANSACTION_ID}, response_body)

        # ensure there are two privilege records for the same jurisdiction
        provider_records = self.config.data_client.get_provider(compact=TEST_COMPACT, provider_id=TEST_PROVIDER_ID)
        privilege_records = [record for record in provider_records['items'] if record['type'] == 'privilege']
        self.assertEqual(2, len(privilege_records))

        # ensure the date of renewal is updated
        updated_privilege_record = next(
            record for record in privilege_records if record['dateOfRenewal'].isoformat() == '2024-10-05T23:59:59+00:00'
        )
        # ensure the expiration is updated
        self.assertEqual(updated_expiration_date, updated_privilege_record['dateOfExpiration'].isoformat())
        # ensure the issuance date is the same
        self.assertEqual(test_issuance_date, updated_privilege_record['dateOfIssuance'].isoformat())

    @patch('handlers.privileges.PurchaseClient')
    def test_post_purchase_privileges_returns_404_if_provider_not_found(self, mock_purchase_client_constructor):
        from handlers.privileges import post_purchase_privileges

        self._when_purchase_client_successfully_processes_request(mock_purchase_client_constructor)

        event = self._when_testing_provider_user_event_with_custom_claims()
        event['requestContext']['authorizer']['claims']['custom:providerId'] = 'foobar'
        event['body'] = _generate_test_request_body()

        resp = post_purchase_privileges(event, self.mock_context)
        self.assertEqual(404, resp['statusCode'])
        response_body = json.loads(resp['body'])

        self.assertEqual({'message': 'Provider not found'}, response_body)

    @patch('handlers.privileges.PurchaseClient')
    def test_post_purchase_privileges_returns_400_if_no_active_license_found(self, mock_purchase_client_constructor):
        from handlers.privileges import post_purchase_privileges

        self._when_purchase_client_successfully_processes_request(mock_purchase_client_constructor)

        event = self._when_testing_provider_user_event_with_custom_claims(license_status='inactive')
        event['body'] = _generate_test_request_body()

        resp = post_purchase_privileges(event, self.mock_context)
        self.assertEqual(400, resp['statusCode'])
        response_body = json.loads(resp['body'])

        self.assertEqual({'message': 'No active license found for this user'}, response_body)

    @patch('handlers.privileges.PurchaseClient')
    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
    def test_post_purchase_privileges_adds_privilege_record_if_transaction_successful(
        self, mock_purchase_client_constructor
    ):
        from handlers.privileges import post_purchase_privileges

        self._when_purchase_client_successfully_processes_request(mock_purchase_client_constructor)

        event = self._when_testing_provider_user_event_with_custom_claims(license_expiration_date='2050-01-01')
        event['body'] = _generate_test_request_body()

        resp = post_purchase_privileges(event, self.mock_context)
        self.assertEqual(200, resp['statusCode'])

        # check that the privilege record for ky was created
        provider_records = self.config.data_client.get_provider(compact=TEST_COMPACT, provider_id=TEST_PROVIDER_ID)

        privilege_record = next(record for record in provider_records['items'] if record['type'] == 'privilege')
        license_record = next(record for record in provider_records['items'] if record['type'] == 'license')

        # make sure the expiration on the license matches the expiration on the privilege
        expected_expiration_date = date(2050, 1, 1)
        self.assertEqual(expected_expiration_date, license_record['dateOfExpiration'])
        self.assertEqual(expected_expiration_date, privilege_record['dateOfExpiration'])
        # the date of issuance should be mocked timestamp
        mock_datetime = datetime.fromisoformat('2024-11-08T23:59:59+00:00')
        self.assertEqual(mock_datetime, privilege_record['dateOfIssuance'])
        self.assertEqual(mock_datetime, privilege_record['dateOfUpdate'])
        self.assertEqual(TEST_COMPACT, privilege_record['compact'])
        self.assertEqual('ky', privilege_record['jurisdiction'])
        self.assertEqual(TEST_PROVIDER_ID, str(privilege_record['providerId']))
        self.assertEqual('active', privilege_record['status'])
        self.assertEqual('privilege', privilege_record['type'])
        self.assertEqual([
            {
                'attestationId': JURISPRUDENCE_CONFIRMATION_ATTESTATION_ID,
                'version': '1'
             }], privilege_record['attestations'])
        # make sure we are tracking the transaction id
        self.assertEqual(MOCK_TRANSACTION_ID, privilege_record['compactTransactionId'])

    @patch('handlers.privileges.PurchaseClient')
    @patch('handlers.privileges.config.data_client')
    def test_post_purchase_privileges_voids_transaction_if_aws_error_occurs(
        self, mock_data_client, mock_purchase_client_constructor
    ):
        from handlers.privileges import post_purchase_privileges

        mock_purchase_client = self._when_purchase_client_successfully_processes_request(
            mock_purchase_client_constructor
        )
        # set the first two api calls to call the actual implementation
        mock_data_client.get_privilege_purchase_options = config.data_client.get_privilege_purchase_options
        mock_data_client.get_provider = config.data_client.get_provider
        # raise an exception when creating the privilege record
        mock_data_client.create_provider_privileges.side_effect = CCAwsServiceException('dynamo down')

        event = self._when_testing_provider_user_event_with_custom_claims()
        event['body'] = _generate_test_request_body()

        with self.assertRaises(CCInternalException):
            post_purchase_privileges(event, self.mock_context)

        # verify that the transaction was voided
        mock_purchase_client.void_privilege_purchase_transaction.assert_called_once_with(
            compact_name=TEST_COMPACT, order_information={'transactionId': MOCK_TRANSACTION_ID}
        )

    @patch('handlers.privileges.PurchaseClient')
    def test_post_purchase_privileges_validates_attestation_version(self, mock_purchase_client_constructor):
        """Test that the endpoint validates attestation versions."""
        from handlers.privileges import post_purchase_privileges

        self._when_purchase_client_successfully_processes_request(mock_purchase_client_constructor)

        event = self._when_testing_provider_user_event_with_custom_claims()
        # Use an old version number
        event['body'] = _generate_test_request_body(attestations=[
            {'attestationId': JURISPRUDENCE_CONFIRMATION_ATTESTATION_ID, 'version': '0'}])

        resp = post_purchase_privileges(event, self.mock_context)
        self.assertEqual(400, resp['statusCode'])
        response_body = json.loads(resp['body'])

        self.assertEqual(
            {
                'message': 'Attestation "jurisprudence-confirmation" version 0 is not the latest version (1)'
            },
            response_body,
        )
        mock_purchase_client_constructor.assert_not_called()


    @patch('handlers.privileges.PurchaseClient')
    def test_post_purchase_privileges_validates_attestation_in_list_of_required_attestations(self, mock_purchase_client_constructor):
        """Test that the endpoint validates attestation existence."""
        from handlers.privileges import post_purchase_privileges

        self._when_purchase_client_successfully_processes_request(mock_purchase_client_constructor)

        event = self._when_testing_provider_user_event_with_custom_claims()
        event['body'] = _generate_test_request_body(attestations=[{'attestationId': 'nonexistent-attestation', 'version': '1'}])

        resp = post_purchase_privileges(event, self.mock_context)
        self.assertEqual(400, resp['statusCode'])
        response_body = json.loads(resp['body'])

        self.assertEqual(
            {'message': 'Invalid attestation provided: "nonexistent-attestation"'},
            response_body,
        )

    @patch('handlers.privileges.PurchaseClient')
    def test_post_purchase_privileges_validates_all_required_attestations_present(self, mock_purchase_client_constructor):
        """Test that the endpoint validates attestation existence."""
        from handlers.privileges import post_purchase_privileges

        self._when_purchase_client_successfully_processes_request(mock_purchase_client_constructor)

        event = self._when_testing_provider_user_event_with_custom_claims()
        event['body'] = _generate_test_request_body(attestations=[])

        resp = post_purchase_privileges(event, self.mock_context)
        self.assertEqual(400, resp['statusCode'])
        response_body = json.loads(resp['body'])

        self.assertEqual(
            {'message': 'Attestations do not match required list.'},
            response_body,
        )

    @patch('handlers.privileges.PurchaseClient')
    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
    def test_post_purchase_privileges_stores_attestations_in_privilege_record(self, mock_purchase_client_constructor):
        """Test that attestations are stored in the privilege record."""
        from handlers.privileges import post_purchase_privileges

        self._when_purchase_client_successfully_processes_request(mock_purchase_client_constructor)

        event = self._when_testing_provider_user_event_with_custom_claims(license_expiration_date='2050-01-01')
        test_attestations = [{'attestationId': JURISPRUDENCE_CONFIRMATION_ATTESTATION_ID, 'version': '1'}]
        event['body'] = _generate_test_request_body(attestations=test_attestations)

        resp = post_purchase_privileges(event, self.mock_context)
        self.assertEqual(200, resp['statusCode'])

        # check that the privilege record for ky was created with attestations
        provider_records = self.config.data_client.get_provider(compact=TEST_COMPACT, provider_id=TEST_PROVIDER_ID)
        privilege_record = next(record for record in provider_records['items'] if record['type'] == 'privilege')

        self.assertEqual(test_attestations, privilege_record['attestations'])
