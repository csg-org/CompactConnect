from random import randint

from moto import mock_aws
from tests.function import TstFunction


@mock_aws
class TestClient(TstFunction):
    def test_get_ssn(self):
        from data_model.client import DataClient
        from data_model.schema.license import LicensePostSchema, LicenseRecordSchema
        from data_model.schema.privilege import PrivilegePostSchema, PrivilegeRecordSchema

        with open('tests/resources/api/license.json', 'r') as f:
            license_data = LicensePostSchema().loads(f.read())

        self._table.put_item(
            # We'll use the schema/serializer to populate index fields for us
            Item=LicenseRecordSchema().dump({
                'compact': 'aslp',
                'jurisdiction': 'co',
                **license_data
            })
        )

        with open('tests/resources/api/privilege.json', 'r') as f:
            privilege = PrivilegePostSchema().loads(f.read())

        self._table.put_item(
            Item=PrivilegeRecordSchema().dump({
                'compact': 'aslp',
                'jurisdiction': 'co',
                **privilege
            })
        )

        client = DataClient(self.config)

        resp = client.get_ssn(ssn='123-12-1234')  # pylint: disable=missing-kwoa
        self.assertEqual(2, len(resp['items']))

    def test_get_ssn_garbage_in_db(self):
        """
        Because of the risk of exposing sensitive data to the public if we manage to get corrupted
        data into our database, we'll specifically validate data coming _out_ of the database
        and throw an error if it doesn't look as expected.
        """
        from data_model.client import DataClient
        from data_model.schema.license import LicensePostSchema, LicenseRecordSchema
        from exceptions import CCInternalException

        with open('tests/resources/api/license.json', 'r') as f:
            license_data = LicensePostSchema().loads(f.read())

        self._table.put_item(
            Item={
                # Oh, no! We've somehow put somebody's SSN in the wrong place!
                'something_unexpected': '123-12-1234',
                **LicenseRecordSchema().dump({
                    'compact': 'aslp',
                    'jurisdiction': 'co',
                    **license_data
                })
            }
        )

        client = DataClient(self.config)

        # This record should not be allowed out via API
        with self.assertRaises(CCInternalException):
            client.get_ssn(ssn='123-12-1234')  # pylint: disable=missing-kwoa

    def test_get_licenses_sorted_by_family_name(self):
        from data_model.client import DataClient

        # 100 licenses homed in co with privileges in fl
        self._generate_licensees('co', 'fl', 9999)
        # 100 licenses homed in fl with privileges in co
        self._generate_licensees('fl', 'co', 9899)
        client = DataClient(self.config)

        # We expect to see 100 co licenses, 100 co privileges, none of the al licenses/privileges
        resp = client.get_licenses_sorted_by_family_name(  # pylint: disable=missing-kwoa
            board='aslp',
            jurisdiction='co'
        )
        self.assertEqual(100, len(resp['items']))
        self.assertIn('lastKey', resp.keys())

        last_key = resp['lastKey']
        resp = client.get_licenses_sorted_by_family_name(  # pylint: disable=unexpected-keyword-arg,missing-kwoa
            board='aslp',
            jurisdiction='co',
            pagination={'last_key': last_key}
        )
        self.assertEqual(100, len(resp['items']))
        self.assertNotIn('lastKey', resp.keys())

    def test_get_licenses_sorted_by_updated_date(self):
        from data_model.client import DataClient

        # 100 licenses homed in co with privileges in fl
        self._generate_licensees('co', 'fl', 9999)
        # 100 licenses homed in fl with privileges in co
        self._generate_licensees('fl', 'co', 9899)
        client = DataClient(self.config)

        # We expect to see 100 co licenses, 100 co privileges, none of the fl licenses/privileges
        resp = client.get_licenses_sorted_by_date_updated(  # pylint: disable=missing-kwoa
            board='aslp',
            jurisdiction='co'
        )
        self.assertEqual(100, len(resp['items']))
        self.assertIn('lastKey', resp.keys())

        last_key = resp['lastKey']
        resp = client.get_licenses_sorted_by_date_updated(  # pylint: disable=unexpected-keyword-arg,missing-kwoa
            board='aslp',
            jurisdiction='co',
            pagination={'last_key': last_key}
        )
        self.assertEqual(100, len(resp['items']))
        self.assertNotIn('lastKey', resp.keys())

    def _generate_licensees(self, home: str, priv: str, start_serial: int):
        from data_model.schema.license import LicensePostSchema, LicenseRecordSchema
        from data_model.schema.privilege import PrivilegePostSchema, PrivilegeRecordSchema

        with open('tests/resources/api/license.json', 'r') as f:
            license_data = LicensePostSchema().loads(f.read())

        with open('tests/resources/api/privilege.json', 'r') as f:
            privilege_data = PrivilegePostSchema().loads(f.read())

        # Generate 100 licensees, each with a license and a privilege
        for i in range(start_serial, start_serial-100, -1):
            ssn = f'{randint(100, 999)}-{randint(10, 99)}-{i}'
            license_data['ssn'] = ssn
            item = LicenseRecordSchema().dump({
                    'compact': 'aslp',
                    'jurisdiction': home,
                    **license_data
                })
            self._table.put_item(
                # We'll use the schema/serializer to populate index fields for us
                Item=item
            )

            privilege_data['ssn'] = ssn
            privilege_data['home_jurisdiction'] = home
            item = PrivilegeRecordSchema().dump({
                    'compact': 'aslp',
                    'jurisdiction': priv,
                    **privilege_data
                })
            self._table.put_item(
                Item=item
            )
