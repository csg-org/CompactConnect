import json
import logging
import os
from typing import List

import boto3
from boto3.dynamodb.types import TypeDeserializer
from botocore.exceptions import ClientError
from faker import Faker
from moto import mock_aws

from tests import TstLambdas


logger = logging.getLogger(__name__)
logging.basicConfig()
logger.setLevel(logging.DEBUG if os.environ.get('DEBUG', 'false') == 'true' else logging.INFO)


@mock_aws
class TstFunction(TstLambdas):
    """
    Base class to set up Moto mocking and create mock AWS resources for functional testing
    """

    def setUp(self):  # pylint: disable=invalid-name
        super().setUp()

        self.faker = Faker(['en_US', 'ja_JP', 'es_MX'])
        self.build_resources()

        self.addCleanup(self.delete_resources)

    def build_resources(self):
        self._table = boto3.resource('dynamodb').create_table(
            AttributeDefinitions=[
                {
                    'AttributeName': 'pk',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'sk',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'famGiv',
                    'AttributeType': 'S'
                }
            ],
            TableName=self.config.users_table_name,
            KeySchema=[
                {
                    'AttributeName': 'pk',
                    'KeyType': 'HASH'
                },
                {
                    'AttributeName': 'sk',
                    'KeyType': 'RANGE'
                }
            ],
            BillingMode='PAY_PER_REQUEST',
            GlobalSecondaryIndexes=[
                {
                    'IndexName': os.environ['FAM_GIV_INDEX_NAME'],
                    'KeySchema': [
                        {
                            'AttributeName': 'sk',
                            'KeyType': 'HASH'
                        },
                        {
                            'AttributeName': 'famGiv',
                            'KeyType': 'RANGE'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    }
                }
            ]
        )
        # Adding a waiter allows for testing against an actual AWS account, if needed
        waiter = self._table.meta.client.get_waiter('table_exists')
        waiter.wait(TableName=self._table.name)

        # Create a new Cognito user pool
        cognito_client = boto3.client('cognito-idp')
        user_pool_name = 'TestUserPool'
        user_pool_response = cognito_client.create_user_pool(
            PoolName=user_pool_name,
            AliasAttributes=[
                'email'
            ],
            UsernameAttributes=[
                'email'
            ]
        )
        os.environ['USER_POOL_ID'] = user_pool_response['UserPool']['Id']
        self._user_pool_id = user_pool_response['UserPool']['Id']

    def delete_resources(self):
        self._table.delete()
        waiter = self._table.meta.client.get_waiter('table_not_exists')
        waiter.wait(TableName=self._table.name)
        # Delete the Cognito user pool
        cognito_client = boto3.client('cognito-idp')
        cognito_client.delete_user_pool(
            UserPoolId=self._user_pool_id
        )

    def _load_user_data(self) -> str:
        with open('tests/resources/dynamo/user.json', 'r') as f:
            # This item is saved in its serialized form, so we have to deserialize it first
            item = TypeDeserializer().deserialize({'M': json.load(f)})

        logger.info('Loading user: %s', item)
        self._table.put_item(
            Item=item
        )
        return item['userId']

    def _create_compact_staff_user(self, compacts: List[str]):
        """
        Create a compact-staff style user for each jurisdiction in the provided compact.
        """
        from data_model.schema.user import UserRecordSchema
        schema = UserRecordSchema()

        email = self.faker.unique.email()
        sub = self._create_cognito_user(
            email=email
        )
        for compact in compacts:
            logger.info('Writing compact %s permissions for %s', compact, email)
            self._table.put_item(
                Item=schema.dump({
                    'userId': sub,
                    'compact': compact,
                    'attributes': {
                        'email': email,
                        'familyName': self.faker.unique.last_name(),
                        'givenName': self.faker.unique.first_name()
                    },
                    'permissions': {
                        'actions': {'read'},
                        'jurisdictions': {}
                    }
                })
            )
        return sub

    def _create_board_staff_users(self, compacts: List[str]):
        """
        Create a board-staff style user for each jurisdiction in the provided compact.
        """
        from data_model.schema.user import UserRecordSchema
        schema = UserRecordSchema()

        for jurisdiction in self.config.jurisdictions:
            email = self.faker.unique.email()
            sub = self._create_cognito_user(
                email=email
            )
            for compact in compacts:
                logger.info('Writing board %s/%s permissions for %s', compact, jurisdiction, email)
                self._table.put_item(
                Item=schema.dump({
                        'userId': sub,
                        'compact': compact,
                        'attributes': {
                            'email': email,
                            'familyName': self.faker.unique.last_name(),
                            'givenName': self.faker.unique.first_name()
                        },
                        'permissions':  self._create_write_permissions(
                            jurisdiction
                        )
                    })
                )

    def _create_cognito_user(self, *, email: str):
        from utils import get_sub_from_user_attributes

        user_data = self.config.cognito_client.admin_create_user(
            UserPoolId=self.config.user_pool_id,
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
        return get_sub_from_user_attributes(user_data['User']['Attributes'])

    @staticmethod
    def _create_write_permissions(jurisdiction: str):
        permissions = {
            'actions': {'read'},
            'jurisdictions': {
                jurisdiction: {'write'}
            }
        }
        return permissions
