from tests import TstLambdas


class TestCSVParser(TstLambdas):
    def test_csv_parser(self):
        from cc_common.config import logger
        from cc_common.data_model.schema.license.api import LicensePostRequestSchema
        from license_csv_reader import LicenseCSVReader

        schema = LicensePostRequestSchema()
        with open('../common/tests/resources/licenses.csv') as f:
            reader = LicenseCSVReader()
            for license_row in reader.licenses(f):
                validated = schema.load({'compact': 'aslp', 'jurisdiction': 'oh', **license_row})
                logger.debug('Read validated license', license_data=reader.schema.dump(validated))
