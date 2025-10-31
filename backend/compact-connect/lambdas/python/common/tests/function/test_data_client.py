import json
from datetime import UTC, date, datetime
from unittest.mock import patch
from uuid import UUID, uuid4

from boto3.dynamodb.conditions import Key
from cc_common.exceptions import CCAwsServiceException, CCInvalidRequestException
from common_test.test_constants import DEFAULT_PROVIDER_ID
from moto import mock_aws

from tests.function import TstFunction


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
class TestDataClient(TstFunction):
    sample_privilege_attestations = [{'attestationId': 'jurisprudence-confirmation', 'version': '1'}]

    def setUp(self):
        super().setUp()
        self.maxDiff = None

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

        provider_id = self._load_provider_data()

        with open('tests/resources/dynamo/license.json') as f:
            license_record = json.load(f)

        self._provider_table.put_item(
            Item={
                # Oh, no! We've somehow put somebody's full SSN in the wrong place!
                'something_unexpected': '123-12-1234',
                **license_record,
            },
        )

        client = DataClient(self.config)

        # The field should not be allowed out via API
        resp = client.get_provider(
            compact='aslp',
            provider_id=provider_id,
        )
        for item in resp['items']:
            self.assertNotIn('something_unexpected', item)

    def _load_provider_data(self) -> UUID:
        with open('tests/resources/dynamo/provider.json') as f:
            provider_record = json.load(f)
        provider_id = UUID(provider_record['providerId'])
        provider_record['privilegeJurisdictions'] = set(provider_record['privilegeJurisdictions'])
        self._provider_table.put_item(Item=provider_record)

        with open('tests/resources/dynamo/privilege.json') as f:
            privilege_record = json.load(f)
        self._provider_table.put_item(Item=privilege_record)

        with open('tests/resources/dynamo/license.json') as f:
            license_record = json.load(f)
        self._provider_table.put_item(Item=license_record)

        with open('tests/resources/dynamo/provider-ssn.json') as f:
            provider_ssn_record = json.load(f)
        self._ssn_table.put_item(Item=provider_ssn_record)

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
        with open('tests/resources/dynamo/military-affiliation.json') as f:
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

    def test_data_client_created_privilege_record(self):
        from cc_common.data_model.data_client import DataClient

        # Imagine that there have been 123 privileges issued for the compact
        # and that the next privilege number will be 124
        self.config.provider_table.put_item(
            Item={
                'pk': 'aslp#PRIVILEGE_COUNT',
                'sk': 'aslp#PRIVILEGE_COUNT',
                'privilegeCount': 123,
            }
        )

        test_data_client = DataClient(self.config)

        response = test_data_client.create_provider_privileges(
            compact='aslp',
            provider_id=DEFAULT_PROVIDER_ID,
            license_type='audiologist',
            jurisdiction_postal_abbreviations=['ky'],
            license_expiration_date=date.fromisoformat('2024-10-31'),
            provider_record=self.test_data_generator.generate_default_provider(),
            existing_privileges_for_license=[],
            compact_transaction_id='test_transaction_id',
            attestations=self.sample_privilege_attestations,
        )

        # Verify that the privilege record was created
        new_privilege = self._provider_table.get_item(
            Key={'pk': f'aslp#PROVIDER#{DEFAULT_PROVIDER_ID}', 'sk': 'aslp#PROVIDER#privilege/ky/aud#'}
        )['Item']
        self.assertEqual(
            {
                'pk': f'aslp#PROVIDER#{DEFAULT_PROVIDER_ID}',
                'sk': 'aslp#PROVIDER#privilege/ky/aud#',
                'type': 'privilege',
                'providerId': DEFAULT_PROVIDER_ID,
                'compact': 'aslp',
                'jurisdiction': 'ky',
                'licenseJurisdiction': 'oh',
                'licenseType': 'audiologist',
                'administratorSetStatus': 'active',
                'dateOfIssuance': '2024-11-08T23:59:59+00:00',
                'dateOfRenewal': '2024-11-08T23:59:59+00:00',
                'dateOfExpiration': '2024-10-31',
                'dateOfUpdate': '2024-11-08T23:59:59+00:00',
                'compactTransactionId': 'test_transaction_id',
                'compactTransactionIdGSIPK': 'COMPACT#aslp#TX#test_transaction_id#',
                'attestations': self.sample_privilege_attestations,
                'privilegeId': 'AUD-KY-124',
            },
            new_privilege,
        )

        # Verify that the provider record was updated
        updated_provider = self._provider_table.get_item(
            Key={'pk': f'aslp#PROVIDER#{DEFAULT_PROVIDER_ID}', 'sk': 'aslp#PROVIDER'}
        )['Item']
        self.assertEqual({'ky'}, updated_provider['privilegeJurisdictions'])

        # Verify the privilege data is being passed back in the response
        self.assertEqual(1, len(response))
        self.assertEqual(
            {
                'administratorSetStatus': 'active',
                'attestations': [{'attestationId': 'jurisprudence-confirmation', 'version': '1'}],
                'compact': 'aslp',
                'compactTransactionId': 'test_transaction_id',
                'compactTransactionIdGSIPK': 'COMPACT#aslp#TX#test_transaction_id#',
                'dateOfIssuance': '2024-11-08T23:59:59+00:00',
                'dateOfRenewal': '2024-11-08T23:59:59+00:00',
                'dateOfExpiration': '2024-10-31',
                'dateOfUpdate': '2024-11-08T23:59:59+00:00',
                'jurisdiction': 'ky',
                'licenseJurisdiction': 'oh',
                'licenseType': 'audiologist',
                'pk': f'aslp#PROVIDER#{DEFAULT_PROVIDER_ID}',
                'privilegeId': 'AUD-KY-124',
                'providerId': DEFAULT_PROVIDER_ID,
                'sk': 'aslp#PROVIDER#privilege/ky/aud#',
                'type': 'privilege',
            },
            response[0].serialize_to_database_record(),
        )

    def test_data_client_updates_privilege_records_for_specific_license_type(self):
        """
        In this test case, a user has two license types, audiologist and speech-language pathologist.
        The user is purchasing a renewal for their audiologist privilege in ky, and purchasing a new
        audiologist privilege in ne. The privilege for the speech-language pathologist license should not be
        referenced nor updated in any way as part of this purchase.
        """
        from cc_common.data_model.data_client import DataClient
        from cc_common.data_model.provider_record_util import ProviderUserRecords
        from cc_common.data_model.schema.privilege import PrivilegeData

        # Imagine that there have been 123 privileges issued for the compact
        # and that the next privilege number will be 124
        self.config.provider_table.put_item(
            Item={
                'pk': 'aslp#PRIVILEGE_COUNT',
                'sk': 'aslp#PRIVILEGE_COUNT',
                'privilegeCount': 123,
            }
        )

        # Create the first privilege
        provider_uuid = str(uuid4())
        original_privilege = PrivilegeData.from_database_record(
            {
                'pk': f'aslp#PROVIDER#{provider_uuid}',
                'sk': 'aslp#PROVIDER#privilege/ky/aud#',
                'type': 'privilege',
                'providerId': provider_uuid,
                'compact': 'aslp',
                'jurisdiction': 'ky',
                'licenseJurisdiction': 'oh',
                'licenseType': 'audiologist',
                'administratorSetStatus': 'active',
                'dateOfIssuance': '2023-11-08T23:59:59+00:00',
                'dateOfRenewal': '2023-11-08T23:59:59+00:00',
                'dateOfExpiration': '2024-10-31',
                'dateOfUpdate': '2023-11-08T23:59:59+00:00',
                'compactTransactionId': '1234567890',
                'compactTransactionIdGSIPK': 'COMPACT#aslp#TX#1234567890#',
                'attestations': self.sample_privilege_attestations,
                'privilegeId': 'AUD-KY-1',
            }
        )
        self._provider_table.put_item(Item=original_privilege.serialize_to_database_record())
        # Put in another privilege for the slp license type in same jurisdiction to ensure
        # it is not modified by the renewal
        slp_ne_privilege = PrivilegeData.from_database_record(
            {
                'pk': f'aslp#PROVIDER#{provider_uuid}',
                'sk': 'aslp#PROVIDER#privilege/ne/slp#',
                'type': 'privilege',
                'providerId': provider_uuid,
                'compact': 'aslp',
                'jurisdiction': 'ne',
                'licenseJurisdiction': 'oh',
                'licenseType': 'speech-language pathologist',
                'administratorSetStatus': 'active',
                'dateOfIssuance': '2023-11-08T23:59:59+00:00',
                'dateOfRenewal': '2023-11-08T23:59:59+00:00',
                'dateOfExpiration': '2024-10-31',
                'dateOfUpdate': '2023-11-08T23:59:59+00:00',
                'compactTransactionId': '1234567890',
                'compactTransactionIdGSIPK': 'COMPACT#aslp#TX#1234567890#',
                'attestations': self.sample_privilege_attestations,
                'privilegeId': 'SLP-NE-2',
            }
        )
        self._provider_table.put_item(Item=slp_ne_privilege.serialize_to_database_record())

        test_data_client = DataClient(self.config)

        # Now, renew the privilege
        test_data_client.create_provider_privileges(
            compact='aslp',
            provider_id=provider_uuid,
            # in this case, the user is renewing their ky priv, and purchasing a new priv in ne
            jurisdiction_postal_abbreviations=['ky', 'ne'],
            license_expiration_date=date.fromisoformat('2025-10-31'),
            provider_record=self.test_data_generator.generate_default_provider(
                value_overrides={
                    'provider_id': provider_uuid,
                    'licenseJurisdiction': 'oh',
                }
            ),
            # set error scenario where a developer passes in both privileges, even though only one is related to the
            # specific license type, which should be handled gracefully in the implementation
            existing_privileges_for_license=[
                original_privilege,
                slp_ne_privilege,
            ],
            compact_transaction_id='test_transaction_id',
            attestations=self.sample_privilege_attestations,
            license_type='audiologist',
        )

        # Verify that the audiologist privilege update record was created for ky
        provider_user_records: ProviderUserRecords = self.config.data_client.get_provider_user_records(
            compact='aslp', provider_id=provider_uuid, include_updates=True
        )

        new_aud_ky_privilege = provider_user_records.get_specific_privilege_record(
            jurisdiction='ky', license_abbreviation='aud'
        )

        self.assertEqual(
            # Primary record
            {
                'pk': f'aslp#PROVIDER#{provider_uuid}',
                'sk': 'aslp#PROVIDER#privilege/ky/aud#',
                'type': 'privilege',
                'providerId': provider_uuid,
                'compact': 'aslp',
                'jurisdiction': 'ky',
                'licenseJurisdiction': 'oh',
                'licenseType': 'audiologist',
                'administratorSetStatus': 'active',
                # Should be updated dates for renewal, expiration, update
                'dateOfIssuance': '2023-11-08T23:59:59+00:00',
                'dateOfRenewal': '2024-11-08T23:59:59+00:00',
                'dateOfExpiration': '2025-10-31',
                'dateOfUpdate': '2024-11-08T23:59:59+00:00',
                'compactTransactionId': 'test_transaction_id',
                'compactTransactionIdGSIPK': 'COMPACT#aslp#TX#test_transaction_id#',
                'attestations': self.sample_privilege_attestations,
                # Should remain the same, since we're renewing the same privilege
                'privilegeId': 'AUD-KY-1',
            },
            new_aud_ky_privilege.serialize_to_database_record(),
        )

        ky_aud_update_record = provider_user_records.get_update_records_for_privilege(
            jurisdiction=new_aud_ky_privilege.jurisdiction, license_type=new_aud_ky_privilege.licenseType
        )[0]

        self.assertEqual(
            # A new history record
            {
                'pk': f'aslp#PROVIDER#{provider_uuid}',
                'sk': 'aslp#PROV_UPDATE#privilege/ky/aud/1731110399/f61e34798e1775ff6230d1187d444146',
                'type': 'privilegeUpdate',
                'updateType': 'renewal',
                'providerId': provider_uuid,
                'compact': 'aslp',
                'compactTransactionIdGSIPK': 'COMPACT#aslp#TX#1234567890#',
                'jurisdiction': 'ky',
                'licenseType': 'audiologist',
                'dateOfUpdate': '2024-11-08T23:59:59+00:00',
                'createDate': '2024-11-08T23:59:59+00:00',
                'effectiveDate': '2024-11-08T23:59:59+00:00',
                'previous': {
                    'dateOfIssuance': '2023-11-08T23:59:59+00:00',
                    'dateOfRenewal': '2023-11-08T23:59:59+00:00',
                    'dateOfExpiration': '2024-10-31',
                    'dateOfUpdate': '2023-11-08T23:59:59+00:00',
                    'compactTransactionId': '1234567890',
                    'attestations': self.sample_privilege_attestations,
                    'administratorSetStatus': 'active',
                    'licenseJurisdiction': 'oh',
                    'privilegeId': 'AUD-KY-1',
                },
                'updatedValues': {
                    'attestations': self.sample_privilege_attestations,
                    'dateOfRenewal': '2024-11-08T23:59:59+00:00',
                    'dateOfExpiration': '2025-10-31',
                    'compactTransactionId': 'test_transaction_id',
                    'privilegeId': 'AUD-KY-1',
                },
            },
            ky_aud_update_record.serialize_to_database_record(),
        )

        # Verify that a new audiologist privilege record was created for ne with expected values
        new_aud_ne_privilege = provider_user_records.get_specific_privilege_record(
            jurisdiction='ne', license_abbreviation='aud'
        )
        self.assertEqual(
            # Primary record
            {
                'pk': f'aslp#PROVIDER#{provider_uuid}',
                'sk': 'aslp#PROVIDER#privilege/ne/aud#',
                'type': 'privilege',
                'providerId': provider_uuid,
                'compact': 'aslp',
                'jurisdiction': 'ne',
                'licenseJurisdiction': 'oh',
                'licenseType': 'audiologist',
                'administratorSetStatus': 'active',
                # issuance and renewal dates should be the same
                'dateOfIssuance': '2024-11-08T23:59:59+00:00',
                'dateOfRenewal': '2024-11-08T23:59:59+00:00',
                'dateOfExpiration': '2025-10-31',
                'dateOfUpdate': '2024-11-08T23:59:59+00:00',
                'compactTransactionId': 'test_transaction_id',
                'compactTransactionIdGSIPK': 'COMPACT#aslp#TX#test_transaction_id#',
                'attestations': self.sample_privilege_attestations,
                # Should remain the same, since we're renewing the same privilege
                'privilegeId': 'AUD-NE-124',
            },
            new_aud_ne_privilege.serialize_to_database_record(),
        )
        # assert there are no update records for this privilege
        ne_aud_update_records = provider_user_records.get_update_records_for_privilege(
            jurisdiction=new_aud_ne_privilege.jurisdiction, license_type=new_aud_ne_privilege.licenseType
        )
        self.assertEqual([], ne_aud_update_records)

        # ensure that slp privilege was not updated with an update record
        slp_privilege = self._provider_table.query(
            KeyConditionExpression=Key('pk').eq(f'aslp#PROVIDER#{provider_uuid}')
            & Key('sk').begins_with('aslp#PROVIDER#privilege/ne/slp#'),
        )['Items']
        self.assertEqual([slp_ne_privilege.serialize_to_database_record()], slp_privilege)

        # The renewal should ensure that 'ky' and 'ne' are listed in provider privilegeJurisdictions
        provider = self._provider_table.get_item(
            Key={'pk': f'aslp#PROVIDER#{provider_uuid}', 'sk': 'aslp#PROVIDER'},
        )['Item']
        self.assertEqual({'ky', 'ne'}, provider['privilegeJurisdictions'])

    def test_data_client_create_privilege_record_invalid_license_type(self):
        from cc_common.data_model.data_client import DataClient
        from cc_common.exceptions import CCInvalidRequestException

        test_data_client = DataClient(self.config)

        with self.assertRaises(CCInvalidRequestException):
            test_data_client.create_provider_privileges(
                compact='aslp',
                provider_id='test_provider_id',
                jurisdiction_postal_abbreviations=['ca'],
                license_expiration_date=date.fromisoformat('2024-10-31'),
                provider_record=self.test_data_generator.generate_default_provider(),
                existing_privileges_for_license=[],
                compact_transaction_id='test_transaction_id',
                attestations=self.sample_privilege_attestations,
                license_type='not-supported-license-type',
            )

    def test_data_client_handles_large_privilege_purchase(self):
        """Test that we can process privilege purchases with more than 100 transaction items."""
        from cc_common.data_model.data_client import DataClient
        from cc_common.data_model.provider_record_util import ProviderUserRecords
        from cc_common.data_model.schema.common import ActiveInactiveStatus
        from cc_common.data_model.schema.privilege import PrivilegeData

        test_data_client = DataClient(self.config)
        provider_uuid = str(uuid4())

        # use first 51 jurisdictions (will create 102 records - 51 privileges and 51 updates)
        jurisdictions = [jurisdiction for jurisdiction in self.config.jurisdictions[0:51]]
        original_privileges = []

        # Create original privileges that will be updated
        for jurisdiction in jurisdictions:
            original_privilege = PrivilegeData.create_new(
                {
                    'type': 'privilege',
                    'providerId': provider_uuid,
                    'compact': 'aslp',
                    'jurisdiction': jurisdiction,
                    'licenseJurisdiction': 'oh',
                    'licenseType': 'audiologist',
                    'privilegeId': f'AUD-{jurisdiction.upper()}-1',
                    'dateOfIssuance': datetime(2023, 11, 8, 23, 59, 59, tzinfo=UTC),
                    'dateOfRenewal': datetime(2023, 11, 8, 23, 59, 59, tzinfo=UTC),
                    'dateOfExpiration': date(2024, 10, 31),
                    'dateOfUpdate': datetime(2023, 11, 8, 23, 59, 59, tzinfo=UTC),
                    'compactTransactionId': '1234567890',
                    'administratorSetStatus': ActiveInactiveStatus.ACTIVE,
                    'attestations': [],
                }
            )
            self._provider_table.put_item(Item=original_privilege.serialize_to_database_record())
            original_privileges.append(original_privilege)

        # Now update all privileges
        test_data_client.create_provider_privileges(
            compact='aslp',
            provider_id=provider_uuid,
            jurisdiction_postal_abbreviations=jurisdictions,
            license_expiration_date=date.fromisoformat('2025-10-31'),
            provider_record=self.test_data_generator.generate_default_provider(
                {
                    'providerId': provider_uuid,
                    'privilegeJurisdictions': set(jurisdictions),
                    'licenseJurisdiction': 'oh',
                }
            ),
            existing_privileges_for_license=original_privileges,
            compact_transaction_id='test_transaction_id',
            attestations=self.sample_privilege_attestations,
            license_type='audiologist',
        )

        # Verify that all privileges were updated
        provider_user_records: ProviderUserRecords = self.config.data_client.get_provider_user_records(
            compact='aslp', provider_id=provider_uuid, include_updates=True
        )

        for jurisdiction in jurisdictions:
            # Get the privilege record using ProviderUserRecords
            privilege_record = provider_user_records.get_specific_privilege_record(
                jurisdiction=jurisdiction, license_abbreviation='aud'
            )
            self.assertIsNotNone(privilege_record, f'Privilege record not found for jurisdiction {jurisdiction}')
            self.assertEqual('2025-10-31', privilege_record.dateOfExpiration.isoformat())
            self.assertEqual('test_transaction_id', privilege_record.compactTransactionId)

            # Get the update record using ProviderUserRecords
            update_records = provider_user_records.get_update_records_for_privilege(
                jurisdiction=jurisdiction, license_type=privilege_record.licenseType
            )
            self.assertEqual(1, len(update_records), f'Expected 1 update record for jurisdiction {jurisdiction}')
            update_record = update_records[0]
            self.assertEqual('renewal', update_record.updateType)
            self.assertEqual('2024-10-31', update_record.previous['dateOfExpiration'].isoformat())
            self.assertEqual('2025-10-31', update_record.updatedValues['dateOfExpiration'].isoformat())

        # Verify the provider record was updated correctly
        provider = self._provider_table.get_item(
            Key={'pk': f'aslp#PROVIDER#{provider_uuid}', 'sk': 'aslp#PROVIDER'},
        )['Item']
        self.assertEqual(set(jurisdictions), provider['privilegeJurisdictions'])

    def test_data_client_rolls_back_failed_large_privilege_purchase(self):
        """Test that we properly roll back when a large privilege purchase fails."""
        from botocore.exceptions import ClientError
        from cc_common.data_model.data_client import DataClient
        from cc_common.data_model.schema.common import ActiveInactiveStatus
        from cc_common.data_model.schema.privilege import PrivilegeData

        test_data_client = DataClient(self.config)
        provider_uuid = str(uuid4())

        # use first 51 jurisdictions (will create 102 records - 51 privileges and 51 updates)
        jurisdictions = [jurisdiction for jurisdiction in self.config.jurisdictions[0:51]]
        original_privileges = []

        # Create original privileges that will be updated
        for jurisdiction in jurisdictions:
            original_privilege = PrivilegeData.create_new(
                {
                    'type': 'privilege',
                    'providerId': provider_uuid,
                    'compact': 'aslp',
                    'jurisdiction': jurisdiction,
                    'licenseJurisdiction': 'oh',
                    'licenseType': 'audiologist',
                    'privilegeId': f'AUD-{jurisdiction.upper()}-1',
                    'dateOfIssuance': datetime(2023, 11, 8, 23, 59, 59, tzinfo=UTC),
                    'dateOfRenewal': datetime(2023, 11, 8, 23, 59, 59, tzinfo=UTC),
                    'dateOfExpiration': date(2024, 10, 31),
                    'dateOfUpdate': datetime(2023, 11, 8, 23, 59, 59, tzinfo=UTC),
                    'compactTransactionId': '1234567890',
                    'administratorSetStatus': ActiveInactiveStatus.ACTIVE,
                    'attestations': [],
                }
            )
            self._provider_table.put_item(Item=original_privilege.serialize_to_database_record())
            original_privileges.append(original_privilege)

        # Store original provider record
        original_provider = self.test_data_generator.put_default_provider_record_in_provider_table(
            value_overrides={
                'providerId': provider_uuid,
                'compact': 'aslp',
                'licenseJurisdiction': 'oh',
                'privilegeJurisdictions': set(jurisdictions),
            }
        )

        # Mock DynamoDB to fail after first batch
        original_transact_write_items = self.config.dynamodb_client.transact_write_items
        call_count = 0

        def mock_transact_write_items(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:  # Fail on second batch
                raise ClientError(
                    {'Error': {'Code': 'TransactionCanceledException', 'Message': 'Test error'}},
                    'TransactWriteItems',
                )
            return original_transact_write_items(**kwargs)

        self.config.dynamodb_client.transact_write_items = mock_transact_write_items

        # Attempt to update all privileges (should fail)
        with self.assertRaises(CCAwsServiceException):
            test_data_client.create_provider_privileges(
                compact='aslp',
                provider_id=provider_uuid,
                jurisdiction_postal_abbreviations=jurisdictions,
                license_expiration_date=date.fromisoformat('2025-10-31'),
                provider_record=original_provider,
                existing_privileges_for_license=original_privileges,
                compact_transaction_id='test_transaction_id',
                attestations=self.sample_privilege_attestations,
                license_type='audiologist',
            )

        # Verify that all privileges were restored to their original state
        for jurisdiction in jurisdictions:
            privilege_records = self._provider_table.query(
                KeyConditionExpression=Key('pk').eq(f'aslp#PROVIDER#{provider_uuid}')
                & Key('sk').begins_with(f'aslp#PROVIDER#privilege/{jurisdiction}/aud#'),
            )['Items']

            self.assertEqual(1, len(privilege_records))  # Only the original privilege record should exist
            privilege_record = privilege_records[0]

            self.assertEqual('2024-10-31', privilege_record['dateOfExpiration'])
            self.assertEqual('1234567890', privilege_record['compactTransactionId'])

        # Verify the provider record was restored to its original state
        provider = self._provider_table.get_item(
            Key={'pk': f'aslp#PROVIDER#{provider_uuid}', 'sk': 'aslp#PROVIDER'},
        )['Item']
        self.assertEqual(set(jurisdictions), provider['privilegeJurisdictions'])

    def test_claim_privilege_id_creates_counter_if_not_exists(self):
        """Test that claiming a privilege id creates the counter if it doesn't exist"""
        from cc_common.data_model.data_client import DataClient

        client = DataClient(self.config)

        # First claim should create the counter and return 1
        privilege_count = client.claim_privilege_number(compact='aslp')
        self.assertEqual(1, privilege_count)

        # Verify the counter was created with the correct value
        counter_record = self.config.provider_table.get_item(
            Key={
                'pk': 'aslp#PRIVILEGE_COUNT',
                'sk': 'aslp#PRIVILEGE_COUNT',
            }
        )['Item']
        self.assertEqual(1, counter_record['privilegeCount'])

    def test_claim_privilege_id_increments_existing_counter(self):
        """Test that claiming a privilege id increments an existing counter"""
        from cc_common.data_model.data_client import DataClient

        client = DataClient(self.config)

        # Create initial counter record
        self.config.provider_table.put_item(
            Item={
                'pk': 'aslp#PRIVILEGE_COUNT',
                'sk': 'aslp#PRIVILEGE_COUNT',
                'type': 'privilegeCount',
                'compact': 'aslp',
                'privilegeCount': 42,
            }
        )

        # Claim should increment the counter and return 43
        privilege_count = client.claim_privilege_number(compact='aslp')
        self.assertEqual(43, privilege_count)

        # Verify the counter was incremented
        counter_record = self.config.provider_table.get_item(
            Key={
                'pk': 'aslp#PRIVILEGE_COUNT',
                'sk': 'aslp#PRIVILEGE_COUNT',
            }
        )['Item']
        self.assertEqual(43, counter_record['privilegeCount'])
        self.assertEqual('privilegeCount', counter_record['type'])
        self.assertEqual('aslp', counter_record['compact'])

    def test_get_ssn_by_provider_id_returns_ssn_if_provider_id_exists(self):
        """Test that get_ssn_by_provider_id returns the SSN if the provider ID exists"""
        from cc_common.data_model.data_client import DataClient

        client = DataClient(self.config)

        # Create a provider record with an SSN
        self._load_provider_data()

        ssn = client.get_ssn_by_provider_id(compact='aslp', provider_id='89a6377e-c3a5-40e5-bca5-317ec854c570')
        self.assertEqual('123-12-1234', ssn)

    def test_get_ssn_by_provider_id_raises_exception_if_provider_id_does_not_exist(self):
        """Test that get_ssn_by_provider_id returns the SSN if the provider ID exists"""
        from cc_common.data_model.data_client import DataClient
        from cc_common.exceptions import CCNotFoundException

        client = DataClient(self.config)

        # We didn't create the provider this time, so this won't exist
        with self.assertRaises(CCNotFoundException):
            client.get_ssn_by_provider_id(compact='aslp', provider_id='89a6377e-c3a5-40e5-bca5-317ec854c570')

    def test_get_ssn_by_provider_id_raises_exception_multiple_records_found(self):
        """Test that get_ssn_by_provider_id returns the SSN if the provider ID exists"""
        from cc_common.data_model.data_client import DataClient
        from cc_common.exceptions import CCInternalException

        client = DataClient(self.config)

        self._load_provider_data()
        # Put a duplicate record into the table, so this provider id has two SSNs associated with it
        self.config.ssn_table.put_item(
            Item={
                'pk': 'aslp#SSN#123-12-5678',
                'sk': 'aslp#SSN#123-12-5678',
                'providerIdGSIpk': 'aslp#PROVIDER#89a6377e-c3a5-40e5-bca5-317ec854c570',
                'compact': 'aslp',
                'ssn': '123-12-5678',
                'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570',
            }
        )

        with self.assertRaises(CCInternalException):
            client.get_ssn_by_provider_id(compact='aslp', provider_id='89a6377e-c3a5-40e5-bca5-317ec854c570')

    def test_deactivate_privilege_updates_record(self):
        from cc_common.data_model.data_client import DataClient
        from cc_common.data_model.provider_record_util import ProviderUserRecords

        provider_id = self._load_provider_data()

        # Create the first privilege
        original_privilege = {
            'pk': f'aslp#PROVIDER#{provider_id}',
            'sk': 'aslp#PROVIDER#privilege/ne/aud#',
            'type': 'privilege',
            'providerId': str(provider_id),
            'compact': 'aslp',
            'licenseJurisdiction': 'oh',
            'licenseType': 'audiologist',
            'jurisdiction': 'ne',
            'administratorSetStatus': 'active',
            'dateOfIssuance': '2023-11-08T23:59:59+00:00',
            'dateOfRenewal': '2023-11-08T23:59:59+00:00',
            'dateOfExpiration': '2024-10-31',
            'dateOfUpdate': '2023-11-08T23:59:59+00:00',
            'compactTransactionId': '1234567890',
            'compactTransactionIdGSIPK': 'COMPACT#aslp#TX#1234567890#',
            'attestations': self.sample_privilege_attestations,
            'privilegeId': 'AUD-NE-1',
        }
        self._provider_table.put_item(Item=original_privilege)

        test_data_client = DataClient(self.config)

        # Now, deactivate the privilege
        test_data_client.deactivate_privilege(
            compact='aslp',
            provider_id=provider_id,
            jurisdiction='ne',
            license_type_abbr='aud',
            deactivation_details={
                'note': 'test deactivation note',
                'deactivatedByStaffUserId': 'a4182428-d061-701c-82e5-a3d1d547d797',
                'deactivatedByStaffUserName': 'John Doe',
            },
        )

        # Verify that the privilege record was updated
        provider_user_records: ProviderUserRecords = self.config.data_client.get_provider_user_records(
            compact='aslp', provider_id=provider_id, include_updates=True
        )

        new_privilege = provider_user_records.get_specific_privilege_record(
            jurisdiction='ne', license_abbreviation='aud'
        )
        self.assertIsNotNone(new_privilege, 'Privilege record not found')

        self.assertEqual(
            {
                'pk': f'aslp#PROVIDER#{provider_id}',
                'sk': 'aslp#PROVIDER#privilege/ne/aud#',
                'type': 'privilege',
                'providerId': str(provider_id),
                'compact': 'aslp',
                'licenseJurisdiction': 'oh',
                'licenseType': 'audiologist',
                'jurisdiction': 'ne',
                'administratorSetStatus': 'inactive',
                'dateOfIssuance': '2023-11-08T23:59:59+00:00',
                'dateOfRenewal': '2023-11-08T23:59:59+00:00',
                'dateOfExpiration': '2024-10-31',
                'dateOfUpdate': '2024-11-08T23:59:59+00:00',
                'compactTransactionId': '1234567890',
                'compactTransactionIdGSIPK': 'COMPACT#aslp#TX#1234567890#',
                'attestations': self.sample_privilege_attestations,
                'privilegeId': 'AUD-NE-1',
            },
            new_privilege.serialize_to_database_record(),
        )

        # Get the update record
        update_records = provider_user_records.get_update_records_for_privilege(
            jurisdiction='ne', license_type=new_privilege.licenseType
        )
        self.assertEqual(1, len(update_records), 'Expected 1 update record')
        update_record = update_records[0]

        self.assertEqual(
            {
                'pk': f'aslp#PROVIDER#{provider_id}',
                'sk': 'aslp#PROV_UPDATE#privilege/ne/aud/1731110399/aac682a76e1182a641a1b40dd606ae51',
                'type': 'privilegeUpdate',
                'updateType': 'deactivation',
                'providerId': str(provider_id),
                'compact': 'aslp',
                'compactTransactionIdGSIPK': 'COMPACT#aslp#TX#1234567890#',
                'jurisdiction': 'ne',
                'licenseType': 'audiologist',
                'dateOfUpdate': '2024-11-08T23:59:59+00:00',
                'createDate': '2024-11-08T23:59:59+00:00',
                'effectiveDate': '2024-11-08T23:59:59+00:00',
                'deactivationDetails': {
                    'note': 'test deactivation note',
                    'deactivatedByStaffUserId': 'a4182428-d061-701c-82e5-a3d1d547d797',
                    'deactivatedByStaffUserName': 'John Doe',
                },
                'previous': {
                    'dateOfIssuance': '2023-11-08T23:59:59+00:00',
                    'dateOfRenewal': '2023-11-08T23:59:59+00:00',
                    'dateOfExpiration': '2024-10-31',
                    'dateOfUpdate': '2023-11-08T23:59:59+00:00',
                    'compactTransactionId': '1234567890',
                    'attestations': self.sample_privilege_attestations,
                    'administratorSetStatus': 'active',
                    'licenseJurisdiction': 'oh',
                    'privilegeId': 'AUD-NE-1',
                },
                'updatedValues': {
                    'administratorSetStatus': 'inactive',
                },
            },
            update_record.serialize_to_database_record(),
        )

        # The deactivation should not remove 'ne' from privilegeJurisdictions, as that set is intended to include
        # all active/inactive privileges associated with the provider
        provider = self._provider_table.get_item(
            Key={'pk': f'aslp#PROVIDER#{provider_id}', 'sk': 'aslp#PROVIDER'},
        )['Item']
        self.assertEqual({'ne'}, provider.get('privilegeJurisdictions', set()))

    def test_deactivate_privilege_raises_if_privilege_not_found(self):
        from cc_common.data_model.data_client import DataClient
        from cc_common.exceptions import CCNotFoundException

        test_data_client = DataClient(self.config)

        # We haven't created any providers or privileges but we'll try to deactivate a privilege
        with self.assertRaises(CCNotFoundException):
            test_data_client.deactivate_privilege(
                compact='aslp',
                provider_id='some-provider-id',
                jurisdiction='ne',
                license_type_abbr='aud',
                deactivation_details={
                    'note': 'test deactivation note',
                    'deactivatedByStaffUserId': 'a4182428-d061-701c-82e5-a3d1d547d797',
                    'deactivatedByStaffUserName': 'John Doe',
                },
            )

    def test_deactivate_privilege_on_inactive_privilege_raises_exception(self):
        from cc_common.data_model.data_client import DataClient
        from cc_common.data_model.provider_record_util import ProviderUserRecords

        provider_id = self._load_provider_data()

        # Remove 'ne' from privilegeJurisdictions
        self._provider_table.update_item(
            Key={'pk': f'aslp#PROVIDER#{provider_id}', 'sk': 'aslp#PROVIDER'},
            UpdateExpression='DELETE privilegeJurisdictions :jurisdiction',
            ExpressionAttributeValues={':jurisdiction': {'ne'}},
        )

        # Create the first privilege
        original_privilege = {
            'pk': f'aslp#PROVIDER#{provider_id}',
            'sk': 'aslp#PROVIDER#privilege/ne/aud#',
            'type': 'privilege',
            'providerId': str(provider_id),
            'compact': 'aslp',
            'jurisdiction': 'ne',
            'licenseJurisdiction': 'oh',
            'licenseType': 'audiologist',
            'administratorSetStatus': 'inactive',
            'dateOfIssuance': '2023-11-08T23:59:59+00:00',
            'dateOfRenewal': '2023-11-08T23:59:59+00:00',
            'dateOfExpiration': '2024-10-31',
            'dateOfUpdate': '2023-11-08T23:59:59+00:00',
            'compactTransactionId': '1234567890',
            'compactTransactionIdGSIPK': 'COMPACT#aslp#TX#1234567890#',
            'attestations': self.sample_privilege_attestations,
            'privilegeId': 'AUD-NE-1',
        }
        self._provider_table.put_item(Item=original_privilege)
        # We'll create it as if it were already deactivated
        original_history = {
            'pk': f'aslp#PROVIDER#{provider_id}',
            'sk': 'aslp#PROV_UPDATE#privilege/ne/aud/1731110399/4ebb3dc8f1ffcc30fe7aad5ec49d0ca6',
            'type': 'privilegeUpdate',
            'updateType': 'renewal',
            'providerId': str(provider_id),
            'compact': 'aslp',
            'licenseType': 'audiologist',
            'createDate': '2024-11-08T23:59:59+00:00',
            'effectiveDate': '2024-11-08T23:59:59+00:00',
            'compactTransactionIdGSIPK': 'COMPACT#aslp#TX#1234567890#',
            'jurisdiction': 'ne',
            'dateOfUpdate': '2024-11-08T23:59:59+00:00',
            'previous': {
                'dateOfIssuance': '2023-11-08T23:59:59+00:00',
                'dateOfRenewal': '2023-11-08T23:59:59+00:00',
                'dateOfExpiration': '2024-10-31',
                'dateOfUpdate': '2023-11-08T23:59:59+00:00',
                'compactTransactionId': '1234567890',
                'attestations': self.sample_privilege_attestations,
                'licenseJurisdiction': 'oh',
                'privilegeId': 'AUD-NE-1',
            },
            'updatedValues': {
                'administratorSetStatus': 'inactive',
            },
        }
        self._provider_table.put_item(Item=original_history)

        test_data_client = DataClient(self.config)

        # Now, deactivate the privilege
        with self.assertRaises(CCInvalidRequestException) as context:
            test_data_client.deactivate_privilege(
                compact='aslp',
                provider_id=provider_id,
                jurisdiction='ne',
                license_type_abbr='aud',
                deactivation_details={
                    'note': 'test deactivation note',
                    'deactivatedByStaffUserId': 'a4182428-d061-701c-82e5-a3d1d547d797',
                    'deactivatedByStaffUserName': 'John Doe',
                },
            )
        self.assertEqual('Privilege already deactivated', context.exception.message)

        # Verify that the privilege record was unchanged
        provider_user_records: ProviderUserRecords = self.config.data_client.get_provider_user_records(
            compact='aslp', provider_id=provider_id, include_updates=True
        )

        new_privilege = provider_user_records.get_specific_privilege_record(
            jurisdiction='ne', license_abbreviation='aud'
        )
        self.assertIsNotNone(new_privilege, 'Privilege record not found')
        serialized_record = new_privilege.serialize_to_database_record()
        # the serialize_to_database_record() call automatically generates a new dateOfUpdate stamp,
        # setting it back to the original timestamp for comparison
        serialized_record['dateOfUpdate'] = original_privilege['dateOfUpdate']
        self.assertEqual(original_privilege, serialized_record)

        # Verify the update record is unchanged
        update_records = provider_user_records.get_update_records_for_privilege(
            jurisdiction='ne', license_type=new_privilege.licenseType
        )
        self.assertEqual(1, len(update_records), 'Expected 1 update record')
        self.assertEqual(original_history, update_records[0].serialize_to_database_record())

        # 'ne' should still be removed from privilegeJurisdictions
        provider = provider_user_records.get_provider_record()
        self.assertEqual(set(), provider.privilegeJurisdictions)

    def test_get_provider_user_records_correctly_handles_pagination(self):
        """Test that get_provider_user_records correctly handles pagination by returning all records.

        This test ensures the fix for a bug where only the last page of results was being returned,
        discarding everything collected in previous iterations.
        """
        from cc_common.data_model.data_client import DataClient

        # Create a client
        client = DataClient(self.config)

        # Create a provider record
        provider_uuid = str(uuid4())
        self.test_data_generator.put_default_provider_record_in_provider_table(
            value_overrides={
                'providerId': provider_uuid,
                'compact': 'aslp',
            }
        )

        # Creating 30 records, to test pagination with 10 records at a time.
        jurisdictions = self.config.jurisdictions[:30]
        for jurisdiction in jurisdictions:
            self.test_data_generator.put_default_privilege_record_in_provider_table(
                value_overrides={
                    'providerId': provider_uuid,
                    'compact': 'aslp',
                    'jurisdiction': jurisdiction,
                    'licenseType': 'audiologist',
                    'privilegeId': f'AUD-{jurisdiction.upper()}-1',
                    'dateOfIssuance': datetime(2023, 11, 8, 23, 59, 59, tzinfo=UTC),
                    'dateOfRenewal': datetime(2023, 11, 8, 23, 59, 59, tzinfo=UTC),
                    'dateOfExpiration': date(2024, 10, 31),
                    'dateOfUpdate': datetime(2023, 11, 8, 23, 59, 59, tzinfo=UTC),
                    'compactTransactionId': '1234567890',
                    'administratorSetStatus': 'active',
                    'attestations': [],
                }
            )

        # Create license records for each jurisdiction as well
        for jurisdiction in jurisdictions:
            self.test_data_generator.put_default_license_record_in_provider_table(
                value_overrides={
                    'providerId': provider_uuid,
                    'compact': 'aslp',
                    'jurisdiction': jurisdiction,
                    'licenseType': 'audiologist',
                }
            )

        # Override the DynamoDB query method to force pagination with a small limit
        original_query = self.config.provider_table.query

        def mock_query(**kwargs):
            # Force a small page size to ensure pagination
            kwargs['Limit'] = 10
            return original_query(**kwargs)

        self.config.provider_table.query = mock_query

        try:
            # Call the method that should handle pagination correctly
            provider_records = client.get_provider_user_records(compact='aslp', provider_id=provider_uuid)

            # Verify that we got all the records
            # We expect 1 provider record + 30 privilege records + 30 license records = 61 total
            self.assertEqual(61, len(provider_records.provider_records))

            # Check that we have all the different record types
            record_types = {record['type'] for record in provider_records.provider_records}
            self.assertEqual({'provider', 'privilege', 'license'}, record_types)

            # Verify we have all privileges from all jurisdictions
            privilege_records = provider_records.get_privilege_records()
            self.assertEqual(30, len(privilege_records))
            privilege_jurisdictions = {priv.jurisdiction for priv in privilege_records}
            self.assertEqual(set(jurisdictions), privilege_jurisdictions)

            # Verify we have all license records
            license_records = provider_records.get_license_records()
            self.assertEqual(30, len(license_records))
            license_jurisdictions = {lic.jurisdiction for lic in license_records}
            self.assertEqual(set(jurisdictions), license_jurisdictions)

        finally:
            # Restore the original query method
            self.config.provider_table.query = original_query

    def test_create_privilege_investigation_success(self):
        """Test successful creation of privilege investigation"""
        from cc_common.data_model.data_client import DataClient

        # Load test data
        provider_id = self._load_provider_data()

        client = DataClient(self.config)

        # Create investigation data using test data generator
        investigation = self.test_data_generator.generate_default_investigation(
            {
                'providerId': provider_id,
                'compact': 'aslp',
                'jurisdiction': 'ne',
                'licenseType': 'speech-language pathologist',
                'investigationAgainst': 'privilege',
            }
        )

        # Call the method
        client.create_investigation(investigation)

        # Verify investigation record was created
        investigation_records = self.config.provider_table.query(
            KeyConditionExpression=Key('pk').eq(f'aslp#PROVIDER#{provider_id}')
            & Key('sk').begins_with('aslp#PROVIDER#privilege/ne/slp#INVESTIGATION#')
        )['Items']

        self.assertEqual(1, len(investigation_records))
        investigation_record = investigation_records[0]

        # Verify the complete investigation record structure
        expected_investigation = {
            'pk': f'aslp#PROVIDER#{provider_id}',
            'sk': f'aslp#PROVIDER#privilege/ne/slp#INVESTIGATION#{investigation.investigationId}',
            'type': 'investigation',
            'compact': 'aslp',
            'providerId': str(provider_id),
            'jurisdiction': 'ne',
            'licenseType': 'speech-language pathologist',
            'investigationAgainst': 'privilege',
            'investigationId': str(investigation.investigationId),
            'submittingUser': str(investigation.submittingUser),
            'creationDate': investigation.creationDate.isoformat(),
        }
        # Pop dynamic fields that we don't want to assert on
        investigation_record.pop('dateOfUpdate')

        self.assertEqual(expected_investigation, investigation_record)

        # Verify privilege record was updated with investigation status
        privilege_records = self.config.provider_table.query(
            KeyConditionExpression=Key('pk').eq(f'aslp#PROVIDER#{provider_id}')
            & Key('sk').eq('aslp#PROVIDER#privilege/ne/slp#')
        )['Items']

        self.assertEqual(1, len(privilege_records))
        privilege_record = privilege_records[0]
        self.assertEqual('underInvestigation', privilege_record['investigationStatus'])

        # Verify update record was created
        update_records = self.config.provider_table.query(
            KeyConditionExpression=Key('pk').eq(f'aslp#PROVIDER#{provider_id}')
            & Key('sk').begins_with('aslp#PROVIDER#privilege/ne/slp#UPDATE#')
        )['Items']

        self.assertEqual(1, len(update_records))
        update_record = update_records[0]

        # Verify the complete update record structure
        expected_update = {
            'pk': f'aslp#PROVIDER#{provider_id}',
            'compactTransactionIdGSIPK': 'COMPACT#aslp#TX#1234567890#',
            'type': 'privilegeUpdate',
            'updateType': 'investigation',
            'compact': 'aslp',
            'providerId': str(provider_id),
            'jurisdiction': 'ne',
            'licenseType': 'speech-language pathologist',
            'createDate': investigation.creationDate.isoformat(),
            'effectiveDate': investigation.creationDate.isoformat(),
            'previous': {
                'administratorSetStatus': 'active',
                'attestations': [{'attestationId': 'jurisprudence-confirmation', 'version': '1'}],
                'compactTransactionId': '1234567890',
                'dateOfExpiration': '2025-04-04',
                'dateOfIssuance': '2016-05-05T12:59:59+00:00',
                'dateOfRenewal': '2020-05-05T12:59:59+00:00',
                'dateOfUpdate': '2020-05-05T12:59:59+00:00',
                'licenseJurisdiction': 'oh',
                'privilegeId': 'SLP-NE-1',
            },
            'updatedValues': {
                'investigationStatus': 'underInvestigation',
            },
            'investigationDetails': {
                'investigationId': str(investigation.investigationId),
            },
        }
        # Pop dynamic fields that we don't want to assert on
        update_record.pop('dateOfUpdate')
        update_record.pop('sk')

        self.assertEqual(expected_update, update_record)

    def test_create_license_investigation_success(self):
        """Test successful creation of license investigation"""
        from cc_common.data_model.data_client import DataClient
        from cc_common.data_model.schema.investigation import InvestigationData

        # Load test data
        provider_id = self._load_provider_data()

        client = DataClient(self.config)

        # Create investigation data
        investigation = InvestigationData.create_new(
            {
                'providerId': provider_id,
                'compact': 'aslp',
                'jurisdiction': 'oh',
                'licenseTypeAbbreviation': 'slp',
                'licenseType': 'speech-language pathologist',
                'investigationAgainst': 'license',
                'submittingUser': str(uuid4()),
                'creationDate': datetime.fromisoformat('2024-11-08T23:59:59+00:00'),
                'investigationId': str(uuid4()),
            }
        )

        # Call the method
        client.create_investigation(investigation)

        # Verify investigation record was created
        investigation_records = self.config.provider_table.query(
            KeyConditionExpression=Key('pk').eq(f'aslp#PROVIDER#{provider_id}')
            & Key('sk').begins_with('aslp#PROVIDER#license/oh/slp#INVESTIGATION#')
        )['Items']

        self.assertEqual(1, len(investigation_records))
        investigation_record = investigation_records[0]

        # Verify the complete investigation record structure
        expected_investigation = {
            'pk': f'aslp#PROVIDER#{provider_id}',
            'sk': f'aslp#PROVIDER#license/oh/slp#INVESTIGATION#{investigation.investigationId}',
            'type': 'investigation',
            'compact': 'aslp',
            'providerId': str(provider_id),
            'jurisdiction': 'oh',
            'licenseType': 'speech-language pathologist',
            'investigationAgainst': 'license',
            'investigationId': str(investigation.investigationId),
            'submittingUser': str(investigation.submittingUser),
            'creationDate': investigation.creationDate.isoformat(),
        }
        # Pop dynamic fields that we don't want to assert on
        investigation_record.pop('dateOfUpdate')

        self.assertEqual(expected_investigation, investigation_record)

        # Verify license record was updated with investigation status
        license_records = self.config.provider_table.query(
            KeyConditionExpression=Key('pk').eq(f'aslp#PROVIDER#{provider_id}')
            & Key('sk').eq('aslp#PROVIDER#license/oh/slp#')
        )['Items']

        self.assertEqual(1, len(license_records))
        license_record = license_records[0]
        self.assertEqual('underInvestigation', license_record['investigationStatus'])

        # Verify update record was created
        update_records = self.config.provider_table.query(
            KeyConditionExpression=Key('pk').eq(f'aslp#PROVIDER#{provider_id}')
            & Key('sk').begins_with('aslp#PROVIDER#license/oh/slp#UPDATE#')
        )['Items']

        self.assertEqual(1, len(update_records))
        update_record = update_records[0]

        # Verify the complete update record structure
        expected_update = {
            'pk': f'aslp#PROVIDER#{provider_id}',
            'type': 'licenseUpdate',
            'updateType': 'investigation',
            'compact': 'aslp',
            'providerId': str(provider_id),
            'jurisdiction': 'oh',
            'licenseType': 'speech-language pathologist',
            'createDate': investigation.creationDate.isoformat(),
            'effectiveDate': investigation.creationDate.isoformat(),
            'previous': {
                'npi': '0608337260',
                'licenseNumber': 'A0608337260',
                'ssnLastFour': '1234',
                'givenName': 'Björk',
                'middleName': 'Gunnar',
                'familyName': 'Guðmundsdóttir',
                'dateOfUpdate': '2024-06-06T12:59:59+00:00',
                'dateOfIssuance': '2010-06-06',
                'dateOfRenewal': '2020-04-04',
                'dateOfExpiration': '2025-04-04',
                'dateOfBirth': '1985-06-06',
                'homeAddressStreet1': '123 A St.',
                'homeAddressStreet2': 'Apt 321',
                'homeAddressCity': 'Columbus',
                'homeAddressState': 'oh',
                'homeAddressPostalCode': '43004',
                'emailAddress': 'björk@example.com',
                'phoneNumber': '+13213214321',
                'licenseStatusName': 'DEFINITELY_A_HUMAN',
                'jurisdictionUploadedLicenseStatus': 'active',
                'jurisdictionUploadedCompactEligibility': 'eligible',
            },
            'updatedValues': {
                'investigationStatus': 'underInvestigation',
            },
            'investigationDetails': {
                'investigationId': str(investigation.investigationId),
            },
        }
        # Pop dynamic fields that we don't want to assert on
        update_record.pop('dateOfUpdate')
        update_record.pop('sk')

        self.assertEqual(expected_update, update_record)

    def test_create_privilege_investigation_privilege_not_found(self):
        """Test creation of privilege investigation when privilege doesn't exist"""
        from cc_common.data_model.data_client import DataClient
        from cc_common.data_model.schema.investigation import InvestigationData
        from cc_common.exceptions import CCNotFoundException

        # Load test data, privilege in Nebraska, license in Ohio
        provider_id = self._load_provider_data()

        client = DataClient(self.config)

        # Create investigation data for non-existent privilege (no privilege in Ohio)
        investigation = InvestigationData.create_new(
            {
                'providerId': str(provider_id),
                'compact': 'aslp',
                'jurisdiction': 'oh',
                'licenseTypeAbbreviation': 'slp',
                'licenseType': 'speech-language pathologist',
                'investigationAgainst': 'privilege',
                'submittingUser': str(uuid4()),
                'creationDate': datetime.fromisoformat('2024-11-08T23:59:59+00:00'),
                'investigationId': str(uuid4()),
            }
        )

        # Call the method and expect exception
        with self.assertRaises(CCNotFoundException) as context:
            client.create_investigation(investigation)

        self.assertIn('Privilege not found', str(context.exception))

    def test_create_license_investigation_license_not_found(self):
        """Test creation of license investigation when license doesn't exist"""
        from cc_common.data_model.data_client import DataClient
        from cc_common.data_model.schema.investigation import InvestigationData
        from cc_common.exceptions import CCNotFoundException

        # Load test data, privilege in Nebraska, license in Ohio
        provider_id = self._load_provider_data()

        client = DataClient(self.config)

        # Create investigation data for non-existent license (no license in Nebraska)
        investigation = InvestigationData.create_new(
            {
                'providerId': str(provider_id),
                'compact': 'aslp',
                'jurisdiction': 'ne',
                'licenseTypeAbbreviation': 'slp',
                'licenseType': 'speech-language pathologist',
                'investigationAgainst': 'license',
                'submittingUser': str(uuid4()),
                'creationDate': datetime.fromisoformat('2024-11-08T23:59:59+00:00'),
                'investigationId': str(uuid4()),
            }
        )

        # Call the method and expect exception
        with self.assertRaises(CCNotFoundException) as context:
            client.create_investigation(investigation)

        self.assertIn('License not found', str(context.exception))

    def test_close_privilege_investigation_success(self):
        """Test successful closing of privilege investigation"""
        from cc_common.data_model.data_client import DataClient
        from cc_common.data_model.schema.common import InvestigationAgainstEnum
        from cc_common.data_model.schema.investigation import InvestigationData

        # Load test data
        provider_id = self._load_provider_data()

        client = DataClient(self.config)

        # First create an investigation
        investigation = InvestigationData.create_new(
            {
                'providerId': provider_id,
                'compact': 'aslp',
                'jurisdiction': 'ne',
                'licenseTypeAbbreviation': 'slp',
                'licenseType': 'speech-language pathologist',
                'investigationAgainst': 'privilege',
                'submittingUser': str(uuid4()),
                'creationDate': datetime.fromisoformat('2024-11-08T23:59:59+00:00'),
                'investigationId': uuid4(),
            }
        )

        client.create_investigation(investigation)

        # Now close the investigation
        closing_user = str(uuid4())
        client.close_investigation(
            compact='aslp',
            provider_id=provider_id,
            jurisdiction='ne',
            license_type_abbreviation='slp',
            investigation_id=investigation.investigationId,
            closing_user=closing_user,
            close_date=datetime.fromisoformat('2024-11-08T23:59:59+00:00'),
            investigation_against=InvestigationAgainstEnum.PRIVILEGE,
        )

        # Verify investigation record was updated with close information
        investigation_records = self.config.provider_table.query(
            KeyConditionExpression=Key('pk').eq(f'aslp#PROVIDER#{provider_id}')
            & Key('sk').begins_with('aslp#PROVIDER#privilege/ne/slp#INVESTIGATION#')
        )['Items']

        self.assertEqual(1, len(investigation_records))
        investigation_record = investigation_records[0]

        # Verify the investigation record was updated with close information
        expected_investigation_close = {
            'pk': f'aslp#PROVIDER#{provider_id}',
            'sk': f'aslp#PROVIDER#privilege/ne/slp#INVESTIGATION#{investigation.investigationId}',
            'type': 'investigation',
            'compact': 'aslp',
            'providerId': str(provider_id),
            'jurisdiction': 'ne',
            'licenseType': 'speech-language pathologist',
            'investigationAgainst': 'privilege',
            'investigationId': str(investigation.investigationId),
            'submittingUser': str(investigation.submittingUser),
            'creationDate': investigation.creationDate.isoformat(),
            'closeDate': investigation.creationDate.isoformat(),
            'closingUser': closing_user,
        }
        # Pop dynamic fields that we don't want to assert on
        investigation_record.pop('dateOfUpdate')

        self.assertEqual(expected_investigation_close, investigation_record)

        # Verify privilege record no longer has investigation status
        privilege_records = self.config.provider_table.query(
            KeyConditionExpression=Key('pk').eq(f'aslp#PROVIDER#{provider_id}')
            & Key('sk').eq('aslp#PROVIDER#privilege/ne/slp#')
        )['Items']

        self.assertEqual(1, len(privilege_records))
        privilege_record = privilege_records[0]
        self.assertNotIn('investigationStatus', privilege_record)

        # Verify update record was created for closure
        update_records = self.config.provider_table.query(
            KeyConditionExpression=Key('pk').eq(f'aslp#PROVIDER#{provider_id}')
            & Key('sk').begins_with('aslp#PROVIDER#privilege/ne/slp#UPDATE#')
        )['Items']

        # Should have 2 update records: one for creation, one for closure
        self.assertEqual(2, len(update_records))

        # Find the closure update record
        closure_update = None
        for update_record in update_records:
            if update_record.get('updateType') == 'closingInvestigation':
                closure_update = update_record
                break

        self.assertIsNotNone(closure_update, 'Closure update record not found!')

        # Verify the complete closure update record structure
        expected_closure_update = {
            'pk': f'aslp#PROVIDER#{provider_id}',
            'type': 'privilegeUpdate',
            'updateType': 'closingInvestigation',
            'compact': 'aslp',
            'providerId': str(provider_id),
            'jurisdiction': 'ne',
            'licenseType': 'speech-language pathologist',
            'createDate': investigation.creationDate.isoformat(),
            'effectiveDate': investigation.creationDate.isoformat(),
            'previous': {
                'administratorSetStatus': 'active',
                'attestations': [{'attestationId': 'jurisprudence-confirmation', 'version': '1'}],
                'compactTransactionId': '1234567890',
                'dateOfExpiration': '2025-04-04',
                'dateOfIssuance': '2016-05-05T12:59:59+00:00',
                'dateOfRenewal': '2020-05-05T12:59:59+00:00',
                'dateOfUpdate': '2024-11-08T23:59:59+00:00',
                'licenseJurisdiction': 'oh',
                'privilegeId': 'SLP-NE-1',
                'investigationStatus': 'underInvestigation',
            },
            'updatedValues': {},
            'removedValues': ['investigationStatus'],
        }
        # Pop dynamic fields that we don't want to assert on
        closure_update.pop('dateOfUpdate')
        closure_update.pop('sk')
        # Only pop compactTransactionIdGSIPK if it exists
        if 'compactTransactionIdGSIPK' in closure_update:
            closure_update.pop('compactTransactionIdGSIPK')

        self.assertEqual(expected_closure_update, closure_update)

    def test_close_license_investigation_success(self):
        """Test successful closing of license investigation"""
        from cc_common.data_model.data_client import DataClient
        from cc_common.data_model.schema.common import InvestigationAgainstEnum
        from cc_common.data_model.schema.investigation import InvestigationData

        # Load test data
        provider_id = self._load_provider_data()

        client = DataClient(self.config)

        # First create an investigation
        investigation = InvestigationData.create_new(
            {
                'providerId': provider_id,
                'compact': 'aslp',
                'jurisdiction': 'oh',
                'licenseTypeAbbreviation': 'slp',
                'licenseType': 'speech-language pathologist',
                'investigationAgainst': 'license',
                'submittingUser': str(uuid4()),
                'creationDate': datetime.fromisoformat('2024-11-08T23:59:59+00:00'),
                'investigationId': str(uuid4()),
            }
        )

        client.create_investigation(investigation)

        # Now close the investigation
        closing_user = str(uuid4())
        close_date = datetime.fromisoformat('2024-11-08T23:59:59+00:00')
        client.close_investigation(
            compact='aslp',
            provider_id=provider_id,
            jurisdiction='oh',
            license_type_abbreviation='slp',
            investigation_id=investigation.investigationId,
            closing_user=closing_user,
            close_date=close_date,
            investigation_against=InvestigationAgainstEnum.LICENSE,
        )

        # Verify investigation record was updated with close information
        investigation_records = self.config.provider_table.query(
            KeyConditionExpression=Key('pk').eq(f'aslp#PROVIDER#{provider_id}')
            & Key('sk').begins_with('aslp#PROVIDER#license/oh/slp#INVESTIGATION#')
        )['Items']

        self.assertEqual(1, len(investigation_records))
        investigation_record = investigation_records[0]

        # Verify the investigation record was updated with close information
        expected_investigation_close = {
            'pk': f'aslp#PROVIDER#{provider_id}',
            'sk': f'aslp#PROVIDER#license/oh/slp#INVESTIGATION#{investigation.investigationId}',
            'type': 'investigation',
            'compact': 'aslp',
            'providerId': str(provider_id),
            'jurisdiction': 'oh',
            'licenseType': 'speech-language pathologist',
            'investigationAgainst': 'license',
            'investigationId': str(investigation.investigationId),
            'submittingUser': str(investigation.submittingUser),
            'creationDate': investigation.creationDate.isoformat(),
            'closeDate': close_date.isoformat(),
            'closingUser': closing_user,
        }
        # Pop dynamic fields that we don't want to assert on
        investigation_record.pop('dateOfUpdate')

        self.assertEqual(expected_investigation_close, investigation_record)

        # Verify license record no longer has investigation status
        license_records = self.config.provider_table.query(
            KeyConditionExpression=Key('pk').eq(f'aslp#PROVIDER#{provider_id}')
            & Key('sk').eq('aslp#PROVIDER#license/oh/slp#')
        )['Items']

        self.assertEqual(1, len(license_records))
        license_record = license_records[0]
        self.assertNotIn('investigationStatus', license_record)

        # Verify update record was created for closure
        update_records = self.config.provider_table.query(
            KeyConditionExpression=Key('pk').eq(f'aslp#PROVIDER#{provider_id}')
            & Key('sk').begins_with('aslp#PROVIDER#license/oh/slp#UPDATE#')
        )['Items']

        # Should have 2 update records: one for creation, one for closure
        self.assertEqual(2, len(update_records))

        # Find the closure update record
        closure_update = None
        for update_record in update_records:
            if update_record.get('updateType') == 'closingInvestigation':
                closure_update = update_record
                break

        self.assertIsNotNone(closure_update, 'Closure update not found!')

        # Verify the complete closure update record structure
        expected_closure_update = {
            'pk': f'aslp#PROVIDER#{provider_id}',
            'type': 'licenseUpdate',
            'updateType': 'closingInvestigation',
            'compact': 'aslp',
            'providerId': str(provider_id),
            'jurisdiction': 'oh',
            'licenseType': 'speech-language pathologist',
            'createDate': investigation.creationDate.isoformat(),
            'effectiveDate': investigation.creationDate.isoformat(),
            'previous': {
                'npi': '0608337260',
                'licenseNumber': 'A0608337260',
                'ssnLastFour': '1234',
                'givenName': 'Björk',
                'middleName': 'Gunnar',
                'familyName': 'Guðmundsdóttir',
                'dateOfUpdate': '2024-11-08T23:59:59+00:00',
                'dateOfIssuance': '2010-06-06',
                'dateOfRenewal': '2020-04-04',
                'dateOfExpiration': '2025-04-04',
                'dateOfBirth': '1985-06-06',
                'homeAddressStreet1': '123 A St.',
                'homeAddressStreet2': 'Apt 321',
                'homeAddressCity': 'Columbus',
                'homeAddressState': 'oh',
                'homeAddressPostalCode': '43004',
                'emailAddress': 'björk@example.com',
                'phoneNumber': '+13213214321',
                'licenseStatusName': 'DEFINITELY_A_HUMAN',
                'jurisdictionUploadedLicenseStatus': 'active',
                'jurisdictionUploadedCompactEligibility': 'eligible',
                'investigationStatus': 'underInvestigation',
            },
            'updatedValues': {},
            'removedValues': ['investigationStatus'],
        }
        # Pop dynamic fields that we don't want to assert on
        closure_update.pop('dateOfUpdate')
        closure_update.pop('sk')

        self.assertEqual(expected_closure_update, closure_update)

    def test_close_privilege_investigation_not_found(self):
        """Test closing privilege investigation when investigation doesn't exist"""
        from cc_common.data_model.data_client import DataClient
        from cc_common.data_model.schema.common import InvestigationAgainstEnum
        from cc_common.exceptions import CCNotFoundException

        # Load test data
        provider_id = self._load_provider_data()

        client = DataClient(self.config)

        # Try to close a non-existent investigation
        with self.assertRaises(CCNotFoundException) as context:
            client.close_investigation(
                compact='aslp',
                provider_id=provider_id,
                jurisdiction='ne',
                license_type_abbreviation='slp',
                investigation_id=uuid4(),
                closing_user=str(uuid4()),
                close_date=datetime.fromisoformat('2024-11-08T23:59:59+00:00'),
                investigation_against=InvestigationAgainstEnum.PRIVILEGE,
            )

        self.assertIn('Investigation not found', str(context.exception))

    def test_close_license_investigation_not_found(self):
        """Test closing license investigation when investigation doesn't exist"""
        from cc_common.data_model.data_client import DataClient
        from cc_common.data_model.schema.common import InvestigationAgainstEnum
        from cc_common.exceptions import CCNotFoundException

        # Load test data
        provider_id = self._load_provider_data()

        client = DataClient(self.config)

        # Try to close a non-existent investigation
        with self.assertRaises(CCNotFoundException) as context:
            client.close_investigation(
                compact='aslp',
                provider_id=provider_id,
                jurisdiction='oh',
                license_type_abbreviation='slp',
                investigation_id=uuid4(),
                closing_user=str(uuid4()),
                close_date=datetime.fromisoformat('2024-11-08T23:59:59+00:00'),
                investigation_against=InvestigationAgainstEnum.LICENSE,
            )

        self.assertIn('Investigation not found', str(context.exception))

    def test_close_privilege_investigation_already_closed(self):
        """Test closing privilege investigation when investigation was already closed"""
        from cc_common.data_model.data_client import DataClient
        from cc_common.data_model.schema.common import InvestigationAgainstEnum
        from cc_common.data_model.schema.investigation import InvestigationData
        from cc_common.exceptions import CCNotFoundException

        # Load test data
        provider_id = self._load_provider_data()

        client = DataClient(self.config)

        # First create an investigation
        investigation = InvestigationData.create_new(
            {
                'providerId': provider_id,
                'compact': 'aslp',
                'jurisdiction': 'ne',
                'licenseTypeAbbreviation': 'slp',
                'licenseType': 'speech-language pathologist',
                'investigationAgainst': 'privilege',
                'submittingUser': str(uuid4()),
                'creationDate': datetime.fromisoformat('2024-11-08T23:59:59+00:00'),
                'investigationId': uuid4(),
            }
        )

        client.create_investigation(investigation)

        # Now close the investigation
        closing_user = str(uuid4())
        client.close_investigation(
            compact='aslp',
            provider_id=provider_id,
            jurisdiction='ne',
            license_type_abbreviation='slp',
            investigation_id=investigation.investigationId,
            closing_user=closing_user,
            close_date=datetime.fromisoformat('2024-11-08T23:59:59+00:00'),
            investigation_against=InvestigationAgainstEnum.PRIVILEGE,
        )
        with self.assertRaises(CCNotFoundException) as context:
            client.close_investigation(
                compact='aslp',
                provider_id=provider_id,
                jurisdiction='ne',
                license_type_abbreviation='slp',
                investigation_id=investigation.investigationId,
                closing_user=closing_user,
                close_date=datetime.fromisoformat('2024-11-08T23:59:59+00:00'),
                investigation_against=InvestigationAgainstEnum.PRIVILEGE,
            )

        self.assertIn('Investigation not found', str(context.exception))

    def test_close_license_investigation_already_closed(self):
        """Test closing license investigation when investigation was already closed"""
        from cc_common.data_model.data_client import DataClient
        from cc_common.data_model.schema.common import InvestigationAgainstEnum
        from cc_common.data_model.schema.investigation import InvestigationData
        from cc_common.exceptions import CCNotFoundException

        # Load test data
        provider_id = self._load_provider_data()

        client = DataClient(self.config)

        # First create an investigation
        investigation = InvestigationData.create_new(
            {
                'providerId': provider_id,
                'compact': 'aslp',
                'jurisdiction': 'oh',
                'licenseTypeAbbreviation': 'slp',
                'licenseType': 'speech-language pathologist',
                'investigationAgainst': 'license',
                'submittingUser': str(uuid4()),
                'creationDate': datetime.fromisoformat('2024-11-08T23:59:59+00:00'),
                'investigationId': uuid4(),
            }
        )

        client.create_investigation(investigation)

        # Now close the investigation
        closing_user = str(uuid4())
        client.close_investigation(
            compact='aslp',
            provider_id=provider_id,
            jurisdiction='oh',
            license_type_abbreviation='slp',
            investigation_id=investigation.investigationId,
            closing_user=closing_user,
            close_date=datetime.fromisoformat('2024-11-08T23:59:59+00:00'),
            investigation_against=InvestigationAgainstEnum.LICENSE,
        )
        with self.assertRaises(CCNotFoundException) as context:
            client.close_investigation(
                compact='aslp',
                provider_id=provider_id,
                jurisdiction='oh',
                license_type_abbreviation='slp',
                investigation_id=investigation.investigationId,
                closing_user=closing_user,
                close_date=datetime.fromisoformat('2024-11-08T23:59:59+00:00'),
                investigation_against=InvestigationAgainstEnum.LICENSE,
            )

        self.assertIn('Investigation not found', str(context.exception))

    def test_close_privilege_investigation_with_encumbrance(self):
        """Test closing privilege investigation with encumbrance creation"""
        from cc_common.data_model.data_client import DataClient
        from cc_common.data_model.schema.common import InvestigationAgainstEnum
        from cc_common.data_model.schema.investigation import InvestigationData

        # Load test data
        provider_id = self._load_provider_data()

        client = DataClient(self.config)

        # First create an investigation
        investigation = InvestigationData.create_new(
            {
                'providerId': provider_id,
                'compact': 'aslp',
                'jurisdiction': 'ne',
                'licenseTypeAbbreviation': 'slp',
                'licenseType': 'speech-language pathologist',
                'investigationAgainst': 'privilege',
                'submittingUser': str(uuid4()),
                'creationDate': datetime.fromisoformat('2024-11-08T23:59:59+00:00'),
                'investigationId': uuid4(),
            }
        )

        client.create_investigation(investigation)

        # Now close the investigation with encumbrance creation
        closing_user = str(uuid4())
        resulting_encumbrance_id = uuid4()

        close_date = datetime.fromisoformat('2024-11-08T23:59:59+00:00')
        client.close_investigation(
            compact='aslp',
            provider_id=provider_id,
            jurisdiction='ne',
            license_type_abbreviation='slp',
            investigation_id=investigation.investigationId,
            closing_user=closing_user,
            close_date=datetime.fromisoformat('2024-11-08T23:59:59+00:00'),
            investigation_against=InvestigationAgainstEnum.PRIVILEGE,
            resulting_encumbrance_id=resulting_encumbrance_id,
        )

        # Verify investigation record was updated with close information and encumbrance reference
        investigation_records = self.config.provider_table.query(
            KeyConditionExpression=Key('pk').eq(f'aslp#PROVIDER#{provider_id}')
            & Key('sk').begins_with('aslp#PROVIDER#privilege/ne/slp#INVESTIGATION#')
        )['Items']

        self.assertEqual(1, len(investigation_records))
        investigation_record = investigation_records[0]

        # Verify the investigation record was updated with close information and encumbrance reference
        expected_investigation_close = {
            'pk': f'aslp#PROVIDER#{provider_id}',
            'sk': f'aslp#PROVIDER#privilege/ne/slp#INVESTIGATION#{investigation.investigationId}',
            'type': 'investigation',
            'compact': 'aslp',
            'providerId': str(provider_id),
            'jurisdiction': 'ne',
            'licenseType': 'speech-language pathologist',
            'investigationAgainst': 'privilege',
            'investigationId': str(investigation.investigationId),
            'submittingUser': str(investigation.submittingUser),
            'creationDate': investigation.creationDate.isoformat(),
            'closeDate': close_date.isoformat(),
            'closingUser': closing_user,
            'resultingEncumbranceId': str(resulting_encumbrance_id),
        }
        # Pop dynamic fields that we don't want to assert on
        investigation_record.pop('dateOfUpdate')

        self.assertEqual(expected_investigation_close, investigation_record)

    def test_close_license_investigation_with_encumbrance(self):
        """Test closing license investigation with encumbrance creation"""
        from cc_common.data_model.data_client import DataClient
        from cc_common.data_model.schema.common import InvestigationAgainstEnum
        from cc_common.data_model.schema.investigation import InvestigationData

        # Load test data
        provider_id = self._load_provider_data()

        client = DataClient(self.config)

        # First create an investigation
        investigation = InvestigationData.create_new(
            {
                'providerId': provider_id,
                'compact': 'aslp',
                'jurisdiction': 'oh',
                'licenseTypeAbbreviation': 'slp',
                'licenseType': 'speech-language pathologist',
                'investigationAgainst': 'license',
                'submittingUser': str(uuid4()),
                'creationDate': datetime.fromisoformat('2024-11-08T23:59:59+00:00'),
                'investigationId': uuid4(),
            }
        )

        client.create_investigation(investigation)

        # Now close the investigation with encumbrance creation
        closing_user = str(uuid4())
        resulting_encumbrance_id = uuid4()

        close_date = datetime.fromisoformat('2024-11-08T23:59:59+00:00')
        client.close_investigation(
            compact='aslp',
            provider_id=provider_id,
            jurisdiction='oh',
            license_type_abbreviation='slp',
            investigation_id=investigation.investigationId,
            closing_user=closing_user,
            close_date=datetime.fromisoformat('2024-11-08T23:59:59+00:00'),
            investigation_against=InvestigationAgainstEnum.LICENSE,
            resulting_encumbrance_id=resulting_encumbrance_id,
        )

        # Verify investigation record was updated with close information and encumbrance reference
        investigation_records = self.config.provider_table.query(
            KeyConditionExpression=Key('pk').eq(f'aslp#PROVIDER#{provider_id}')
            & Key('sk').begins_with('aslp#PROVIDER#license/oh/slp#INVESTIGATION#')
        )['Items']

        self.assertEqual(1, len(investigation_records))
        investigation_record = investigation_records[0]

        # Verify the investigation record was updated with close information and encumbrance reference
        expected_investigation_close = {
            'pk': f'aslp#PROVIDER#{provider_id}',
            'sk': f'aslp#PROVIDER#license/oh/slp#INVESTIGATION#{investigation.investigationId}',
            'type': 'investigation',
            'compact': 'aslp',
            'providerId': str(provider_id),
            'jurisdiction': 'oh',
            'licenseType': 'speech-language pathologist',
            'investigationAgainst': 'license',
            'investigationId': str(investigation.investigationId),
            'submittingUser': str(investigation.submittingUser),
            'creationDate': investigation.creationDate.isoformat(),
            'closeDate': close_date.isoformat(),
            'closingUser': closing_user,
            'resultingEncumbranceId': str(resulting_encumbrance_id),
        }
        # Pop dynamic fields that we don't want to assert on
        investigation_record.pop('dateOfUpdate')

        self.assertEqual(expected_investigation_close, investigation_record)
