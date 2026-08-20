import json
from datetime import datetime
from unittest.mock import patch

from marshmallow import ValidationError

from tests import TstLambdas


class TestPrivilegeRecordSchema(TstLambdas):
    def test_serde(self):
        """Test round-trip deserialization/serialization"""
        from cc_common.data_model.schema.privilege.record import PrivilegeRecordSchema

        with open('tests/resources/dynamo/privilege.json') as f:
            expected_privilege = json.load(f)

        schema = PrivilegeRecordSchema()
        loaded_schema = schema.load(expected_privilege.copy())
        # assert status field is added
        self.assertIn('status', loaded_schema)

        privilege_data = schema.dump(loaded_schema)
        # assert that the status field was stripped from the data on dump
        self.assertNotIn('status', privilege_data)

        # Drop dynamic fields
        del expected_privilege['dateOfUpdate']
        del privilege_data['dateOfUpdate']

        self.assertEqual(privilege_data, expected_privilege)

    def test_invalid(self):
        from cc_common.data_model.schema.privilege.record import PrivilegeRecordSchema

        with open('tests/resources/dynamo/privilege.json') as f:
            privilege_data = json.load(f)
        privilege_data.pop('providerId')

        with self.assertRaises(ValidationError):
            PrivilegeRecordSchema().load(privilege_data)

    def test_invalid_license_type(self):
        from cc_common.data_model.schema.privilege.record import PrivilegeRecordSchema

        with open('tests/resources/dynamo/privilege.json') as f:
            privilege_data = json.load(f)
        # This privilege is in the ASLP compact, not Counseling
        privilege_data['licenseType'] = 'occupational therapist'

        with self.assertRaises(ValidationError):
            PrivilegeRecordSchema().load(privilege_data)

    def test_status_is_set_to_inactive_when_past_expiration(self):
        from cc_common.data_model.schema.privilege.record import PrivilegeRecordSchema

        with open('tests/resources/dynamo/privilege.json') as f:
            privilege_data = json.load(f)
            privilege_data['dateOfExpiration'] = '2020-01-01'

        result = PrivilegeRecordSchema().load(privilege_data)

        self.assertEqual(result['status'], 'inactive')

    def test_status_is_set_to_active_when_not_past_expiration(self):
        from cc_common.data_model.schema.privilege.record import PrivilegeRecordSchema

        with open('tests/resources/dynamo/privilege.json') as f:
            privilege_data = json.load(f)
            privilege_data['dateOfExpiration'] = '2100-01-01'

        result = PrivilegeRecordSchema().load(privilege_data)

        self.assertEqual(result['status'], 'active')

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-09T03:59:59+00:00'))
    def test_status_is_set_to_active_right_before_expiration_for_utc_minus_four_timezone(self):
        from cc_common.data_model.schema.privilege.record import PrivilegeRecordSchema

        with open('tests/resources/dynamo/privilege.json') as f:
            privilege_data = json.load(f)
            privilege_data['dateOfExpiration'] = '2024-11-08'

        result = PrivilegeRecordSchema().load(privilege_data)

        self.assertEqual(result['status'], 'active')

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-09T04:00:00+00:00'))
    def test_status_is_set_to_inactive_right_at_expiration_for_utc_minus_four_timezone(self):
        from cc_common.data_model.schema.privilege.record import PrivilegeRecordSchema

        with open('tests/resources/dynamo/privilege.json') as f:
            privilege_data = json.load(f)
            privilege_data['dateOfExpiration'] = '2024-11-08'

        result = PrivilegeRecordSchema().load(privilege_data)

        self.assertEqual(result['status'], 'inactive')

    def test_status_is_set_to_inactive_when_privilege_is_encumbered(self):
        from cc_common.data_model.schema.privilege.record import PrivilegeRecordSchema

        with open('tests/resources/dynamo/privilege.json') as f:
            privilege_data = json.load(f)
            privilege_data['dateOfExpiration'] = '2050-11-08'
            privilege_data['encumberedStatus'] = 'encumbered'

        result = PrivilegeRecordSchema().load(privilege_data)

        self.assertEqual(result['status'], 'inactive')

    def test_status_is_set_to_active_if_privilege_is_unencumbered(self):
        from cc_common.data_model.schema.privilege.record import PrivilegeRecordSchema

        with open('tests/resources/dynamo/privilege.json') as f:
            privilege_data = json.load(f)
            privilege_data['dateOfExpiration'] = '2050-11-08'
            privilege_data['encumberedStatus'] = 'unencumbered'

        result = PrivilegeRecordSchema().load(privilege_data)

        self.assertEqual(result['status'], 'active')

    def test_status_is_set_to_active_if_privilege_encumbrance_status_not_present(self):
        from cc_common.data_model.schema.privilege.record import PrivilegeRecordSchema

        with open('tests/resources/dynamo/privilege.json') as f:
            privilege_data = json.load(f)
            privilege_data['dateOfExpiration'] = '2050-11-08'
            privilege_data.pop('encumberedStatus', None)

        result = PrivilegeRecordSchema().load(privilege_data)

        self.assertEqual(result['status'], 'active')


class TestPrivilegeUpdateRecordSchema(TstLambdas):
    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
    def test_serde(self):
        """Test round-trip deserialization/serialization"""
        from cc_common.data_model.schema.privilege.record import PrivilegeUpdateRecordSchema

        with open('tests/resources/dynamo/privilege-update.json') as f:
            expected_privilege_update = json.load(f)

        schema = PrivilegeUpdateRecordSchema()
        loaded_schema = schema.load(expected_privilege_update.copy())

        privilege_data = schema.dump(loaded_schema)

        # Drop dynamic fields
        del expected_privilege_update['dateOfUpdate']
        del privilege_data['dateOfUpdate']

        self.assertEqual(expected_privilege_update, privilege_data)

    def test_invalid(self):
        from cc_common.data_model.schema.privilege.record import PrivilegeUpdateRecordSchema

        with open('tests/resources/dynamo/privilege-update.json') as f:
            privilege_data = json.load(f)
        privilege_data.pop('providerId')

        with self.assertRaises(ValidationError):
            PrivilegeUpdateRecordSchema().load(privilege_data)

    def test_invalid_license_type(self):
        from cc_common.data_model.schema.privilege.record import PrivilegeUpdateRecordSchema

        with open('tests/resources/dynamo/privilege-update.json') as f:
            privilege_data = json.load(f)
        # This privilege is in the ASLP compact, not Counseling
        privilege_data['licenseType'] = 'occupational therapist'

        with self.assertRaises(ValidationError):
            PrivilegeUpdateRecordSchema().load(privilege_data)

    def test_invalid_if_missing_deactivation_details_when_update_type_is_deactivation(self):
        from cc_common.data_model.schema.privilege.record import PrivilegeUpdateRecordSchema

        with open('tests/resources/dynamo/privilege-update.json') as f:
            privilege_data = json.load(f)
        # Privilege deactivation updates require a 'deactivationDetails' fields
        privilege_data['updateType'] = 'deactivation'

        with self.assertRaises(ValidationError) as context:
            PrivilegeUpdateRecordSchema().load(privilege_data)

        self.assertEqual(
            {'deactivationDetails': ['This field is required when update was deactivation type']},
            context.exception.messages,
        )

    def test_invalid_if_missing_investigation_details_when_update_type_is_investigation(self):
        from cc_common.data_model.schema.privilege.record import PrivilegeUpdateRecordSchema

        with open('tests/resources/dynamo/privilege-update.json') as f:
            privilege_data = json.load(f)
        # Privilege investigation updates require an 'investigationDetails' fields
        privilege_data['updateType'] = 'investigation'

        with self.assertRaises(ValidationError) as context:
            PrivilegeUpdateRecordSchema().load(privilege_data)

        self.assertEqual(
            {'investigationDetails': ['This field is required when update was investigation type']},
            context.exception.messages,
        )

    def test_valid_if_deactivation_details_present_when_update_type_is_deactivation(self):
        from cc_common.data_model.schema.common import UpdateCategory
        from cc_common.data_model.schema.privilege.record import PrivilegeUpdateRecordSchema

        with open('tests/resources/dynamo/privilege-update.json') as f:
            privilege_data = json.load(f)
        # Privilege deactivation updates require a 'deactivationDetails' fields
        privilege_data['updateType'] = UpdateCategory.DEACTIVATION
        privilege_data['deactivationDetails'] = {
            'note': 'test deactivation note',
            'deactivatedByStaffUserId': 'a4182428-d061-701c-82e5-a3d1d547d797',
            'deactivatedByStaffUserName': 'John Doe',
        }

        PrivilegeUpdateRecordSchema().load(privilege_data)


class TestPrivilegeGeneralResponseSchemaExpirationCheck(TstLambdas):
    """
    Tests for the PrivilegeExpirationStatusMixin applied to PrivilegeGeneralResponseSchema.

    This mixin checks for stale 'status' values when loading privilege data from sources
    like OpenSearch where the status may not have been updated after expiration.
    """

    def _make_privilege_data(self, *, status='active', date_of_expiration='2100-01-01'):
        """Create minimal valid privilege data for testing."""
        return {
            'type': 'privilege',
            'providerId': 'a4182428-d061-701c-82e5-a3d1d547d797',
            'compact': 'aslp',
            'jurisdiction': 'oh',
            'licenseJurisdiction': 'ne',
            'licenseType': 'audiologist',
            'dateOfIssuance': '2024-01-01',
            'dateOfRenewal': '2024-01-01',
            'dateOfExpiration': date_of_expiration,
            'dateOfUpdate': '2024-01-01T00:00:00+00:00',
            'administratorSetStatus': 'active',
            'privilegeId': 'test-priv-123',
            'status': status,
        }

    def test_expired_privilege_status_corrected_to_inactive(self):
        """When status is 'active' but dateOfExpiration is in the past, status becomes 'inactive'."""
        from cc_common.data_model.schema.privilege.api import PrivilegeGeneralResponseSchema

        privilege_data = self._make_privilege_data(
            status='active',
            date_of_expiration='2020-01-01',  # Expired
        )

        result = PrivilegeGeneralResponseSchema().load(privilege_data)

        self.assertEqual('inactive', result['status'])

    def test_unexpired_privilege_status_remains_active(self):
        """When status is 'active' and dateOfExpiration is in the future, status stays 'active'."""
        from cc_common.data_model.schema.privilege.api import PrivilegeGeneralResponseSchema

        privilege_data = self._make_privilege_data(
            status='active',
            date_of_expiration='2100-01-01',  # Far in the future
        )

        result = PrivilegeGeneralResponseSchema().load(privilege_data)

        self.assertEqual('active', result['status'])

    def test_already_inactive_status_remains_inactive(self):
        """When status is already 'inactive', it stays 'inactive' regardless of expiration."""
        from cc_common.data_model.schema.privilege.api import PrivilegeGeneralResponseSchema

        privilege_data = self._make_privilege_data(
            status='inactive',
            date_of_expiration='2100-01-01',  # Not expired, but status is inactive
        )

        result = PrivilegeGeneralResponseSchema().load(privilege_data)

        self.assertEqual('inactive', result['status'])

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-09T03:59:59+00:00'))
    def test_status_active_right_before_expiration_utc_minus_four(self):
        """Status remains 'active' right before midnight UTC-4 on expiration day."""
        from cc_common.data_model.schema.privilege.api import PrivilegeGeneralResponseSchema

        privilege_data = self._make_privilege_data(
            status='active',
            date_of_expiration='2024-11-08',  # Expires at midnight UTC-4 on Nov 9
        )

        result = PrivilegeGeneralResponseSchema().load(privilege_data)

        self.assertEqual('active', result['status'])

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-09T04:00:00+00:00'))
    def test_status_corrected_to_inactive_at_expiration_utc_minus_four(self):
        """Status corrected to 'inactive' at midnight UTC-4 on the day after expiration."""
        from cc_common.data_model.schema.privilege.api import PrivilegeGeneralResponseSchema

        privilege_data = self._make_privilege_data(
            status='active',
            date_of_expiration='2024-11-08',  # Expired at midnight UTC-4 on Nov 9
        )

        result = PrivilegeGeneralResponseSchema().load(privilege_data)

        self.assertEqual('inactive', result['status'])


class TestPrivilegeRecordFieldOwnership(TstLambdas):
    """
    Guards the classification behind privilege renewals.

    DataClient._generate_privilege_record rebuilds the whole privilege record from the purchase inputs on
    a renewal, so any field a purchase cannot supply is dropped unless it is deliberately carried forward.
    That is how a board encumbrance and an open investigation could be cleared by repurchasing. This test
    fails if a new privilege field is added without deciding which side of that line it falls on.

    Unlike the license equivalent there is no ingest schema to derive "what a purchase can supply" from -
    a purchase is not schema-driven - so SET_BY_PURCHASE mirrors the dict that method builds. The
    completeness check below is still mechanical: every field on the record has to land in some bucket.
    """

    # The keys DataClient._generate_privilege_record passes to PrivilegeData.create_new.
    SET_BY_PURCHASE = {
        'providerId',
        'compact',
        'jurisdiction',
        'licenseJurisdiction',
        'licenseType',
        'dateOfIssuance',
        'dateOfRenewal',
        'dateOfExpiration',
        'compactTransactionId',
        'attestations',
        'privilegeId',
        'administratorSetStatus',
    }
    # Written by the base record schema or regenerated by PrivilegeRecordSchema's pre_dump hooks.
    GENERATED_ON_WRITE = {'pk', 'sk', 'type', 'dateOfUpdate', 'compactTransactionIdGSIPK'}
    # Calculated when a record is loaded and stripped again before it is written.
    CALCULATED_ON_LOAD = {'status'}
    # Deliberately dropped by a renewal, which reactivates the privilege. DataClient records these in the
    # renewal update record's removedValues.
    CLEARED_ON_RENEWAL = {'homeJurisdictionChangeStatus', 'licenseDeactivatedStatus'}

    def test_every_privilege_field_a_purchase_cannot_supply_is_classified(self):
        from cc_common.data_model.schema.privilege.record import (
            SYSTEM_OWNED_PRIVILEGE_FIELDS,
            PrivilegeRecordSchema,
        )

        unclassified = (
            set(PrivilegeRecordSchema().fields)
            - self.SET_BY_PURCHASE
            - self.GENERATED_ON_WRITE
            - self.CALCULATED_ON_LOAD
            - self.CLEARED_ON_RENEWAL
            - SYSTEM_OWNED_PRIVILEGE_FIELDS
        )

        self.assertEqual(
            set(),
            unclassified,
            f'New privilege record field(s) {sorted(unclassified)} are not accounted for by a renewal, '
            'which rebuilds the record from the purchase inputs and will silently drop them. Decide which '
            'they are and add them to the right place: SYSTEM_OWNED_PRIVILEGE_FIELDS (in '
            'schema/privilege/record.py) if the system owns the value and it must survive a repurchase, or '
            'one of the SET_BY_PURCHASE / GENERATED_ON_WRITE / CALCULATED_ON_LOAD / CLEARED_ON_RENEWAL sets '
            'in this test if the purchase supplies it, it is rebuilt on every write, or a renewal is meant '
            'to clear it.',
        )

    def test_system_owned_fields_are_not_supplied_or_cleared_by_a_purchase(self):
        """A preserved field that a purchase also sets would be frozen at its first value, and one a
        renewal is meant to clear cannot also be carried forward.
        """
        from cc_common.data_model.schema.privilege.record import SYSTEM_OWNED_PRIVILEGE_FIELDS

        self.assertEqual(set(), SYSTEM_OWNED_PRIVILEGE_FIELDS & self.SET_BY_PURCHASE)
        self.assertEqual(set(), SYSTEM_OWNED_PRIVILEGE_FIELDS & self.CLEARED_ON_RENEWAL)

    def test_classified_fields_all_exist_on_the_record(self):
        """A classification naming a field the schema does not have is dead weight, and usually a rename
        that was only half applied.
        """
        from cc_common.data_model.schema.privilege.record import (
            SYSTEM_OWNED_PRIVILEGE_FIELDS,
            PrivilegeRecordSchema,
        )

        classified = (
            SYSTEM_OWNED_PRIVILEGE_FIELDS
            | self.SET_BY_PURCHASE
            | self.GENERATED_ON_WRITE
            | self.CALCULATED_ON_LOAD
            | self.CLEARED_ON_RENEWAL
        )

        self.assertEqual(set(), classified - set(PrivilegeRecordSchema().fields))
