from io import StringIO

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
                validated = schema.load({'compact': 'cosm', 'jurisdiction': 'oh', **license_row})
                logger.debug('Read validated license', license_data=reader.schema.dump(validated))

    def test_csv_parser_treats_a_blank_ssn_column_as_omitted(self):
        """
        A state uploading without SSNs will most often leave the ssn column present but empty. The reader
        drops blank values, so such a row must validate as an SSN-less upload rather than failing on a
        malformed SSN.
        """
        from cc_common.data_model.schema.license.api import LicensePostRequestSchema
        from license_csv_reader import LicenseCSVReader

        with open('../common/tests/resources/licenses.csv') as f:
            lines = f.read().splitlines()
        header_fields = lines[0].split(',')
        ssn_index = header_fields.index('ssn')
        row_fields = lines[1].split(',')
        row_fields[ssn_index] = ''

        stream = StringIO('\n'.join([lines[0], ','.join(row_fields)]) + '\n')

        rows = list(LicenseCSVReader().licenses(stream))

        self.assertEqual(1, len(rows))
        self.assertNotIn('ssn', rows[0])

        validated = LicensePostRequestSchema().load({'compact': 'cosm', 'jurisdiction': 'oh', **rows[0]})

        self.assertNotIn('ssn', validated)
        self.assertEqual('A0608337260', validated['licenseNumber'])
