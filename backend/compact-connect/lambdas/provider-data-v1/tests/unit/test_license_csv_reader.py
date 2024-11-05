from tests import TstLambdas


class TestCSVParser(TstLambdas):
    def test_csv_parser(self):
        from common.config import logger
        from common.data_model.schema.license import LicensePostSchema
        from license_csv_reader import LicenseCSVReader

        schema = LicensePostSchema()
        with open('tests/resources/licenses.csv') as f:
            reader = LicenseCSVReader()
            for license_row in reader.licenses(f):
                validated = schema.load({'compact': 'aslp', 'jurisdiction': 'oh', **license_row})
                logger.debug('Read validated license', license_data=reader.schema.dump(validated))
