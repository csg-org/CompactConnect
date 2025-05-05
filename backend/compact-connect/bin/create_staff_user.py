#!/usr/bin/env python3
"""Staff user generation helper script. Run from `backend/compact-connect`.

Note: This script requires the boto3 library and two environment variables:
USER_POOL_ID=us-east-1_7zzexample
USER_TABLE_NAME=Sandbox-PersistentStack-StaffUsersUsersTableB4F6C7C8-example

The CLI must also be configured with AWS credentials that have appropriate access to Cognito and DynamoDB
"""

import json
import os
import sys

import boto3
from botocore.exceptions import ClientError

provider_data_path = os.path.join('lambdas', 'python', 'staff-users')
common_lib_path = os.path.join('lambdas', 'python', 'common')

sys.path.append(provider_data_path)
sys.path.append(common_lib_path)

with open('cdk.json') as context_file:
    _context = json.load(context_file)['context']
JURISDICTIONS = _context['jurisdictions']
COMPACTS = _context['compacts']

os.environ['COMPACTS'] = json.dumps(COMPACTS)
os.environ['JURISDICTIONS'] = json.dumps(JURISDICTIONS)
# The environment name has no bearing on the staff user creation process, but we need a value to be set
# for the data model to work.
os.environ['ENVIRONMENT_NAME'] = 'test'

# We have to import this after we've mucked with our path and environment
from cc_common.data_model.schema.common import StaffUserStatus  # noqa: E402
from cc_common.data_model.schema.user.record import UserRecordSchema  # noqa: E402

USER_POOL_ID = os.environ['USER_POOL_ID']
USER_TABLE_NAME = os.environ['USER_TABLE_NAME']


cognito_client = boto3.client('cognito-idp')
user_table = boto3.resource('dynamodb').Table(USER_TABLE_NAME)
schema = UserRecordSchema()


def create_compact_ed_user(*, email: str, compact: str, user_attributes: dict, permanent_password: str | None = None):
    sys.stdout.write(f"Creating Compact ED user, '{email}', in {compact}\n")
    sub = create_cognito_user(email=email, permanent_password=permanent_password)
    user_table.put_item(
        Item=schema.dump(
            {
                'type': 'user',
                'userId': sub,
                'status': StaffUserStatus.ACTIVE.value,
                'compact': compact,
                'attributes': user_attributes,
                'permissions': {'actions': {'read', 'admin'}, 'jurisdictions': {}},
            },
        ),
    )


def create_board_ed_user(
    *, email: str, compact: str, jurisdiction: str, user_attributes: dict, permanent_password: str | None = None
):
    sys.stdout.write(f"Creating Board ED user, '{email}', in {compact}/{jurisdiction}\n")
    sub = create_cognito_user(email=email, permanent_password=permanent_password)
    user_table.put_item(
        Item=schema.dump(
            {
                'type': 'user',
                'userId': sub,
                'status': StaffUserStatus.ACTIVE.value,
                'compact': compact,
                'attributes': user_attributes,
                'permissions': {'actions': {'read'}, 'jurisdictions': {jurisdiction: {'write', 'admin'}}},
            },
        ),
    )


def create_cognito_user(*, email: str, permanent_password: str | None):
    """Create a Cognito user with the given email address and password.
    Note that the password should only be provided in testing environments."""

    def get_sub_from_attributes(user_attributes: list):
        for attribute in user_attributes:
            if attribute['Name'] == 'sub':
                return attribute['Value']
        raise ValueError('Failed to find user sub!')

    try:
        # By including the TemporaryPassword on user creation, we avoid creating a user if the desired permanent
        # password does not adhere to the password policy. Either no user is created, or a user is created with
        # the desired password.
        kwargs = {'TemporaryPassword': permanent_password} if permanent_password is not None else {}
        user_data = cognito_client.admin_create_user(
            UserPoolId=USER_POOL_ID,
            Username=email,
            UserAttributes=[{'Name': 'email', 'Value': email}],
            DesiredDeliveryMediums=['EMAIL'],
            **kwargs,
        )

        if permanent_password is not None:
            cognito_client.admin_set_user_password(
                UserPoolId=USER_POOL_ID, Username=email, Password=permanent_password, Permanent=True
            )
        return get_sub_from_attributes(user_data['User']['Attributes'])

    except ClientError as e:
        if e.response['Error']['Code'] == 'UsernameExistsException':
            sys.stdout.write('User already exists, returning existing user')
            user_data = cognito_client.admin_get_user(UserPoolId=USER_POOL_ID, Username=email)
            return get_sub_from_attributes(user_data['UserAttributes'])
        if e.response['Error']['Code'] == 'InvalidPasswordException':
            sys.stdout.write(f'Invalid password: {e.response["Error"]["Message"]}')
            sys.exit(2)
        else:
            sys.stdout.write(f'Failed to create user: {e.response["Error"]["Message"]}')
            sys.exit(2)


if __name__ == '__main__':
    from argparse import ArgumentParser

    # Pull compacts and jurisdictions from cdk.json
    with open('cdk.json') as f:
        context = json.load(f)['context']
        jurisdictions = context['jurisdictions']
        compacts = context['compacts']

    parser = ArgumentParser(
        description='Create a staff user',
        epilog='example: bin/create_staff_user.py -e justin@example.org -f williams -g justin -t board-ed -c octp -j oh',  # noqa: E501 line-too-long
    )
    parser.add_argument('-e', '--email', help="The new user's email address", required=True)
    parser.add_argument('-f', '--family-name', help="The new user's family name", required=True)
    parser.add_argument('-g', '--given-name', help="The new user's given name", required=True)
    parser.add_argument('-t', '--type', help="The new user's type", required=True, choices=['compact-ed', 'board-ed'])
    parser.add_argument('-c', '--compact', help="The new user's compact", required=True, choices=compacts)
    parser.add_argument(
        '-j',
        '--jurisdiction',
        help="The new user's jurisdiction, required for board users",
        required=False,
        choices=jurisdictions,
    )

    args = parser.parse_args()

    _user_attributes = {'email': args.email, 'familyName': args.family_name, 'givenName': args.given_name}

    match args.type:
        case 'compact-ed':
            create_compact_ed_user(email=args.email, compact=args.compact, user_attributes=_user_attributes)
        case 'board-ed':
            if not args.jurisdiction:
                sys.stdout.write('jurisdiction is required for board-ed users.')
                sys.exit(2)
            create_board_ed_user(
                email=args.email,
                compact=args.compact,
                jurisdiction=args.jurisdiction,
                user_attributes=_user_attributes,
            )
        case _:
            sys.stdout.write(f'Unsupported user type: {args.type}')
            sys.exit(2)
