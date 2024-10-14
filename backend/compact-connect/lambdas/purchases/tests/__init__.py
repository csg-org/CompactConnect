import json
import os
from unittest import TestCase
from unittest.mock import MagicMock

from aws_lambda_powertools.utilities.typing import LambdaContext


class TstLambdas(TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.update({
            # Set to 'true' to enable debug logging
            'DEBUG': 'false',
            'AWS_DEFAULT_REGION': 'us-east-1',
            'COMPACT_CONFIGURATION_TABLE_NAME': 'compact-configuration-table',
            'COMPACTS': '["aslp", "octp", "coun"]',
            'JURISDICTIONS': '["ne", "oh", "ky"]',
        })
        # Monkey-patch config object to be sure we have it based
        # on the env vars we set above
        import config
        cls.config = config._Config()  # pylint: disable=protected-access
        config.config = cls.config
        cls.mock_context = MagicMock(name='MockLambdaContext', spec=LambdaContext)
