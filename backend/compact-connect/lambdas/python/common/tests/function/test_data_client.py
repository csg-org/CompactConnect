from datetime import UTC, date, datetime
from unittest.mock import patch
from uuid import uuid4

from boto3.dynamodb.conditions import Key
from moto import mock_aws

from tests.function import TstFunction


@mock_aws
class TestDataClient(TstFunction):
    sample_privilege_attestations = [{'attestationId': 'jurisprudence-confirmation', 'version': '1'}]

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
    def test_data_client_created_privilege_record(self):
        from cc_common.data_model.data_client import DataClient

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
                'dateOfIssuance': '2024-11-08T23:59:59+00:00',
                'dateOfRenewal': '2024-11-08T23:59:59+00:00',
                'dateOfExpiration': '2024-10-31',
                'dateOfUpdate': '2024-11-08T23:59:59+00:00',
                'compactTransactionId': 'test_transaction_id',
                'attestations': self.sample_privilege_attestations,
                'privilegeId': 'AUD-CA-1',
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

        # Create the first privilege
        provider_uuid = str(uuid4())
        original_privilege = {
            'pk': f'aslp#PROVIDER#{provider_uuid}',
            'sk': 'aslp#PROVIDER#privilege/ky#',
            'type': 'privilege',
            'providerId': provider_uuid,
            'compact': 'aslp',
            'jurisdiction': 'ky',
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
                    # Should be updated dates for renewal, expiration, update
                    'dateOfIssuance': '2023-11-08T23:59:59+00:00',
                    'dateOfRenewal': '2024-11-08T23:59:59+00:00',
                    'dateOfExpiration': '2025-10-31',
                    'dateOfUpdate': '2024-11-08T23:59:59+00:00',
                    'compactTransactionId': 'test_transaction_id',
                    'attestations': self.sample_privilege_attestations,
                    'privilegeId': 'AUD-KY-1',
                },
                # A new history record
                {
                    'pk': 'aslp#PROVIDER#test_provider_id',
                    'sk': 'aslp#PROVIDER#privilege/ky#UPDATE#1731110399/483bebc6cb3fd6b517f8ce9ad706c518',
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
