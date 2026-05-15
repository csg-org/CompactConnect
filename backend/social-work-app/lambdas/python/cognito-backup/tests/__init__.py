import logging
import os
from unittest import TestCase
from unittest.mock import MagicMock

logger = logging.getLogger(__name__)
logging.basicConfig()
logger.setLevel(logging.DEBUG if os.environ.get('DEBUG', 'false') == 'true' else logging.INFO)


class TstLambdas(TestCase):
    """Base test class for Cognito backup lambda tests."""

    @classmethod
    def setUpClass(cls):
        os.environ.update(
            {
                # Set to 'true' to enable debug logging
                'DEBUG': 'true',
                'AWS_DEFAULT_REGION': 'us-east-1',
                'ENVIRONMENT_NAME': 'test',
            },
        )

        cls.mock_context = MagicMock(name='MockLambdaContext')
        cls.mock_context.aws_request_id = 'test-request-id'
