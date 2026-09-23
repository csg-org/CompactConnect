import json
from base64 import b64decode

from common_test.test_constants import DEFAULT_COMPACT
from moto import mock_aws

from .. import TstFunction

MOCK_PROVIDER_ID_PREFIX = '89a6377e-c3a5-40e5-bca5-317ec854c5'


@mock_aws
class TestPaginated(TstFunction):
    def test_pagination_returns_pagination_key_if_more_items_than_page_size_on_first_query(self):
        """Test edge case: page size 5, 10 providers total, 8 providers match filter. Only 5 should be returned within
        the response. The call should handle generating the expected last key since there are more matching providers
        that were truncated due to page size. So even though DynamoDB itself won't return a last key from the initial
        query, we ensure that a valid last key is returned for the caller to get all records.
        """
        # Create 10 provider records with different jurisdictions
        # 8 will have 'ky' jurisdiction (match filter), 2 will have 'oh' jurisdiction (don't match filter)
        provider_ids = []
        for i in range(1, 11):
            provider_id = f'{MOCK_PROVIDER_ID_PREFIX}{i:02d}'
            provider_ids.append(provider_id)

            # Providers 3 and 7 will have 'oh' jurisdiction (won't match filter)
            jurisdiction = 'oh' if i in [3, 7] else 'ky'

            self.test_data_generator.put_default_provider_record_in_provider_table(
                value_overrides={
                    'providerId': provider_id,
                    'licenseJurisdiction': jurisdiction,
                    'familyName': f'Provider{i:02d}',  # For consistent sorting
                    'givenName': f'Test{i:02d}',
                }
            )

        # Query with page size 5, filtering for 'ky' jurisdiction only
        resp = self.config.data_client.get_providers_sorted_by_family_name(
            compact='aslp',
            pagination={'pageSize': 5},
            jurisdiction='ky',  # This will filter out providers 3 and 7
        )

        # Should return 5 providers (page size)
        self.assertEqual(len(resp['items']), 5)

        # Should have a last key since there are more matching providers available (3 more)
        self.assertIsNotNone(resp['pagination']['lastKey'])

        # Decode the last key to verify it's for the 5th matching provider (number 6 in this case, since 3 did not match
        # the filter)
        last_key = json.loads(b64decode(resp['pagination']['lastKey']).decode('utf-8'))
        self.assertEqual(f'{DEFAULT_COMPACT}#PROVIDER#{MOCK_PROVIDER_ID_PREFIX}06', last_key['pk'])
        self.assertEqual(f'{DEFAULT_COMPACT}#PROVIDER', last_key['sk'])
        self.assertIn('providerFamGivMid', last_key)

        # now we call again with the last key and ensure we get the remaining 3 providers
        resp = self.config.data_client.get_providers_sorted_by_family_name(
            compact='aslp', pagination={'pageSize': 5, 'lastKey': resp['pagination']['lastKey']}, jurisdiction='ky'
        )
        self.assertEqual(len(resp['items']), 3)
        self.assertIsNone(resp['pagination']['lastKey'])

    def test_pagination_does_not_return_pagination_key_if_number_of_items_is_exact_match_to_page_size(self):
        """Test edge case: page size 5, 5 providers total, all 5 providers match filter.
        Verify the code does not return a last key since all available providers fit in the response page size.
        """
        # Create exactly 5 provider records - all will match the filter
        provider_ids = []
        for i in range(1, 6):
            provider_id = f'{MOCK_PROVIDER_ID_PREFIX}{i:02d}'
            provider_ids.append(provider_id)

            self.test_data_generator.put_default_provider_record_in_provider_table(
                value_overrides={
                    'providerId': provider_id,
                    'licenseJurisdiction': 'ky',  # All will match the jurisdiction filter
                    'familyName': f'Provider{i:02d}',  # For consistent sorting
                    'givenName': f'Test{i:02d}',
                }
            )

        # Query with page size 5, filtering for 'ky' jurisdiction
        resp = self.config.data_client.get_providers_sorted_by_family_name(
            compact='aslp',
            pagination={'pageSize': 5},
            jurisdiction='ky',  # All 5 providers will match
        )

        # Should return exactly 5 providers (all available)
        self.assertEqual(len(resp['items']), 5)

        # Should have NO last key since we've seen all available data
        self.assertIsNone(resp['pagination']['lastKey'])
