import json
from datetime import UTC, date, datetime
from unittest.mock import ANY, patch
from uuid import UUID, uuid4

from boto3.dynamodb.conditions import Key
from cc_common.data_model.update_tier_enum import UpdateTierEnum
from moto import mock_aws

from tests.function import TstFunction


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
class TestDataClient(TstFunction):
    def setUp(self):
        super().setUp()
        self.maxDiff = None

    def test_get_provider(self):
        from cc_common.data_model.data_client import DataClient

        provider_id = self._load_provider_data()

        client = DataClient(self.config)

        resp = client.get_provider(
            compact='cosm',
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
            compact='cosm',
            provider_id=provider_id,
        )
        for item in resp['items']:
            self.assertNotIn('something_unexpected', item)

    def _load_provider_data(self) -> UUID:
        with open('tests/resources/dynamo/provider.json') as f:
            provider_record = json.load(f)
        provider_id = UUID(provider_record['providerId'])
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

    def test_get_ssn_by_provider_id_returns_ssn_if_provider_id_exists(self):
        """Test that get_ssn_by_provider_id returns the SSN if the provider ID exists"""
        from cc_common.data_model.data_client import DataClient

        client = DataClient(self.config)

        # Create a provider record with an SSN
        self._load_provider_data()

        ssn = client.get_ssn_by_provider_id(compact='cosm', provider_id='89a6377e-c3a5-40e5-bca5-317ec854c570')
        self.assertEqual('123-12-1234', ssn)

    def test_get_ssn_by_provider_id_raises_exception_if_provider_id_does_not_exist(self):
        """Test that get_ssn_by_provider_id returns the SSN if the provider ID exists"""
        from cc_common.data_model.data_client import DataClient
        from cc_common.exceptions import CCNotFoundException

        client = DataClient(self.config)

        # We didn't create the provider this time, so this won't exist
        with self.assertRaises(CCNotFoundException):
            client.get_ssn_by_provider_id(compact='cosm', provider_id='89a6377e-c3a5-40e5-bca5-317ec854c570')

    def test_get_ssn_by_provider_id_raises_exception_multiple_records_found(self):
        """Test that get_ssn_by_provider_id returns the SSN if the provider ID exists"""
        from cc_common.data_model.data_client import DataClient
        from cc_common.exceptions import CCInternalException

        client = DataClient(self.config)

        self._load_provider_data()
        # Put a duplicate record into the table, so this provider id has two SSNs associated with it
        self.config.ssn_table.put_item(
            Item={
                'pk': 'cosm#SSN#123-12-5678',
                'sk': 'cosm#SSN#123-12-5678',
                'providerIdGSIpk': 'cosm#PROVIDER#89a6377e-c3a5-40e5-bca5-317ec854c570',
                'compact': 'cosm',
                'ssn': '123-12-5678',
                'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570',
            }
        )

        with self.assertRaises(CCInternalException):
            client.get_ssn_by_provider_id(compact='cosm', provider_id='89a6377e-c3a5-40e5-bca5-317ec854c570')

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
                'compact': 'cosm',
            }
        )

        # Creating 30 records, to test pagination with 10 records at a time.
        jurisdictions = self.config.jurisdictions[:30]
        for jurisdiction in jurisdictions:
            self.test_data_generator.put_default_privilege_record_in_provider_table(
                value_overrides={
                    'providerId': provider_uuid,
                    'compact': 'cosm',
                    'jurisdiction': jurisdiction,
                    'licenseType': 'esthetician',
                    'privilegeId': f'EST-{jurisdiction.upper()}-1',
                    'dateOfIssuance': datetime(2023, 11, 8, 23, 59, 59, tzinfo=UTC),
                    'dateOfRenewal': datetime(2023, 11, 8, 23, 59, 59, tzinfo=UTC),
                    'dateOfExpiration': date(2024, 10, 31),
                    'dateOfUpdate': datetime(2023, 11, 8, 23, 59, 59, tzinfo=UTC),
                    'administratorSetStatus': 'active',
                }
            )

        # Create license records for each jurisdiction as well
        for jurisdiction in jurisdictions:
            self.test_data_generator.put_default_license_record_in_provider_table(
                value_overrides={
                    'providerId': provider_uuid,
                    'compact': 'cosm',
                    'jurisdiction': jurisdiction,
                    'licenseType': 'esthetician',
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
            provider_records = client.get_provider_user_records(compact='cosm', provider_id=provider_uuid)

            # Verify that we got all the records
            # We expect 1 provider record + 30 privilege records + 30 license records = 61 total
            self.assertEqual(61, len(provider_records.provider_records))

            # Check that we have all the different record types
            record_types = {record['type'] for record in provider_records.provider_records}
            self.assertEqual({'provider', 'privilege', 'license'}, record_types)

            # Verify we have all privileges from all jurisdictions
            privilege_records = provider_records.get_privilege_records()
            self.assertEqual(30, len(privilege_records))

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
                'compact': 'cosm',
                'jurisdiction': 'ne',
                'licenseType': 'cosmetologist',
                'investigationAgainst': 'privilege',
            }
        )

        # Call the method
        client.create_investigation(investigation)

        # Verify investigation record was created
        provider_user_records = self.config.data_client.get_provider_user_records(
            compact='cosm', provider_id=provider_id, include_update_tier=UpdateTierEnum.TIER_THREE
        )
        investigation_records = provider_user_records.get_investigation_records_for_privilege(
            privilege_jurisdiction='ne',
            privilege_license_type_abbreviation='cos',
        )

        self.assertEqual(1, len(investigation_records))
        investigation_record = investigation_records[0]

        # Verify the complete investigation record structure
        expected_investigation = {
            'pk': f'cosm#PROVIDER#{provider_id}',
            'sk': f'cosm#PROVIDER#privilege/ne/cos#INVESTIGATION#{investigation.investigationId}',
            'type': 'investigation',
            'compact': 'cosm',
            'providerId': str(provider_id),
            'jurisdiction': 'ne',
            'licenseType': 'cosmetologist',
            'investigationAgainst': 'privilege',
            'investigationId': str(investigation.investigationId),
            'submittingUser': str(investigation.submittingUser),
            'creationDate': investigation.creationDate.isoformat(),
            'dateOfUpdate': ANY,
        }
        # Pop dynamic fields that we don't want to assert on
        self.assertEqual(expected_investigation, investigation_record.serialize_to_database_record())

        # Verify privilege record was updated with investigation status
        privilege_records = provider_user_records.get_privilege_records()

        self.assertEqual(1, len(privilege_records))
        privilege_record = privilege_records[0]
        self.assertEqual('underInvestigation', privilege_record.investigationStatus)

        # Verify update record was created
        update_records = provider_user_records.get_update_records_for_privilege(
            jurisdiction=privilege_record.jurisdiction,
            license_type=privilege_record.licenseType,
        )

        self.assertEqual(1, len(update_records))
        update_record = update_records[0]

        # Verify the complete update record structure
        expected_update = {
            'pk': f'cosm#PROVIDER#{provider_id}',
            'sk': ANY,
            'type': 'privilegeUpdate',
            'updateType': 'investigation',
            'compact': 'cosm',
            'providerId': str(provider_id),
            'jurisdiction': 'ne',
            'licenseType': 'cosmetologist',
            'createDate': investigation.creationDate.isoformat(),
            'effectiveDate': investigation.creationDate.isoformat(),
            'previous': {
                'administratorSetStatus': 'active',
                'dateOfExpiration': '2025-04-04',
                'dateOfIssuance': '2016-05-05T12:59:59+00:00',
                'dateOfRenewal': '2020-05-05T12:59:59+00:00',
                'dateOfUpdate': '2020-05-05T12:59:59+00:00',
                'licenseJurisdiction': 'oh',
                'privilegeId': 'COS-NE-1',
            },
            'updatedValues': {
                'investigationStatus': 'underInvestigation',
            },
            'investigationDetails': {
                'investigationId': str(investigation.investigationId),
            },
            'dateOfUpdate': ANY,
        }

        self.assertEqual(expected_update, update_record.serialize_to_database_record())

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
                'compact': 'cosm',
                'jurisdiction': 'oh',
                'licenseTypeAbbreviation': 'cos',
                'licenseType': 'cosmetologist',
                'investigationAgainst': 'license',
                'submittingUser': str(uuid4()),
                'creationDate': datetime.fromisoformat('2024-11-08T23:59:59+00:00'),
                'investigationId': str(uuid4()),
            }
        )

        # Call the method
        client.create_investigation(investigation)

        # Verify investigation record was created
        provider_user_records = self.config.data_client.get_provider_user_records(
            compact='cosm', provider_id=provider_id, include_update_tier=UpdateTierEnum.TIER_THREE
        )
        investigation_records = provider_user_records.get_investigation_records_for_license(
            license_jurisdiction='oh',
            license_type_abbreviation='cos',
        )

        self.assertEqual(1, len(investigation_records))
        investigation_record = investigation_records[0]

        # Verify the complete investigation record structure
        expected_investigation = {
            'pk': f'cosm#PROVIDER#{provider_id}',
            'sk': f'cosm#PROVIDER#license/oh/cos#INVESTIGATION#{investigation.investigationId}',
            'type': 'investigation',
            'compact': 'cosm',
            'providerId': str(provider_id),
            'jurisdiction': 'oh',
            'licenseType': 'cosmetologist',
            'investigationAgainst': 'license',
            'investigationId': str(investigation.investigationId),
            'submittingUser': str(investigation.submittingUser),
            'creationDate': investigation.creationDate.isoformat(),
            'dateOfUpdate': ANY,
        }

        self.assertEqual(expected_investigation, investigation_record.serialize_to_database_record())

        # Verify license record was updated with investigation status
        license_records = provider_user_records.get_license_records()

        self.assertEqual(1, len(license_records))
        license_record = license_records[0]
        self.assertEqual('underInvestigation', license_record.investigationStatus)

        # Verify update record was created
        update_records = provider_user_records.get_update_records_for_license(
            jurisdiction=license_record.jurisdiction,
            license_type=license_record.licenseType,
        )

        self.assertEqual(1, len(update_records))
        update_record = update_records[0]

        # Verify the complete update record structure
        expected_update = {
            'pk': f'cosm#PROVIDER#{provider_id}',
            'sk': ANY,
            'type': 'licenseUpdate',
            'updateType': 'investigation',
            'compact': 'cosm',
            'providerId': str(provider_id),
            'jurisdiction': 'oh',
            'licenseType': 'cosmetologist',
            'createDate': investigation.creationDate.isoformat(),
            'effectiveDate': investigation.creationDate.isoformat(),
            'previous': {
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
            'dateOfUpdate': ANY,
        }

        self.assertEqual(expected_update, update_record.serialize_to_database_record())

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
                'compact': 'cosm',
                'jurisdiction': 'oh',
                'licenseTypeAbbreviation': 'cos',
                'licenseType': 'cosmetologist',
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
                'compact': 'cosm',
                'jurisdiction': 'ne',
                'licenseTypeAbbreviation': 'cos',
                'licenseType': 'cosmetologist',
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
                'compact': 'cosm',
                'jurisdiction': 'ne',
                'licenseTypeAbbreviation': 'cos',
                'licenseType': 'cosmetologist',
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
            compact='cosm',
            provider_id=provider_id,
            jurisdiction='ne',
            license_type_abbreviation='cos',
            investigation_id=investigation.investigationId,
            closing_user=closing_user,
            close_date=datetime.fromisoformat('2024-11-08T23:59:59+00:00'),
            investigation_against=InvestigationAgainstEnum.PRIVILEGE,
        )

        # Verify investigation record was updated with close information
        provider_user_records = self.config.data_client.get_provider_user_records(
            compact='cosm', provider_id=provider_id, include_update_tier=UpdateTierEnum.TIER_THREE
        )
        investigation_records = provider_user_records.get_investigation_records_for_privilege(
            privilege_jurisdiction='ne', privilege_license_type_abbreviation='cos', include_closed=True
        )

        self.assertEqual(1, len(investigation_records))
        investigation_record = investigation_records[0]

        # Verify the investigation record was updated with close information
        expected_investigation_close = {
            'pk': f'cosm#PROVIDER#{provider_id}',
            'sk': f'cosm#PROVIDER#privilege/ne/cos#INVESTIGATION#{investigation.investigationId}',
            'type': 'investigation',
            'compact': 'cosm',
            'providerId': str(provider_id),
            'jurisdiction': 'ne',
            'licenseType': 'cosmetologist',
            'investigationAgainst': 'privilege',
            'investigationId': str(investigation.investigationId),
            'submittingUser': str(investigation.submittingUser),
            'creationDate': investigation.creationDate.isoformat(),
            'closeDate': investigation.creationDate.isoformat(),
            'closingUser': closing_user,
            'dateOfUpdate': ANY,
        }
        self.assertEqual(expected_investigation_close, investigation_record.serialize_to_database_record())

        # Verify privilege record no longer has investigation status
        privilege_records = provider_user_records.get_privilege_records()
        self.assertEqual(1, len(privilege_records))
        privilege_record = privilege_records[0]
        self.assertIsNone(privilege_record.investigationStatus)

        # Verify update record was created for closure
        update_records = provider_user_records.get_update_records_for_privilege(
            jurisdiction='ne',
            license_type=privilege_record.licenseType,
        )

        # Should have 2 update records: one for creation, one for closure
        self.assertEqual(2, len(update_records))

        # Find the closure update record
        closure_update = None
        for update_record in update_records:
            if update_record.updateType == 'closingInvestigation':
                closure_update = update_record
                break

        self.assertIsNotNone(closure_update, 'Closure update record not found!')

        # Verify the complete closure update record structure
        expected_closure_update = {
            'pk': f'cosm#PROVIDER#{provider_id}',
            'sk': ANY,
            'type': 'privilegeUpdate',
            'updateType': 'closingInvestigation',
            'compact': 'cosm',
            'providerId': str(provider_id),
            'jurisdiction': 'ne',
            'licenseType': 'cosmetologist',
            'createDate': investigation.creationDate.isoformat(),
            'effectiveDate': investigation.creationDate.isoformat(),
            'previous': {
                'administratorSetStatus': 'active',
                'dateOfExpiration': '2025-04-04',
                'dateOfIssuance': '2016-05-05T12:59:59+00:00',
                'dateOfRenewal': '2020-05-05T12:59:59+00:00',
                'dateOfUpdate': '2024-11-08T23:59:59+00:00',
                'licenseJurisdiction': 'oh',
                'privilegeId': 'COS-NE-1',
                'investigationStatus': 'underInvestigation',
            },
            'updatedValues': {},
            'removedValues': ['investigationStatus'],
            'dateOfUpdate': ANY,
        }

        self.assertEqual(expected_closure_update, closure_update.serialize_to_database_record())

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
                'compact': 'cosm',
                'jurisdiction': 'oh',
                'licenseTypeAbbreviation': 'cos',
                'licenseType': 'cosmetologist',
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
            compact='cosm',
            provider_id=provider_id,
            jurisdiction='oh',
            license_type_abbreviation='cos',
            investigation_id=investigation.investigationId,
            closing_user=closing_user,
            close_date=close_date,
            investigation_against=InvestigationAgainstEnum.LICENSE,
        )

        # grab all provider records to make assertions
        provider_user_records = self.config.data_client.get_provider_user_records(
            compact='cosm', provider_id=provider_id, include_update_tier=UpdateTierEnum.TIER_THREE
        )

        # Verify investigation record was updated with close information
        investigation_records = provider_user_records.get_investigation_records_for_license(
            license_jurisdiction='oh', license_type_abbreviation='cos', include_closed=True
        )

        self.assertEqual(1, len(investigation_records))
        investigation_record = investigation_records[0]

        # Verify the investigation record was updated with close information
        expected_investigation_close = {
            'pk': f'cosm#PROVIDER#{provider_id}',
            'sk': f'cosm#PROVIDER#license/oh/cos#INVESTIGATION#{investigation.investigationId}',
            'type': 'investigation',
            'compact': 'cosm',
            'providerId': str(provider_id),
            'jurisdiction': 'oh',
            'licenseType': 'cosmetologist',
            'investigationAgainst': 'license',
            'investigationId': str(investigation.investigationId),
            'submittingUser': str(investigation.submittingUser),
            'creationDate': investigation.creationDate.isoformat(),
            'closeDate': close_date.isoformat(),
            'closingUser': closing_user,
            'dateOfUpdate': ANY,
        }

        self.assertEqual(expected_investigation_close, investigation_record.serialize_to_database_record())

        # Verify license record no longer has investigation status
        license_records = provider_user_records.get_license_records()

        self.assertEqual(1, len(license_records))
        license_record = license_records[0]
        self.assertNotIn('investigationStatus', license_record.to_dict())

        # Verify update record was created for closure
        update_records = provider_user_records.get_update_records_for_license(
            jurisdiction=license_record.jurisdiction, license_type=license_record.licenseType
        )

        # Should have 2 update records: one for creation, one for closure
        self.assertEqual(2, len(update_records))

        # Find the closure update record
        closure_update = None
        for update_record in update_records:
            if update_record.updateType == 'closingInvestigation':
                closure_update = update_record
                break

        self.assertIsNotNone(closure_update, 'Closure update not found!')

        # Verify the complete closure update record structure
        expected_closure_update = {
            'pk': f'cosm#PROVIDER#{provider_id}',
            'sk': ANY,
            'type': 'licenseUpdate',
            'updateType': 'closingInvestigation',
            'compact': 'cosm',
            'providerId': str(provider_id),
            'jurisdiction': 'oh',
            'licenseType': 'cosmetologist',
            'createDate': investigation.creationDate.isoformat(),
            'effectiveDate': investigation.creationDate.isoformat(),
            'previous': {
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
            'dateOfUpdate': ANY,
        }

        self.assertEqual(expected_closure_update, closure_update.serialize_to_database_record())

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
                compact='cosm',
                provider_id=provider_id,
                jurisdiction='ne',
                license_type_abbreviation='cos',
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
                compact='cosm',
                provider_id=provider_id,
                jurisdiction='oh',
                license_type_abbreviation='cos',
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
                'compact': 'cosm',
                'jurisdiction': 'ne',
                'licenseTypeAbbreviation': 'cos',
                'licenseType': 'cosmetologist',
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
            compact='cosm',
            provider_id=provider_id,
            jurisdiction='ne',
            license_type_abbreviation='cos',
            investigation_id=investigation.investigationId,
            closing_user=closing_user,
            close_date=datetime.fromisoformat('2024-11-08T23:59:59+00:00'),
            investigation_against=InvestigationAgainstEnum.PRIVILEGE,
        )
        with self.assertRaises(CCNotFoundException) as context:
            client.close_investigation(
                compact='cosm',
                provider_id=provider_id,
                jurisdiction='ne',
                license_type_abbreviation='cos',
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
                'compact': 'cosm',
                'jurisdiction': 'oh',
                'licenseTypeAbbreviation': 'cos',
                'licenseType': 'cosmetologist',
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
            compact='cosm',
            provider_id=provider_id,
            jurisdiction='oh',
            license_type_abbreviation='cos',
            investigation_id=investigation.investigationId,
            closing_user=closing_user,
            close_date=datetime.fromisoformat('2024-11-08T23:59:59+00:00'),
            investigation_against=InvestigationAgainstEnum.LICENSE,
        )
        with self.assertRaises(CCNotFoundException) as context:
            client.close_investigation(
                compact='cosm',
                provider_id=provider_id,
                jurisdiction='oh',
                license_type_abbreviation='cos',
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
                'compact': 'cosm',
                'jurisdiction': 'ne',
                'licenseTypeAbbreviation': 'cos',
                'licenseType': 'cosmetologist',
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
            compact='cosm',
            provider_id=provider_id,
            jurisdiction='ne',
            license_type_abbreviation='cos',
            investigation_id=investigation.investigationId,
            closing_user=closing_user,
            close_date=datetime.fromisoformat('2024-11-08T23:59:59+00:00'),
            investigation_against=InvestigationAgainstEnum.PRIVILEGE,
            resulting_encumbrance_id=resulting_encumbrance_id,
        )

        # Verify investigation record was updated with close information and encumbrance reference
        investigation_records = self.config.provider_table.query(
            KeyConditionExpression=Key('pk').eq(f'cosm#PROVIDER#{provider_id}')
            & Key('sk').begins_with('cosm#PROVIDER#privilege/ne/cos#INVESTIGATION#')
        )['Items']

        self.assertEqual(1, len(investigation_records))
        investigation_record = investigation_records[0]

        # Verify the investigation record was updated with close information and encumbrance reference
        expected_investigation_close = {
            'pk': f'cosm#PROVIDER#{provider_id}',
            'sk': f'cosm#PROVIDER#privilege/ne/cos#INVESTIGATION#{investigation.investigationId}',
            'type': 'investigation',
            'compact': 'cosm',
            'providerId': str(provider_id),
            'jurisdiction': 'ne',
            'licenseType': 'cosmetologist',
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
                'compact': 'cosm',
                'jurisdiction': 'oh',
                'licenseTypeAbbreviation': 'cos',
                'licenseType': 'cosmetologist',
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
            compact='cosm',
            provider_id=provider_id,
            jurisdiction='oh',
            license_type_abbreviation='cos',
            investigation_id=investigation.investigationId,
            closing_user=closing_user,
            close_date=datetime.fromisoformat('2024-11-08T23:59:59+00:00'),
            investigation_against=InvestigationAgainstEnum.LICENSE,
            resulting_encumbrance_id=resulting_encumbrance_id,
        )

        # Verify investigation record was updated with close information and encumbrance reference
        investigation_records = self.config.provider_table.query(
            KeyConditionExpression=Key('pk').eq(f'cosm#PROVIDER#{provider_id}')
            & Key('sk').begins_with('cosm#PROVIDER#license/oh/cos#INVESTIGATION#')
        )['Items']

        self.assertEqual(1, len(investigation_records))
        investigation_record = investigation_records[0]

        # Verify the investigation record was updated with close information and encumbrance reference
        expected_investigation_close = {
            'pk': f'cosm#PROVIDER#{provider_id}',
            'sk': f'cosm#PROVIDER#license/oh/cos#INVESTIGATION#{investigation.investigationId}',
            'type': 'investigation',
            'compact': 'cosm',
            'providerId': str(provider_id),
            'jurisdiction': 'oh',
            'licenseType': 'cosmetologist',
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
