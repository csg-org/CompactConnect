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
            'BULK_BUCKET_NAME': 'cc-license-data-bulk-bucket',
            'EVENT_BUS_NAME': 'license-data-events',
            'LICENSE_TABLE_NAME': 'license-table',
            'SSN_INDEX_NAME': 'ssn',
            'CJ_NAME_INDEX_NAME': 'cj_name',
            'CJ_UPDATED_INDEX_NAME': 'cj_updated',
            'COMPACTS': '["aslp", "octp", "coun"]',
            'JURISDICTIONS': '["al", "co"]',
            'LICENSE_TYPES': json.dumps({
                'aslp': [
                    "audiologist",
                    "speech-language pathologist",
                    "speech and language pathologist"
                ]
            })
        })
        # Monkey-patch config object to be sure we have it based
        # on the env vars we set above
        import config
        cls.config = config._Config()  # pylint: disable=protected-access
        config.config = cls.config
        cls.mock_context = MagicMock(name='MockLambdaContext', spec=LambdaContext)
