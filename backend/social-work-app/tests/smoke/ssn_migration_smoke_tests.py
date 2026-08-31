# ruff: noqa: T201  we use print statements for smoke testing
#!/usr/bin/env python3
"""
Smoke tests for the SSN-correction migration feature (the optional 'previousSSN' license upload field).

When a state uploads a license carrying a 'previousSSN', the system migrates that license record - and its
adverse action, investigation, and update history records - from the provider id the incorrect SSN resolved
to over to the provider id of the corrected SSN. A correction moves ONE license record at a time, identified
by its jurisdiction, license type, and scope.

The practitioner here holds licenses in TWO states under one incorrect SSN, and only the first state's
licenses are corrected. That shape is what makes the Compact Unique Identifier (CUID) behaviour observable:
a CUID is earned by holding a matching single-state/multi-state pair, it is a public search key, and it must
neither be duplicated nor silently retired.

- The FIRST state's pair is uploaded first, so it is the pair that earns the CUID.
- After correcting the first of its two licenses, the corrected practitioner holds a lone license and does
  not qualify, so the identifier must stay on the original record and must not be minted on the new one.
- After correcting the second, the pair is whole again under the corrected provider id and it is older than
  anything the original record still holds, so the identifier must move across - and BOTH records must carry
  a providerUpdate record of that, since the original provider survives (it still holds the second state's
  licenses) and would otherwise lose its CUID with no trace in its own partition.

These tests require:
- Both test jurisdictions live in the target environment, with the test license type recognized in each.
- A state IT-system app client with write access to both (created and torn down here).
- A staff user with read access to the compact (created and torn down here).

Expect a long runtime. A practitioner's single-state license must be fully ingested before their multi-state
license is uploaded (see the Upload order section of docs/README.md), so building the two pairs takes four
sequential upload/ingest cycles before the two corrections even begin - six waits in total, each of which
can take several minutes because of the SQS batching windows in front of the preprocess and ingest handlers.

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
# The state whose licenses get corrected. Uploaded FIRST, so its pair is the one that earns the CUID and the
# one the identifier must follow.
CORRECTED_JURISDICTION = 'oh'
# The state whose licenses stay put, keeping the original provider record alive through both corrections.
RETAINED_JURISDICTION = 'az'
# Recognized in both jurisdictions above - see the home state change flow in license_upload_smoke_tests.py,
# which moves this same license type between these same two states.
LICENSE_TYPE = 'licensed bachelors social worker'

# A standalone mock practitioner, named distinctly from other smoke tests' practitioners. Note that this
# name deliberately resolves to TWO provider ids part way through the test: the original and the corrected
# one - which is why the provider query below collects every match rather than taking the first.
GIVEN_NAME = 'SsnMigration'
FAMILY_NAME = 'CuidSmokeTest'
ORIGINAL_SSN = '999-66-6666'
CORRECTED_SSN = '999-66-6677'

# The jurisdiction the practitioner holds a privilege in. Privileges are generated for every live
# jurisdiction that recognises the license type, except the home jurisdiction - which for an OH-homed LBSW
# leaves AZ, since CO does not recognise this license type. It coincides with RETAINED_JURISDICTION for
# that reason rather than by design, and is named separately because it is chosen on different grounds.
PRIVILEGE_JURISDICTION = 'az'
LICENSE_TYPE_ABBREVIATION = 'lbsw'

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
def _build_license(jurisdiction: str, license_scope: str, ssn: str, previous_ssn: str | None = None) -> dict:
    """Build one license upload row. Passing previous_ssn makes it an SSN correction."""
    scope_suffix = 'SS' if license_scope == 'single-state' else 'MS'
    license_record = {
        'ssn': ssn,
        'licenseNumber': f'SSN-MIG-CUID-{jurisdiction.upper()}-{scope_suffix}',
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
        'homeAddressCity': 'Testville',
        'homeAddressState': jurisdiction.upper(),
        'homeAddressPostalCode': '43004',
    }
    if previous_ssn is not None:
        license_record['previousSSN'] = previous_ssn
    return license_record


def _upload_license(client_id: str, client_secret: str, jurisdiction: str, license_record: dict):
    """POST one license row to the State API. Access tokens are short lived, so headers are regenerated here."""
    headers = get_client_auth_headers(client_id, client_secret, COMPACT, jurisdiction)
    post_response = requests.post(
        url=f'{config.state_api_base_url}/v1/compacts/{COMPACT}/jurisdictions/{jurisdiction}/licenses',
        headers=headers,
        json=[license_record],
        timeout=60,
    )
    if post_response.status_code != 200:
        raise SmokeTestFailureException(
            f'Failed to POST {jurisdiction}/{license_record["licenseScope"]} license. Response: {post_response.json()}'
        )
    print(f'Uploaded {jurisdiction}/{license_record["licenseScope"]} license')


def _encumber_and_investigate_a_privilege(staff_headers: dict, provider_id: str):
    """Place an encumbrance and open an investigation against the practitioner's privilege.

    Called while the corrected state's pair is the practitioner's ONLY pair, so the home jurisdiction
    stamped onto both records is unambiguously that state. Doing it before the second state's licenses land
    is what makes the assertions below deterministic: the home license for a license type is the most
    recently renewed pair of that type, and both of this practitioner's pairs share a license type.
    """
    base = (
        f'{config.api_base_url}/v1/compacts/{COMPACT}/providers/{provider_id}'
        f'/privileges/jurisdiction/{PRIVILEGE_JURISDICTION}/licenseType/{LICENSE_TYPE_ABBREVIATION}'
    )

    encumbrance_response = requests.post(
        f'{base}/encumbrance',
        headers=staff_headers,
        json={
            'encumbranceEffectiveDate': '2024-01-15',
            'encumbranceType': 'suspension',
            'clinicalPrivilegeActionCategories': ['Fraud, Deception, or Misrepresentation'],
        },
        timeout=30,
    )
    if encumbrance_response.status_code != 200:
        raise SmokeTestFailureException(f'Failed to encumber the privilege. Response: {encumbrance_response.json()}')

    investigation_response = requests.post(f'{base}/investigation', headers=staff_headers, json={}, timeout=30)
    if investigation_response.status_code != 200:
        raise SmokeTestFailureException(
            f'Failed to open a privilege investigation. Response: {investigation_response.json()}'
        )

    print(f'Encumbered and opened an investigation against the {PRIVILEGE_JURISDICTION} privilege')


def _privilege_records(records: list[dict]) -> list[dict]:
    """The adverse action and investigation records recorded against a privilege, rather than a license."""
    return [
        record
        for record in records
        if record.get('actionAgainst') == 'privilege' or record.get('investigationAgainst') == 'privilege'
    ]


def _verify_privilege_records_are_on(records: list[dict], provider_id: str, description: str):
    if len(_privilege_records(records)) != 2:
        raise SmokeTestFailureException(
            f'Expected the privilege encumbrance and investigation to be on {description} '
            f'(provider {provider_id}); found {len(_privilege_records(records))} privilege record(s). These '
            f'belong to the multi-state license that generated the privilege and must travel with it.'
        )
    for record in _privilege_records(records):
        if record.get('homeJurisdictionAtTimeOfCreation') != CORRECTED_JURISDICTION:
            raise SmokeTestFailureException(
                f'A privilege record carries homeJurisdictionAtTimeOfCreation '
                f'{record.get("homeJurisdictionAtTimeOfCreation")!r}, expected {CORRECTED_JURISDICTION!r}. '
                f'That field is what routes it during a correction.'
            )
    print(f'Verified both privilege records are on {description}')


def _verify_no_privilege_records_on(records: list[dict], provider_id: str, description: str):
    if _privilege_records(records):
        raise SmokeTestFailureException(
            f'Found {len(_privilege_records(records))} privilege record(s) on {description} '
            f'(provider {provider_id}); expected none.'
        )
    print(f'Verified no privilege records on {description}')


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


def _license_keys(records: list[dict]) -> set[tuple[str, str]]:
    """The (jurisdiction, scope) of every license record, which is what identifies one here."""
    return {(record['jurisdiction'], record['licenseScope']) for record in records if record['type'] == 'license'}


def _ssn_correction_updates(records: list[dict]) -> list[dict]:
    return [
        record for record in records if record['type'] == 'providerUpdate' and record['updateType'] == 'ssnCorrection'
    ]


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
    *,
    records: list[dict],
    expected_ssn_last_four: str,
    jurisdiction: str | None = None,
    license_scope: str | None = None,
):
    """Verify license records carry the expected ssnLastFour.

    Checked separately from the record comparison above, which deliberately excludes ssnLastFour since it
    legitimately differs before and after a correction.
    """
    license_records = [
        record
        for record in records
        if record['type'] == 'license'
        and (jurisdiction is None or record['jurisdiction'] == jurisdiction)
        and (license_scope is None or record['licenseScope'] == license_scope)
    ]
    if not license_records:
        raise SmokeTestFailureException('No license record found to verify ssnLastFour against')
    mismatched = [
        f'{record["jurisdiction"]}/{record["licenseScope"]}: {record["ssnLastFour"]}'
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
def _records_once_licenses_present(provider_id: str, expected_license_keys: set, *, require_cuid: bool = False):
    """Return the provider's records once the expected licenses are present, else None to keep polling."""
    records = get_all_provider_database_records(COMPACT, provider_id)
    if not records or not expected_license_keys.issubset(_license_keys(records)):
        return None
    if require_cuid and not _cuid(records):
        return None
    return records


def _build_both_pairs_under_the_incorrect_ssn(client_id: str, client_secret: str, staff_headers: dict):
    """Create the practitioner with a full license pair in each of two states, under one incorrect SSN.

    Uploaded strictly in order - the corrected state's pair first, and within each state the single-state
    license fully ingested before the multi-state one. Both orderings matter:

    - Single before multi is required of states generally (see docs/README.md, Upload order).
    - The corrected state's pair going first is what makes it the pair that earns the CUID, and therefore
      the pair the identifier has to follow when it is corrected. Uploading everything at once would leave
      that to the order the ingest queue happened to process the rows in.

    :return: (provider_id, cuid, all records under that provider)
    """
    _upload_license(
        client_id,
        client_secret,
        CORRECTED_JURISDICTION,
        _build_license(CORRECTED_JURISDICTION, 'single-state', ORIGINAL_SSN),
    )
    provider_id = wait_for_provider_creation(
        staff_headers, COMPACT, GIVEN_NAME, FAMILY_NAME, staff_user_email=TEST_STAFF_USER_EMAIL
    )
    _wait_until(
        f'the {CORRECTED_JURISDICTION} single-state license to be ingested',
        lambda: _records_once_licenses_present(provider_id, {(CORRECTED_JURISDICTION, 'single-state')}),
    )

    _upload_license(
        client_id,
        client_secret,
        CORRECTED_JURISDICTION,
        _build_license(CORRECTED_JURISDICTION, 'multi-state', ORIGINAL_SSN),
    )
    # The pair completing is what mints the CUID, so this is the first point at which one exists
    records = _wait_until(
        f'the {CORRECTED_JURISDICTION} pair to be complete and a CUID to be assigned',
        lambda: _records_once_licenses_present(
            provider_id,
            {(CORRECTED_JURISDICTION, 'single-state'), (CORRECTED_JURISDICTION, 'multi-state')},
            require_cuid=True,
        ),
    )
    cuid = _cuid(records)
    print(f'Practitioner {provider_id} was assigned CUID {cuid} by the {CORRECTED_JURISDICTION} pair')

    # Encumber and investigate the privilege now, while this is the practitioner's only pair, so the home
    # jurisdiction recorded on both is unambiguously the state whose licenses get corrected below
    _encumber_and_investigate_a_privilege(staff_headers, provider_id)
    _wait_until(
        'the privilege encumbrance and investigation to be recorded',
        lambda: len(_privilege_records(get_all_provider_database_records(COMPACT, provider_id))) == 2,
    )

    _upload_license(
        client_id,
        client_secret,
        RETAINED_JURISDICTION,
        _build_license(RETAINED_JURISDICTION, 'single-state', ORIGINAL_SSN),
    )
    _wait_until(
        f'the {RETAINED_JURISDICTION} single-state license to be ingested',
        lambda: _records_once_licenses_present(provider_id, {(RETAINED_JURISDICTION, 'single-state')}),
    )
    _upload_license(
        client_id,
        client_secret,
        RETAINED_JURISDICTION,
        _build_license(RETAINED_JURISDICTION, 'multi-state', ORIGINAL_SSN),
    )
    all_records = _wait_until(
        f'the {RETAINED_JURISDICTION} pair to be complete',
        lambda: _records_once_licenses_present(
            provider_id,
            {(RETAINED_JURISDICTION, 'single-state'), (RETAINED_JURISDICTION, 'multi-state')},
        ),
    )

    if _cuid(all_records) != cuid:
        raise SmokeTestFailureException(
            f'The CUID changed while building the second pair: was {cuid}, now {_cuid(all_records)!r}. A '
            f'practitioner is assigned one identifier, and holding a second qualifying pair must not reissue it.'
        )
    print(f'Practitioner {provider_id} now holds pairs in both {CORRECTED_JURISDICTION} and {RETAINED_JURISDICTION}')
    return provider_id, cuid, all_records


def _verify_state_after_first_correction(
    *, original_records: list[dict], corrected_records: list[dict], original_cuid: str, original_provider_id: str
):
    """After the first of two corrections, the identifier must not have moved, and neither record may claim it.

    The corrected practitioner holds a lone single-state license at this point, which has never been enough
    to qualify, so there is nothing for a CUID to attach to yet.
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
    # The corrected provider gets an audit record for every migration, but the original provider only gets
    # one when it actually loses something - which has not happened yet.
    if not _ssn_correction_updates(corrected_records):
        raise SmokeTestFailureException(
            'No ssnCorrection record was written under the corrected provider id; every migration has to '
            'leave an audit trail there'
        )
    if _ssn_correction_updates(original_records):
        raise SmokeTestFailureException(
            'An ssnCorrection record was written under the original provider id after the first correction, '
            'but it kept its CUID and lost nothing. A record of a loss that did not happen is worse than none.'
        )
    print(f'Verified CUID {original_cuid} stayed on provider {original_provider_id} after the first correction')


def _verify_cuid_history_records(
    *, original_records: list[dict], corrected_records: list[dict], original_cuid: str, original_provider_id: str
):
    """Both partitions must record the identifier changing hands.

    The corrected side has the audit record every migration writes. The original side needs its own, because
    it survives this correction (it still holds the second state's licenses) and its top-level record is
    rewritten without the CUID - so without a record here, 'what was this provider's CUID before the
    correction?' is unanswerable from the partition support staff would actually be looking at.
    """
    corrected_updates = _ssn_correction_updates(corrected_records)
    if len(corrected_updates) != 2:
        raise SmokeTestFailureException(
            f'Expected one ssnCorrection record under the corrected provider per correction (2), found '
            f'{len(corrected_updates)}'
        )

    original_updates = _ssn_correction_updates(original_records)
    if len(original_updates) != 1:
        raise SmokeTestFailureException(
            f'Expected exactly one ssnCorrection record under the original provider {original_provider_id} - '
            f'written when it lost its CUID on the second correction - found {len(original_updates)}'
        )
    history_record = original_updates[0]
    if history_record.get('previous', {}).get('publicCompactIdentifier') != original_cuid:
        raise SmokeTestFailureException(
            f'The history record under the original provider does not carry the CUID it lost. Expected '
            f'{original_cuid} in previous.publicCompactIdentifier, found '
            f'{history_record.get("previous", {}).get("publicCompactIdentifier")!r}. Without it the old '
            f'identifier is unrecoverable from this partition.'
        )
    if 'publicCompactIdentifier' not in history_record.get('removedValues', []):
        raise SmokeTestFailureException(
            f'The history record under the original provider does not name publicCompactIdentifier in '
            f'removedValues; found {history_record.get("removedValues")!r}'
        )
    print(f'Verified both providers carry a record of CUID {original_cuid} changing hands')


def test_ssn_correction_migrates_cuid_with_the_final_license(client_id: str, client_secret: str, staff_headers: dict):
    """
    A practitioner holds a license pair in each of two states under one incorrect SSN. Only the first
    state's licenses are corrected, one upload at a time, and their CUID must end up on the corrected record
    while the original record survives on the second state's licenses.

    Step 1: Build both pairs under the incorrect SSN, the corrected state's first so it earns the CUID.
    Step 2: Correct the first state's single-state license. The corrected practitioner holds one license and
            does not qualify, so the CUID stays put and neither record claims it.
    Step 3: Correct the first state's multi-state license. That pair is whole again under the corrected
            provider id and is older than anything left behind, so the CUID moves across.
    Step 4: Verify both providers carry a record of the change, the retained state's licenses were never
            touched, and the migrated records arrived intact.

    Both provider partitions are cleaned up here rather than by the caller, so that a failure part way
    through still clears whatever records had been created by that point.
    """
    original_provider_id = None
    corrected_provider_id = None
    try:
        # Step 1
        original_provider_id, original_cuid, pre_correction_records = _build_both_pairs_under_the_incorrect_ssn(
            client_id, client_secret, staff_headers
        )

        # Step 2: correct the single-state license of the first state only
        _upload_license(
            client_id,
            client_secret,
            CORRECTED_JURISDICTION,
            _build_license(CORRECTED_JURISDICTION, 'single-state', CORRECTED_SSN, previous_ssn=ORIGINAL_SSN),
        )
        corrected_provider_id = _wait_until(
            'the single-state license to migrate to the corrected provider id',
            lambda: _find_other_provider_id(staff_headers, original_provider_id),
        )
        _wait_until(
            f'the {CORRECTED_JURISDICTION} single-state license to leave provider {original_provider_id}',
            lambda: (
                (CORRECTED_JURISDICTION, 'single-state')
                not in _license_keys(get_all_provider_database_records(COMPACT, original_provider_id))
            ),
        )

        after_first_original = get_all_provider_database_records(COMPACT, original_provider_id)
        after_first_corrected = get_all_provider_database_records(COMPACT, corrected_provider_id)
        _verify_state_after_first_correction(
            original_records=after_first_original,
            corrected_records=after_first_corrected,
            original_cuid=original_cuid,
            original_provider_id=original_provider_id,
        )
        # A single-state license never generates privileges, so its correction must leave these behind
        _verify_privilege_records_are_on(
            after_first_original, original_provider_id, 'the original practitioner after the first correction'
        )
        _verify_no_privilege_records_on(
            after_first_corrected, corrected_provider_id, 'the corrected practitioner after the first correction'
        )
        _verify_license_ssn_last_four(records=after_first_corrected, expected_ssn_last_four=CORRECTED_SSN[-4:])
        # everything still on the original record was untouched, so it keeps the original last four
        _verify_license_ssn_last_four(records=after_first_original, expected_ssn_last_four=ORIGINAL_SSN[-4:])

        # Step 3: correct the multi-state license, completing the pair under the corrected provider id
        _upload_license(
            client_id,
            client_secret,
            CORRECTED_JURISDICTION,
            _build_license(CORRECTED_JURISDICTION, 'multi-state', CORRECTED_SSN, previous_ssn=ORIGINAL_SSN),
        )
        final_corrected_records = _wait_until(
            f'both {CORRECTED_JURISDICTION} licenses to exist under the corrected provider {corrected_provider_id}',
            lambda: _records_once_licenses_present(
                corrected_provider_id,
                {(CORRECTED_JURISDICTION, 'single-state'), (CORRECTED_JURISDICTION, 'multi-state')},
                require_cuid=True,
            ),
        )
        final_original_records = get_all_provider_database_records(COMPACT, original_provider_id)

        # Step 4
        final_cuid = _cuid(final_corrected_records)
        if final_cuid != original_cuid:
            raise SmokeTestFailureException(
                f'Expected the corrected provider {corrected_provider_id} to carry the original CUID '
                f'{original_cuid} after the final correction, found {final_cuid!r}. A different value means '
                f"a new identifier was minted and the practitioner's published CUID has been retired."
            )
        if _cuid(final_original_records) is not None:
            raise SmokeTestFailureException(
                f'The original provider {original_provider_id} still carries CUID '
                f'{_cuid(final_original_records)!r} after it moved to the corrected provider. One '
                f'practitioner cannot hold the identifier in two places.'
            )
        print(f'Verified CUID {original_cuid} moved to provider {corrected_provider_id} with the final license')

        # the original provider must still exist, holding the state whose licenses were never corrected
        if _license_keys(final_original_records) != {
            (RETAINED_JURISDICTION, 'single-state'),
            (RETAINED_JURISDICTION, 'multi-state'),
        }:
            raise SmokeTestFailureException(
                f'Expected the original provider to retain only the {RETAINED_JURISDICTION} pair, found '
                f'{sorted(_license_keys(final_original_records))}'
            )
        _verify_cuid_history_records(
            original_records=final_original_records,
            corrected_records=final_corrected_records,
            original_cuid=original_cuid,
            original_provider_id=original_provider_id,
        )

        # The multi-state license that generated the privilege has moved, so its records go with it
        _verify_privilege_records_are_on(
            final_corrected_records, corrected_provider_id, 'the corrected practitioner after the final correction'
        )
        _verify_no_privilege_records_on(
            final_original_records, original_provider_id, 'the original practitioner after the final correction'
        )
        _verify_license_ssn_last_four(records=final_corrected_records, expected_ssn_last_four=CORRECTED_SSN[-4:])
        # the retained state's licenses were never part of a correction, so they keep the original last four
        _verify_license_ssn_last_four(
            records=final_original_records,
            expected_ssn_last_four=ORIGINAL_SSN[-4:],
            jurisdiction=RETAINED_JURISDICTION,
        )
        # and the corrected state's records must have arrived intact, not merely be present
        _verify_all_records_migrated(
            source_records=[
                record for record in pre_correction_records if record.get('jurisdiction') == CORRECTED_JURISDICTION
            ],
            source_provider_id=original_provider_id,
            target_records=final_corrected_records,
            target_provider_id=corrected_provider_id,
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
            jurisdiction=CORRECTED_JURISDICTION,
            permissions={
                'actions': {'admin'},
                'jurisdictions': {
                    CORRECTED_JURISDICTION: {'write', 'admin'},
                    RETAINED_JURISDICTION: {'write', 'admin'},
                },
            },
        )
        client_credentials = create_test_app_client(
            TEST_APP_CLIENT_NAME, COMPACT, jurisdictions=[CORRECTED_JURISDICTION, RETAINED_JURISDICTION]
        )
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
