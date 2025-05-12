import json

from marshmallow import ValidationError
from tests import TstLambdas


class TestMilitaryAffiliationRecordSchema(TstLambdas):
    def test_serde(self):
        """Test round-trip deserialization/serialization"""
        from cc_common.data_model.schema.military_affiliation.record import MilitaryAffiliationRecordSchema

        with open('tests/resources/dynamo/military-affiliation.json') as f:
            expected_military_affiliation = json.load(f)

        schema = MilitaryAffiliationRecordSchema()
        loaded_schema = schema.load(expected_military_affiliation.copy())

        military_affiliation_data = schema.dump(loaded_schema)

        # remove dynamic update fields
        military_affiliation_data.pop('dateOfUpdate')
        expected_military_affiliation.pop('dateOfUpdate')

        self.assertEqual(expected_military_affiliation, military_affiliation_data)

    def test_invalid(self):
        from cc_common.data_model.schema.military_affiliation.record import MilitaryAffiliationRecordSchema

        with open('tests/resources/dynamo/military-affiliation.json') as f:
            military_affiliation_data = json.load(f)
        military_affiliation_data.pop('providerId')

        with self.assertRaises(ValidationError):
            MilitaryAffiliationRecordSchema().load(military_affiliation_data)
