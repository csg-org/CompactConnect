# ruff: noqa: T201  we use print statements for smoke testing
#!/usr/bin/env python3
"""
Smoke tests for the SSN-correction migration feature (the optional 'previousSSN' license upload field).

When a state uploads a license carrying a 'previousSSN', the system migrates that license record - and its
adverse action, investigation, and update history records - from the provider id the incorrect SSN resolved
to over to the provider id of the corrected SSN. A correction moves ONE license record at a time, identified
by its jurisdiction, license type, and scope, so correcting a practitioner who holds both a single-state and
a multi-state license takes two uploads.

The behaviour these tests exist to protect is what happens to the practitioner's Compact Unique Identifier
(CUID) across those two uploads. A CUID is earned by holding a matching single-state/multi-state pair, and
it is a public search key, so it must neither be duplicated nor silently retired:

- After the FIRST correction the corrected practitioner holds only one license, so they do not qualify for a
  CUID yet. The identifier must stay on the original provider record.
- After the SECOND correction the pair is whole again under the corrected provider id and nothing remains
  behind, so the identifier must move across with it - the practitioner keeps the same public identifier
  they had before the correction.

These tests require:
- A state IT-system app client with write access to the test jurisdiction (created and torn down here).
- A staff user with read access to the compact (created and torn down here).

Note that by design, developers do not have the ability to delete records from the SSN DynamoDB table, so
the SSN records created by these tests are left in place. The tests use fixed mock SSNs so repeated runs
reuse the same SSN -> provider id mappings rather than accumulating new ones.

License uploads are performed against the State API (CC_TEST_STATE_API_BASE_URL) using a Cognito
client-credentials app client, the same way state IT systems authenticate in production. Provider lookups
(query by name) go through the general API (CC_TEST_API_BASE_URL) using a staff user, since
'providers/query' is a staff-facing endpoint, not a state-facing one.
"""

import json
import time
from collections.abc import Callable

import requests
from config import config, logger
from smoke_common import (
    SmokeTestFailureException,
    cleanup_test_provider_records,
    create_test_app_client,
    create_test_staff_user,
    delete_test_app_client,
    delete_test_staff_user,
    get_all_provider_database_records,
    get_client_auth_headers,
    get_staff_user_auth_headers,
    load_smoke_test_env,
    wait_for_provider_creation,
)

COMPACT = 'socw'
JURISDICTION = 'oh'
LICENSE_TYPE = 'licensed clinical social worker'

# A standalone mock practitioner, named distinctly from other smoke tests' practitioners. Note that this
# name deliberately resolves to TWO provider ids part way through the test: the original and the corrected
# one - which is why the provider query below collects every match rather than taking the first.
GIVEN_NAME = 'SsnMigration'
FAMILY_NAME = 'CuidSmokeTest'
ORIGINAL_SSN = '999-66-6666'
CORRECTED_SSN = '999-66-6677'

TEST_STAFF_USER_EMAIL = 'testStaffUserSocwSsnMigration@smokeTestFakeEmail.com'
TEST_APP_CLIENT_NAME = 'test-ssn-migration-smoke-client'

# Ingest runs through two SQS stages whose event source mappings use multi-minute batching windows, so a
# correction can take a while to land. See the developer note in license_upload_smoke_tests.py.
_MIGRATION_WAIT_SECONDS = 900
_POLL_INTERVAL_SECONDS = 30

# Record fields that legitimately change when a record is re-keyed to a new provider id, so they are
# excluded when comparing a provider's records before and after a migration. The provider id itself is
# normalized rather than dropped, so provider-id-derived values still participate in the comparison.
_VOLATILE_RECORD_FIELDS = ('pk', 'sk', 'dateOfUpdate', 'providerDateOfUpdate', 'ssnLastFour')


# -------------------------------------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------------------------------------
def _build_license(license_scope: str, ssn: str, previous_ssn: str | None = None) -> dict:
    """Build one license upload row. Passing previous_ssn makes it an SSN correction."""
    scope_suffix = 'SS' if license_scope == 'single-state' else 'MS'
    license_record = {
        'ssn': ssn,
        'licenseNumber': f'SSN-MIG-CUID-{scope_suffix}',
        'givenName': GIVEN_NAME,
        'familyName': FAMILY_NAME,
        'dateOfBirth': '1990-01-01',
        'dateOfIssuance': '2020-01-01',
        'dateOfExpiration': '2050-01-01',
        'licenseType': LICENSE_TYPE,
        'licenseScope': license_scope,
        'licenseStatus': 'active',
        'compactEligibility': 'eligible',
        'homeAddressStreet1': '123 Test Street',
        'homeAddressCity': 'Columbus',
        'homeAddressState': JURISDICTION.upper(),
        'homeAddressPostalCode': '43004',
    }
    if previous_ssn is not None:
        license_record['previousSSN'] = previous_ssn
    return license_record


def _upload_license_records(client_id: str, client_secret: str, license_records: list[dict]):
    """POST license records to the State API. Access tokens are short lived, so headers are regenerated here."""
    headers = get_client_auth_headers(client_id, client_secret, COMPACT, JURISDICTION)
    post_response = requests.post(
        url=f'{config.state_api_base_url}/v1/compacts/{COMPACT}/jurisdictions/{JURISDICTION}/licenses',
        headers=headers,
        json=license_records,
        timeout=60,
    )
    if post_response.status_code != 200:
        raise SmokeTestFailureException(f'Failed to POST license records. Response: {post_response.json()}')
    scopes = [record['licenseScope'] for record in license_records]
    print(f'Successfully uploaded {len(license_records)} license record(s) with scope(s) {scopes}')


def _wait_until(description: str, predicate: Callable, max_wait_seconds: int = _MIGRATION_WAIT_SECONDS):
    """Poll the given predicate until it returns a truthy value, or raise after the wait limit."""
    start_time = time.time()
    while time.time() - start_time < max_wait_seconds:
        result = predicate()
        if result:
            print(f'✅ {description} (after {time.time() - start_time:.0f} seconds)')
            return result
        print(f'Waiting for {description}...')
        time.sleep(_POLL_INTERVAL_SECONDS)
    raise SmokeTestFailureException(f'Timed out after {max_wait_seconds} seconds waiting for {description}')


def _provider_record(records: list[dict]) -> dict | None:
    return next((record for record in records if record['type'] == 'provider'), None)


def _license_scopes(records: list[dict]) -> set[str]:
    return {record['licenseScope'] for record in records if record['type'] == 'license'}


def _cuid(records: list[dict]) -> str | None:
    provider_record = _provider_record(records)
    return provider_record.get('publicCompactIdentifier') if provider_record else None


def _query_all_provider_ids_by_name(staff_headers: dict) -> list[str]:
    """Query the providers endpoint by name and return ALL matching provider ids.

    smoke_common.query_provider_by_name returns only the first match, on the assumption that each smoke test
    names its practitioner uniquely. A correction deliberately breaks that assumption: mid-test the same
    practitioner exists under two provider ids, and the one we need may not be first.

    The polling below can run for many minutes - long enough for the staff user's access token to expire,
    after which the endpoint returns 401. On a 401 the token is refreshed (mutating staff_headers in place,
    so every caller holding this dict picks up the new token) and the request retried once, so the
    long-running loops don't fail spuriously.
    """

    def _post():
        return requests.post(
            url=f'{config.api_base_url}/v1/compacts/{COMPACT}/providers/query',
            headers=staff_headers,
            json={'query': {'familyName': FAMILY_NAME, 'givenName': GIVEN_NAME}},
            timeout=10,
        )

    query_response = _post()
    if query_response.status_code == 401:
        logger.info('Staff auth token expired (401); refreshing and retrying provider query')
        staff_headers.update(get_staff_user_auth_headers(TEST_STAFF_USER_EMAIL))
        query_response = _post()
    if query_response.status_code != 200:
        logger.warning(f'Provider query failed with status {query_response.status_code}')
        return []
    return [provider['providerId'] for provider in query_response.json().get('providers', [])]


def _find_other_provider_id(staff_headers: dict, known_provider_id: str) -> str | None:
    """Find a provider id for our test practitioner that is not the one we already know about.

    Used to detect that a correction has landed: the corrected SSN resolves to a different provider id, and
    the practitioner becomes queryable under it once the migrated records arrive.
    """
    provider_ids = _query_all_provider_ids_by_name(staff_headers)
    return next((provider_id for provider_id in provider_ids if provider_id != known_provider_id), None)


def _stable_record_key(record: dict, provider_id: str) -> str:
    """A record identity that survives a migration.

    Every sort key this system writes is stable across a migration except for update records, whose final
    segment is a hash over the record's `previous` snapshot - and that snapshot can carry the provider id, so
    re-keying a record changes it. Dropping that one segment leaves the scope and the createDate, neither of
    which a migration touches.
    """
    sort_key = record['sk'].replace(provider_id, '<PROVIDER_ID>')
    if '#UPDATE#' in sort_key:
        sort_key = sort_key.rsplit('/', 1)[0]
    return f'{record["type"]}: {sort_key}'


def _normalized_migratable_records(records: list[dict], provider_id: str) -> dict[str, list[str]]:
    """Canonicalize a provider's records for comparison across provider ids.

    The top-level provider record is excluded because a migration rebuilds rather than moves it, and the
    ssnCorrection provider update records are excluded because each migration adds one rather than moving it.
    """
    normalized = {}
    for record in records:
        if record['type'] == 'provider' or (
            record['type'] == 'providerUpdate' and record.get('updateType') == 'ssnCorrection'
        ):
            continue
        scrubbed = {key: value for key, value in record.items() if key not in _VOLATILE_RECORD_FIELDS}
        canonical = json.dumps(scrubbed, sort_keys=True, default=str).replace(provider_id, '<PROVIDER_ID>')
        normalized.setdefault(_stable_record_key(record, provider_id), []).append(canonical)
    return normalized


def _describe_record_differences(source_canonical: str, target_canonical: str) -> str:
    """Describe field-by-field how two canonicalized records differ, for a readable failure message."""
    source_fields = json.loads(source_canonical)
    target_fields = json.loads(target_canonical)
    differences = []
    for field in sorted(set(source_fields) | set(target_fields)):
        before = source_fields.get(field, '<absent>')
        after = target_fields.get(field, '<absent>')
        if before != after:
            differences.append(f'{field}: before={before!r} after={after!r}')
    return '; '.join(differences)


def _verify_all_records_migrated(
    *, source_records: list[dict], source_provider_id: str, target_records: list[dict], target_provider_id: str
):
    """Verify every migratable record captured from the source provider now exists under the target, field for field.

    Records are paired on the stable part of their sort key and compared on content, so a record that changed
    is reported as a field-level diff rather than as a missing record.
    """
    source_normalized = _normalized_migratable_records(source_records, source_provider_id)
    target_normalized = _normalized_migratable_records(target_records, target_provider_id)

    problems = []
    source_record_count = 0
    for record_key, source_canonicals in source_normalized.items():
        unmatched_target_canonicals = list(target_normalized.get(record_key, []))
        for source_canonical in source_canonicals:
            source_record_count += 1
            if source_canonical in unmatched_target_canonicals:
                unmatched_target_canonicals.remove(source_canonical)
            elif unmatched_target_canonicals:
                differences = _describe_record_differences(source_canonical, unmatched_target_canonicals.pop(0))
                problems.append(f'{record_key}: {differences}')
            else:
                problems.append(f'{record_key}: no matching record under provider {target_provider_id}')

    if problems:
        raise SmokeTestFailureException(
            f'The following records did not survive migration to provider {target_provider_id} intact:\n  '
            + '\n  '.join(problems)
        )
    print(f'Verified all {source_record_count} migratable record(s) now exist under provider {target_provider_id}')


def _verify_license_ssn_last_four(
    *, records: list[dict], expected_ssn_last_four: str, license_scope: str | None = None
):
    """Verify license records carry the expected ssnLastFour.

    Checked separately from the record comparison above, which deliberately excludes ssnLastFour since it
    legitimately differs before and after a correction.
    """
    license_records = [
        record
        for record in records
        if record['type'] == 'license' and (license_scope is None or record['licenseScope'] == license_scope)
    ]
    if not license_records:
        raise SmokeTestFailureException('No license record found to verify ssnLastFour against')
    mismatched = [
        f'{record["licenseScope"]}: {record["ssnLastFour"]}'
        for record in license_records
        if record['ssnLastFour'] != expected_ssn_last_four
    ]
    if mismatched:
        raise SmokeTestFailureException(
            f'Expected ssnLastFour {expected_ssn_last_four} on all license records; found: {mismatched}'
        )
    print(f'Verified ssnLastFour {expected_ssn_last_four} on {len(license_records)} license record(s)')


# -------------------------------------------------------------------------------------------------
# The test
# -------------------------------------------------------------------------------------------------
def _records_with_both_scopes_and_a_cuid(provider_id: str):
    """Both licenses landed AND a CUID was assigned. Used to wait out the initial two-license upload.

    Waiting on the CUID rather than on the provider record matters: the provider record appears as soon as
    the first license is ingested, which is before the pair is complete and before a CUID exists.
    """
    records = get_all_provider_database_records(COMPACT, provider_id)
    if records and _license_scopes(records) == {'single-state', 'multi-state'} and _cuid(records):
        return records
    return None


def _records_with_both_scopes(provider_id: str):
    records = get_all_provider_database_records(COMPACT, provider_id)
    return records if records and _license_scopes(records) == {'single-state', 'multi-state'} else None


def _verify_cuid_stayed_after_first_correction(
    *, original_records: list[dict], corrected_records: list[dict], original_cuid: str, original_provider_id: str
):
    """After correcting one of two licenses, the identifier must not have moved or been reissued.

    The corrected practitioner holds a lone single-state license at this point, which has never been enough
    to qualify for a CUID, so there is nothing for one to attach to yet.
    """
    if _cuid(original_records) != original_cuid:
        raise SmokeTestFailureException(
            f'The original provider record lost its CUID after the first correction. Expected '
            f'{original_cuid}, found {_cuid(original_records)!r}. The corrected practitioner does not hold '
            f'a qualifying pair yet, so the identifier had to stay put.'
        )
    if _cuid(corrected_records) is not None:
        raise SmokeTestFailureException(
            f'The corrected provider record was given CUID {_cuid(corrected_records)!r} after only one of '
            f'two licenses had been corrected. A correction upload must never mint an identifier, and the '
            f'practitioner does not qualify for one yet.'
        )
    print(f'Verified CUID {original_cuid} stayed on provider {original_provider_id} after the first correction')


def test_ssn_correction_migrates_cuid_with_the_final_license(client_id: str, client_secret: str, staff_headers: dict):
    """
    A practitioner holding a matching single-state and multi-state license under one incorrect SSN has both
    corrected, one upload at a time, and their CUID must end up on the corrected provider record.

    Step 1: Upload both licenses under the incorrect SSN and wait for the practitioner to qualify for a CUID.
    Step 2: Correct the single-state license. The corrected practitioner now holds one license and does not
            qualify, so the CUID must stay on the original record.
    Step 3: Correct the multi-state license. The pair is whole again under the corrected provider id and
            nothing remains behind, so the CUID must move across with it, unchanged.
    Step 4: Verify the original partition is empty and every record arrived intact.

    Both provider partitions are cleaned up here rather than by the caller, so that a failure part way
    through still clears whatever records had been created by that point.
    """
    original_provider_id = None
    corrected_provider_id = None
    try:
        # Step 1: create the practitioner with a full pair under the incorrect SSN
        _upload_license_records(
            client_id,
            client_secret,
            [
                _build_license('single-state', ORIGINAL_SSN),
                _build_license('multi-state', ORIGINAL_SSN),
            ],
        )
        original_provider_id = wait_for_provider_creation(
            staff_headers,
            COMPACT,
            GIVEN_NAME,
            FAMILY_NAME,
            staff_user_email=TEST_STAFF_USER_EMAIL,
        )
        original_records = _wait_until(
            f'both licenses and a CUID to exist under provider {original_provider_id}',
            lambda: _records_with_both_scopes_and_a_cuid(original_provider_id),
        )
        original_cuid = _cuid(original_records)
        print(f'Practitioner {original_provider_id} was assigned CUID {original_cuid}')

        # Step 2: correct the single-state license only
        _upload_license_records(
            client_id,
            client_secret,
            [_build_license('single-state', CORRECTED_SSN, previous_ssn=ORIGINAL_SSN)],
        )
        corrected_provider_id = _wait_until(
            'the single-state license to migrate to the corrected provider id',
            lambda: _find_other_provider_id(staff_headers, original_provider_id),
        )
        _wait_until(
            f'the single-state license to leave provider {original_provider_id}',
            lambda: (
                _license_scopes(get_all_provider_database_records(COMPACT, original_provider_id)) == {'multi-state'}
            ),
        )

        after_first_correction_original = get_all_provider_database_records(COMPACT, original_provider_id)
        after_first_correction_corrected = get_all_provider_database_records(COMPACT, corrected_provider_id)
        _verify_cuid_stayed_after_first_correction(
            original_records=after_first_correction_original,
            corrected_records=after_first_correction_corrected,
            original_cuid=original_cuid,
            original_provider_id=original_provider_id,
        )
        _verify_license_ssn_last_four(
            records=after_first_correction_corrected, expected_ssn_last_four=CORRECTED_SSN[-4:]
        )
        # the license that stayed behind was never touched, so it must still carry the original last four
        _verify_license_ssn_last_four(
            records=after_first_correction_original,
            expected_ssn_last_four=ORIGINAL_SSN[-4:],
            license_scope='multi-state',
        )

        # Step 3: correct the multi-state license, completing the pair under the corrected provider id
        _upload_license_records(
            client_id,
            client_secret,
            [_build_license('multi-state', CORRECTED_SSN, previous_ssn=ORIGINAL_SSN)],
        )
        _wait_until(
            f'all records to be removed from the original provider {original_provider_id}',
            lambda: not get_all_provider_database_records(COMPACT, original_provider_id),
        )
        final_corrected_records = _wait_until(
            f'both licenses to exist under the corrected provider {corrected_provider_id}',
            lambda: _records_with_both_scopes(corrected_provider_id),
        )

        # Step 4: the identifier must have come across unchanged, not been reissued
        final_cuid = _cuid(final_corrected_records)
        if final_cuid != original_cuid:
            raise SmokeTestFailureException(
                f'Expected the corrected provider {corrected_provider_id} to carry the original CUID '
                f'{original_cuid} after the final correction, found {final_cuid!r}. A different value means '
                f"a new identifier was minted and the practitioner's published CUID has been retired."
            )
        print(f'Verified CUID {original_cuid} moved to provider {corrected_provider_id} with the final license')

        _verify_license_ssn_last_four(records=final_corrected_records, expected_ssn_last_four=CORRECTED_SSN[-4:])
        # every record the practitioner had must have arrived, not just the licenses
        _verify_all_records_migrated(
            source_records=original_records,
            source_provider_id=original_provider_id,
            target_records=final_corrected_records,
            target_provider_id=corrected_provider_id,
        )
        if not any(
            record['type'] == 'providerUpdate' and record.get('updateType') == 'ssnCorrection'
            for record in final_corrected_records
        ):
            raise SmokeTestFailureException(
                'No ssnCorrection provider update record found under the corrected provider id; the '
                'migration leaves no audit trail without it'
            )
        print('SSN correction CUID migration smoke test passed.')
    finally:
        # The SSN table records cannot be deleted by developers, and the fixed mock SSNs make reruns reuse
        # the same mappings, so only the provider partitions need clearing.
        for cleanup_provider_id in (original_provider_id, corrected_provider_id):
            if cleanup_provider_id:
                cleanup_test_provider_records(cleanup_provider_id, COMPACT)


if __name__ == '__main__':
    load_smoke_test_env()
    test_staff_user_sub = None
    test_client_id = None
    try:
        test_staff_user_sub = create_test_staff_user(
            email=TEST_STAFF_USER_EMAIL,
            compact=COMPACT,
            jurisdiction=JURISDICTION,
            permissions={'actions': {'admin'}, 'jurisdictions': {JURISDICTION: {'write', 'admin'}}},
        )
        client_credentials = create_test_app_client(TEST_APP_CLIENT_NAME, COMPACT, JURISDICTION)
        test_client_id = client_credentials['client_id']
        test_ssn_correction_migrates_cuid_with_the_final_license(
            client_id=test_client_id,
            client_secret=client_credentials['client_secret'],
            staff_headers=get_staff_user_auth_headers(TEST_STAFF_USER_EMAIL),
        )
        logger.info('SSN migration smoke tests passed')
    except SmokeTestFailureException as e:
        logger.error(f'SSN migration smoke test failed: {str(e)}')
    finally:
        if test_client_id:
            delete_test_app_client(test_client_id)
        if test_staff_user_sub:
            delete_test_staff_user(TEST_STAFF_USER_EMAIL, user_sub=test_staff_user_sub, compact=COMPACT)
