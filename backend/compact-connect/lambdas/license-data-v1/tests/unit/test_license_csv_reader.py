from tests import TstLambdas


class TestCSVParser(TstLambdas):
    def test_csv_parser(self):
        from config import logger

        from data_model.schema.license import LicensePostSchema
        from license_csv_reader import LicenseCSVReader

        schema = LicensePostSchema()
        with open('tests/resources/licenses.csv', 'r') as f:
            reader = LicenseCSVReader()
            for license_row in reader.licenses(f):
                validated = schema.load({
                    'compact': 'aslp',
                    'jurisdiction': 'al',
                    **license_row
                })
                logger.debug('Read validated license', license_data=reader.schema.dump(validated))
