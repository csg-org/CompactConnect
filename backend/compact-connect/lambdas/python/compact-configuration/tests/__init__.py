import json
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
                'ALLOWED_ORIGINS': '["https://example.org"]',
                'AWS_DEFAULT_REGION': 'us-east-1',
                'COMPACT_CONFIGURATION_TABLE_NAME': 'compact-configuration-table',
                'COMPACTS': '["aslp", "octp", "coun"]',
                'JURISDICTIONS': '["ne", "oh", "ky"]',
                'ENVIRONMENT_NAME': 'test',
                'LICENSE_TYPES': json.dumps(
                    {
                        'aslp': [
                            {'name': 'audiologist', 'abbreviation': 'aud'},
                            {'name': 'speech-language pathologist', 'abbreviation': 'slp'},
                        ],
                        'octp': [
                            {'name': 'occupational therapist', 'abbreviation': 'ot'},
                            {'name': 'occupational therapy assistant', 'abbreviation': 'ota'},
                        ],
                        'coun': [{'name': 'licensed professional counselor', 'abbreviation': 'lpc'}],
                    },
                ),
            },
        )
        # Monkey-patch config object to be sure we have it based
        # on the env vars we set above
        from cc_common import config

        cls.config = config._Config()  # noqa: SLF001 protected-access
        config.config = cls.config
        cls.mock_context = MagicMock(name='MockLambdaContext', spec=LambdaContext)
