# ruff: noqa: T201  we use print statements for smoke testing
#!/usr/bin/env python3
"""
Smoke test for optional, non-searchable license upload fields (country, altFamilyName, militaryStatus).

Does NOT require security_profile: VULNERABLE. It creates a Cognito state app client via
app_clients/bin/create_app_client.py, uploads a license through the state API (client credentials),
then asserts the optional fields on the DynamoDB license record.

Run from social-work-app:

  python3 tests/smoke/optional_license_fields_smoke_tests.py

Expect a multi-minute wait while license ingest SQS batching windows drain.
"""

from __future__ import annotations

import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote

import requests
from boto3.dynamodb.conditions import Key
from config import config, logger
from smoke_common import (
    SmokeTestFailureException,
    cleanup_test_provider_records,
    delete_test_app_client,
    get_client_auth_headers,
    get_provider_user_dynamodb_table,
    load_smoke_test_env,
)

# Import the shared state-auth app-client creator (same script used for real state clients).
_APP_CLIENTS_BIN = Path(__file__).resolve().parents[2] / 'app_clients' / 'bin'
sys.path.insert(0, str(_APP_CLIENTS_BIN))
from create_app_client import create_app_client  # noqa: E402

COMPACT = 'socw'
JURISDICTION = 'az'
LICENSE_TYPE = 'licensed bachelors social worker'
TEST_APP_CLIENT_NAME = 'test-optional-license-fields-smoke-client'

OPTIONAL_UPLOAD_COUNTRY = 'United States'
OPTIONAL_UPLOAD_ALT_FAMILY_NAME = 'García'
OPTIONAL_UPLOAD_MILITARY_STATUS = False


def _optional_upload_fields() -> dict:
    return {
        'country': OPTIONAL_UPLOAD_COUNTRY,
        'altFamilyName': OPTIONAL_UPLOAD_ALT_FAMILY_NAME,
        'militaryStatus': OPTIONAL_UPLOAD_MILITARY_STATUS,
    }


def _assert_optional_upload_fields(license_record: dict, *, owner: str) -> None:
    expected = _optional_upload_fields()
    for field_name, expected_value in expected.items():
        actual_value = license_record.get(field_name)
        if actual_value != expected_value:
            raise SmokeTestFailureException(
                f'Expected {field_name}={expected_value!r} on {owner}, found {actual_value!r}'
            )
    logger.info(f'Verified optional upload fields on {owner}: {expected}')


def _create_state_app_client_via_script(*, client_name: str, compact: str, jurisdiction: str) -> dict:
    """
    Create a state Cognito app client using create_app_client from app_clients/bin/create_app_client.py.

    Grants the same scopes smoke upload helpers request for client-credentials tokens:
    {compact}/readGeneral and {jurisdiction}/{compact}.write.
    """
    logger.info(
        f'Creating state app client via create_app_client.py: name={client_name}, '
        f'compact={compact}, jurisdiction={jurisdiction}'
    )
    try:
        response = create_app_client(
            config.cognito_state_auth_user_pool_id,
            {
                'clientName': client_name,
                'scopes': [
                    f'{compact}/readGeneral',
                    f'{jurisdiction}/{compact}.write',
                ],
            },
        )
    except SystemExit as e:
        raise SmokeTestFailureException(
            f'create_app_client.py exited while creating app client {client_name!r}'
        ) from e

    user_pool_client = response.get('UserPoolClient', {})
    client_id = user_pool_client.get('ClientId')
    client_secret = user_pool_client.get('ClientSecret')
    if not client_id or not client_secret:
        raise SmokeTestFailureException('create_app_client.py response missing ClientId or ClientSecret')

    logger.info(f'Successfully created state app client with ID: {client_id}')
    return {'client_id': client_id, 'client_secret': client_secret}


def _build_license_post_body(*, given_name: str, family_name: str, ssn: str, license_number: str) -> list[dict]:
    return [
        {
            'licenseNumber': license_number,
            'homeAddressPostalCode': '85001',
            'givenName': given_name,
            'familyName': family_name,
            'homeAddressStreet1': '123 Optional Fields Smoke Street',
            'dateOfBirth': '1990-06-15',
            'dateOfIssuance': '2024-01-15',
            'ssn': ssn,
            'licenseType': LICENSE_TYPE,
            'licenseScope': 'single-state',
            'dateOfExpiration': '2050-12-10',
            'homeAddressState': JURISDICTION.upper(),
            'homeAddressCity': 'Phoenix',
            'compactEligibility': 'eligible',
            'licenseStatus': 'active',
            **_optional_upload_fields(),
        }
    ]


def _post_license(*, client_id: str, client_secret: str, post_body: list[dict]) -> None:
    auth_headers = get_client_auth_headers(client_id, client_secret, COMPACT, JURISDICTION)
    post_response = requests.post(
        url=f'{config.state_api_base_url}/v1/compacts/{COMPACT}/jurisdictions/{JURISDICTION}/licenses',
        headers=auth_headers,
        json=post_body,
        timeout=60,
    )
    if post_response.status_code != 200:
        raise SmokeTestFailureException(
            f'Failed to POST optional-fields license. Status: {post_response.status_code}, '
            f'Response: {post_response.text}'
        )
    logger.info(f'License upload accepted: {post_response.json()}')


def _wait_for_license_record_in_dynamo(
    *,
    given_name: str,
    family_name: str,
    max_wait_seconds: int = 720,
    poll_interval_seconds: int = 60,
) -> dict:
    """Poll the license GSI until the uploaded license appears (no staff Cognito auth required)."""
    table = get_provider_user_dynamodb_table()
    gsi_pk = f'C#{COMPACT}#J#{JURISDICTION}'
    gsi_sk = f'FN#{quote(family_name.lower())}#GN#{quote(given_name.lower())}'
    max_attempts = max_wait_seconds // poll_interval_seconds

    for attempt in range(1, max_attempts + 1):
        response = table.query(
            IndexName='licenseGSI',
            KeyConditionExpression=Key('licenseGSIPK').eq(gsi_pk) & Key('licenseGSISK').eq(gsi_sk),
            ConsistentRead=False,
        )
        items = [item for item in response.get('Items', []) if item.get('type') == 'license']
        if items:
            logger.info(f'Found license record in DynamoDB after attempt {attempt}/{max_attempts}')
            return items[0]

        if attempt < max_attempts:
            logger.info(
                f'License not found yet for {given_name} {family_name}. '
                f'Attempt {attempt}/{max_attempts}. Retrying in {poll_interval_seconds}s.'
            )
            time.sleep(poll_interval_seconds)

    raise SmokeTestFailureException(
        f'Timed out waiting for license record in DynamoDB for {given_name} {family_name} '
        f'(licenseGSI pk={gsi_pk}, sk={gsi_sk})'
    )


def test_optional_license_fields_round_trip(*, client_id: str, client_secret: str) -> str:
    """
    Upload a license with country/altFamilyName/militaryStatus and assert they persist in DynamoDB.

    Returns the created provider_id for cleanup.
    """
    run_id = datetime.now(UTC).strftime('%H%M%S')
    given_name = 'OptionalFields'
    family_name = f'Smoke{run_id}'
    # 999-HH-MMSS keeps this distinct from other smoke SSNs and unique per second.
    ssn = f'999-{run_id[:2]}-{run_id[2:]}'
    license_number = f'AZ-OPT-FIELDS-{run_id}'

    _post_license(
        client_id=client_id,
        client_secret=client_secret,
        post_body=_build_license_post_body(
            given_name=given_name,
            family_name=family_name,
            ssn=ssn,
            license_number=license_number,
        ),
    )

    license_record = _wait_for_license_record_in_dynamo(given_name=given_name, family_name=family_name)
    provider_id = license_record.get('providerId')
    if not provider_id:
        raise SmokeTestFailureException('Ingested license record is missing providerId')

    _assert_optional_upload_fields(license_record, owner='DynamoDB license record after state API upload')
    logger.info(f'Optional license fields smoke test passed for provider {provider_id}')
    return provider_id


if __name__ == '__main__':
    load_smoke_test_env()

    client_id = None
    provider_id = None
    try:
        credentials = _create_state_app_client_via_script(
            client_name=TEST_APP_CLIENT_NAME,
            compact=COMPACT,
            jurisdiction=JURISDICTION,
        )
        client_id = credentials['client_id']
        client_secret = credentials['client_secret']

        provider_id = test_optional_license_fields_round_trip(
            client_id=client_id,
            client_secret=client_secret,
        )
        logger.info('optional_license_fields_smoke_tests passed')
    except SmokeTestFailureException as e:
        logger.error(f'optional_license_fields_smoke_tests failed: {e}')
        sys.exit(1)
    finally:
        if provider_id:
            logger.info(f'Cleaning up provider records for {provider_id}')
            cleanup_test_provider_records(provider_id, COMPACT)
        if client_id:
            delete_test_app_client(client_id)
