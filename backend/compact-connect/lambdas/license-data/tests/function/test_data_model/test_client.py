import json

from moto import mock_aws
from tests.function import TstFunction


@mock_aws
class TestClient(TstFunction):
    def test_get_ssn(self):
        from data_model.client import DataClient

        with open('tests/resources/license.json', 'r') as f:
            license_data = json.load(f)

        self._table.put_item(
            Item={
                'pk': '123-123-1234',
                'sk': 'aslp/co/license-home',
                'type': 'license-home',
                'birth_month_day': '06-06',
                'date_of_update': '2024-06-27',
                **license_data
            }
        )

        with open('tests/resources/privilege.json', 'r') as f:
            privilege = json.load(f)

        self._table.put_item(
            Item={
                'pk': '123-123-1234',
                'sk': 'aslp/fl/license-privilege',
                'type': 'license-privilege',
                'birth_month_day': '06-06',
                'date_of_update': '2024-06-27',
                **privilege
            }
        )

        client = DataClient(self.config)

        resp = client.get_ssn(ssn='123-123-1234')  # pylint: disable=missing-kwoa
        self.assertEqual(2, len(resp['items']))
