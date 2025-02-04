import json
from urllib.parse import quote

from boto3.dynamodb.conditions import Key
from moto import mock_aws

from .. import TstFunction


@mock_aws
class TestClient(TstFunction):
    def test_get_provider_id(self):
        from cc_common.data_model.data_client import DataClient

        with open('../common/tests/resources/dynamo/provider-ssn.json') as f:
            record = json.load(f)
        provider_ssn = record['ssn']
        expected_provider_id = record['providerId']

        self._ssn_table.put_item(
            # We'll use the schema/serializer to populate index fields for us
            Item=record,
        )

        client = DataClient(self.config)

        resp = client.get_provider_id(compact='aslp', ssn=provider_ssn)
        # Verify that we're getting the expected provider ID
        self.assertEqual(expected_provider_id, resp)

    def test_get_provider_id_not_found(self):
        """Provider ID not found should raise an exception"""
        from cc_common.data_model.data_client import DataClient
        from cc_common.exceptions import CCNotFoundException

        client = DataClient(self.config)

        # This SSN isn't in the DB, so it should raise an exception
        with self.assertRaises(CCNotFoundException):
            client.get_provider_id(compact='aslp', ssn='321-21-4321')

    def test_get_provider(self):
        from cc_common.data_model.data_client import DataClient

        provider_id = self._load_provider_data()

        client = DataClient(self.config)

        resp = client.get_provider(
            compact='aslp',
            provider_id=provider_id,
        )
        self.assertEqual(3, len(resp['items']))
        # Should be one each of provider, license, privilege
        self.assertEqual({'provider', 'license', 'privilege'}, {record['type'] for record in resp['items']})

    def test_get_provider_garbage_in_db(self):
        """Because of the risk of exposing sensitive data to the public if we manage to get corrupted
        data into our database, we'll specifically validate data coming _out_ of the database
        and throw an error if it doesn't look as expected.
        """
        from cc_common.data_model.data_client import DataClient
        from cc_common.exceptions import CCInternalException

        provider_id = self._load_provider_data()

        with open('../common/tests/resources/dynamo/license.json') as f:
            license_record = json.load(f)

        self._provider_table.put_item(
            Item={
                # Oh, no! We've somehow put somebody's SSN in the wrong place!
                'something_unexpected': '123-12-1234',
                **license_record,
            },
        )

        client = DataClient(self.config)

        # This record should not be allowed out via API
        with self.assertRaises(CCInternalException):
            client.get_provider(
                compact='aslp',
                provider_id=provider_id,
            )

    def test_get_providers_sorted_by_family_name(self):
        from cc_common.data_model.data_client import DataClient

        self._generate_providers(home='oh', privilege='ne', start_serial=9999)
        self._generate_providers(home='ne', privilege='oh', start_serial=9989)
        self._generate_providers(home='ne', privilege='co', start_serial=9979)
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

        self._generate_providers(home='oh', privilege='ne', start_serial=9999)
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
            privilege='ne',
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
            privilege='ne',
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

        self._generate_providers(home='oh', privilege='ne', start_serial=9999)
        self._generate_providers(home='ne', privilege='oh', start_serial=9989)
        self._generate_providers(home='ne', privilege='ky', start_serial=9979)
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

        self._generate_providers(home='oh', privilege='ne', start_serial=9999)
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

    def _get_military_affiliation_records(self, provider_id: str) -> list[dict]:
        return self.config.provider_table.query(
            KeyConditionExpression=Key('pk').eq(f'aslp#PROVIDER#{provider_id}')
            & Key('sk').begins_with('aslp#PROVIDER#military-affiliation#')
        )['Items']

    def test_complete_military_affiliation_initialization_sets_expected_status(self):
        from cc_common.data_model.data_client import DataClient

        # Here we are testing an edge case where there are two military affiliation records
        # both in an initializing state. This could happen in the event of a failed file upload.
        # We want to ensure that the most recent record is set to active and the older record is
        # set to inactive.
        with open('../common/tests/resources/dynamo/military-affiliation.json') as f:
            military_affiliation_record = json.load(f)
            military_affiliation_record['status'] = 'initializing'

        military_affiliation_record['sk'] = 'aslp#PROVIDER#military-affiliation#2024-07-08'
        military_affiliation_record['dateOfUpload'] = '2024-07-08T13:34:59+00:00'
        self._provider_table.put_item(Item=military_affiliation_record)

        # now add record on following day
        military_affiliation_record['sk'] = 'aslp#PROVIDER#military-affiliation#2024-07-09'
        military_affiliation_record['dateOfUpload'] = '2024-07-09T10:34:59+00:00'
        self._provider_table.put_item(Item=military_affiliation_record)

        provider_id = military_affiliation_record['providerId']

        # assert that two records exist, both in an initializing state
        military_affiliation_record = self._get_military_affiliation_records(provider_id)
        self.assertEqual(2, len(military_affiliation_record))
        self.assertEqual('initializing', military_affiliation_record[0]['status'])
        self.assertEqual('initializing', military_affiliation_record[1]['status'])

        # now complete the initialization to set the most recent record to active
        # and the older record to inactive
        client = DataClient(self.config)
        client.complete_military_affiliation_initialization(compact='aslp', provider_id=provider_id)

        military_affiliation_record = self._get_military_affiliation_records(provider_id)
        self.assertEqual(2, len(military_affiliation_record))
        # This asserts that the records are sorted by dateOfUpload, from oldest to newest
        oldest_record = military_affiliation_record[0]
        newest_record = military_affiliation_record[1]
        self.assertTrue(oldest_record['dateOfUpload'] < newest_record['dateOfUpload'], 'Records are not sorted by date')
        self.assertEqual('inactive', oldest_record['status'])
        self.assertEqual('active', newest_record['status'])
