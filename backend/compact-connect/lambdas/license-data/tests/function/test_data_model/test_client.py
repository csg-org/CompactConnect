import json
from uuid import uuid4

from moto import mock_aws
from tests.function import TstFunction


@mock_aws
class TestClient(TstFunction):
    def test_get_provider_id(self):
        from data_model.client import DataClient
        from data_model.schema.license import LicensePostSchema, LicenseRecordSchema
        from data_model.schema.privilege import PrivilegePostSchema, PrivilegeRecordSchema
        from exceptions import CCNotFoundException, CCInternalException

        with open('tests/resources/api/license-post.json', 'r') as f:
            license_data = LicensePostSchema().load({
                'compact': 'aslp',
                'jurisdiction': 'co',
                **json.load(f)
            })

        with open('tests/resources/dynamo/license.json', 'r') as f:
            provider_id = json.load(f)['providerId']

        self._table.put_item(
            # We'll use the schema/serializer to populate index fields for us
            Item=LicenseRecordSchema().dump({
                'providerId': provider_id,
                'compact': 'aslp',
                'jurisdiction': 'co',
                **license_data
            })
        )

        with open('tests/resources/api/privilege.json', 'r') as f:
            privilege = PrivilegePostSchema().loads(f.read())

        self._table.put_item(
            Item=PrivilegeRecordSchema().dump({
                'providerId': provider_id,
                'compact': 'aslp',
                'jurisdiction': 'co',
                **privilege
            })
        )

        client = DataClient(self.config)

        resp = client.get_provider_id(ssn='123-12-1234')  # pylint: disable=missing-kwoa
        self.assertEqual(provider_id, resp)

        with self.assertRaises(CCNotFoundException):
            client.get_provider_id(ssn='321-21-4321')  # pylint: disable=missing-kwoa

        # Associate a second provider with the same ssn - force a data consistency error
        self._table.put_item(
            # We'll use the schema/serializer to populate index fields for us
            Item=LicenseRecordSchema().dump({
                'providerId': str(uuid4()),
                'compact': 'aslp',
                'jurisdiction': 'co',
                **license_data
            })
        )
        with self.assertRaises(CCInternalException):
            client.get_provider_id(ssn='123-12-1234')  # pylint: disable=missing-kwoa

    def test_get_provider(self):
        from data_model.client import DataClient
        from data_model.schema.license import LicensePostSchema, LicenseRecordSchema
        from data_model.schema.privilege import PrivilegePostSchema, PrivilegeRecordSchema

        with open('tests/resources/api/license-post.json', 'r') as f:
            license_data = LicensePostSchema().load({
                'compact': 'aslp',
                'jurisdiction': 'co',
                **json.load(f)
            })

        with open('tests/resources/dynamo/license.json', 'r') as f:
            provider_id = json.load(f)['providerId']

        self._table.put_item(
            # We'll use the schema/serializer to populate index fields for us
            Item=LicenseRecordSchema().dump({
                'providerId': provider_id,
                'compact': 'aslp',
                'jurisdiction': 'co',
                **license_data
            })
        )

        with open('tests/resources/api/privilege.json', 'r') as f:
            privilege = PrivilegePostSchema().loads(f.read())

        self._table.put_item(
            Item=PrivilegeRecordSchema().dump({
                'providerId': provider_id,
                'compact': 'aslp',
                'jurisdiction': 'co',
                **privilege
            })
        )

        client = DataClient(self.config)

        resp = client.get_provider(provider_id=provider_id)  # pylint: disable=missing-kwoa
        self.assertEqual(2, len(resp['items']))

    def test_get_provider_garbage_in_db(self):
        """
        Because of the risk of exposing sensitive data to the public if we manage to get corrupted
        data into our database, we'll specifically validate data coming _out_ of the database
        and throw an error if it doesn't look as expected.
        """
        from data_model.client import DataClient
        from data_model.schema.license import LicensePostSchema, LicenseRecordSchema
        from exceptions import CCInternalException

        with open('tests/resources/api/license-post.json', 'r') as f:
            license_data = LicensePostSchema().load({
                'compact': 'aslp',
                'jurisdiction': 'co',
                **json.load(f)
            })

        with open('tests/resources/dynamo/license.json', 'r') as f:
            provider_id = json.load(f)['providerId']

        self._table.put_item(
            Item={
                # Oh, no! We've somehow put somebody's SSN in the wrong place!
                'something_unexpected': '123-12-1234',
                **LicenseRecordSchema().dump({
                    'providerId': provider_id,
                    'compact': 'aslp',
                    'jurisdiction': 'co',
                    **license_data
                })
            }
        )

        client = DataClient(self.config)

        # This record should not be allowed out via API
        with self.assertRaises(CCInternalException):
            client.get_provider(provider_id=provider_id)  # pylint: disable=missing-kwoa

    def test_get_licenses_sorted_by_family_name(self):
        from data_model.client import DataClient

        # 100 licenses homed in co with privileges in fl
        self._generate_licensees('co', 'al', 9999)
        # 100 licenses homed in fl with privileges in co
        self._generate_licensees('al', 'co', 9899)
        client = DataClient(self.config)

        # We expect to see 100 co licenses, 100 co privileges, none of the al licenses/privileges
        resp = client.get_licenses_sorted_by_family_name(  # pylint: disable=missing-kwoa
            compact='aslp',
            jurisdiction='co'
        )
        self.assertEqual(100, len(resp['items']))
        self.assertIn('lastKey', resp.keys())

        last_key = resp['lastKey']
        resp = client.get_licenses_sorted_by_family_name(  # pylint: disable=unexpected-keyword-arg,missing-kwoa
            compact='aslp',
            jurisdiction='co',
            pagination={'lastKey': last_key}
        )
        # moto does not properly mimic dynamodb pagination in the case of an index with duplicate keys,
        # so we cannot test for the expected length of 100 records, here.
        # Possibly related to this issue: https://github.com/getmoto/moto/issues/7834
        self.assertNotIn('lastKey', resp.keys())

    def test_get_licenses_sorted_by_updated_date(self):
        from data_model.client import DataClient

        # 100 licenses homed in co with privileges in fl
        self._generate_licensees('co', 'al', 9999)
        # 100 licenses homed in fl with privileges in co
        self._generate_licensees('al', 'co', 9899)
        client = DataClient(self.config)

        # We expect to see 100 co licenses, 100 co privileges, none of the fl licenses/privileges
        resp = client.get_licenses_sorted_by_date_updated(  # pylint: disable=missing-kwoa
            compact='aslp',
            jurisdiction='co'
        )
        self.assertEqual(100, len(resp['items']))
        self.assertIn('lastKey', resp.keys())

        # The second should be the last 100 licenses, so no lastKey for a next page
        last_key = resp['lastKey']
        resp = client.get_licenses_sorted_by_date_updated(  # pylint: disable=unexpected-keyword-arg,missing-kwoa
            compact='aslp',
            jurisdiction='co',
            pagination={'lastKey': last_key}
        )
        # moto does not properly mimic dynamodb pagination in the case of an index with duplicate keys,
        # so we cannot test for the expected length of 100 records, here
        # Possibly related to this issue: https://github.com/getmoto/moto/issues/7834
        self.assertNotIn('lastKey', resp.keys())

        # The first page sorted descending should be the same as the second page ascending, but reversed
        # Again, moto does not mimic dynamodb pagination correctly, so we cannot test item sorting, but
        # we _can_ at least test that we get the expected 100 items.
        resp = client.get_licenses_sorted_by_date_updated(  # pylint: disable=unexpected-keyword-arg,missing-kwoa
            compact='aslp',
            jurisdiction='co',
            scan_forward=False
        )
        self.assertEqual(100, len(resp['items']))
