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
ALL_ATTESTATION_IDS = [
    'jurisprudence-confirmation',
    'scope-of-practice-attestation',
    'personal-information-home-state-attestation',
    'personal-information-address-attestation',
    'discipline-no-current-encumbrance-attestation',
    'discipline-no-prior-encumbrance-attestation',
    'provision-of-true-information-attestation',
    'not-under-investigation-attestation',
    'military-affiliation-confirmation-attestation',
    'under-investigation-attestation',
]

TEST_EMAIL = 'testRegisteredEmail@example.com'
TEST_COGNITO_SUB = '1234567890'

TEST_LICENSE_TYPE = 'speech-language pathologist'
MOCK_LINE_ITEMS = [{'name': 'Alaska Big Fee', 'quantity': '1', 'unitPrice': '55.5', 'description': 'Fee for Alaska'}]


def generate_default_attestation_list():
    return [
        {'attestationId': 'jurisprudence-confirmation', 'version': '1'},
        {'attestationId': 'scope-of-practice-attestation', 'version': '1'},
        {'attestationId': 'personal-information-home-state-attestation', 'version': '1'},
        {'attestationId': 'personal-information-address-attestation', 'version': '1'},
        {'attestationId': 'discipline-no-current-encumbrance-attestation', 'version': '1'},
        {'attestationId': 'discipline-no-prior-encumbrance-attestation', 'version': '1'},
        {'attestationId': 'provision-of-true-information-attestation', 'version': '1'},
        {'attestationId': 'not-under-investigation-attestation', 'version': '1'},
    ]


def _generate_test_request_body(
    selected_jurisdictions: list[str] = None, attestations: list[dict] = None, license_type: str = TEST_LICENSE_TYPE
):
    if not selected_jurisdictions:
        selected_jurisdictions = ['ky']
    if attestations is None:
        attestations = generate_default_attestation_list()

    return json.dumps(
        {
            'licenseType': license_type,
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
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
class TestPostPurchasePrivileges(TstFunction):
    """
    In this test setup, we simulate having a licensee that has a license in ohio and is
    purchasing a privilege in kentucky.
    """

    def setUp(self):
        from cc_common.data_model.schema.attestation import AttestationRecordSchema

        super().setUp()
        # Load test attestation data
        with open('../common/tests/resources/dynamo/attestation.json') as f:
            test_attestation = json.load(f)
            # put in one attestation record for each attestation id
            for attestation_id in ALL_ATTESTATION_IDS:
                test_attestation['attestationId'] = attestation_id
                test_attestation.pop('pk')
                test_attestation.pop('sk')
                serialized_data = AttestationRecordSchema().dump(test_attestation)

                self.config.compact_configuration_table.put_item(Item=serialized_data)
        # register the user in the system
        self.config.data_client.process_registration_values(
            compact=TEST_COMPACT,
            provider_id=TEST_PROVIDER_ID,
            cognito_sub=TEST_COGNITO_SUB,
            email_address=TEST_EMAIL,
            jurisdiction='oh',
        )

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
        eligibility: str = 'eligible',
        license_expiration_date: str = '2050-01-01',
    ):
        self._load_compact_configuration_data()
        self._load_provider_data()
        self._load_test_jurisdiction()
        self._load_license_data(eligibility=eligibility, expiration_date=license_expiration_date)
        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)
            event['requestContext']['authorizer']['claims']['custom:providerId'] = TEST_PROVIDER_ID
            event['requestContext']['authorizer']['claims']['custom:compact'] = test_compact

        return event

    def _when_purchase_client_successfully_processes_request(self, mock_purchase_client_constructor):
        mock_purchase_client = MagicMock()
        mock_purchase_client_constructor.return_value = mock_purchase_client
        mock_purchase_client.process_charge_for_licensee_privileges.return_value = {
            'transactionId': MOCK_TRANSACTION_ID,
            'lineItems': MOCK_LINE_ITEMS,
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
        self.assertEqual(TEST_COMPACT, purchase_client_call_kwargs['compact_configuration'].compact_abbr)
        self.assertEqual(
            ['ky'],
            [
                jurisdiction.postal_abbreviation
                for jurisdiction in purchase_client_call_kwargs['selected_jurisdictions']
            ],
        )
        self.assertEqual('slp', purchase_client_call_kwargs['license_type_abbreviation'])
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
        attestations = generate_default_attestation_list()
        # add the military affiliation attestation if active
        if military_affiliation_status == 'active':
            attestations.append({'attestationId': 'military-affiliation-confirmation-attestation', 'version': '1'})
        event['body'] = _generate_test_request_body(attestations=attestations)

        resp = post_purchase_privileges(event, self.mock_context)
        self.assertEqual(200, resp['statusCode'], resp['body'])

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
    def test_post_purchase_privileges_returns_necessary_data(self, mock_purchase_client_constructor):
        from handlers.privileges import post_purchase_privileges

        self._when_purchase_client_successfully_processes_request(mock_purchase_client_constructor)

        event = self._when_testing_provider_user_event_with_custom_claims()
        event['body'] = _generate_test_request_body()

        resp = post_purchase_privileges(event, self.mock_context)
        self.assertEqual(200, resp['statusCode'])
        response_body = json.loads(resp['body'])

        self.assertEqual(
            {
                'transactionId': MOCK_TRANSACTION_ID,
                'lineItems': MOCK_LINE_ITEMS,
            },
            response_body,
        )

    @patch('handlers.privileges.PurchaseClient')
    @patch('handlers.privileges.config.event_bus_client', autospec=True)
    def test_post_purchase_privileges_kicks_off_privilege_purchase_event(
        self,
        mock_event_bus,
        mock_purchase_client_constructor,
    ):
        from handlers.privileges import post_purchase_privileges

        self._when_purchase_client_successfully_processes_request(mock_purchase_client_constructor)

        event = self._when_testing_provider_user_event_with_custom_claims()
        event['body'] = _generate_test_request_body()

        post_purchase_privileges(event, self.mock_context)
        mock_event_bus.publish_privilege_purchase_event.assert_called_once_with(
            source='post_purchase_privileges',
            jurisdiction='oh',
            compact='aslp',
            provider_email='björkRegisteredEmail@example.com',
            privileges=[
                {
                    'compact': 'aslp',
                    'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570',
                    'jurisdiction': 'ky',
                    'licenseTypeAbbrev': 'slp',
                    'privilegeId': 'SLP-KY-1',
                }
            ],
            total_cost='55.5',
            cost_line_items=MOCK_LINE_ITEMS,
        )

    @patch('handlers.privileges.PurchaseClient')
    @patch('handlers.privileges.config.event_bus_client', autospec=True)
    def test_post_purchase_privileges_kicks_off_privilege_issued_event(
        self,
        mock_event_bus,
        mock_purchase_client_constructor,
    ):
        from handlers.privileges import post_purchase_privileges

        self._when_purchase_client_successfully_processes_request(mock_purchase_client_constructor)

        event = self._when_testing_provider_user_event_with_custom_claims()
        event['body'] = _generate_test_request_body()

        post_purchase_privileges(event, self.mock_context)
        mock_event_bus.publish_privilege_issued_event.assert_called_once_with(
            source='post_purchase_privileges',
            jurisdiction='ky',
            compact='aslp',
            provider_email='björkRegisteredEmail@example.com',
        )

    @patch('handlers.privileges.PurchaseClient')
    @patch('handlers.privileges.config.event_bus_client', autospec=True)
    def test_post_purchase_privileges_kicks_off_privilege_renewed_event(
        self,
        mock_event_bus,
        mock_purchase_client_constructor,
    ):
        from handlers.privileges import post_purchase_privileges

        self._when_purchase_client_successfully_processes_request(mock_purchase_client_constructor)

        event = self._when_testing_provider_user_event_with_custom_claims()
        event['body'] = _generate_test_request_body()

        test_expiration_date = date(2026, 10, 8).isoformat()
        event = self._when_testing_provider_user_event_with_custom_claims(license_expiration_date=test_expiration_date)
        event['body'] = _generate_test_request_body()
        test_issuance_date = datetime(2023, 10, 8, hour=5, tzinfo=UTC).isoformat()

        # create an existing privilege record for the kentucky jurisdiction, simulating a previous purchase
        with open('../common/tests/resources/dynamo/privilege.json') as f:
            privilege_record = json.load(f)
            privilege_record['pk'] = f'{TEST_COMPACT}#PROVIDER#{TEST_PROVIDER_ID}'
            privilege_record['sk'] = f'{TEST_COMPACT}#PROVIDER#privilege/ky/slp#'
            # in this case, the user is purchasing the privilege for the first time
            # so the date of renewal is the same as the date of issuance
            privilege_record['dateOfRenewal'] = test_issuance_date
            privilege_record['dateOfIssuance'] = test_issuance_date
            privilege_record['dateOfExpiration'] = test_expiration_date
            privilege_record['compact'] = TEST_COMPACT
            privilege_record['jurisdiction'] = 'ky'
            privilege_record['providerId'] = TEST_PROVIDER_ID
            privilege_record['administratorSetStatus'] = 'inactive'
            self.config.provider_table.put_item(Item=privilege_record)

        post_purchase_privileges(event, self.mock_context)
        mock_event_bus.publish_privilege_renewed_event.assert_called_once_with(
            source='post_purchase_privileges',
            jurisdiction='ky',
            compact='aslp',
            provider_email='björkRegisteredEmail@example.com',
        )

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
    def test_purchase_privileges_invalid_if_existing_privilege_expiration_matches_license_expiration_and_is_active(
        self, mock_purchase_client_constructor
    ):
        """
        In this case, the user is attempting to purchase a privilege in kentucky twice, the license expiration
        date has not been updated since the last renewal and the initial privilege is still active.
        We reject the request in this case.
        """
        from handlers.privileges import post_purchase_privileges

        self._when_purchase_client_successfully_processes_request(mock_purchase_client_constructor)

        event = self._when_testing_provider_user_event_with_custom_claims()
        event['body'] = _generate_test_request_body()

        resp = post_purchase_privileges(event, self.mock_context)
        self.assertEqual(200, resp['statusCode'], resp['body'])

        # now make the same call with the same jurisdiction
        resp = post_purchase_privileges(event, self.mock_context)
        self.assertEqual(400, resp['statusCode'])
        response_body = json.loads(resp['body'])

        self.assertEqual(
            {
                'message': "Selected privilege jurisdiction 'ky' matches existing privilege "
                'jurisdiction for license type'
            },
            response_body,
        )

    @patch('handlers.privileges.PurchaseClient')
    def test_purchase_privileges_valid_even_if_existing_privilege_for_another_license_type_has_same_expiration(
        self, mock_purchase_client_constructor
    ):
        """
        This test checks for a rare edge case where a user has two licenses which happen to have the *exact* same
        expiration date, and the user has a privilege for the first license.

        If the user attempts to buy a privilege for the other license in the same jurisdiction as the privilege of the
        first license, the handler should allow the purchase, ensuring that we are only checking the existing privileges
        specific to the license type which the user has selected.
        """
        from handlers.privileges import post_purchase_privileges

        self._when_purchase_client_successfully_processes_request(mock_purchase_client_constructor)

        test_license_expiration_date = '2050-01-01'
        event = self._when_testing_provider_user_event_with_custom_claims(
            license_expiration_date=test_license_expiration_date
        )
        event['body'] = _generate_test_request_body(license_type=TEST_LICENSE_TYPE)
        # buy a privilege for the first license type
        resp = post_purchase_privileges(event, self.mock_context)
        self.assertEqual(200, resp['statusCode'], resp['body'])

        # now make the same call with the same jurisdiction, but for a different license type
        # a new privilege record should be generated for that specific license type
        self._load_license_data(expiration_date=test_license_expiration_date, license_type='audiologist')
        event['body'] = _generate_test_request_body(license_type='audiologist')
        resp = post_purchase_privileges(event, self.mock_context)
        self.assertEqual(200, resp['statusCode'])

        # check that the privilege records for ky were created for both license types
        provider_records = self.config.data_client.get_provider(compact=TEST_COMPACT, provider_id=TEST_PROVIDER_ID)

        privilege_records_license_types = set(
            [record['licenseType'] for record in provider_records['items'] if record['type'] == 'privilege']
        )
        self.assertEqual({'audiologist', 'speech-language pathologist'}, privilege_records_license_types)

    @patch('handlers.privileges.PurchaseClient')
    def test_purchase_privileges_allows_existing_privilege_purchase_if_license_expiration_matches_but_is_inactive(
        self, mock_purchase_client_constructor
    ):
        """
        In this case, the user is attempting to purchase a privilege in kentucky twice with the same expiration date
        but the status of the first privilege is inactive
        """
        from handlers.privileges import post_purchase_privileges

        self._when_purchase_client_successfully_processes_request(mock_purchase_client_constructor)
        test_expiration_date = date(2026, 10, 8).isoformat()
        event = self._when_testing_provider_user_event_with_custom_claims(license_expiration_date=test_expiration_date)
        event['body'] = _generate_test_request_body()
        test_issuance_date = datetime(2023, 10, 8, hour=5, tzinfo=UTC).isoformat()

        # create an existing privilege record for the kentucky jurisdiction, simulating a previous purchase
        with open('../common/tests/resources/dynamo/privilege.json') as f:
            privilege_record = json.load(f)
            privilege_record['pk'] = f'{TEST_COMPACT}#PROVIDER#{TEST_PROVIDER_ID}'
            privilege_record['sk'] = f'{TEST_COMPACT}#PROVIDER#privilege/ky/slp#'
            # in this case, the user is purchasing the privilege for the first time
            # so the date of renewal is the same as the date of issuance
            privilege_record['dateOfRenewal'] = test_issuance_date
            privilege_record['dateOfIssuance'] = test_issuance_date
            privilege_record['dateOfExpiration'] = test_expiration_date
            privilege_record['compact'] = TEST_COMPACT
            privilege_record['jurisdiction'] = 'ky'
            privilege_record['providerId'] = TEST_PROVIDER_ID
            privilege_record['administratorSetStatus'] = 'inactive'
            self.config.provider_table.put_item(Item=privilege_record)

        # now make the same call with the same jurisdiction
        resp = post_purchase_privileges(event, self.mock_context)
        self.assertEqual(200, resp['statusCode'], resp['body'])
        response_body = json.loads(resp['body'])

        self.assertEqual(response_body, {
            'transactionId': MOCK_TRANSACTION_ID,
            'lineItems': MOCK_LINE_ITEMS
        })

        # ensure the persistent status is now active
        provider_records = self.config.data_client.get_provider(compact=TEST_COMPACT, provider_id=TEST_PROVIDER_ID)
        privilege_records = [record for record in provider_records['items'] if record['type'] == 'privilege']
        self.assertEqual('active', privilege_records[0]['administratorSetStatus'])

    @patch('handlers.privileges.PurchaseClient')
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
        self.assertEqual(200, resp['statusCode'], resp['body'])
        response_body = json.loads(resp['body'])

        self.assertEqual(response_body, {
            'transactionId': MOCK_TRANSACTION_ID,
            'lineItems': MOCK_LINE_ITEMS
        })

        # ensure there are two privilege records for the same jurisdiction
        provider_records = self.config.data_client.get_provider(compact=TEST_COMPACT, provider_id=TEST_PROVIDER_ID)
        privilege_records = [record for record in provider_records['items'] if record['type'] == 'privilege']
        self.assertEqual(2, len(privilege_records))

        # ensure the date of renewal is updated
        updated_privilege_record = next(
            record for record in privilege_records if record['dateOfRenewal'].isoformat() == '2024-11-08T23:59:59+00:00'
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

        event = self._when_testing_provider_user_event_with_custom_claims(eligibility='ineligible')
        event['body'] = _generate_test_request_body()

        resp = post_purchase_privileges(event, self.mock_context)
        self.assertEqual(400, resp['statusCode'])
        response_body = json.loads(resp['body'])

        self.assertEqual(
            {'message': 'Specified license type does not match any eligible licenses in the home state.'}, response_body
        )

    @patch('handlers.privileges.PurchaseClient')
    def test_post_purchase_privileges_returns_400_if_license_type_does_not_match_any_home_state_license(
        self, mock_purchase_client_constructor
    ):
        from handlers.privileges import post_purchase_privileges

        self._when_purchase_client_successfully_processes_request(mock_purchase_client_constructor)

        event = self._when_testing_provider_user_event_with_custom_claims(eligibility='eligible')
        event['body'] = _generate_test_request_body(license_type='some-bogus-license-type')

        resp = post_purchase_privileges(event, self.mock_context)
        self.assertEqual(400, resp['statusCode'])
        response_body = json.loads(resp['body'])

        self.assertEqual(
            {'message': 'Specified license type does not match any eligible licenses in the home state.'}, response_body
        )

    @patch('handlers.privileges.PurchaseClient')
    def test_post_purchase_privileges_adds_privilege_record_if_transaction_successful(
        self, mock_purchase_client_constructor
    ):
        from handlers.privileges import post_purchase_privileges

        self._when_purchase_client_successfully_processes_request(mock_purchase_client_constructor)

        event = self._when_testing_provider_user_event_with_custom_claims(license_expiration_date='2050-01-01')
        event['body'] = _generate_test_request_body()

        resp = post_purchase_privileges(event, self.mock_context)
        self.assertEqual(200, resp['statusCode'], resp['body'])

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
        self.assertEqual(len(generate_default_attestation_list()), len(privilege_record['attestations']))
        # make sure we are tracking the transaction id
        self.assertEqual(MOCK_TRANSACTION_ID, privilege_record['compactTransactionId'])
        # verify the privilegeId is formatted correctly
        self.assertEqual('SLP-KY-1', privilege_record['privilegeId'])

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
        mock_data_client.get_privilege_purchase_options = (
            config.compact_configuration_client.get_privilege_purchase_options
        )
        mock_data_client.get_provider = config.data_client.get_provider
        # raise an exception when creating the privilege record
        mock_data_client.create_provider_privileges.side_effect = CCAwsServiceException('dynamo down')

        event = self._when_testing_provider_user_event_with_custom_claims()
        event['body'] = _generate_test_request_body()

        with self.assertRaises(CCInternalException):
            post_purchase_privileges(event, self.mock_context)

        # verify that the transaction was voided
        mock_purchase_client.void_privilege_purchase_transaction.assert_called_once_with(
            compact_abbr=TEST_COMPACT,
            order_information={'transactionId': MOCK_TRANSACTION_ID, 'lineItems': MOCK_LINE_ITEMS},
        )

    @patch('handlers.privileges.PurchaseClient')
    def test_post_purchase_privileges_validates_attestation_version(self, mock_purchase_client_constructor):
        """Test that the endpoint validates attestation versions."""
        from handlers.privileges import post_purchase_privileges

        self._when_purchase_client_successfully_processes_request(mock_purchase_client_constructor)

        event = self._when_testing_provider_user_event_with_custom_claims()
        attestations = generate_default_attestation_list()
        # Use an old version number
        attestations[0]['version'] = '0'
        event['body'] = _generate_test_request_body(attestations=attestations)

        resp = post_purchase_privileges(event, self.mock_context)
        self.assertEqual(400, resp['statusCode'])
        response_body = json.loads(resp['body'])

        self.assertEqual(
            {'message': f'Attestation "{attestations[0]["attestationId"]}" version 0 is not the latest version (1)'},
            response_body,
        )
        mock_purchase_client_constructor.assert_not_called()

    @patch('handlers.privileges.PurchaseClient')
    def test_post_purchase_privileges_validates_attestation_exists_in_list_of_required_attestations(
        self, mock_purchase_client_constructor
    ):
        """Test that the endpoint validates attestation existence."""
        from handlers.privileges import post_purchase_privileges

        self._when_purchase_client_successfully_processes_request(mock_purchase_client_constructor)

        event = self._when_testing_provider_user_event_with_custom_claims()
        attestations = generate_default_attestation_list()
        # Use an attestation that doesn't exist
        attestations.append({'attestationId': 'nonexistent-attestation', 'version': '1'})
        event['body'] = _generate_test_request_body(attestations=attestations)

        resp = post_purchase_privileges(event, self.mock_context)
        self.assertEqual(400, resp['statusCode'])
        response_body = json.loads(resp['body'])

        self.assertEqual(
            {'message': 'Invalid attestations provided: nonexistent-attestation'},
            response_body,
        )

    @patch('handlers.privileges.PurchaseClient')
    def test_post_purchase_privileges_stores_attestations_in_privilege_record(self, mock_purchase_client_constructor):
        """Test that attestations are stored in the privilege record."""
        from handlers.privileges import post_purchase_privileges

        self._when_purchase_client_successfully_processes_request(mock_purchase_client_constructor)

        event = self._when_testing_provider_user_event_with_custom_claims(license_expiration_date='2050-01-01')
        event['body'] = _generate_test_request_body()

        resp = post_purchase_privileges(event, self.mock_context)
        self.assertEqual(200, resp['statusCode'], resp['body'])

        # check that the privilege record for ky was created with attestations
        provider_records = self.config.data_client.get_provider(compact=TEST_COMPACT, provider_id=TEST_PROVIDER_ID)
        privilege_record = next(record for record in provider_records['items'] if record['type'] == 'privilege')

        self.assertEqual(generate_default_attestation_list(), privilege_record['attestations'])

    @patch('handlers.privileges.PurchaseClient')
    def test_post_purchase_privileges_stores_license_type_in_privilege_record(self, mock_purchase_client_constructor):
        """Test that license type is stored in the privilege record."""
        from handlers.privileges import post_purchase_privileges

        self._when_purchase_client_successfully_processes_request(mock_purchase_client_constructor)

        event = self._when_testing_provider_user_event_with_custom_claims(license_expiration_date='2050-01-01')
        event['body'] = _generate_test_request_body()

        resp = post_purchase_privileges(event, self.mock_context)
        self.assertEqual(200, resp['statusCode'], resp['body'])

        # check that the privilege record for ky was created with the expected license type
        provider_records = self.config.data_client.get_provider(compact=TEST_COMPACT, provider_id=TEST_PROVIDER_ID)
        privilege_record = next(record for record in provider_records['items'] if record['type'] == 'privilege')

        self.assertEqual(TEST_LICENSE_TYPE, privilege_record['licenseType'])

    @patch('handlers.privileges.PurchaseClient')
    def test_post_purchase_privileges_validates_investigation_attestations(self, mock_purchase_client_constructor):
        """Test that exactly one investigation attestation must be provided."""
        from handlers.privileges import post_purchase_privileges

        self._when_purchase_client_successfully_processes_request(mock_purchase_client_constructor)

        event = self._when_testing_provider_user_event_with_custom_claims()

        # Test with no investigation attestation
        mock_attestation_list_copy = generate_default_attestation_list()
        mock_attestation_list_copy.remove({'attestationId': 'not-under-investigation-attestation', 'version': '1'})
        event['body'] = _generate_test_request_body(attestations=mock_attestation_list_copy)
        resp = post_purchase_privileges(event, self.mock_context)
        self.assertEqual(400, resp['statusCode'])
        self.assertIn('Exactly one investigation attestation must be provided', json.loads(resp['body'])['message'])

        # Test with both investigation attestations
        attestations = [
            {'attestationId': 'not-under-investigation-attestation', 'version': '1'},
            {'attestationId': 'under-investigation-attestation', 'version': '1'},
        ]
        event['body'] = _generate_test_request_body(attestations=attestations)
        resp = post_purchase_privileges(event, self.mock_context)
        self.assertEqual(400, resp['statusCode'])
        self.assertIn('Exactly one investigation attestation must be provided', json.loads(resp['body'])['message'])

    @patch('handlers.privileges.PurchaseClient')
    def test_post_purchase_privileges_validates_military_attestation(self, mock_purchase_client_constructor):
        """Test that military attestation is required when user has active military affiliation."""
        from handlers.privileges import post_purchase_privileges

        self._when_purchase_client_successfully_processes_request(mock_purchase_client_constructor)
        self._load_military_affiliation_record_data(status='active')

        event = self._when_testing_provider_user_event_with_custom_claims()
        event['body'] = _generate_test_request_body()

        resp = post_purchase_privileges(event, self.mock_context)
        self.assertEqual(400, resp['statusCode'], resp['body'])
        self.assertIn('military-affiliation-confirmation-attestation', json.loads(resp['body'])['message'])

        # Add military attestation and verify it works
        event_body = json.loads(event['body'])
        event_body['attestations'].append(
            {'attestationId': 'military-affiliation-confirmation-attestation', 'version': '1'}
        )
        event['body'] = json.dumps(event_body)

        resp = post_purchase_privileges(event, self.mock_context)
        self.assertEqual(200, resp['statusCode'], resp['body'])
