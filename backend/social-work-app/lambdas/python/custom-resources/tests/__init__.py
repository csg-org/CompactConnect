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
                'DEBUG': 'false',
                'AWS_DEFAULT_REGION': 'us-east-1',
                'COMPACTS': '["cosm"]',
                'JURISDICTIONS': '["oh", "ky", "ne"]',
                'COMPACT_CONFIGURATION_TABLE_NAME': 'compact-configuration-table',
                'ENVIRONMENT_NAME': 'test',
            },
        )
        # Monkey-patch config object to be sure we have it based
        # on the env vars we set above
        import cc_common.config

        cls.config = cc_common.config._Config()  # noqa: SLF001 protected-access
        cc_common.config.config = cls.config
        cls.mock_context = MagicMock(name='MockLambdaContext', spec=LambdaContext)
