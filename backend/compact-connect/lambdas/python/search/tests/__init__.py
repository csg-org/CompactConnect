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
                'AWS_REGION': 'us-east-1',
                'ENVIRONMENT_NAME': 'test',
                'COMPACTS': '["aslp", "octp", "coun"]',
                'PROVIDER_TABLE_NAME': 'provider-table',
                'PROV_DATE_OF_UPDATE_INDEX_NAME': 'providerDateOfUpdate',
                'PROV_FAM_GIV_MID_INDEX_NAME': 'providerFamGivMid',
                'LICENSE_GSI_NAME': 'licenseGSI',
                'LICENSE_UPLOAD_DATE_INDEX_NAME': 'licenseUploadDateGSI',
                'OPENSEARCH_HOST_ENDPOINT': 'vpc-providersearchd-5bzuqxhpxffk-w6dkpddu.us-east-1.es.amazonaws.com',
                'EXPORT_RESULTS_BUCKET_NAME': 'test-export-results-bucket',
                'JURISDICTIONS': json.dumps(
                    [
                        'al',
                        'ak',
                        'az',
                        'ar',
                        'ca',
                        'co',
                        'ct',
                        'de',
                        'dc',
                        'fl',
                        'ga',
                        'hi',
                        'id',
                        'il',
                        'in',
                        'ia',
                        'ks',
                        'ky',
                        'la',
                        'me',
                        'md',
                        'ma',
                        'mi',
                        'mn',
                        'ms',
                        'mo',
                        'mt',
                        'ne',
                        'nv',
                        'nh',
                        'nj',
                        'nm',
                        'ny',
                        'nc',
                        'nd',
                        'oh',
                        'ok',
                        'or',
                        'pa',
                        'pr',
                        'ri',
                        'sc',
                        'sd',
                        'tn',
                        'tx',
                        'ut',
                        'vt',
                        'va',
                        'vi',
                        'wa',
                        'wv',
                        'wi',
                        'wy',
                    ]
                ),
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
        import cc_common.config

        cls.config = cc_common.config._Config()  # noqa: SLF001 protected-access
        cc_common.config.config = cls.config
        cls.mock_context = MagicMock(name='MockLambdaContext', spec=LambdaContext)
