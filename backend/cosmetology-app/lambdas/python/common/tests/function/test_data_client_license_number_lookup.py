from unittest.mock import patch

from cc_common.exceptions import CCAmbiguousLicenseNumberException
from common_test.test_constants import (
    DEFAULT_COMPACT,
    DEFAULT_LICENSE_JURISDICTION,
    DEFAULT_LICENSE_NUMBER,
    DEFAULT_PROVIDER_ID,
    DEFAULT_SSN_LAST_FOUR,
)
from moto import mock_aws

from tests.function import TstFunction

OTHER_PROVIDER_ID = '2d3f1b0e-4c5a-4d6b-8e7f-9a0b1c2d3e4f'
OTHER_LICENSE_TYPE = 'esthetician'


@mock_aws
class TestFindProviderByLicenseNumber(TstFunction):
    """
    Tests for resolving a practitioner from a license number, which lets a state omit the SSN on
    license uploads after the initial SSN-bearing upload has created the record.
    """

    def _lookup(self, license_number: str = DEFAULT_LICENSE_NUMBER):
        from cc_common.data_model.data_client import DataClient

        return DataClient(self.config).find_provider_by_license_number(
            compact=DEFAULT_COMPACT,
            jurisdiction=DEFAULT_LICENSE_JURISDICTION,
            license_number=license_number,
        )

    def test_returns_none_when_no_license_record_matches(self):
        self.assertIsNone(self._lookup())

    def test_returns_provider_id_and_ssn_last_four_for_a_single_match(self):
        self.test_data_generator.put_default_license_record_in_provider_table()

        result = self._lookup()

        self.assertIsNotNone(result)
        self.assertEqual(DEFAULT_PROVIDER_ID, result.provider_id)
        self.assertEqual(DEFAULT_SSN_LAST_FOUR, result.ssn_last_four)

    def test_returns_single_provider_when_one_provider_holds_the_number_for_two_license_types(self):
        """
        A state may reuse one license number across license types for the same practitioner. That is
        unambiguous as far as identity goes, so it must resolve rather than error.
        """
        self.test_data_generator.put_default_license_record_in_provider_table()
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={'licenseType': OTHER_LICENSE_TYPE}
        )

        result = self._lookup()

        self.assertIsNotNone(result)
        self.assertEqual(DEFAULT_PROVIDER_ID, result.provider_id)
        self.assertEqual(DEFAULT_SSN_LAST_FOUR, result.ssn_last_four)

    def test_raises_when_the_same_number_maps_to_two_providers(self):
        """
        A license number is expected to identify exactly one practitioner within a jurisdiction. If it
        does not, we cannot safely pick one, so this is an internal error rather than a caller error.
        """
        self.test_data_generator.put_default_license_record_in_provider_table()
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={'providerId': OTHER_PROVIDER_ID, 'licenseType': OTHER_LICENSE_TYPE}
        )

        with self.assertRaises(CCAmbiguousLicenseNumberException):
            self._lookup()

    def test_raises_when_matches_disagree_on_ssn_last_four(self):
        """
        Defensive: one provider's license records should always agree on ssnLastFour. If they don't, we
        would be guessing which value to forward to the ingest handler.
        """
        self.test_data_generator.put_default_license_record_in_provider_table()
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={'licenseType': OTHER_LICENSE_TYPE, 'ssnLastFour': '9999'}
        )

        with self.assertRaises(CCAmbiguousLicenseNumberException):
            self._lookup()

    def test_does_not_match_a_license_number_in_a_different_jurisdiction(self):
        self.test_data_generator.put_default_license_record_in_provider_table(value_overrides={'jurisdiction': 'ne'})

        self.assertIsNone(self._lookup())

    def test_does_not_match_a_license_number_in_a_different_compact(self):
        """
        The index partition key scopes matches to one compact and jurisdiction. The record is written
        with its GSI key overridden directly, because only one compact is configured in these tests.
        """
        license_record = self.test_data_generator.generate_default_license().serialize_to_database_record()
        license_record['pk'] = license_record['pk'].replace(DEFAULT_COMPACT, 'aslp')
        license_record['licenseGSIPK'] = f'C#aslp#J#{DEFAULT_LICENSE_JURISDICTION}'
        self.test_data_generator.store_record_in_provider_table(license_record)

        self.assertIsNone(self._lookup())

    def test_does_not_match_a_license_record_without_a_license_number(self):
        """
        licenseNumber is optional on license records, so the index is sparse. Records without one are
        not resolvable and the practitioner must still be identified by SSN.
        """
        license_data = self.test_data_generator.generate_default_license()
        license_record = license_data.serialize_to_database_record()
        del license_record['licenseNumber']
        self.test_data_generator.store_record_in_provider_table(license_record)

        self.assertIsNone(self._lookup())

    def test_does_not_match_a_license_number_with_different_casing(self):
        """
        The index sort key is matched byte for byte, so a state must send the license number exactly as
        it was originally uploaded. This is documented behavior, not a bug: a near-miss returns no match
        and the caller is told to upload with the SSN.
        """
        self.test_data_generator.put_default_license_record_in_provider_table()

        self.assertIsNone(self._lookup(license_number=DEFAULT_LICENSE_NUMBER.lower()))

    def test_does_not_log_the_license_number_above_debug_level(self):
        """The license number identifies a licensee, so it must not appear in INFO-level logs."""
        self.test_data_generator.put_default_license_record_in_provider_table()

        with patch('cc_common.data_model.data_client.logger') as mock_logger:
            self._lookup()

        logged_at_info = ' '.join(str(call) for call in mock_logger.info.call_args_list)
        self.assertNotIn(DEFAULT_LICENSE_NUMBER, logged_at_info)
