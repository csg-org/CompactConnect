#!/usr/bin/env python3
"""
Staff user generation helper script. Run from `backend/compact-connect`.

Note: This script requires the boto3 library and two environment variables:
USER_POOL_ID=us-east-1_7zzexample
USER_TABLE_NAME=Sandbox-PersistentStack-StaffUsersUsersTableB4F6C7C8-example

The CLI must also be configured with AWS credentials that have appropriate access to Cognito and DynamoDB
"""
import os

import boto3
from botocore.exceptions import ClientError

USER_POOL_ID = os.environ['USER_POOL_ID']
USER_TABLE_NAME = os.environ['USER_TABLE_NAME']


cognito_client = boto3.client('cognito-idp')
user_table = boto3.resource('dynamodb').Table(USER_TABLE_NAME)


def create_compact_ed_user(*, username: str, email: str, compact: str):
    print(f"Creating Compact ED user, '{username}', in {compact}")
    sub = create_cognito_user(username=username, email=email)
    user_table.put_item(
        Item={
            'pk': sub,
            'createdCompactJurisdiction': f'{compact}/{compact}',
            'permissions': {
                compact: {
                    'actions': {'read', 'admin'},
                    'jurisdictions': {}
                }
            }
        }
    )


def create_board_ed_user(*, username: str, email: str, compact: str, jurisdiction: str):
    print(f"Creating Board ED user, '{username}', in {compact}/{jurisdiction}")
    sub = create_cognito_user(username=username, email=email)
    user_table.put_item(
        Item={
            'pk': sub,
            'createdCompactJurisdiction': f'{compact}/{jurisdiction}',
            'permissions': {
                compact: {
                    'actions': {'read'},
                    'jurisdictions': {
                        jurisdiction: {'actions': {'write', 'admin'}}
                    }
                }
            }
        }
    )


def create_cognito_user(*, username: str, email: str):
    def get_sub_from_attributes(attributes: list):
        for attribute in attributes:
            if attribute['Name'] == 'sub':
                return attribute['Value']
        raise ValueError('Failed to find user sub!')

    try:
        user_data = cognito_client.admin_create_user(
            UserPoolId=USER_POOL_ID,
            Username=username,
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
                Username=username
            )
            return get_sub_from_attributes(user_data['UserAttributes'])


if __name__ == '__main__':
    import json
    import sys
    from argparse import ArgumentParser

    # Pull compacts and jurisdictions from cdk.json
    with open('cdk.json', 'r') as f:
        context = json.load(f)['context']
        jurisdictions = context['jurisdictions']
        compacts = context['compacts']

    parser = ArgumentParser(
        description='Create a staff user'
    )
    parser.add_argument('username')
    parser.add_argument('-e', '--email', help="The new user's email address", required=True)
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

    match args.type:
        case 'compact-ed':
            create_compact_ed_user(
                username=args.username,
                email=args.email,
                compact=args.compact
            )
        case 'board-ed':
            if not args.jurisdiction:
                print('jurisdiction is required for board-ed users.')
                sys.exit(2)
            create_board_ed_user(
                username=args.username,
                email=args.email,
                compact=args.compact,
                jurisdiction=args.jurisdiction
            )
        case _:
            print(f'Unsupported user type: {args.type}')
            sys.exit(2)
