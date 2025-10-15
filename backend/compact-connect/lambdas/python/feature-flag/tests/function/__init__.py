import logging
import os

from moto import mock_aws

from tests import TstLambdas

logger = logging.getLogger(__name__)
logging.basicConfig()
logger.setLevel(logging.DEBUG if os.environ.get('DEBUG', 'false') == 'true' else logging.INFO)


@mock_aws
class TstFunction(TstLambdas):
    """Base class to set up Moto mocking and create mock AWS resources for functional testing"""

    def setUp(self):  # noqa: N801 invalid-name
        super().setUp()
        # This must be imported within the tests, since they import modules which require
        # environment variables that are not set until the TstLambdas class is initialized
        from common_test.test_data_generator import TestDataGenerator

        self.test_data_generator = TestDataGenerator
