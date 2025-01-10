#!/usr/bin/env python3
"""Provider user generation helper script. Run from `backend/compact-connect`.

Note: This script requires the boto3 library and the environment variable:
# The provider user pool id
USER_POOL_ID=us-east-1_7zzexample

The CLI must also be configured with AWS credentials that have appropriate access to Cognito
"""

import json
import os
import sys

import boto3
from botocore.exceptions import ClientError

with open('cdk.json') as context_file:
    _context = json.load(context_file)['context']

COMPACTS = _context['compacts']
USER_POOL_ID = os.environ['USER_POOL_ID']


cognito_client = boto3.client('cognito-idp')


def create_cognito_user(*, email: str, compact: str, provider_id: str):
    sys.stdout.write(f"Creating new provider user, '{email}', in {compact}")

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
                {'Name': 'email', 'Value': email},
                {'Name': 'custom:compact', 'Value': compact},
                {'Name': 'custom:providerId', 'Value': provider_id},
            ],
            DesiredDeliveryMediums=['EMAIL'],
        )
        return get_sub_from_attributes(user_data['User']['Attributes'])

    except ClientError as e:
        if e.response['Error']['Code'] == 'UsernameExistsException':
            user_data = cognito_client.admin_get_user(UserPoolId=USER_POOL_ID, Username=email)
            return get_sub_from_attributes(user_data['UserAttributes'])
        raise


if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser(
        description='Create a provider user',
        epilog='example: bin/create_provider_user.py -e justin@example.org -c octp -p ac5f9901-e4e6-4a2e-8982-27d2517a3ab8',  # noqa: E501 line-too-long
    )
    parser.add_argument('-e', '--email', help="The new user's email address", required=True)
    parser.add_argument('-c', '--compact', help="The new user's compact", required=True, choices=COMPACTS)
    parser.add_argument('-p', '--provider-id', help="The new user's associated provider id", required=True)

    args = parser.parse_args()

    create_cognito_user(email=args.email, compact=args.compact, provider_id=args.provider_id)
