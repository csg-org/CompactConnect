import json
from datetime import UTC, date, datetime
from unittest.mock import MagicMock, patch

from config import config
from exceptions import CCFailedTransactionException, CCAwsServiceException, CCInternalException
from moto import mock_aws

from tests.function import TstFunction

TEST_COMPACT = 'aslp'
# this value is defined in the provider.json file
TEST_PROVIDER_ID = '89a6377e-c3a5-40e5-bca5-317ec854c570'

MOCK_TRANSACTION_ID = '1234'


def _generate_test_request_body(selected_jurisdictions: list[str] = None):
    if not selected_jurisdictions:
        selected_jurisdictions = ['oh']

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
        }
    )


@mock_aws
class TestPostPurchasePrivileges(TstFunction):
    def _when_testing_provider_user_event_with_custom_claims(self, test_compact=TEST_COMPACT, load_license=True):
        self._load_compact_configuration_data()
        self._load_provider_data()
        if load_license:
            self._load_license_data()
        with open('tests/resources/api-event.json') as f:
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
            ['oh'],
            [
                jurisdiction.postal_abbreviation
                for jurisdiction in purchase_client_call_kwargs['selected_jurisdictions']
            ],
        )
        self.assertEqual(False, purchase_client_call_kwargs['user_active_military'])

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

        self.assertEqual({'message': 'Invalid jurisdiction postal code'}, response_body)

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
    def test_post_purchase_privileges_returns_404_if_license_not_found(self, mock_purchase_client_constructor):
        from handlers.privileges import post_purchase_privileges

        self._when_purchase_client_successfully_processes_request(mock_purchase_client_constructor)

        event = self._when_testing_provider_user_event_with_custom_claims(load_license=False)
        event['body'] = _generate_test_request_body()

        resp = post_purchase_privileges(event, self.mock_context)
        self.assertEqual(404, resp['statusCode'])
        response_body = json.loads(resp['body'])

        self.assertEqual({'message': 'License record not found for this user'}, response_body)

    @patch('handlers.privileges.PurchaseClient')
    def test_post_purchase_privileges_adds_privilege_record_if_transaction_successful(
        self, mock_purchase_client_constructor
    ):
        from handlers.privileges import post_purchase_privileges

        self._when_purchase_client_successfully_processes_request(mock_purchase_client_constructor)

        event = self._when_testing_provider_user_event_with_custom_claims()
        event['body'] = _generate_test_request_body()

        resp = post_purchase_privileges(event, self.mock_context)
        self.assertEqual(200, resp['statusCode'])

        # check that the privilege record for oh was created
        provider_records = self.config.data_client.get_provider(compact=TEST_COMPACT, provider_id=TEST_PROVIDER_ID)

        privilege_record = next(record for record in provider_records['items'] if record['type'] == 'privilege')
        license_record = next(record for record in provider_records['items'] if record['type'] == 'license')

        # make sure the expiration on the license matches the expiration on the privilege
        expected_expiration_date = date(2024, 6, 6)
        self.assertEqual(expected_expiration_date, license_record['dateOfExpiration'])
        self.assertEqual(expected_expiration_date, privilege_record['dateOfExpiration'])
        # the date of issuance should be today
        self.assertEqual(datetime.now(tz=UTC).date(), privilege_record['dateOfIssuance'])
        self.assertEqual(datetime.now(tz=UTC).date(), privilege_record['dateOfUpdate'])
        self.assertEqual(TEST_COMPACT, privilege_record['compact'])
        self.assertEqual('oh', privilege_record['jurisdiction'])
        self.assertEqual(TEST_PROVIDER_ID, str(privilege_record['providerId']))
        self.assertEqual('active', privilege_record['status'])
        self.assertEqual('privilege', privilege_record['type'])
        # make sure we are tracking the transaction id
        self.assertEqual(MOCK_TRANSACTION_ID, privilege_record['compactTransactionId'])


    @patch('handlers.privileges.PurchaseClient')
    @patch('handlers.privileges.config.data_client')
    def test_post_purchase_privileges_voids_transaction_if_aws_error_occurs(
        self, mock_data_client, mock_purchase_client_constructor
    ):
        from handlers.privileges import post_purchase_privileges

        mock_purchase_client = (
            self._when_purchase_client_successfully_processes_request(mock_purchase_client_constructor))
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
