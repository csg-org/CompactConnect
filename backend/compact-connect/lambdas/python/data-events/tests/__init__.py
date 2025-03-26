import os
from unittest import TestCase
from unittest.mock import MagicMock

from aws_lambda_powertools.utilities.typing import LambdaContext


class TstLambdas(TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.update(
            {
                # Set to 'true' to enable debug logging
                'DEBUG': 'true',
                'AWS_DEFAULT_REGION': 'us-east-1',
                'DATA_EVENT_TABLE_NAME': 'data-event-table',
                'COMPACTS': '["aslp", "octp", "coun"]',
                'JURISDICTIONS': '["ne", "oh", "ky"]',
                'ENVIRONMENT_NAME': 'test',
            },
        )
        # Monkey-patch config object to be sure we have it based
        # on the env vars we set above
        from cc_common import config

        cls.config = config._Config()  # noqa: SLF001 protected-access
        config.config = cls.config
        cls.mock_context = MagicMock(name='MockLambdaContext', spec=LambdaContext)
