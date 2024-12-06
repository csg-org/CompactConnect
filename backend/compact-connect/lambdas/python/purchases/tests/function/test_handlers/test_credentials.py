import json
from unittest.mock import MagicMock, patch

from cc_common.exceptions import CCInvalidRequestException
from moto import mock_aws

from .. import TstFunction

TEST_COMPACT = 'aslp'
# this value is defined in the provider.json file
TEST_PROVIDER_ID = '89a6377e-c3a5-40e5-bca5-317ec854c570'

MOCK_LOGIN_ID = '1234'
MOCK_TRANSACTION_KEY = '5678'


def _generate_test_request_body():
    return json.dumps(
        {
            'processor': 'authorize.net',
            'apiLoginId': MOCK_LOGIN_ID,
            'transactionKey': MOCK_TRANSACTION_KEY,
        }
    )


@mock_aws
class TestPostPaymentProcessorCredentials(TstFunction):
    def _when_testing_compact_admin_user(self):
        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)
            event['pathParameters'] = {'compact': TEST_COMPACT}
            # user is a compact admin with admin scoped permissions
            event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/admin aslp/aslp.admin'
            event['body'] = _generate_test_request_body()

        return event

    def _when_testing_jurisdiction_admin_user(self):
        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)
            event['pathParameters'] = {'compact': TEST_COMPACT}
            # user is an admin with jurisdiction scoped permissions
            event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/admin aslp/oh.admin'
            event['body'] = _generate_test_request_body()

        return event

    def _when_purchase_client_successfully_verifies_credentials(self, mock_purchase_client_constructor):
        mock_purchase_client = MagicMock()
        mock_purchase_client_constructor.return_value = mock_purchase_client
        mock_purchase_client.validate_and_store_credentials.return_value = {
            'message': 'Successfully verified credentials'
        }

        return mock_purchase_client

    def _when_purchase_client_raises_exception(self, mock_purchase_client_constructor):
        mock_purchase_client = MagicMock()
        mock_purchase_client_constructor.return_value = mock_purchase_client
        mock_purchase_client.validate_and_store_credentials.side_effect = CCInvalidRequestException(
            # actual error code and error message from the authorize.net client
            'Failed to verify credentials. Error code: E00124, Error message: ' 'The provided access token is invalid'
        )

        return mock_purchase_client

    @patch('handlers.credentials.PurchaseClient')
    def test_post_payment_processor_credentials_calls_purchase_client_with_expected_parameters(
        self, mock_purchase_client_constructor
    ):
        mock_purchase_client = self._when_purchase_client_successfully_verifies_credentials(
            mock_purchase_client_constructor
        )
        from handlers.credentials import post_payment_processor_credentials

        event = self._when_testing_compact_admin_user()

        resp = post_payment_processor_credentials(event, self.mock_context)
        self.assertEqual(200, resp['statusCode'])

        purchase_client_call_kwargs = mock_purchase_client.validate_and_store_credentials.call_args.kwargs

        self.assertEqual(TEST_COMPACT, purchase_client_call_kwargs['compact_name'])
        self.assertEqual(json.loads(event['body']), purchase_client_call_kwargs['credentials'])

    @patch('handlers.credentials.PurchaseClient')
    def test_post_payment_processor_credentials_returns_exception_message_if_credentials_invalid(
        self, mock_purchase_client_constructor
    ):
        from handlers.credentials import post_payment_processor_credentials

        self._when_purchase_client_raises_exception(mock_purchase_client_constructor)

        event = self._when_testing_compact_admin_user()

        resp = post_payment_processor_credentials(event, self.mock_context)
        self.assertEqual(400, resp['statusCode'])
        response_body = json.loads(resp['body'])

        self.assertEqual(
            {
                'message': 'Failed to verify credentials. Error code: E00124, Error message: '
                'The provided access token is invalid'
            },
            response_body,
        )

    @patch('handlers.credentials.PurchaseClient')
    def test_post_payment_processor_credentials_returns_unauthorized_for_jurisdiction_admins(
        self, mock_purchase_client_constructor
    ):
        from handlers.credentials import post_payment_processor_credentials

        # if authorization fails, the PurchaseClient will not be called
        mock_purchase_client = self._when_purchase_client_successfully_verifies_credentials(
            mock_purchase_client_constructor
        )

        event = self._when_testing_jurisdiction_admin_user()

        resp = post_payment_processor_credentials(event, self.mock_context)
        self.assertEqual(403, resp['statusCode'])
        response_body = json.loads(resp['body'])

        self.assertEqual(
            {'message': 'Access denied'},
            response_body,
        )

        mock_purchase_client.validate_and_store_credentials.assert_not_called()
