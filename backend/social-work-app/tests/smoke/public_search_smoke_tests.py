# ruff: noqa: T201  we use print statements for smoke testing
#!/usr/bin/env python3
"""
Smoke tests for public license search (unauthenticated).

POST /v1/public/compacts/{compact}/providers/query and GET /v1/public/compacts/{compact}/providers/{providerId}.
Uses CC_TEST_PROVIDER_ID and mutates the smoke license in DynamoDB; restores state in finally blocks.

Prerequisites:
- The test provider must have at least one multi-state license with a paired single-state license 
(public search and lookup only expose multi-state licenses).
- For baseline eligible assertions to pass, both the multi-state and its paired single-state license
  must be eligible (e.g. not expired, not jurisdiction-marked ineligible, no blocking adverse actions).
- The test provider must have no existing license in TEST_JURISDICTION. If this is not the case,
  change TEST_JURISDICTION to a jurisdiction where the test provider does not have a license.

After deploying public-search indexing changes (mostRecentLicenseForType), re-index or run populate
so OpenSearch documents include the new field before running these tests.

Run from repo root with social-work-app cwd, or set paths like other smoke scripts:

  cd backend/social-work-app && python tests/smoke/public_search_smoke_tests.py
"""

from __future__ import annotations

import copy

from config import config, logger
from smoke_common import (
    SmokeTestFailureException,
    call_public_get_provider,
    call_public_query_providers,
    get_all_provider_database_records,
    get_license_type_abbreviation,
    get_provider_user_dynamodb_table,
    load_smoke_test_env,
    wait_for_opensearch_sync,
)

COMPACT = 'socw'
EXPIRED_DATE_FOR_TEST = '2020-05-05'
# set older date of issuance and renewal for the test license that should be excluded from the public search results
TEST_DATE_OF_ISSUANCE = '2013-05-05'
TEST_DATE_OF_RENEWAL = '2014-05-05'
TEST_JURISDICTION = 'az'
TEST_LICENSE_NUMBER = 'SMOKE-TEST-LICENSE'


def _get_smoke_multi_state_license(license_records: list[dict]) -> dict:
    """
    Return the most recently issued/renewed multi-state license for smoke tests.

    The caller must also verify a paired single-state license exists in the same jurisdiction and
    license type before asserting eligible compactEligibility / licenseEligibility.
    """
    from cc_common.data_model.provider_record_util import ProviderRecordUtility
    from cc_common.data_model.schema.common import LicenseScopeEnum

    smoke_license_record = ProviderRecordUtility.find_most_recently_issued_or_renewed_license(
        license_records, LicenseScopeEnum.MULTI_STATE
    )
    if smoke_license_record is None:
        raise SmokeTestFailureException(
            'Smoke test prerequisite failed: the configured test provider must have at least one '
            'multi-state license for public search smoke tests.'
        )
    return smoke_license_record


def _ensure_smoke_multi_state_has_paired_single_state_license(
    license_records: list[dict], smoke_license_record: dict
) -> None:
    """Multi-state compact eligibility follows the paired single-state license in the same jurisdiction."""
    jurisdiction = str(smoke_license_record.get('jurisdiction', '')).lower()
    license_type = smoke_license_record.get('licenseType')
    has_paired_single_state = any(
        record.get('licenseScope') == 'single-state'
        and str(record.get('jurisdiction', '')).lower() == jurisdiction
        and record.get('licenseType') == license_type
        for record in license_records
    )
    if not has_paired_single_state:
        raise SmokeTestFailureException(
            'Smoke test prerequisite failed: the smoke multi-state license must have a paired '
            f'single-state license in jurisdiction {jurisdiction!r} for license type {license_type!r}. '
            'A multi-state license is only displayed as eligible when that paired single-state license '
            'is eligible.'
        )


def _ensure_no_existing_license_in_test_jurisdiction(license_records: list[dict]) -> None:
    for record in license_records:
        if str(record.get('jurisdiction', '')).lower() == TEST_JURISDICTION:
            raise SmokeTestFailureException(
                'Smoke test prerequisite failed: the configured test provider already has at least one '
                f'license in jurisdiction {TEST_JURISDICTION}. Set TEST_JURISDICTION to a jurisdiction where '
                'the test provider has no license, then re-run.'
            )


def _assert_license_eligibility_for_smoke_license(
    *,
    provider_id: str,
    license_number: str,
    expected_license_eligibility: str,
) -> None:
    """
    Public query by license number; assert ``licenseEligibility`` for the smoke provider's row.

    Eligibility is derived from the indexed multi-state license, whose displayed compactEligibility
    follows the paired single-state license in the same jurisdiction and license type when present.
    """
    matching_license_rows = call_public_query_providers(
        COMPACT,
        license_number_filter=license_number,
        provider_id_filter=provider_id,
        page_size=25,
    )
    if not matching_license_rows:
        raise SmokeTestFailureException(
            f'Public query returned no rows for provider {provider_id} (licenseNumber={license_number!r})'
        )
    license_row = matching_license_rows[0]
    if license_row.get('licenseScope') != 'multi-state':
        raise SmokeTestFailureException(
            f'Expected licenseScope multi-state for provider {provider_id}, got {license_row.get("licenseScope")!r}'
        )
    actual_eligibility = license_row.get('licenseEligibility')
    if actual_eligibility != expected_license_eligibility:
        raise SmokeTestFailureException(
            f'Expected licenseEligibility {expected_license_eligibility!r} for provider {provider_id}, '
            f'got {actual_eligibility!r}'
        )


def test_public_search_endpoints_returns_details_of_provider() -> dict:
    """
    Public query by smoke multi-state license number; verify eligible search row and public GET
    compactEligibility.

    Requires a paired single-state license in the same jurisdiction and license type; the multi-state
    license is only eligible when that single-state license is eligible.
    """
    provider_id = config.test_provider_id
    database_records = get_all_provider_database_records(COMPACT, provider_id)
    license_records = [record for record in database_records if record.get('type') == 'license']
    logger.info(f'License record count: {len(license_records)}')
    _ensure_no_existing_license_in_test_jurisdiction(license_records)
    smoke_license_record = _get_smoke_multi_state_license(license_records)
    _ensure_smoke_multi_state_has_paired_single_state_license(license_records, smoke_license_record)
    license_number = smoke_license_record.get('licenseNumber')
    if not license_number:
        raise SmokeTestFailureException('Smoke license record has no licenseNumber for public query')

    logger.info('Running public query endpoint test')
    matching_license_rows = call_public_query_providers(
        COMPACT,
        license_number_filter=license_number,
        provider_id_filter=provider_id,
    )
    if not matching_license_rows:
        raise SmokeTestFailureException(
            f'Public query returned no rows for provider {provider_id} (licenseNumber={license_number})'
        )
    license_row = matching_license_rows[0]
    if license_row.get('licenseScope') != 'multi-state':
        raise SmokeTestFailureException(
            f'Expected licenseScope multi-state for provider {provider_id}, got {license_row.get("licenseScope")!r}'
        )
    if license_row.get('licenseEligibility') != 'eligible':
        raise SmokeTestFailureException(
            f'Expected licenseEligibility eligible for provider {provider_id}, '
            f'got {license_row.get("licenseEligibility")!r}'
        )

    public_provider_detail = call_public_get_provider(COMPACT, provider_id)
    licenses_from_get = public_provider_detail.get('licenses') or []
    # get the license from the public GET response that matches the smoke license record
    matching_license_from_detail_response = next(
        (
            license_payload
            for license_payload in licenses_from_get
            if str(license_payload.get('jurisdiction', '')).lower() == smoke_license_record.get('jurisdiction')
            and license_payload.get('licenseType') == smoke_license_record.get('licenseType')
        ),
        None,
    )
    if matching_license_from_detail_response is None:
        raise SmokeTestFailureException(
            f'Matching license not found for provider {provider_id} from public GET response'
        )
    if matching_license_from_detail_response.get('licenseScope') != 'multi-state':
        raise SmokeTestFailureException(
            f'Expected licenseScope multi-state on public GET license, got '
            f'{matching_license_from_detail_response.get("licenseScope")!r}'
        )
    if matching_license_from_detail_response.get('compactEligibility') != 'eligible':
        raise SmokeTestFailureException(
            f'Expected compactEligibility eligible on public GET license, got '
            f'{matching_license_from_detail_response.get("compactEligibility")!r}'
        )

    logger.info('Public search smoke: baseline query + GET checks passed')

    return {
        'provider_id': provider_id,
        'license_number': license_number,
        'license_pk': smoke_license_record['pk'],
        'license_sk': smoke_license_record['sk'],
        'original_date_of_expiration': smoke_license_record['dateOfExpiration'],
        'original_jurisdiction_uploaded_compact_eligibility': smoke_license_record[
            'jurisdictionUploadedCompactEligibility'
        ],
    }


def test_public_query_endpoint_returns_ineligible_license_if_license_is_expired(provider_context: dict) -> None:
    """Mutates the smoke multi-state license expiration; row remains visible with ineligible eligibility."""
    provider_user_table = get_provider_user_dynamodb_table()
    license_partition_and_sort_key = {'pk': provider_context['license_pk'], 'sk': provider_context['license_sk']}
    original_date_of_expiration = provider_context['original_date_of_expiration']

    try:
        logger.info('Updating license expiration date to expired date')
        provider_user_table.update_item(
            Key=license_partition_and_sort_key,
            UpdateExpression='SET dateOfExpiration = :exp',
            ExpressionAttributeValues={':exp': EXPIRED_DATE_FOR_TEST},
        )
        wait_for_opensearch_sync()
        _assert_license_eligibility_for_smoke_license(
            provider_id=provider_context['provider_id'],
            license_number=provider_context['license_number'],
            expected_license_eligibility='ineligible',
        )
        logger.info('expiration ineligibility test passed')
    finally:
        logger.info('Restoring license expiration date to original value')
        provider_user_table.update_item(
            Key=license_partition_and_sort_key,
            UpdateExpression='SET dateOfExpiration = :exp',
            ExpressionAttributeValues={':exp': original_date_of_expiration},
        )
        wait_for_opensearch_sync()
        _assert_license_eligibility_for_smoke_license(
            provider_id=provider_context['provider_id'],
            license_number=provider_context['license_number'],
            expected_license_eligibility='eligible',
        )
        logger.info('license expiration date restored to original value')


def test_public_query_endpoint_returns_ineligible_license_if_license_is_marked_by_jurisdiction_as_ineligible(
    provider_context: dict,
) -> None:
    """Mutates jurisdictionUploadedCompactEligibility on the smoke multi-state license record."""
    provider_user_table = get_provider_user_dynamodb_table()
    license_partition_and_sort_key = {'pk': provider_context['license_pk'], 'sk': provider_context['license_sk']}
    original_jurisdiction_uploaded_compact_eligibility = provider_context[
        'original_jurisdiction_uploaded_compact_eligibility'
    ]

    try:
        logger.info('Updating license jurisdiction uploaded compact eligibility to ineligible')
        provider_user_table.update_item(
            Key=license_partition_and_sort_key,
            UpdateExpression='SET jurisdictionUploadedCompactEligibility = :ineligible',
            ExpressionAttributeValues={':ineligible': 'ineligible'},
        )
        wait_for_opensearch_sync()
        _assert_license_eligibility_for_smoke_license(
            provider_id=provider_context['provider_id'],
            license_number=provider_context['license_number'],
            expected_license_eligibility='ineligible',
        )
        logger.info('jurisdiction ineligibility test passed')
    finally:
        logger.info('Restoring license jurisdiction uploaded compact eligibility to original value')
        provider_user_table.update_item(
            Key=license_partition_and_sort_key,
            UpdateExpression='SET jurisdictionUploadedCompactEligibility = :j',
            ExpressionAttributeValues={':j': original_jurisdiction_uploaded_compact_eligibility},
        )
        wait_for_opensearch_sync()
        _assert_license_eligibility_for_smoke_license(
            provider_id=provider_context['provider_id'],
            license_number=provider_context['license_number'],
            expected_license_eligibility='eligible',
        )
        logger.info('license jurisdiction uploaded compact eligibility restored to original value')


def test_public_lookup_does_not_match_against_old_license_records(provider_context: dict) -> None:
    """
    Inserts a license with older issuance/renewal and verifies that it is not included in the public search results.
    """
    table = get_provider_user_dynamodb_table()
    source_key = {'pk': provider_context['license_pk'], 'sk': provider_context['license_sk']}
    response = table.get_item(Key=source_key)

    clone = copy.deepcopy(response['Item'])
    license_type = clone['licenseType']
    license_type_abbr = get_license_type_abbreviation(license_type)

    clone['dateOfIssuance'] = TEST_DATE_OF_ISSUANCE
    clone['dateOfRenewal'] = TEST_DATE_OF_RENEWAL
    clone['licenseNumber'] = TEST_LICENSE_NUMBER
    clone['jurisdiction'] = TEST_JURISDICTION

    license_scope = clone['licenseScope']
    clone['sk'] = f'{COMPACT}#PROVIDER#license/{TEST_JURISDICTION}/{license_type_abbr}/{license_scope}#'

    new_key: dict[str, str] | None = None
    try:
        table.put_item(Item=clone)
        new_key = {'pk': clone['pk'], 'sk': clone['sk']}
        wait_for_opensearch_sync()

        matching_rows = call_public_query_providers(
            COMPACT,
            license_number_filter=TEST_LICENSE_NUMBER,
            provider_id_filter=provider_context['provider_id'],
        )
        if matching_rows:
            raise SmokeTestFailureException(
                f'Expected no public query rows for test license {TEST_LICENSE_NUMBER!r}, got {matching_rows}'
            )

        public_provider_detail = call_public_get_provider(COMPACT, provider_context['provider_id'])
        for lic in public_provider_detail.get('licenses'):
            if lic.get('licenseNumber') == TEST_LICENSE_NUMBER:
                raise SmokeTestFailureException(f'Public GET unexpectedly included test license: {lic}')

        logger.info('Public search old license exclusion test passed')
    finally:
        if new_key is not None:
            logger.info(f'Deleting test license {new_key}')
            table.delete_item(Key=new_key)


if __name__ == '__main__':
    load_smoke_test_env()
    provider_context = test_public_search_endpoints_returns_details_of_provider()
    test_public_query_endpoint_returns_ineligible_license_if_license_is_expired(provider_context=provider_context)
    test_public_query_endpoint_returns_ineligible_license_if_license_is_marked_by_jurisdiction_as_ineligible(
        provider_context=provider_context
    )
    test_public_lookup_does_not_match_against_old_license_records(provider_context=provider_context)
    logger.info('All public search smoke tests completed successfully.')
