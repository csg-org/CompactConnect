import json
import logging
import os
from decimal import Decimal
from glob import glob

import boto3
from boto3.dynamodb.types import TypeDeserializer
from faker import Faker
from moto import mock_aws

from tests import TstLambdas

logger = logging.getLogger(__name__)
logging.basicConfig()
logger.setLevel(logging.DEBUG if os.environ.get('DEBUG', 'false') == 'true' else logging.INFO)


@mock_aws
class TstFunction(TstLambdas):
    """Base class to set up Moto mocking and create mock AWS resources for functional testing"""

    def setUp(self):  # noqa: N801 invalid-name
        super().setUp()

        self.faker = Faker(['en_US', 'ja_JP', 'es_MX'])
        self.build_resources()

        self.addCleanup(self.delete_resources)

        import cc_common.config
        from common_test.test_data_generator import TestDataGenerator

        cc_common.config.config = cc_common.config._Config()  # noqa: SLF001 protected-access
        self.config = cc_common.config.config
        self.test_data_generator = TestDataGenerator

    def build_resources(self):
        self.create_compact_configuration_table()
        self.create_provider_table()
        self.create_ssn_table()
        self.create_users_table()
        self.create_transaction_history_table()
        self.create_license_preprocessing_queue()
        self.create_rate_limiting_table()
        self.create_event_state_table()

        # Adding a waiter allows for testing against an actual AWS account, if needed
        waiter = self._compact_configuration_table.meta.client.get_waiter('table_exists')
        waiter.wait(TableName=self._compact_configuration_table.name)
        waiter.wait(TableName=self._provider_table.name)
        waiter.wait(TableName=self._users_table.name)
        waiter.wait(TableName=self._transaction_history_table.name)
        waiter.wait(TableName=self._rate_limiting_table.name)
        waiter.wait(TableName=self._event_state_table.name)
        # Create a new Cognito user pool
        cognito_client = boto3.client('cognito-idp')
        user_pool_name = 'TestUserPool'
        user_pool_response = cognito_client.create_user_pool(
            PoolName=user_pool_name,
            AliasAttributes=['email'],
            UsernameAttributes=['email'],
            Policies={
                'PasswordPolicy': {
                    'MinimumLength': 12,
                    'RequireUppercase': False,
                    'RequireLowercase': True,
                    'RequireNumbers': True,
                    'RequireSymbols': False,
                },
            },
        )
        os.environ['USER_POOL_ID'] = user_pool_response['UserPool']['Id']
        self._user_pool_id = user_pool_response['UserPool']['Id']

    def create_compact_configuration_table(self):
        self._compact_configuration_table = boto3.resource('dynamodb').create_table(
            AttributeDefinitions=[
                {'AttributeName': 'pk', 'AttributeType': 'S'},
                {'AttributeName': 'sk', 'AttributeType': 'S'},
            ],
            TableName=os.environ['COMPACT_CONFIGURATION_TABLE_NAME'],
            KeySchema=[{'AttributeName': 'pk', 'KeyType': 'HASH'}, {'AttributeName': 'sk', 'KeyType': 'RANGE'}],
            BillingMode='PAY_PER_REQUEST',
        )

    def create_event_state_table(self):
        self._event_state_table = boto3.resource('dynamodb').create_table(
            AttributeDefinitions=[
                {'AttributeName': 'pk', 'AttributeType': 'S'},
                {'AttributeName': 'sk', 'AttributeType': 'S'},
                {'AttributeName': 'providerId', 'AttributeType': 'S'},
                {'AttributeName': 'eventTime', 'AttributeType': 'S'},
            ],
            TableName=os.environ['EVENT_STATE_TABLE_NAME'],
            KeySchema=[{'AttributeName': 'pk', 'KeyType': 'HASH'}, {'AttributeName': 'sk', 'KeyType': 'RANGE'}],
            BillingMode='PAY_PER_REQUEST',
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'providerId-eventTime-index',
                    'KeySchema': [
                        {'AttributeName': 'providerId', 'KeyType': 'HASH'},
                        {'AttributeName': 'eventTime', 'KeyType': 'RANGE'},
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                }
            ],
        )

    def create_users_table(self):
        self._users_table = boto3.resource('dynamodb').create_table(
            AttributeDefinitions=[
                {'AttributeName': 'pk', 'AttributeType': 'S'},
                {'AttributeName': 'sk', 'AttributeType': 'S'},
                {'AttributeName': 'famGiv', 'AttributeType': 'RANGE'},
            ],
            TableName=os.environ['USERS_TABLE_NAME'],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': os.environ['FAM_GIV_INDEX_NAME'],
                    'KeySchema': [
                        {'AttributeName': 'sk', 'KeyType': 'HASH'},
                        {'AttributeName': 'famGiv', 'KeyType': 'RANGE'},
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                },
            ],
            KeySchema=[
                {'AttributeName': 'pk', 'KeyType': 'HASH'},
                {'AttributeName': 'sk', 'KeyType': 'RANGE'},
            ],
            BillingMode='PAY_PER_REQUEST',
        )

    def create_ssn_table(self):
        self._ssn_table = boto3.resource('dynamodb').create_table(
            AttributeDefinitions=[
                {'AttributeName': 'pk', 'AttributeType': 'S'},
                {'AttributeName': 'sk', 'AttributeType': 'S'},
                {'AttributeName': 'providerIdGSIpk', 'AttributeType': 'S'},
            ],
            TableName=os.environ['SSN_TABLE_NAME'],
            KeySchema=[
                {'AttributeName': 'pk', 'KeyType': 'HASH'},
                {'AttributeName': 'sk', 'KeyType': 'RANGE'},
            ],
            BillingMode='PAY_PER_REQUEST',
            GlobalSecondaryIndexes=[
                {
                    'IndexName': os.environ['SSN_INDEX_NAME'],
                    'KeySchema': [
                        {'AttributeName': 'providerIdGSIpk', 'KeyType': 'HASH'},
                        {'AttributeName': 'sk', 'KeyType': 'RANGE'},
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                },
            ],
        )

    def create_provider_table(self):
        self._provider_table = boto3.resource('dynamodb').create_table(
            KeySchema=[{'AttributeName': 'pk', 'KeyType': 'HASH'}, {'AttributeName': 'sk', 'KeyType': 'RANGE'}],
            BillingMode='PAY_PER_REQUEST',
            AttributeDefinitions=[
                {'AttributeName': 'pk', 'AttributeType': 'S'},
                {'AttributeName': 'sk', 'AttributeType': 'S'},
                {'AttributeName': 'providerFamGivMid', 'AttributeType': 'S'},
                {'AttributeName': 'providerDateOfUpdate', 'AttributeType': 'S'},
            ],
            TableName=os.environ['PROVIDER_TABLE_NAME'],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': os.environ['PROV_FAM_GIV_MID_INDEX_NAME'],
                    'KeySchema': [
                        {'AttributeName': 'sk', 'KeyType': 'HASH'},
                        {'AttributeName': 'providerFamGivMid', 'KeyType': 'RANGE'},
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                },
                {
                    'IndexName': os.environ['PROV_DATE_OF_UPDATE_INDEX_NAME'],
                    'KeySchema': [
                        {'AttributeName': 'sk', 'KeyType': 'HASH'},
                        {'AttributeName': 'providerDateOfUpdate', 'KeyType': 'RANGE'},
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                },
            ],
        )

    def create_transaction_history_table(self):
        self._transaction_history_table = boto3.resource('dynamodb').create_table(
            KeySchema=[{'AttributeName': 'pk', 'KeyType': 'HASH'}, {'AttributeName': 'sk', 'KeyType': 'RANGE'}],
            AttributeDefinitions=[
                {'AttributeName': 'pk', 'AttributeType': 'S'},
                {'AttributeName': 'sk', 'AttributeType': 'S'},
            ],
            TableName=os.environ['TRANSACTION_HISTORY_TABLE_NAME'],
            BillingMode='PAY_PER_REQUEST',
        )

    def create_license_preprocessing_queue(self):
        self._license_preprocessing_queue = boto3.resource('sqs').create_queue(QueueName='workflow-queue')
        os.environ['LICENSE_PREPROCESSING_QUEUE_URL'] = self._license_preprocessing_queue.url

    def delete_resources(self):
        self._compact_configuration_table.delete()
        self._provider_table.delete()
        self._ssn_table.delete()
        self._users_table.delete()
        self._transaction_history_table.delete()
        self._license_preprocessing_queue.delete()
        self._rate_limiting_table.delete()
        self._event_state_table.delete()

        waiter = self._users_table.meta.client.get_waiter('table_not_exists')
        waiter.wait(TableName=self._compact_configuration_table.name)
        waiter.wait(TableName=self._provider_table.name)
        waiter.wait(TableName=self._users_table.name)
        waiter.wait(TableName=self._transaction_history_table.name)
        waiter.wait(TableName=self._ssn_table.name)
        waiter.wait(TableName=self._rate_limiting_table.name)
        waiter.wait(TableName=self._event_state_table.name)

        # Delete the Cognito user pool
        cognito_client = boto3.client('cognito-idp')
        cognito_client.delete_user_pool(UserPoolId=self._user_pool_id)

    def _load_compact_configuration_data(self):
        """Use the canned test resources to load compact and jurisdiction information into the DB"""
        test_resources = [
            'tests/resources/dynamo/compact.json',
            'tests/resources/dynamo/jurisdiction.json',
        ]

        for resource in test_resources:
            with open(resource) as f:
                record = json.load(f, parse_float=Decimal)

            logger.debug('Loading resource, %s: %s', resource, str(record))
            # compact and jurisdiction records go in the compact configuration table
            self._compact_configuration_table.put_item(Item=record)

    def _load_provider_data(self) -> str:
        """Use the canned test resources to load a basic provider to the DB"""
        test_resources = glob('../common/tests/resources/dynamo/provider.json')

        def privilege_jurisdictions_to_set(obj: dict):
            if obj.get('type') == 'provider' and 'privilegeJurisdictions' in obj:
                obj['privilegeJurisdictions'] = set(obj['privilegeJurisdictions'])
            return obj

        for resource in test_resources:
            with open(resource) as f:
                record = json.load(f, object_hook=privilege_jurisdictions_to_set, parse_float=Decimal)

            logger.debug('Loading resource, %s: %s', resource, str(record))
            self._provider_table.put_item(Item=record)
        return record['providerId']

    def _load_license_data(self, status: str = 'active', expiration_date: str = None):
        """Use the canned test resources to load a basic provider to the DB"""
        license_test_resources = ['../common/tests/resources/dynamo/license.json']

        for resource in license_test_resources:
            with open(resource) as f:
                record = json.load(f, parse_float=Decimal)
                record['jurisdictionStatus'] = status
                if expiration_date:
                    record['dateOfExpiration'] = expiration_date

            logger.debug('Loading resource, %s: %s', resource, str(record))
            self._provider_table.put_item(Item=record)

    def _load_user_data(self) -> str:
        with open('tests/resources/dynamo/user.json') as f:
            # This item is saved in its serialized form, so we have to deserialize it first
            item = TypeDeserializer().deserialize({'M': json.load(f)})

        logger.info('Loading user: %s', item)
        self._users_table.put_item(Item=item)
        return item['userId']

    def _create_compact_staff_user(self, compacts: list[str]):
        """Create a compact-staff style user for each jurisdiction in the provided compact."""
        from cc_common.data_model.schema.common import StaffUserStatus
        from cc_common.data_model.schema.user.record import UserRecordSchema

        schema = UserRecordSchema()

        email = self.faker.unique.email()
        sub = self._create_cognito_user(email=email)
        for compact in compacts:
            logger.info('Writing compact %s permissions for %s', compact, email)
            self._users_table.put_item(
                Item=schema.dump(
                    {
                        'userId': sub,
                        'compact': compact,
                        'status': StaffUserStatus.INACTIVE.value,
                        'attributes': {
                            'email': email,
                            'familyName': self.faker.unique.last_name(),
                            'givenName': self.faker.unique.first_name(),
                        },
                        'permissions': {'actions': {'read'}, 'jurisdictions': {}},
                    },
                ),
            )
        return sub

    def _create_board_staff_users(self, compacts: list[str], jurisdiction_list: list[str] = None):
        """Create a board-staff style user for each jurisdiction in the provided compact.

        :param compacts: List of compact abbreviations
        :param jurisdiction_list: Optional list of jurisdictions to use, defaults to ['oh', 'ne', 'ky']
        """
        from cc_common.data_model.schema.common import StaffUserStatus
        from cc_common.data_model.schema.user.record import UserRecordSchema

        schema = UserRecordSchema()

        # Use default jurisdictions if none provided
        jurisdictions = jurisdiction_list or ['oh', 'ne', 'ky']

        for jurisdiction in jurisdictions:
            email = self.faker.unique.email()
            sub = self._create_cognito_user(email=email)
            for compact in compacts:
                logger.info('Writing board %s/%s permissions for %s', compact, jurisdiction, email)
                self._users_table.put_item(
                    Item=schema.dump(
                        {
                            'userId': sub,
                            'compact': compact,
                            'status': StaffUserStatus.INACTIVE.value,
                            'attributes': {
                                'email': email,
                                'familyName': self.faker.unique.last_name(),
                                'givenName': self.faker.unique.first_name(),
                            },
                            'permissions': self._create_write_permissions(jurisdiction),
                        },
                    ),
                )

    def _create_cognito_user(self, *, email: str):
        from cc_common.utils import get_sub_from_user_attributes

        user_data = self.config.cognito_client.admin_create_user(
            UserPoolId=self.config.user_pool_id,
            Username=email,
            UserAttributes=[{'Name': 'email', 'Value': email}, {'Name': 'email_verified', 'Value': 'True'}],
            DesiredDeliveryMediums=['EMAIL'],
        )
        return get_sub_from_user_attributes(user_data['User']['Attributes'])

    @staticmethod
    def _create_write_permissions(jurisdiction: str):
        return {'actions': {'read'}, 'jurisdictions': {jurisdiction: {'write'}}}

    def create_rate_limiting_table(self):
        """Create the rate limiting table for testing."""
        self._rate_limiting_table = boto3.resource('dynamodb').create_table(
            AttributeDefinitions=[
                {'AttributeName': 'pk', 'AttributeType': 'S'},
                {'AttributeName': 'sk', 'AttributeType': 'S'},
            ],
            TableName=os.environ['RATE_LIMITING_TABLE_NAME'],
            KeySchema=[{'AttributeName': 'pk', 'KeyType': 'HASH'}, {'AttributeName': 'sk', 'KeyType': 'RANGE'}],
            BillingMode='PAY_PER_REQUEST',
        )
