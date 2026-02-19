from cc_common.config import logger

from tests import TstLambdas


class TestEmailServiceClient(TstLambdas):
    def _generate_test_model(self, mock_lambda_client):
        from cc_common.email_service_client import EmailServiceClient

        mock_lambda_client.invoke.return_value = {
            'StatusCode': 200,
            'LogResult': 'string',
            'Payload': '{"message": "Email message sent"}',
            'ExecutedVersion': '1',
        }

        return EmailServiceClient(
            lambda_client=mock_lambda_client, email_notification_service_lambda_name='test-lambda-name', logger=logger
        )
