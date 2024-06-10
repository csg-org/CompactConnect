from tests import TstLambdas


class TestCSVParser(TstLambdas):
    def test_csv_parser(self):
        from config import logger

        from license_csv_reader import LicenseCSVReader

        with open('tests/resources/licenses.csv', 'r') as f:
            reader = LicenseCSVReader()
            for license_row in reader.validated_licenses(f):
                logger.debug('Read validated license', license=reader.schema.dump(license_row))
