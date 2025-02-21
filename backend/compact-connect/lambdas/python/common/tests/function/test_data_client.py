import json
from datetime import UTC, date, datetime
from unittest.mock import patch
from uuid import uuid4

from boto3.dynamodb.conditions import Key
from moto import mock_aws

from tests.function import TstFunction


@mock_aws
class TestDataClient(TstFunction):
    sample_privilege_attestations = [{'attestationId': 'jurisprudence-confirmation', 'version': '1'}]

    def test_get_provider_id(self):
        from cc_common.data_model.data_client import DataClient

        with open('tests/resources/dynamo/provider-ssn.json') as f:
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

        with open('tests/resources/dynamo/license.json') as f:
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

    def _load_provider_data(self) -> str:
        with open('tests/resources/dynamo/provider.json') as f:
            provider_record = json.load(f)
        provider_id = provider_record['providerId']
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

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
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

        test_data_client.create_provider_privileges(
            compact='aslp',
            provider_id='test_provider_id',
            jurisdiction_postal_abbreviations=['ca'],
            license_expiration_date=date.fromisoformat('2024-10-31'),
            provider_record={},
            existing_privileges=[],
            compact_transaction_id='test_transaction_id',
            attestations=self.sample_privilege_attestations,
            license_type='audiologist',
        )

        # Verify that the privilege record was created
        new_privilege = self._provider_table.get_item(
            Key={'pk': 'aslp#PROVIDER#test_provider_id', 'sk': 'aslp#PROVIDER#privilege/ca#'}
        )['Item']
        self.assertEqual(
            {
                'pk': 'aslp#PROVIDER#test_provider_id',
                'sk': 'aslp#PROVIDER#privilege/ca#',
                'type': 'privilege',
                'providerId': 'test_provider_id',
                'compact': 'aslp',
                'jurisdiction': 'ca',
                'persistedStatus': 'active',
                'dateOfIssuance': '2024-11-08T23:59:59+00:00',
                'dateOfRenewal': '2024-11-08T23:59:59+00:00',
                'dateOfExpiration': '2024-10-31',
                'dateOfUpdate': '2024-11-08T23:59:59+00:00',
                'compactTransactionId': 'test_transaction_id',
                'attestations': self.sample_privilege_attestations,
                'privilegeId': 'AUD-CA-124',
            },
            new_privilege,
        )

        # Verify that the provider record was updated
        updated_provider = self._provider_table.get_item(
            Key={'pk': 'aslp#PROVIDER#test_provider_id', 'sk': 'aslp#PROVIDER'}
        )['Item']
        self.assertEqual({'ca'}, updated_provider['privilegeJurisdictions'])

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
    def test_data_client_updates_privilege_records(self):
        from cc_common.data_model.data_client import DataClient
        from cc_common.data_model.schema.privilege.record import PrivilegeRecordSchema

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
        original_privilege = {
            'pk': f'aslp#PROVIDER#{provider_uuid}',
            'sk': 'aslp#PROVIDER#privilege/ky#',
            'type': 'privilege',
            'providerId': provider_uuid,
            'compact': 'aslp',
            'jurisdiction': 'ky',
            'persistedStatus': 'active',
            'dateOfIssuance': '2023-11-08T23:59:59+00:00',
            'dateOfRenewal': '2023-11-08T23:59:59+00:00',
            'dateOfExpiration': '2024-10-31',
            'dateOfUpdate': '2023-11-08T23:59:59+00:00',
            'compactTransactionId': '1234567890',
            'attestations': self.sample_privilege_attestations,
            'privilegeId': 'AUD-KY-1',
        }
        self._provider_table.put_item(Item=original_privilege)

        test_data_client = DataClient(self.config)

        # Now, renew the privilege
        test_data_client.create_provider_privileges(
            compact='aslp',
            provider_id='test_provider_id',
            jurisdiction_postal_abbreviations=['ky'],
            license_expiration_date=date.fromisoformat('2025-10-31'),
            provider_record={
                'pk': 'aslp#PROVIDER#test_provider_id',
                'sk': 'aslp#PROVIDER',
            },
            existing_privileges=[PrivilegeRecordSchema().load(original_privilege)],
            compact_transaction_id='test_transaction_id',
            attestations=self.sample_privilege_attestations,
            license_type='audiologist',
        )

        # Verify that the privilege record was created
        new_privilege = self._provider_table.query(
            KeyConditionExpression=Key('pk').eq('aslp#PROVIDER#test_provider_id')
            & Key('sk').begins_with('aslp#PROVIDER#privilege/ky#'),
        )['Items']
        self.maxDiff = None
        self.assertEqual(
            [
                # Primary record
                {
                    'pk': 'aslp#PROVIDER#test_provider_id',
                    'sk': 'aslp#PROVIDER#privilege/ky#',
                    'type': 'privilege',
                    'providerId': 'test_provider_id',
                    'compact': 'aslp',
                    'jurisdiction': 'ky',
                    'persistedStatus': 'active',
                    # Should be updated dates for renewal, expiration, update
                    'dateOfIssuance': '2023-11-08T23:59:59+00:00',
                    'dateOfRenewal': '2024-11-08T23:59:59+00:00',
                    'dateOfExpiration': '2025-10-31',
                    'dateOfUpdate': '2024-11-08T23:59:59+00:00',
                    'compactTransactionId': 'test_transaction_id',
                    'attestations': self.sample_privilege_attestations,
                    # Should remain the same, since we're renewing the same privilege
                    'privilegeId': 'AUD-KY-1',
                },
                # A new history record
                {
                    'pk': 'aslp#PROVIDER#test_provider_id',
                    'sk': 'aslp#PROVIDER#privilege/ky#UPDATE#1731110399/11903e4261b10d1a7c806b51522913d1',
                    'type': 'privilegeUpdate',
                    'updateType': 'renewal',
                    'providerId': 'test_provider_id',
                    'compact': 'aslp',
                    'jurisdiction': 'ky',
                    'dateOfUpdate': '2024-11-08T23:59:59+00:00',
                    'previous': {
                        'dateOfIssuance': '2023-11-08T23:59:59+00:00',
                        'dateOfRenewal': '2023-11-08T23:59:59+00:00',
                        'dateOfExpiration': '2024-10-31',
                        'dateOfUpdate': '2023-11-08T23:59:59+00:00',
                        'compactTransactionId': '1234567890',
                        'attestations': self.sample_privilege_attestations,
                        'persistedStatus': 'active',
                        'privilegeId': 'AUD-KY-1',
                    },
                    'updatedValues': {
                        'dateOfRenewal': '2024-11-08T23:59:59+00:00',
                        'dateOfExpiration': '2025-10-31',
                        'compactTransactionId': 'test_transaction_id',
                    },
                },
            ],
            new_privilege,
        )

        # The renewal should still ensure that 'ky' is listed in provider privilegeJurisdictions
        provider = self._provider_table.get_item(
            Key={'pk': 'aslp#PROVIDER#test_provider_id', 'sk': 'aslp#PROVIDER'},
        )['Item']
        self.assertEqual({'ky'}, provider['privilegeJurisdictions'])

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
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
                provider_record={},
                existing_privileges=[],
                compact_transaction_id='test_transaction_id',
                attestations=self.sample_privilege_attestations,
                license_type='not-supported-license-type',
            )

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
    def test_data_client_handles_large_privilege_purchase(self):
        """Test that we can process privilege purchases with more than 100 transaction items."""
        from cc_common.data_model.data_client import DataClient
        from cc_common.data_model.schema.privilege.record import PrivilegeRecordSchema

        test_data_client = DataClient(self.config)
        provider_uuid = str(uuid4())

        # Generate 51 jurisdictions (will create 102 records - 51 privileges and 51 updates)
        jurisdictions = [f'j{i}' for i in range(51)]
        original_privileges = []

        # Create original privileges that will be updated
        privilege_record_schema = PrivilegeRecordSchema()
        for jurisdiction in jurisdictions:
            # We'll use the schema to dump the privilege record to the table, but won't ever load again
            # because we're using invalid jurisdiction abbreviations for testing convenience
            original_privilege = {
                'type': 'privilege',
                'providerId': provider_uuid,
                'compact': 'aslp',
                'jurisdiction': jurisdiction,
                'privilegeId': f'AUD-{jurisdiction.upper()}-1',
                'dateOfIssuance': datetime(2023, 11, 8, 23, 59, 59, tzinfo=UTC),
                'dateOfRenewal': datetime(2023, 11, 8, 23, 59, 59, tzinfo=UTC),
                'dateOfExpiration': date(2024, 10, 31),
                'dateOfUpdate': datetime(2023, 11, 8, 23, 59, 59, tzinfo=UTC),
                'compactTransactionId': '1234567890',
            }
            self._provider_table.put_item(Item=privilege_record_schema.dump(original_privilege))
            original_privileges.append(original_privilege)

        # Now update all privileges
        test_data_client.create_provider_privileges(
            compact='aslp',
            provider_id=provider_uuid,
            jurisdiction_postal_abbreviations=jurisdictions,
            license_expiration_date=date.fromisoformat('2025-10-31'),
            provider_record={
                'pk': f'aslp#PROVIDER#{provider_uuid}',
                'sk': 'aslp#PROVIDER',
                'privilegeJurisdictions': set(jurisdictions),
            },
            existing_privileges=original_privileges,
            compact_transaction_id='test_transaction_id',
            attestations=self.sample_privilege_attestations,
            license_type='audiologist',
        )

        # Verify that all privileges were updated
        for jurisdiction in jurisdictions:
            privilege_records = self._provider_table.query(
                KeyConditionExpression=Key('pk').eq(f'aslp#PROVIDER#{provider_uuid}')
                & Key('sk').begins_with(f'aslp#PROVIDER#privilege/{jurisdiction}#'),
            )['Items']

            self.assertEqual(2, len(privilege_records))  # One privilege record and one update record

            # Find the main privilege record
            privilege_record = next(r for r in privilege_records if r['type'] == 'privilege')
            self.assertEqual('2025-10-31', privilege_record['dateOfExpiration'])
            self.assertEqual('test_transaction_id', privilege_record['compactTransactionId'])

            # Find the update record
            update_record = next(r for r in privilege_records if r['type'] == 'privilegeUpdate')
            self.assertEqual('renewal', update_record['updateType'])
            self.assertEqual('2024-10-31', update_record['previous']['dateOfExpiration'])
            self.assertEqual('2025-10-31', update_record['updatedValues']['dateOfExpiration'])

        # Verify the provider record was updated correctly
        provider = self._provider_table.get_item(
            Key={'pk': f'aslp#PROVIDER#{provider_uuid}', 'sk': 'aslp#PROVIDER'},
        )['Item']
        self.assertEqual(set(jurisdictions), provider['privilegeJurisdictions'])

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
    def test_data_client_rolls_back_failed_large_privilege_purchase(self):
        """Test that we properly roll back when a large privilege purchase fails."""
        from botocore.exceptions import ClientError
        from cc_common.data_model.data_client import DataClient
        from cc_common.data_model.schema.privilege.record import PrivilegeRecordSchema
        from cc_common.exceptions import CCAwsServiceException

        test_data_client = DataClient(self.config)
        provider_uuid = str(uuid4())

        # Generate 51 jurisdictions (will create 102 records - 51 privileges and 51 updates)
        jurisdictions = [f'j{i}' for i in range(51)]
        original_privileges = []

        privilege_record_schema = PrivilegeRecordSchema()
        for jurisdiction in jurisdictions:
            # We'll use the schema to dump the privilege record to the table, but won't ever load again
            # because we're using invalid jurisdiction abbreviations for testing convenience
            original_privilege = {
                'type': 'privilege',
                'providerId': provider_uuid,
                'compact': 'aslp',
                'jurisdiction': jurisdiction,
                'privilegeId': f'AUD-{jurisdiction.upper()}-1',
                'dateOfIssuance': datetime(2023, 11, 8, 23, 59, 59, tzinfo=UTC),
                'dateOfRenewal': datetime(2023, 11, 8, 23, 59, 59, tzinfo=UTC),
                'dateOfExpiration': date(2024, 10, 31),
                'dateOfUpdate': datetime(2023, 11, 8, 23, 59, 59, tzinfo=UTC),
                'compactTransactionId': '1234567890',
            }
            dumped_privilege = privilege_record_schema.dump(original_privilege)
            self._provider_table.put_item(Item=dumped_privilege)
            original_privileges.append(original_privilege)

        # Store original provider record
        original_provider = {
            'pk': f'aslp#PROVIDER#{provider_uuid}',
            'sk': 'aslp#PROVIDER',
            'providerId': provider_uuid,
            'compact': 'aslp',
            'privilegeJurisdictions': set(jurisdictions),
        }
        self._provider_table.put_item(Item=original_provider)

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
                existing_privileges=original_privileges,
                compact_transaction_id='test_transaction_id',
                attestations=self.sample_privilege_attestations,
                license_type='audiologist',
            )

        # Verify that all privileges were restored to their original state
        for jurisdiction in jurisdictions:
            privilege_records = self._provider_table.query(
                KeyConditionExpression=Key('pk').eq(f'aslp#PROVIDER#{provider_uuid}')
                & Key('sk').begins_with(f'aslp#PROVIDER#privilege/{jurisdiction}#'),
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

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
    def test_deactivate_privilege_updates_record(self):
        from cc_common.data_model.data_client import DataClient

        provider_id = self._load_provider_data()

        # Create the first privilege
        original_privilege = {
            'pk': f'aslp#PROVIDER#{provider_id}',
            'sk': 'aslp#PROVIDER#privilege/ne#',
            'type': 'privilege',
            'providerId': provider_id,
            'compact': 'aslp',
            'jurisdiction': 'ne',
            'persistedStatus': 'active',
            'dateOfIssuance': '2023-11-08T23:59:59+00:00',
            'dateOfRenewal': '2023-11-08T23:59:59+00:00',
            'dateOfExpiration': '2024-10-31',
            'dateOfUpdate': '2023-11-08T23:59:59+00:00',
            'compactTransactionId': '1234567890',
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
        )

        # Verify that the privilege record was updated
        new_privilege = self._provider_table.query(
            KeyConditionExpression=Key('pk').eq(f'aslp#PROVIDER#{provider_id}')
            & Key('sk').begins_with('aslp#PROVIDER#privilege/ne#'),
        )['Items']
        self.maxDiff = None
        self.assertEqual(
            [
                # Primary record
                {
                    'pk': f'aslp#PROVIDER#{provider_id}',
                    'sk': 'aslp#PROVIDER#privilege/ne#',
                    'type': 'privilege',
                    'providerId': provider_id,
                    'compact': 'aslp',
                    'jurisdiction': 'ne',
                    'persistedStatus': 'inactive',
                    'dateOfIssuance': '2023-11-08T23:59:59+00:00',
                    'dateOfRenewal': '2023-11-08T23:59:59+00:00',
                    'dateOfExpiration': '2024-10-31',
                    'dateOfUpdate': '2024-11-08T23:59:59+00:00',
                    'compactTransactionId': '1234567890',
                    'attestations': self.sample_privilege_attestations,
                    'privilegeId': 'AUD-NE-1',
                },
                # A new history record
                {
                    'pk': f'aslp#PROVIDER#{provider_id}',
                    'sk': 'aslp#PROVIDER#privilege/ne#UPDATE#1731110399/dba34d0647b68b3d577f8135ad6ec677',
                    'type': 'privilegeUpdate',
                    'updateType': 'deactivation',
                    'providerId': provider_id,
                    'compact': 'aslp',
                    'jurisdiction': 'ne',
                    'dateOfUpdate': '2024-11-08T23:59:59+00:00',
                    'previous': {
                        'dateOfIssuance': '2023-11-08T23:59:59+00:00',
                        'dateOfRenewal': '2023-11-08T23:59:59+00:00',
                        'dateOfExpiration': '2024-10-31',
                        'dateOfUpdate': '2023-11-08T23:59:59+00:00',
                        'compactTransactionId': '1234567890',
                        'attestations': self.sample_privilege_attestations,
                        'persistedStatus': 'active',
                        'privilegeId': 'AUD-NE-1',
                    },
                    'updatedValues': {
                        'persistedStatus': 'inactive',
                    },
                },
            ],
            new_privilege,
        )

        # The deactivation should still ensure that 'ne' is removed from privilegeJurisdictions
        provider = self._provider_table.get_item(
            Key={'pk': f'aslp#PROVIDER#{provider_id}', 'sk': 'aslp#PROVIDER'},
        )['Item']
        self.assertEqual(set(), provider.get('privilegeJurisdictions', set()))

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
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
            )

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
    def test_deactivate_privilege_on_inactive_privilege_has_no_effect(self):
        from cc_common.data_model.data_client import DataClient

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
            'sk': 'aslp#PROVIDER#privilege/ne#',
            'type': 'privilege',
            'providerId': provider_id,
            'compact': 'aslp',
            'jurisdiction': 'ne',
            'persistedStatus': 'inactive',
            'dateOfIssuance': '2023-11-08T23:59:59+00:00',
            'dateOfRenewal': '2023-11-08T23:59:59+00:00',
            'dateOfExpiration': '2024-10-31',
            'dateOfUpdate': '2023-11-08T23:59:59+00:00',
            'compactTransactionId': '1234567890',
            'attestations': self.sample_privilege_attestations,
            'privilegeId': 'AUD-NE-1',
        }
        self._provider_table.put_item(Item=original_privilege)
        # We'll create it as if it were already deactivated
        original_history = {
            'pk': f'aslp#PROVIDER#{provider_id}',
            'sk': 'aslp#PROVIDER#privilege/ne#UPDATE#1731110399/483bebc6cb3fd6b517f8ce9ad706c518',
            'type': 'privilegeUpdate',
            'updateType': 'renewal',
            'providerId': provider_id,
            'compact': 'aslp',
            'jurisdiction': 'ne',
            'dateOfUpdate': '2024-11-08T23:59:59+00:00',
            'previous': {
                'dateOfIssuance': '2023-11-08T23:59:59+00:00',
                'dateOfRenewal': '2023-11-08T23:59:59+00:00',
                'dateOfExpiration': '2024-10-31',
                'dateOfUpdate': '2023-11-08T23:59:59+00:00',
                'compactTransactionId': '1234567890',
                'attestations': self.sample_privilege_attestations,
                'privilegeId': 'AUD-NE-1',
            },
            'updatedValues': {
                'persistedStatus': 'inactive',
            },
        }
        self._provider_table.put_item(Item=original_history)

        test_data_client = DataClient(self.config)

        # Now, deactivate the privilege
        test_data_client.deactivate_privilege(
            compact='aslp',
            provider_id=provider_id,
            jurisdiction='ne',
        )

        # Verify that the privilege record was unchanged
        new_privilege = self._provider_table.query(
            KeyConditionExpression=Key('pk').eq(f'aslp#PROVIDER#{provider_id}')
            & Key('sk').begins_with('aslp#PROVIDER#privilege/ne#'),
        )['Items']
        self.assertEqual([original_privilege, original_history], new_privilege)

        # 'ne' should still be removed from privilegeJurisdictions
        provider = self._provider_table.get_item(
            Key={'pk': f'aslp#PROVIDER#{provider_id}', 'sk': 'aslp#PROVIDER'},
        )['Item']
        self.assertEqual(set(), provider.get('privilegeJurisdictions', set()))
