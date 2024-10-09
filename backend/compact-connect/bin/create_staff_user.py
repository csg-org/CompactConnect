#!/usr/bin/env python3
"""
Staff user generation helper script. Run from `backend/compact-connect`.

Note: This script requires the boto3 library and two environment variables:
USER_POOL_ID=us-east-1_7zzexample
USER_TABLE_NAME=Sandbox-PersistentStack-StaffUsersUsersTableB4F6C7C8-example

The CLI must also be configured with AWS credentials that have appropriate access to Cognito and DynamoDB
"""
import os
import json
import sys

import boto3
from botocore.exceptions import ClientError

provider_data_path = os.path.join('lambdas', 'staff-users')
sys.path.append(provider_data_path)

with open('cdk.json', 'r') as context_file:
    _context = json.load(context_file)['context']
JURISDICTIONS = _context['jurisdictions']
COMPACTS = _context['compacts']

os.environ['COMPACTS'] = json.dumps(COMPACTS)
os.environ['JURISDICTIONS'] = json.dumps(JURISDICTIONS)

# We have to import this after we've mucked with our path and environment
from data_model.schema.user import UserRecordSchema  # pylint: disable=wrong-import-position


USER_POOL_ID = os.environ['USER_POOL_ID']
USER_TABLE_NAME = os.environ['USER_TABLE_NAME']


cognito_client = boto3.client('cognito-idp')
user_table = boto3.resource('dynamodb').Table(USER_TABLE_NAME)
schema = UserRecordSchema()


def create_compact_ed_user(*, email: str, compact: str, user_attributes: dict):
    print(f"Creating Compact ED user, '{email}', in {compact}")
    sub = create_cognito_user(email=email)
    user_table.put_item(
        Item=schema.dump({
            'type': 'user',
            'userId': sub,
            'compact': compact,
            'attributes': user_attributes,
            'permissions': {
                'actions': {'read', 'admin'},
                'jurisdictions': {}
            }
        })
    )


def create_board_ed_user(*, email: str, compact: str, jurisdiction: str, user_attributes: dict):
    print(f"Creating Board ED user, '{email}', in {compact}/{jurisdiction}")
    sub = create_cognito_user(email=email)
    user_table.put_item(
        Item=schema.dump({
            'type': 'user',
            'userId': sub,
            'compact': compact,
            'attributes': user_attributes,
            'permissions': {
                'actions': {'read'},
                'jurisdictions': {
                    jurisdiction: {'write', 'admin'}
                }
            }
        })
    )


def create_cognito_user(*, email: str):
    def get_sub_from_attributes(user_attributes: list):
        for attribute in user_attributes:
            if attribute['Name'] == 'sub':
                return attribute['Value']
        raise ValueError('Failed to find user sub!')

    try:
        user_data = cognito_client.admin_create_user(
            UserPoolId=USER_POOL_ID,
            Username=email,
            UserAttributes=[
                {
                    'Name': 'email',
                    'Value': email
                }
            ],
            DesiredDeliveryMediums=[
                'EMAIL'
            ]
        )
        return get_sub_from_attributes(user_data['User']['Attributes'])

    except ClientError as e:
        if e.response['Error']['Code'] == 'UsernameExistsException':
            user_data = cognito_client.admin_get_user(
                UserPoolId=USER_POOL_ID,
                Username=email
            )
            return get_sub_from_attributes(user_data['UserAttributes'])


if __name__ == '__main__':
    from argparse import ArgumentParser

    # Pull compacts and jurisdictions from cdk.json
    with open('cdk.json', 'r') as f:
        context = json.load(f)['context']
        jurisdictions = context['jurisdictions']
        compacts = context['compacts']

    parser = ArgumentParser(
        description='Create a staff user',
        epilog='example: bin/create_staff_user.py -e justin@example.org -f williams -g justin -t board-ed -c octp -j oh'
    )
    parser.add_argument('-e', '--email', help="The new user's email address", required=True)
    parser.add_argument(
        '-f', '--family-name',
        help="The new user's family name",
        required=True
    )
    parser.add_argument(
        '-g', '--given-name',
        help="The new user's given name",
        required=True
    )
    parser.add_argument(
        '-t', '--type',
        help="The new user's type",
        required=True,
        choices=['compact-ed', 'board-ed']
    )
    parser.add_argument(
        '-c', '--compact',
        help="The new user's compact",
        required=True,
        choices=compacts
    )
    parser.add_argument(
        '-j', '--jurisdiction',
        help="The new user's jurisdiction, required for board users",
        required=False,
        choices=jurisdictions
    )

    args = parser.parse_args()

    _user_attributes = {
        'email': args.email,
        'familyName': args.family_name,
        'givenName': args.given_name
    }

    match args.type:
        case 'compact-ed':
            create_compact_ed_user(
                email=args.email,
                compact=args.compact,
                user_attributes=_user_attributes
            )
        case 'board-ed':
            if not args.jurisdiction:
                print('jurisdiction is required for board-ed users.')
                sys.exit(2)
            create_board_ed_user(
                email=args.email,
                compact=args.compact,
                jurisdiction=args.jurisdiction,
                user_attributes=_user_attributes
            )
        case _:
            print(f'Unsupported user type: {args.type}')
            sys.exit(2)
