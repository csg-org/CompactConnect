from io import TextIOWrapper
from uuid import uuid4

from moto import mock_aws
from tests.function import TstFunction


@mock_aws
class TestCSVParser(TstFunction):
    def test_csv_parser(self):
        from config import logger

        from license_csv_reader import LicenseCSVReader

        # Upload our test file to mocked 'S3' then retrieve it so we can specifically
        # test our reader's ability to process data from boto3's StreamingBody
        key = f'/co/{uuid4().hex}'
        self._bucket.upload_file('tests/resources/licenses.csv', key)
        stream = TextIOWrapper(self._bucket.Object(key).get()['Body'])

        reader = LicenseCSVReader()
        for license_row in reader.validated_licenses(stream):
            logger.debug('Read validated license', license=reader.schema.dump(license_row))
