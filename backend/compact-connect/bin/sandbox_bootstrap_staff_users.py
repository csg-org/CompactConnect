#!/usr/bin/env python3
"""Script to bootstrap staff users in a sandbox environment with predefined credentials to simplify testing.
Run this script from `backend/compact-connect`.

The AWS CLI must be configured with AWS credentials that have appropriate access to Cognito and DynamoDB.
"""

import os
import sys
from argparse import ArgumentParser

import sandbox_fetch_aws_resources

SANDBOX_USER_PASSWORD = 'Test12345678'  # noqa: S105 this script is used in sandbox environments only


def bootstrap_board_ed_user(compact: str, jurisdiction: str, email_username: str, email_domain: str):
    email = f'{email_username}+board-ed-{compact}-{jurisdiction}@{email_domain}'
    _user_attributes = {
        'email': email,
        'familyName': f'{compact.upper()}-{jurisdiction.upper()}',
        'givenName': 'TEST BOARD ED',
    }
    create_staff_user.create_board_ed_user(
        email=email,
        compact=compact,
        jurisdiction=jurisdiction,
        user_attributes=_user_attributes,
        permanent_password=SANDBOX_USER_PASSWORD,
    )


def bootstrap_compact_ed_user(compact: str, email_username: str, email_domain: str):
    email = f'{email_username}+compact-ed-{compact}@{email_domain}'
    _user_attributes = {'email': email, 'familyName': compact.upper(), 'givenName': 'TEST COMPACT ED'}
    create_staff_user.create_compact_ed_user(
        email=email,
        compact=compact,
        user_attributes=_user_attributes,
        permanent_password=SANDBOX_USER_PASSWORD,
    )


if __name__ == '__main__':
    parser = ArgumentParser(
        description='Bootstraps a sandbox environment with a static set of staff users using a base email address.',
        epilog='example: bin/sandbox_bootstrap_staff_users.py -e justin@example.org',
    )
    parser.add_argument('-e', '--email', help='The base email address', required=True)
    args = parser.parse_args()

    # Validate email format and split safely
    if '@' not in args.email or args.email.count('@') > 1:
        sys.stderr.write(f'Invalid email format: {args.email}\n')
        sys.exit(1)

    email_parts = args.email.split('@')
    email_username = email_parts[0]
    email_domain = email_parts[1]

    # Set environment variables required by create_staff_user
    _, _, staff_details = sandbox_fetch_aws_resources.fetch_resources()
    os.environ['ENVIRONMENT_NAME'] = 'sandbox'
    os.environ['USER_TABLE_NAME'] = staff_details['dynamodb_table']  # we want this to fail if the key doesn't exist
    os.environ['USER_POOL_ID'] = staff_details['user_pool_id']  # we want this to fail if the key doesn't exist

    # Import create_staff_user after setting environment variables that it expects
    import create_staff_user

    bootstrap_board_ed_user(compact='aslp', jurisdiction='oh', email_username=email_username, email_domain=email_domain)
    bootstrap_compact_ed_user(compact='aslp', email_username=email_username, email_domain=email_domain)
