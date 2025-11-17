from datetime import datetime
from unittest.mock import patch

from common_test.test_constants import (
    DEFAULT_LICENSE_JURISDICTION,
    DEFAULT_LICENSE_UPDATE_CREATE_DATE,
    DEFAULT_LICENSE_UPDATE_DATETIME,
    DEFAULT_PRIVILEGE_JURISDICTION,
    DEFAULT_PRIVILEGE_UPDATE_DATETIME,
    DEFAULT_PROVIDER_UPDATE_DATETIME,
)
from moto import mock_aws

from . import TstFunction

MOCK_DATETIME_STRING = '2025-10-23T08:15:00+00:00'
MOCK_COMPACT = 'coun'
MOCK_PROVIDER_ID = '01d67765-76dd-47c8-b39a-8389445bb3b7'


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat(MOCK_DATETIME_STRING))
class TestMigrateUpdateSortKeys(TstFunction):
    """Test class for migrating update record sort keys."""

    def test_should_migrate_provider_update_records_to_expected_pattern(self):
        from migrate_update_sort_keys.main import do_migration

        old_provider_update_record = self.test_data_generator.generate_default_provider_update(
            value_overrides={'compact': MOCK_COMPACT, 'providerId': MOCK_PROVIDER_ID}
        )
        serialized_old_record = old_provider_update_record.serialize_to_database_record()
        # replace sk with old pattern to simulate old record to be migrated
        serialized_old_record['sk'] = 'coun#PROVIDER#UPDATE#1752526787/2f429ccda22d273b1ee4876f2917e27f'
        del serialized_old_record['createDate']
        serialized_old_record['dateOfUpdate'] = DEFAULT_PROVIDER_UPDATE_DATETIME
        self.config.provider_table.put_item(Item=serialized_old_record)

        # run migration
        do_migration({})

        # verify old record was deleted
        old_record_resp = self.config.provider_table.get_item(
            Key={'pk': serialized_old_record['pk'], 'sk': serialized_old_record['sk']}
        )
        self.assertIsNone(old_record_resp.get('Item'))

        # verify new record was created with expected sk
        expected_sk = (
            f'{MOCK_COMPACT}#UPDATE#2#provider/{DEFAULT_PROVIDER_UPDATE_DATETIME}/2f429ccda22d273b1ee4876f2917e27f'
        )
        new_record = self.config.provider_table.get_item(Key={'pk': serialized_old_record['pk'], 'sk': expected_sk})[
            'Item'
        ]

        serialized_old_record['sk'] = expected_sk
        # as part of migration, the createDate field will be populated with whatever the dateOfUpdate was
        # so we expect that here
        serialized_old_record['createDate'] = DEFAULT_PROVIDER_UPDATE_DATETIME
        # only the sort key and the createDate should have been modified
        self.assertEqual(serialized_old_record, new_record)

    def test_should_migrate_license_update_records_to_expected_pattern(self):
        from migrate_update_sort_keys.main import do_migration

        old_license_update_record = self.test_data_generator.generate_default_license_update(
            value_overrides={
                'compact': MOCK_COMPACT,
                'providerId': MOCK_PROVIDER_ID,
                'licenseType': 'licensed professional counselor',
            }
        )
        serialized_old_record = old_license_update_record.serialize_to_database_record()
        # replace sk with old pattern to simulate old record to be migrated
        serialized_old_record['sk'] = (
            f'{MOCK_COMPACT}#PROVIDER#license/{DEFAULT_LICENSE_JURISDICTION}/lpc#UPDATE#1752526787/21554583eb71ccc5f8aa5988c8a50ac2'
        )
        serialized_old_record['dateOfUpdate'] = DEFAULT_LICENSE_UPDATE_DATETIME
        self.config.provider_table.put_item(Item=serialized_old_record)

        # run migration
        do_migration({})

        # verify old record was deleted
        old_record_resp = self.config.provider_table.get_item(
            Key={'pk': serialized_old_record['pk'], 'sk': serialized_old_record['sk']}
        )
        self.assertIsNone(old_record_resp.get('Item'))

        # verify new record was created with expected sk
        expected_sk = (
            f'{MOCK_COMPACT}#UPDATE#3#license/{DEFAULT_LICENSE_JURISDICTION}/lpc'
            f'/{DEFAULT_LICENSE_UPDATE_CREATE_DATE}/21554583eb71ccc5f8aa5988c8a50ac2'
        )
        new_record = self.config.provider_table.get_item(Key={'pk': serialized_old_record['pk'], 'sk': expected_sk})[
            'Item'
        ]
        serialized_old_record['sk'] = expected_sk
        # nothing on the record should have changed other than the sort key
        self.assertEqual(serialized_old_record, new_record)

    def test_should_migrate_privilege_update_records_to_expected_pattern(self):
        from migrate_update_sort_keys.main import do_migration

        mock_create_date = '2025-07-07T07:07:07+00:00'

        old_privilege_update_record = self.test_data_generator.generate_default_privilege_update(
            value_overrides={
                'compact': MOCK_COMPACT,
                'providerId': MOCK_PROVIDER_ID,
                'licenseType': 'licensed professional counselor',
                'createDate': datetime.fromisoformat(mock_create_date),
            }
        )
        serialized_old_record = old_privilege_update_record.serialize_to_database_record()
        # replace sk with old pattern to simulate old record to be migrated
        serialized_old_record['sk'] = (
            f'{MOCK_COMPACT}#PROVIDER#privilege/{DEFAULT_PRIVILEGE_JURISDICTION}/lpc#UPDATE#1752526787/399abde0989ad5e936920a3ba9f0944a'
        )
        serialized_old_record['dateOfUpdate'] = DEFAULT_PRIVILEGE_UPDATE_DATETIME
        self.config.provider_table.put_item(Item=serialized_old_record)

        # run migration
        do_migration({})

        # verify old record was deleted
        old_record_resp = self.config.provider_table.get_item(
            Key={'pk': serialized_old_record['pk'], 'sk': serialized_old_record['sk']}
        )
        self.assertIsNone(old_record_resp.get('Item'))

        # verify new record was created with expected sk
        expected_sk = (
            f'{MOCK_COMPACT}#UPDATE#1#privilege/{DEFAULT_PRIVILEGE_JURISDICTION}/lpc'
            f'/{mock_create_date}/399abde0989ad5e936920a3ba9f0944a'
        )
        new_record = self.config.provider_table.get_item(Key={'pk': serialized_old_record['pk'], 'sk': expected_sk})[
            'Item'
        ]
        serialized_old_record['sk'] = expected_sk
        # nothing on the record should have changed other than the sort key
        self.assertEqual(serialized_old_record, new_record)
