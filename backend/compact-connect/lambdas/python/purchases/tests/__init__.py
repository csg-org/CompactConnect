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
                'DEBUG': 'false',
                'ALLOWED_ORIGINS': '["https://example.org"]',
                'AWS_DEFAULT_REGION': 'us-east-1',
                'COMPACT_CONFIGURATION_TABLE_NAME': 'compact-configuration-table',
                'TRANSACTION_HISTORY_TABLE_NAME': 'transaction-history-table',
                'TRANSACTION_REPORTS_BUCKET_NAME': 'transaction-report-bucket',
                'EMAIL_NOTIFICATION_SERVICE_LAMBDA_NAME': 'email-notification-service',
                'COMPACTS': '["aslp", "octp", "coun"]',
                'JURISDICTIONS': '["ne", "oh", "ky"]',
                'ENVIRONMENT_NAME': 'test',
                'PROVIDER_TABLE_NAME': 'provider-table',
                'PROV_FAM_GIV_MID_INDEX_NAME': 'providerFamGivMid',
                'PROV_DATE_OF_UPDATE_INDEX_NAME': 'providerDateOfUpdate',
                'LICENSE_TYPES': json.dumps(
                    {'aslp': ['audiologist', 'speech-language pathologist', 'speech and language pathologist']},
                ),
            },
        )
        # Monkey-patch config object to be sure we have it based
        # on the env vars we set above
        import cc_common.config

        cls.config = cc_common.config._Config()  # noqa: SLF001 protected-access
        cc_common.config.config = cls.config
        cls.mock_context = MagicMock(name='MockLambdaContext', spec=LambdaContext)
