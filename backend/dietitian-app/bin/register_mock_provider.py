#!/usr/bin/env python3
# ruff: noqa: T201 we use print statements for scripts run locally
"""Register an already-uploaded sandbox provider without the frontend.

Looks up the provider by id, creates a Cognito user bound to that id, sets a permanent
password, and writes the registration fields on the provider record.

Run from backend/dietitian-app with sandbox AWS credentials:

    python3 bin/register_mock_provider.py --provider-id <uuid>

Reads the provider user pool and provider table from tests/smoke/smoke_tests_env.json.
"""

from __future__ import annotations

import json
from argparse import ArgumentParser
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

APP_ROOT = Path(__file__).resolve().parent.parent
SMOKE_ENV_PATH = APP_ROOT / 'tests' / 'smoke' / 'smoke_tests_env.json'
DEFAULT_PASSWORD = 'TestPass123!'  # noqa: S105 sandbox login password


def _load_smoke_env() -> dict:
    if not SMOKE_ENV_PATH.exists():
        raise SystemExit(f'Missing {SMOKE_ENV_PATH}. Fill sandbox values before registering a provider.')
    with open(SMOKE_ENV_PATH) as env_file:
        return json.load(env_file)


def _load_cdk_compacts() -> list[str]:
    with open(APP_ROOT / 'cdk.json') as context_file:
        return json.load(context_file)['context']['compacts']


def _provider_key(compact: str, provider_id: str) -> dict:
    return {'pk': f'{compact}#PROVIDER#{provider_id}', 'sk': f'{compact}#PROVIDER'}


def _attribute(user: dict, name: str) -> str | None:
    attributes = user.get('UserAttributes') or user.get('Attributes') or []
    return next((attribute['Value'] for attribute in attributes if attribute['Name'] == name), None)


def _create_or_reuse_cognito_user(
    cognito, *, pool_id: str, email: str, password: str, compact: str, provider_id: str
) -> None:
    try:
        cognito.admin_create_user(
            UserPoolId=pool_id,
            Username=email,
            UserAttributes=[
                {'Name': 'custom:compact', 'Value': compact},
                {'Name': 'custom:providerId', 'Value': provider_id},
                {'Name': 'email', 'Value': email},
                {'Name': 'email_verified', 'Value': 'true'},
            ],
            MessageAction='SUPPRESS',
        )
    except ClientError as error:
        if error.response['Error']['Code'] != 'UsernameExistsException':
            raise SystemExit(f'Failed to create Cognito user: {error.response["Error"]["Message"]}') from error
        existing = cognito.admin_get_user(UserPoolId=pool_id, Username=email)
        bound_provider_id = _attribute(existing, 'custom:providerId')
        if bound_provider_id != provider_id:
            raise SystemExit(
                f'{email} already exists and is bound to provider {bound_provider_id}, not {provider_id}. '
                'custom:providerId cannot be changed. Delete that Cognito user or pass a different --email.'
            ) from None
        print(f'Cognito user {email} already exists and is bound to this provider')

    try:
        cognito.admin_set_user_password(UserPoolId=pool_id, Username=email, Password=password, Permanent=True)
    except ClientError as error:
        raise SystemExit(f'Failed to set password: {error.response["Error"]["Message"]}') from error


def main() -> None:
    compacts = _load_cdk_compacts()
    parser = ArgumentParser(description='Register a sandbox provider by provider id')
    parser.add_argument('--provider-id', required=True, help='Provider UUID from the uploaded license')
    parser.add_argument('--compact', default='diet', choices=compacts)
    parser.add_argument('--email', default=None, help='Login email. Defaults to provider-<id>@example.com')
    parser.add_argument(
        '--password',
        default=DEFAULT_PASSWORD,
        help=f'Permanent password (default: {DEFAULT_PASSWORD})',
    )
    args = parser.parse_args()

    email = args.email or f'provider-{args.provider_id}@example.com'
    smoke_env = _load_smoke_env()
    table = boto3.resource('dynamodb').Table(smoke_env['CC_TEST_PROVIDER_DYNAMO_TABLE_NAME'])
    key = _provider_key(args.compact, args.provider_id)
    provider = table.get_item(Key=key, ConsistentRead=True).get('Item')
    if provider is None:
        raise SystemExit(
            f'No provider record for {args.compact} / {args.provider_id}. '
            'Wait for license ingest to finish, then retry.'
        )

    existing_email = provider.get('compactConnectRegisteredEmailAddress')
    if existing_email and existing_email != email:
        raise SystemExit(
            f'Provider is already registered as {existing_email}. Re-run with --email {existing_email} to reset '
            'that password, or delete the Cognito user first.'
        )

    home_jurisdiction = provider.get('licenseJurisdiction') or provider.get('currentHomeJurisdiction')
    if not home_jurisdiction or home_jurisdiction == 'unknown':
        raise SystemExit('Provider record has no licenseJurisdiction to use as the home jurisdiction.')

    cognito = boto3.client('cognito-idp')
    _create_or_reuse_cognito_user(
        cognito,
        pool_id=smoke_env['CC_TEST_COGNITO_PROVIDER_USER_POOL_ID'],
        email=email,
        password=args.password,
        compact=args.compact,
        provider_id=args.provider_id,
    )

    table.update_item(
        Key=key,
        UpdateExpression=(
            'SET compactConnectRegisteredEmailAddress = :email, currentHomeJurisdiction = :home'
        ),
        ExpressionAttributeValues={':email': email, ':home': home_jurisdiction},
    )

    print('Registered provider')
    print(f'  provider id: {args.provider_id}')
    print(f'  email:       {email}')
    print(f'  password:    {args.password}')
    print(f'  home:        {home_jurisdiction}')
    print('Put the email and password in CC_TEST_PROVIDER_USER_USERNAME / CC_TEST_PROVIDER_USER_PASSWORD.')


if __name__ == '__main__':
    main()
