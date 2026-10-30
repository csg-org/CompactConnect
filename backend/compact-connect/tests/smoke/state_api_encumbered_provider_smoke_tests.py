#!/usr/bin/env python3
"""
Smoke test for the state API provider read when a license is encumbered.

GET /v1/compacts/{compact}/jurisdictions/{jurisdiction}/providers/{providerId}
used to fail whenever the home license and its privileges both stored encumberedStatus.
This walks that path against a sandbox: an unencumbered read, a license-level encumbrance,
the same provider after the encumbrance is lifted, and a privilege-level encumbrance.

Run from the compact-connect directory, with smoke_tests_env.json configured:

    python3 tests/smoke/state_api_encumbered_provider_smoke_tests.py
"""

import requests
from encumbrance_smoke_tests import (
    EncumbranceTestHelper,
    clean_adverse_actions,
    setup_test_environment,
)
from signature_auth_smoke_tests import (
    COMPACT,
    JURISDICTION,
    configure_signature_public_key,
    create_signed_headers,
    create_test_app_client,
    delete_test_app_client,
    get_client_auth_headers,
    get_state_api_base_url,
    load_test_keys,
    remove_signature_public_key,
)
from smoke_common import (
    SmokeTestFailureException,
    call_provider_users_me_endpoint,
    load_smoke_test_env,
    logger,
)

_LICENSE_ENCUMBRANCE = {
    'encumbranceEffectiveDate': '2025-01-15',
    'encumbranceType': 'surrender of license',
    'clinicalPrivilegeActionCategories': ['Fraud, Deception, or Misrepresentation'],
}
_PRIVILEGE_ENCUMBRANCE = {
    'encumbranceEffectiveDate': '2025-03-01',
    'encumbranceType': 'fine',
    'clinicalPrivilegeActionCategories': ['Fraud, Deception, or Misrepresentation'],
}


def _get_state_provider(provider_id: str, *, client_headers: dict, private_key_pem: str) -> dict:
    path = f'/v1/compacts/{COMPACT}/jurisdictions/{JURISDICTION}/providers/{provider_id}'
    signature_headers = create_signed_headers(
        method='GET',
        path=path,
        query_params={},
        private_key_pem=private_key_pem,
    )
    response = requests.get(
        url=get_state_api_base_url() + path,
        headers={**client_headers, **signature_headers},
        timeout=30,
    )
    if response.status_code != 200:
        raise SmokeTestFailureException(
            f'State API GET provider failed. Response: {response.status_code} - {response.text}'
        )
    return response.json()


def _matching_privilege(body: dict, helper: EncumbranceTestHelper) -> dict:
    matches = [
        privilege
        for privilege in body.get('privileges', [])
        if privilege.get('jurisdiction') == helper.privilege_jurisdiction
        and privilege.get('licenseJurisdiction') == helper.license_jurisdiction
        and privilege.get('licenseType') == helper.license_type
    ]
    if len(matches) != 1:
        raise SmokeTestFailureException(
            f'Expected one privilege for {helper.privilege_jurisdiction}/{helper.license_type}, '
            f'found {len(matches)}. Response privileges: {body.get("privileges")}'
        )
    return matches[0]


def _assert_privilege_state(
    body: dict,
    helper: EncumbranceTestHelper,
    *,
    status: str,
    license_status: str,
    compact_eligibility: str,
):
    if helper.provider_id not in body.get('providerUIUrl', ''):
        raise SmokeTestFailureException(f'providerUIUrl missing provider id. Response: {body}')

    privilege = _matching_privilege(body, helper)
    actual = {
        'status': privilege.get('status'),
        'licenseStatus': privilege.get('licenseStatus'),
        'compactEligibility': privilege.get('compactEligibility'),
    }
    expected = {
        'status': status,
        'licenseStatus': license_status,
        'compactEligibility': compact_eligibility,
    }
    if actual != expected:
        raise SmokeTestFailureException(f'Privilege state {actual} did not match {expected}. Privilege: {privilege}')
    if 'encumberedStatus' in privilege:
        raise SmokeTestFailureException(
            f'State API response included encumberedStatus, which this read contract does not publish: {privilege}'
        )


def _first_adverse_action_id(adverse_actions: list[dict], record_name: str) -> str:
    if len(adverse_actions) != 1:
        raise SmokeTestFailureException(f'Expected 1 {record_name} adverse action, found {len(adverse_actions)}')
    adverse_action_id = adverse_actions[0].get('adverseActionId')
    if not adverse_action_id:
        raise SmokeTestFailureException(f'{record_name} adverse action is missing adverseActionId')
    return adverse_action_id


def state_api_encumbered_provider_smoke_test():
    """Read the same provider through the signed state API across encumbrance states."""
    logger.info('Starting state API encumbered provider smoke test')
    setup_test_environment()

    provider_data = call_provider_users_me_endpoint()
    helper = EncumbranceTestHelper(provider_data)
    private_key_pem, public_key_pem = load_test_keys()
    client_id = None
    license_adverse_action_id = None
    privilege_adverse_action_id = None
    license_lifted = False
    privilege_lifted = False

    try:
        if helper.compact != COMPACT or helper.privilege_jurisdiction != JURISDICTION:
            raise SmokeTestFailureException(
                f'Signature client is configured for {COMPACT}/{JURISDICTION}, but the test privilege is '
                f'{helper.compact}/{helper.privilege_jurisdiction}'
            )

        client_credentials = create_test_app_client()
        client_id = client_credentials['client_id']
        configure_signature_public_key(public_key_pem)
        client_headers = get_client_auth_headers(client_id, client_credentials['client_secret'])

        logger.info('Reading provider before any encumbrance')
        baseline = _get_state_provider(
            helper.provider_id, client_headers=client_headers, private_key_pem=private_key_pem
        )
        _assert_privilege_state(
            baseline, helper, status='active', license_status='active', compact_eligibility='eligible'
        )

        logger.info('Encumbering the home license')
        helper.encumber_license(_LICENSE_ENCUMBRANCE)
        license_adverse_action_id = _first_adverse_action_id(helper.get_license_adverse_actions(), 'license')
        helper.validate_privilege_encumbered_state(expected_status='licenseEncumbered')

        logger.info('Reading provider while the home license is encumbered')
        encumbered = _get_state_provider(
            helper.provider_id, client_headers=client_headers, private_key_pem=private_key_pem
        )
        _assert_privilege_state(
            encumbered, helper, status='inactive', license_status='inactive', compact_eligibility='ineligible'
        )

        logger.info('Lifting the license encumbrance')
        helper.lift_license_encumbrance({'effectiveLiftDate': '2025-02-01'}, license_adverse_action_id)
        license_lifted = True
        helper.validate_privilege_encumbered_state(expected_status='unencumbered')

        logger.info('Reading provider after the license encumbrance was lifted')
        lifted = _get_state_provider(
            helper.provider_id, client_headers=client_headers, private_key_pem=private_key_pem
        )
        _assert_privilege_state(
            lifted, helper, status='active', license_status='active', compact_eligibility='eligible'
        )

        logger.info('Encumbering the privilege only')
        helper.encumber_privilege(_PRIVILEGE_ENCUMBRANCE)
        privilege_adverse_action_id = _first_adverse_action_id(helper.get_privilege_adverse_actions(), 'privilege')
        helper.validate_privilege_encumbered_state(expected_status='encumbered', max_wait_time=1, check_interval=1)

        logger.info('Reading provider with a privilege-level encumbrance')
        privilege_encumbered = _get_state_provider(
            helper.provider_id, client_headers=client_headers, private_key_pem=private_key_pem
        )
        _assert_privilege_state(
            privilege_encumbered,
            helper,
            status='inactive',
            license_status='active',
            compact_eligibility='eligible',
        )

        helper.lift_privilege_encumbrance({'effectiveLiftDate': '2025-04-01'}, privilege_adverse_action_id)
        privilege_lifted = True
        helper.validate_privilege_encumbered_state(expected_status='unencumbered')
        logger.info('State API encumbered provider smoke test completed successfully')
    finally:
        if license_adverse_action_id and not license_lifted:
            try:
                helper.lift_license_encumbrance({'effectiveLiftDate': '2025-02-01'}, license_adverse_action_id)
            except Exception as e:  # noqa: BLE001 cleanup must not hide the original failure
                logger.warning(f'Failed to lift license encumbrance during cleanup: {e}')
        if privilege_adverse_action_id and not privilege_lifted:
            try:
                helper.lift_privilege_encumbrance({'effectiveLiftDate': '2025-04-01'}, privilege_adverse_action_id)
            except Exception as e:  # noqa: BLE001 cleanup must not hide the original failure
                logger.warning(f'Failed to lift privilege encumbrance during cleanup: {e}')
        clean_adverse_actions()
        helper.cleanup_staff_users()
        remove_signature_public_key()
        if client_id is not None:
            delete_test_app_client(client_id)


if __name__ == '__main__':
    load_smoke_test_env()

    try:
        state_api_encumbered_provider_smoke_test()
        logger.info('State API encumbered provider smoke test passed')
    except SmokeTestFailureException as e:
        logger.error(f'State API encumbered provider smoke test failed: {str(e)}')
        raise
