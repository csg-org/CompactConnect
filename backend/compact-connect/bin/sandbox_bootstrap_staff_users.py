#!/usr/bin/env python3
"""Script to bootstrap staff users for a sandbox environment. Run from `backend/compact-connect`.

The CLI must also be configured with AWS credentials that have appropriate access to Cognito and DynamoDB
"""

import os
from argparse import ArgumentParser

import sandbox_fetch_aws_resources


def bootstrap_board_ed_user(compact: str, jurisdiction: str, email_username: str, email_domain: str):
    import create_staff_user

    email = f'{email_username}+board-ed-{compact}-{jurisdiction}@{email_domain}'
    _user_attributes = {
        'email': email,
        'familyName': f'{compact.upper()}-{jurisdiction.upper()}',
        'givenName': 'TEST BOARD ED',
    }
    create_staff_user.create_board_ed_user(
        email=email,
        compact=compact,
        jurisdiction='oh',
        user_attributes=_user_attributes,
        permanent_password='Test12345678',  # noqa: S106 this is a test password
    )


def bootstrap_compact_ed_user(compact: str, email_username: str, email_domain: str):
    import create_staff_user

    email = f'{email_username}+compact-ed-{compact}@{email_domain}'
    _user_attributes = {'email': email, 'familyName': compact.upper(), 'givenName': 'TEST COMPACT ED'}
    create_staff_user.create_compact_ed_user(
        email=email,
        compact=compact,
        user_attributes=_user_attributes,
        permanent_password='Test12345678',  # noqa: S106 this is a test password
    )


if __name__ == '__main__':
    parser = ArgumentParser(
        description='Bootstraps a sandbox environment with a static set of staff users using a base email address.',
        epilog='example: bin/sandbox_bootstrap_staff_users.py -e justin@example.org',
    )
    parser.add_argument('-e', '--email', help='The base email address', required=True)
    args = parser.parse_args()

    email_username = args.email.split('@')[0]
    email_domain = args.email.split('@')[1]

    # Set environment variables required by create_staff_user
    _, _, staff_details = sandbox_fetch_aws_resources.fetch_resources()
    os.environ['ENVIRONMENT_NAME'] = 'sandbox'
    os.environ['USER_TABLE_NAME'] = staff_details['dynamodb_table']  # we want this to fail if the key doesn't exist
    os.environ['USER_POOL_ID'] = staff_details['user_pool_id']  # we want this to fail if the key doesn't exist

    bootstrap_board_ed_user(compact='aslp', jurisdiction='oh', email_username=email_username, email_domain=email_domain)
    bootstrap_compact_ed_user(compact='aslp', email_username=email_username, email_domain=email_domain)
