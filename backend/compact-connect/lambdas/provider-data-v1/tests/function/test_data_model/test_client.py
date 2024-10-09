import json

from moto import mock_aws
from tests.function import TstFunction


@mock_aws
class TestClient(TstFunction):
    def test_get_provider_id(self):
        from data_model.client import DataClient

        with open('tests/resources/dynamo/provider-ssn.json', 'r') as f:
            record = json.load(f)
        provider_ssn = record['ssn']
        expected_provider_id = record['providerId']

        self._provider_table.put_item(
            # We'll use the schema/serializer to populate index fields for us
            Item=record
        )

        client = DataClient(self.config)

        resp = client.get_provider_id(compact='aslp', ssn=provider_ssn)  # pylint: disable=unexpected-keyword-arg
        # Verify that we're getting the expected provider ID
        self.assertEqual(expected_provider_id, resp)

    def test_get_provider_id_not_found(self):
        """
        Provider ID not found should raise an exception
        """
        from data_model.client import DataClient
        from exceptions import CCNotFoundException

        client = DataClient(self.config)

        # This SSN isn't in the DB, so it should raise an exception
        with self.assertRaises(CCNotFoundException):
            client.get_provider_id(compact='aslp', ssn='321-21-4321')  # pylint: disable=unexpected-keyword-arg

    def test_get_provider(self):
        from data_model.client import DataClient

        provider_id = self._load_provider_data()

        client = DataClient(self.config)

        resp = client.get_provider(  # pylint: disable=missing-kwoa,unexpected-keyword-arg
            compact='aslp',
            provider_id=provider_id
        )
        self.assertEqual(3, len(resp['items']))
        # Should be one each of provider, license, privilege
        self.assertEqual({'provider', 'license', 'privilege'}, {record['type'] for record in resp['items']})

    def test_get_provider_garbage_in_db(self):
        """
        Because of the risk of exposing sensitive data to the public if we manage to get corrupted
        data into our database, we'll specifically validate data coming _out_ of the database
        and throw an error if it doesn't look as expected.
        """
        from data_model.client import DataClient
        from exceptions import CCInternalException

        provider_id = self._load_provider_data()

        with open('tests/resources/dynamo/license.json', 'r') as f:
            license_record = json.load(f)

        self._provider_table.put_item(
            Item={
                # Oh, no! We've somehow put somebody's SSN in the wrong place!
                'something_unexpected': '123-12-1234',
                **license_record
            }
        )

        client = DataClient(self.config)

        # This record should not be allowed out via API
        with self.assertRaises(CCInternalException):
            client.get_provider(  # pylint: disable=missing-kwoa,unexpected-keyword-arg
                compact='aslp',
                provider_id=provider_id
            )

    def test_get_licenses_sorted_by_family_name(self):
        from data_model.client import DataClient

        self._generate_providers(home='oh', privilege='ne', start_serial=9999)
        self._generate_providers(home='ne', privilege='oh', start_serial=9989)
        self._generate_providers(home='ne', privilege='co', start_serial=9979)
        client = DataClient(self.config)

        # We expect to see 20 providers: 10 have privileges in oh, 10 have licenses in oh
        resp = client.get_providers_sorted_by_family_name(  # pylint: disable=unexpected-keyword-arg,missing-kwoa
            compact='aslp',
            jurisdiction='oh',
            pagination={
                'pageSize': 10
            }
        )
        first_provider_ids = {item['providerId'] for item in resp['items']}
        first_items = resp['items']
        self.assertEqual(10, len(resp['items']))
        self.assertIsInstance(resp['pagination']['lastKey'], str)

        last_key = resp['pagination']['lastKey']
        resp = client.get_providers_sorted_by_family_name(  # pylint: disable=unexpected-keyword-arg,missing-kwoa
            compact='aslp',
            jurisdiction='oh',
            pagination={'lastKey': last_key, 'pageSize': 100}
        )
        self.assertEqual(10, len(resp['items']))
        self.assertIsNone(resp['pagination']['lastKey'])

        second_provider_ids = {item['providerId'] for item in resp['items']}
        # Verify that there are no repeat items between the two calls
        self.assertFalse(first_provider_ids & second_provider_ids)

        # Verify sorting by family name (without getting into how duplicate family names are sorted)
        all_items = [*first_items, *resp['items']]
        family_names = [item['familyName'] for item in all_items]
        self.assertListEqual(sorted(family_names), family_names)

    def test_get_licenses_sorted_by_family_name_descending(self):
        from data_model.client import DataClient

        self._generate_providers(home='oh', privilege='ne', start_serial=9999)
        client = DataClient(self.config)

        resp = client.get_providers_sorted_by_family_name(  # pylint: disable=missing-kwoa
            compact='aslp',
            jurisdiction='oh',
            scan_forward=False
        )
        self.assertEqual(10, len(resp['items']))

        # Verify sorting by family name (without getting into how duplicate family names are sorted)
        family_names = [item['familyName'] for item in resp['items']]
        self.assertListEqual(sorted(family_names, reverse=True), family_names)

    def test_get_licenses_sorted_by_date_updated(self):
        from data_model.client import DataClient

        self._generate_providers(home='oh', privilege='ne', start_serial=9999)
        self._generate_providers(home='ne', privilege='oh', start_serial=9989)
        self._generate_providers(home='ne', privilege='ky', start_serial=9979)
        client = DataClient(self.config)

        # We expect to see 20 providers: 10 have privileges in oh, 10 have licenses in oh
        resp = client.get_providers_sorted_by_updated(  # pylint: disable=unexpected-keyword-arg,missing-kwoa
            compact='aslp',
            jurisdiction='oh',
            pagination={
                'pageSize': 10
            }
        )
        first_provider_ids = {item['providerId'] for item in resp['items']}
        first_provider_items = resp['items']
        self.assertEqual(10, len(resp['items']))
        self.assertIsInstance(resp['pagination']['lastKey'], str)

        last_key = resp['pagination']['lastKey']
        resp = client.get_providers_sorted_by_updated(  # pylint: disable=unexpected-keyword-arg,missing-kwoa
            compact='aslp',
            jurisdiction='oh',
            pagination={'lastKey': last_key, 'pageSize': 10}
        )
        self.assertEqual(10, len(resp['items']))
        self.assertIsNone(resp['pagination']['lastKey'])

        second_provider_ids = {item['providerId'] for item in resp['items']}
        # Verify that there are no repeat items between the two calls
        self.assertFalse(first_provider_ids & second_provider_ids)

        all_items = [*first_provider_items, *resp['items']]
        # Verify sorting by dateOfUpdate
        dates_of_update = [item['dateOfUpdate'] for item in all_items]
        self.assertListEqual(sorted(dates_of_update), dates_of_update)

    def test_get_licenses_sorted_by_date_of_update_descending(self):
        from data_model.client import DataClient

        self._generate_providers(home='oh', privilege='ne', start_serial=9999)
        client = DataClient(self.config)

        resp = client.get_providers_sorted_by_updated(  # pylint: disable=missing-kwoa
            compact='aslp',
            jurisdiction='oh',
            scan_forward=False
        )
        self.assertEqual(10, len(resp['items']))

        # Verify sorting by dateOfUpdate
        dates_of_update = [item['dateOfUpdate'] for item in resp['items']]
        self.assertListEqual(sorted(dates_of_update, reverse=True), dates_of_update)

    def _load_provider_data(self) -> str:
        with open('tests/resources/dynamo/provider.json', 'r') as f:
            provider_record = json.load(f)
        provider_id = provider_record['providerId']
        provider_record['privilegeJurisdictions'] = set(provider_record['privilegeJurisdictions'])
        self._provider_table.put_item(Item=provider_record)

        with open('tests/resources/dynamo/privilege.json', 'r') as f:
            privilege_record = json.load(f)
        self._provider_table.put_item(Item=privilege_record)

        with open('tests/resources/dynamo/license.json', 'r') as f:
            license_record = json.load(f)
        self._provider_table.put_item(Item=license_record)

        return provider_id
