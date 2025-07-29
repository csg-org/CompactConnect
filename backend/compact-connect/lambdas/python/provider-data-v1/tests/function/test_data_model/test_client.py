import json
from urllib.parse import quote

from moto import mock_aws

from .. import TstFunction


@mock_aws
class TestClient(TstFunction):
    def test_get_providers_sorted_by_family_name(self):
        from cc_common.data_model.data_client import DataClient

        self._generate_providers(home='oh', privilege_jurisdiction='ne', start_serial=9999)
        self._generate_providers(home='ne', privilege_jurisdiction='oh', start_serial=9989)
        self._generate_providers(home='ne', privilege_jurisdiction='co', start_serial=9979)
        client = DataClient(self.config)

        # We expect to see 20 providers: 10 have privileges in oh, 10 have licenses in oh
        resp = client.get_providers_sorted_by_family_name(
            compact='aslp',
            jurisdiction='oh',
            pagination={'pageSize': 10},
        )
        first_provider_ids = {item['providerId'] for item in resp['items']}
        first_items = resp['items']
        self.assertEqual(10, len(resp['items']))
        self.assertIsInstance(resp['pagination']['lastKey'], str)

        last_key = resp['pagination']['lastKey']
        resp = client.get_providers_sorted_by_family_name(
            compact='aslp',
            jurisdiction='oh',
            pagination={'lastKey': last_key, 'pageSize': 100},
        )
        self.assertEqual(10, len(resp['items']))
        self.assertIsNone(resp['pagination']['lastKey'])

        second_provider_ids = {item['providerId'] for item in resp['items']}
        # Verify that there are no repeat items between the two calls
        self.assertFalse(first_provider_ids & second_provider_ids)

        # Verify sorting by family name (without getting into how duplicate family names are sorted)
        all_items = [*first_items, *resp['items']]
        family_names = [item['familyName'].lower() for item in all_items]
        self.assertListEqual(sorted(family_names, key=quote), family_names)

    def test_get_providers_sorted_by_family_name_descending(self):
        from cc_common.data_model.data_client import DataClient

        self._generate_providers(home='oh', privilege_jurisdiction='ne', start_serial=9999)
        client = DataClient(self.config)

        resp = client.get_providers_sorted_by_family_name(
            compact='aslp',
            jurisdiction='oh',
            scan_forward=False,
        )
        self.assertEqual(10, len(resp['items']))

        # Verify sorting by family name (without getting into how duplicate family names are sorted)
        family_names = [item['familyName'].lower() for item in resp['items']]
        self.assertListEqual(sorted(family_names, key=quote, reverse=True), family_names)

    def test_get_providers_by_family_name(self):
        from cc_common.data_model.data_client import DataClient

        # We'll provide names, so we know we'll have one record for our friends, Tess and Ted Testerly
        self._generate_providers(
            home='oh',
            privilege_jurisdiction='ne',
            start_serial=9999,
            names=(
                ('Testerly', 'Tess'),
                ('Testerly', 'Ted'),
            ),
        )
        client = DataClient(self.config)

        resp = client.get_providers_sorted_by_family_name(
            compact='aslp',
            jurisdiction='oh',
            provider_name=('Testerly', None),
            scan_forward=False,
        )

        self.assertEqual(2, len(resp['items']))
        # Make sure both our providers have the expected familyName
        for provider in resp['items']:
            self.assertEqual('Testerly', provider['familyName'])

    def test_get_providers_by_family_and_given_name(self):
        from cc_common.data_model.data_client import DataClient

        # We'll provide names, so we know we'll have one record for our friends, Tess and Ted Testerly
        self._generate_providers(
            home='oh',
            privilege_jurisdiction='ne',
            start_serial=9999,
            names=(
                ('Testerly', 'Tess'),
                ('Testerly', 'Ted'),
            ),
        )
        client = DataClient(self.config)

        resp = client.get_providers_sorted_by_family_name(
            compact='aslp',
            jurisdiction='oh',
            # By providing given and family name, we can expect only one provider returned
            provider_name=('Testerly', 'Tess'),
            scan_forward=False,
        )
        self.assertEqual(1, len(resp['items']))

        # Make sure we got the right provider
        self.assertEqual('Tess', resp['items'][0]['givenName'])
        self.assertEqual('Testerly', resp['items'][0]['familyName'])

    def test_get_providers_sorted_by_date_updated(self):
        from cc_common.data_model.data_client import DataClient

        self._generate_providers(home='oh', privilege_jurisdiction='ne', start_serial=9999)
        self._generate_providers(home='ne', privilege_jurisdiction='oh', start_serial=9989)
        self._generate_providers(home='ne', privilege_jurisdiction='ky', start_serial=9979)
        client = DataClient(self.config)

        # We expect to see 20 providers: 10 have privileges in oh, 10 have licenses in oh
        resp = client.get_providers_sorted_by_updated(
            compact='aslp',
            jurisdiction='oh',
            pagination={'pageSize': 10},
        )
        first_provider_ids = {item['providerId'] for item in resp['items']}
        first_provider_items = resp['items']
        self.assertEqual(10, len(resp['items']))
        self.assertIsInstance(resp['pagination']['lastKey'], str)

        last_key = resp['pagination']['lastKey']
        resp = client.get_providers_sorted_by_updated(
            compact='aslp',
            jurisdiction='oh',
            pagination={'lastKey': last_key, 'pageSize': 10},
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

    def test_get_providers_sorted_by_date_of_update_descending(self):
        from cc_common.data_model.data_client import DataClient

        self._generate_providers(home='oh', privilege_jurisdiction='ne', start_serial=9999)
        client = DataClient(self.config)

        resp = client.get_providers_sorted_by_updated(
            compact='aslp',
            jurisdiction='oh',
            scan_forward=False,
        )
        self.assertEqual(10, len(resp['items']))

        # Verify sorting by dateOfUpdate
        dates_of_update = [item['dateOfUpdate'] for item in resp['items']]
        self.assertListEqual(sorted(dates_of_update, reverse=True), dates_of_update)

    def test_get_providers_sorted_by_updated_privileges_in_jurisdiction_requires_jurisdiction(self):
        from cc_common.data_model.data_client import DataClient

        client = DataClient(self.config)

        # Verify that an exception is raised when jurisdiction is None and
        # only_providers_with_privileges_in_jurisdiction is True
        with self.assertRaises(RuntimeError) as context:
            client.get_providers_sorted_by_updated(
                compact='aslp',
                jurisdiction=None,
                only_providers_with_privileges_in_jurisdiction=True,
            )

        self.assertEqual(
            'jurisdiction is required when only_providers_with_privileges_in_jurisdiction is True',
            str(context.exception),
        )

    def test_get_providers_sorted_by_updated_with_jurisdiction_and_only_providers_with_privileges_in_jurisdiction(self):
        from cc_common.data_model.data_client import DataClient

        self._generate_providers(home='oh', privilege_jurisdiction='ne', start_serial=9999)
        client = DataClient(self.config)

        # Verify that the method works correctly when jurisdiction is provided and
        # only_providers_with_privileges_in_jurisdiction is True
        resp = client.get_providers_sorted_by_updated(
            compact='aslp',
            jurisdiction='ne',
            only_providers_with_privileges_in_jurisdiction=True,
        )

        # Should return providers that have privileges in the specified jurisdiction
        self.assertIsInstance(resp['items'], list)
        # All returned providers should have privileges in 'ne' jurisdiction
        for provider in resp['items']:
            self.assertIn('ne', provider['privilegeJurisdictions'])

    def _load_provider_data(self) -> str:
        with open('../common/tests/resources/dynamo/provider.json') as f:
            provider_record = json.load(f)
        provider_id = provider_record['providerId']
        provider_record['privilegeJurisdictions'] = set(provider_record['privilegeJurisdictions'])
        self._provider_table.put_item(Item=provider_record)

        with open('../common/tests/resources/dynamo/privilege.json') as f:
            privilege_record = json.load(f)
        self._provider_table.put_item(Item=privilege_record)

        with open('../common/tests/resources/dynamo/license.json') as f:
            license_record = json.load(f)
        self._provider_table.put_item(Item=license_record)

        return provider_id
