#!/usr/bin/env python3
"""Create valid mock licenses and upload them to a sandbox State API.

Run from backend/dietitian-app (AWS credentials must be able to create a Cognito app client
in the state-auth user pool named in tests/smoke/smoke_tests_env.json):

    python3 bin/upload_mock_licenses.py --count 5 --compact diet --jurisdiction ne

Every record is active, compact-eligible, and checked against LicensePostRequestSchema before upload.
A 200 from the State API means the records were accepted for ingest; they can take a minute to appear.
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from argparse import ArgumentParser
from datetime import UTC, datetime, timedelta
from pathlib import Path

import boto3
import requests
from botocore.exceptions import ClientError
from faker import Faker

APP_ROOT = Path(__file__).resolve().parent.parent
SMOKE_ENV_PATH = APP_ROOT / 'tests' / 'smoke' / 'smoke_tests_env.json'
COMMON_LIB = APP_ROOT / 'lambdas' / 'python' / 'common'

faker = Faker(['en_US'])


def _load_cdk_context() -> dict:
    with open(APP_ROOT / 'cdk.json') as context_file:
        return json.load(context_file)['context']


def _prepare_schema_env(context: dict) -> None:
    os.environ['COMPACTS'] = json.dumps(context['compacts'])
    os.environ['JURISDICTIONS'] = json.dumps(context['jurisdictions'])
    os.environ['LICENSE_TYPES'] = json.dumps(context['license_types'])
    os.environ.setdefault('ENVIRONMENT_NAME', 'test')
    sys.path.append(str(COMMON_LIB))


def _load_smoke_env() -> dict:
    if not SMOKE_ENV_PATH.exists():
        raise SystemExit(f'Missing {SMOKE_ENV_PATH}. Copy smoke_tests_env_example.json and fill sandbox values.')
    with open(SMOKE_ENV_PATH) as env_file:
        return json.load(env_file)


def _build_licenses(*, count: int, compact: str, jurisdiction: str, license_type: str) -> list[dict]:
    """Build records that satisfy LicensePostRequestSchema once compact/jurisdiction are added."""
    today = datetime.now(tz=UTC).date()
    run_tag = int(time.time()) % 100
    licenses = []
    for index in range(count):
        date_of_birth = today - timedelta(days=365 * 35 + index)
        date_of_issuance = today - timedelta(days=365 * 3)
        date_of_renewal = today - timedelta(days=30)
        date_of_expiration = today + timedelta(days=365)
        serial = index + 1
        licenses.append(
            {
                'ssn': f'9{run_tag:02d}-{(serial // 10000) % 100:02d}-{serial % 10000:04d}',
                'npi': f'{8000000000 + serial:010d}'[-10:],
                'licenseNumber': f'{compact.upper()}-{jurisdiction.upper()}-{serial:04d}',
                'licenseType': license_type,
                'licenseStatus': 'active',
                'compactEligibility': 'eligible',
                'givenName': faker.first_name(),
                'familyName': faker.last_name(),
                'dateOfIssuance': date_of_issuance.isoformat(),
                'dateOfRenewal': date_of_renewal.isoformat(),
                'dateOfExpiration': date_of_expiration.isoformat(),
                'dateOfBirth': date_of_birth.isoformat(),
                'homeAddressStreet1': faker.street_address()[:100],
                'homeAddressCity': faker.city()[:100],
                'homeAddressState': jurisdiction.upper(),
                'homeAddressPostalCode': '68508',
                'emailAddress': f'mock-license-{serial:04d}-{run_tag}@example.com',
                'phoneNumber': f'+1402555{serial % 10000:04d}',
            }
        )
    return licenses


def _validate_licenses(licenses: list[dict], compact: str, jurisdiction: str) -> None:
    from cc_common.data_model.schema.license.api import LicensePostRequestSchema

    schema = LicensePostRequestSchema()
    errors = {}
    for index, license_record in enumerate(licenses):
        try:
            schema.load({**license_record, 'compact': compact, 'jurisdiction': jurisdiction})
        except Exception as error:  # marshmallow ValidationError
            errors[index] = getattr(error, 'messages', str(error))
    if errors:
        raise SystemExit(f'Generated licenses failed schema validation: {json.dumps(errors, default=str)}')


def _create_app_client(pool_id: str, compact: str, jurisdiction: str) -> dict:
    client_name = f'mock-license-upload-{uuid.uuid4().hex[:8]}'
    response = boto3.client('cognito-idp').create_user_pool_client(
        UserPoolId=pool_id,
        ClientName=client_name,
        PreventUserExistenceErrors='ENABLED',
        GenerateSecret=True,
        TokenValidityUnits={'AccessToken': 'minutes'},
        AccessTokenValidity=15,
        AllowedOAuthFlowsUserPoolClient=True,
        AllowedOAuthFlows=['client_credentials'],
        AllowedOAuthScopes=[f'{compact}/readGeneral', f'{jurisdiction}/{compact}.write'],
    )
    user_pool_client = response['UserPoolClient']
    return {'client_id': user_pool_client['ClientId'], 'client_secret': user_pool_client['ClientSecret']}


def _delete_app_client(pool_id: str, client_id: str) -> None:
    try:
        boto3.client('cognito-idp').delete_user_pool_client(UserPoolId=pool_id, ClientId=client_id)
    except ClientError as error:
        print(f'Warning: failed to delete temporary app client {client_id}: {error}', file=sys.stderr)


def _access_token(auth_url: str, client_id: str, client_secret: str, compact: str, jurisdiction: str) -> str:
    response = requests.post(
        auth_url,
        data={
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret,
            'scope': f'{compact}/readGeneral {jurisdiction}/{compact}.write',
        },
        headers={'Content-Type': 'application/x-www-form-urlencoded', 'Accept': 'application/json'},
        timeout=15,
    )
    if response.status_code != 200:
        raise SystemExit(f'Failed to get state-auth token ({response.status_code}): {response.text}')
    token = response.json().get('access_token')
    if not token:
        raise SystemExit(f'State-auth response had no access_token: {response.text}')
    return token


def _upload_batch(base_url: str, token: str, compact: str, jurisdiction: str, batch: list[dict]) -> None:
    response = requests.post(
        f'{base_url}/v1/compacts/{compact}/jurisdictions/{jurisdiction}/licenses',
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
        json=batch,
        timeout=60,
    )
    if response.status_code != 200:
        raise SystemExit(f'License upload failed ({response.status_code}): {response.text}')


def main() -> None:
    context = _load_cdk_context()
    parser = ArgumentParser(description='Generate valid mock licenses and upload them to the State API')
    parser.add_argument('--count', type=int, default=5, help='Number of licenses to create (default: 5)')
    parser.add_argument('--compact', default='diet', choices=context['compacts'])
    parser.add_argument('--jurisdiction', default='ne', choices=context['jurisdictions'])
    parser.add_argument(
        '--license-type',
        default=None,
        help='License type name. Defaults to the first type configured for the compact.',
    )
    parser.add_argument('--batch-size', type=int, default=25)
    args = parser.parse_args()

    if args.count < 1:
        parser.error('--count must be at least 1')
    if args.batch_size < 1:
        parser.error('--batch-size must be at least 1')

    license_types = [license_type['name'] for license_type in context['license_types'][args.compact]]
    license_type = args.license_type or license_types[0]
    if license_type not in license_types:
        parser.error(f'--license-type must be one of: {", ".join(license_types)}')

    _prepare_schema_env(context)
    smoke_env = _load_smoke_env()
    licenses = _build_licenses(
        count=args.count, compact=args.compact, jurisdiction=args.jurisdiction, license_type=license_type
    )
    _validate_licenses(licenses, args.compact, args.jurisdiction)

    pool_id = smoke_env['CC_TEST_COGNITO_STATE_AUTH_USER_POOL_ID']
    client = _create_app_client(pool_id, args.compact, args.jurisdiction)
    try:
        token = _access_token(
            smoke_env['CC_TEST_STATE_AUTH_URL'],
            client['client_id'],
            client['client_secret'],
            args.compact,
            args.jurisdiction,
        )
        base_url = smoke_env['CC_TEST_STATE_API_BASE_URL'].rstrip('/')
        for start in range(0, len(licenses), args.batch_size):
            batch = licenses[start : start + args.batch_size]
            _upload_batch(base_url, token, args.compact, args.jurisdiction, batch)
            print(f'Accepted {len(batch)} license(s) ({start + len(batch)}/{len(licenses)})')
    finally:
        _delete_app_client(pool_id, client['client_id'])

    output_path = Path.cwd() / f'{args.compact}-{args.jurisdiction}-uploaded-licenses.json'
    output_path.write_text(json.dumps(licenses, indent=2))
    print(f'Wrote {output_path}')
    print('Ingest is asynchronous. Records usually show up within a minute or two.')
    for license_record in licenses:
        print(
            f"  {license_record['givenName']} {license_record['familyName']} "
            f"ssn={license_record['ssn']} license={license_record['licenseNumber']}"
        )


if __name__ == '__main__':
    main()
