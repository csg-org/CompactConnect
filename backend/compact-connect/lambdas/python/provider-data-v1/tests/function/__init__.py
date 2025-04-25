import json
import logging
import os
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from glob import glob
from random import randint
from unittest.mock import patch

import boto3
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

        self.build_resources()

        # these must be imported within the tests, since they import modules which require
        # environment variables that are not set until the TstLambdas class is initialized
        import cc_common.config
        from common_test.test_data_generator import TestDataGenerator

        cc_common.config.config = cc_common.config._Config()  # noqa: SLF001 protected-access
        self.config = cc_common.config.config
        self.test_data_generator = TestDataGenerator

        self.addCleanup(self.delete_resources)

    def build_resources(self):
        self._bucket = boto3.resource('s3').create_bucket(Bucket=os.environ['BULK_BUCKET_NAME'])
        self.create_provider_table()
        self.create_staff_users_table()
        self.create_ssn_table()
        self.create_rate_limiting_table()
        self.create_compact_configuration_table()
        self.create_license_preprocessing_queue()
        self.create_staff_user_pool()

        boto3.client('events').create_event_bus(Name=os.environ['EVENT_BUS_NAME'])

        # Create a new Cognito user pool for providers
        cognito_client = boto3.client('cognito-idp')
        user_pool_name = 'TestProviderUserPool'
        user_pool_response = cognito_client.create_user_pool(
            PoolName=user_pool_name,
            AliasAttributes=['email'],
            UsernameAttributes=['email'],
        )
        os.environ['PROVIDER_USER_POOL_ID'] = user_pool_response['UserPool']['Id']
        self._provider_user_pool_id = user_pool_response['UserPool']['Id']

    def create_staff_user_pool(self):
        # Create a new Cognito user pool
        cognito_client = boto3.client('cognito-idp')
        user_pool_name = 'TestUserPool'
        user_pool_response = cognito_client.create_user_pool(
            PoolName=user_pool_name,
            AliasAttributes=['email'],
            UsernameAttributes=['email'],
        )
        os.environ['USER_POOL_ID'] = user_pool_response['UserPool']['Id']
        self._user_pool_id = user_pool_response['UserPool']['Id']

    def create_staff_users_table(self):
        self._staff_users_table = boto3.resource('dynamodb').create_table(
            AttributeDefinitions=[
                {'AttributeName': 'pk', 'AttributeType': 'S'},
                {'AttributeName': 'sk', 'AttributeType': 'S'},
                {'AttributeName': 'famGiv', 'AttributeType': 'S'},
            ],
            TableName=self.config.users_table_name,
            KeySchema=[{'AttributeName': 'pk', 'KeyType': 'HASH'}, {'AttributeName': 'sk', 'KeyType': 'RANGE'}],
            BillingMode='PAY_PER_REQUEST',
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
        )

    def create_provider_table(self):
        self._provider_table = boto3.resource('dynamodb').create_table(
            AttributeDefinitions=[
                {'AttributeName': 'pk', 'AttributeType': 'S'},
                {'AttributeName': 'sk', 'AttributeType': 'S'},
                {'AttributeName': 'providerFamGivMid', 'AttributeType': 'S'},
                {'AttributeName': 'providerDateOfUpdate', 'AttributeType': 'S'},
                {'AttributeName': 'licenseGSIPK', 'AttributeType': 'S'},
                {'AttributeName': 'licenseGSISK', 'AttributeType': 'S'},
            ],
            TableName=os.environ['PROVIDER_TABLE_NAME'],
            KeySchema=[{'AttributeName': 'pk', 'KeyType': 'HASH'}, {'AttributeName': 'sk', 'KeyType': 'RANGE'}],
            BillingMode='PAY_PER_REQUEST',
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
                {
                    'IndexName': os.environ['LICENSE_GSI_NAME'],
                    'KeySchema': [
                        {'AttributeName': 'licenseGSIPK', 'KeyType': 'HASH'},
                        {'AttributeName': 'licenseGSISK', 'KeyType': 'RANGE'},
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                },
            ],
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

    def create_rate_limiting_table(self):
        self._rate_limiting_table = boto3.resource('dynamodb').create_table(
            AttributeDefinitions=[
                {'AttributeName': 'pk', 'AttributeType': 'S'},
                {'AttributeName': 'sk', 'AttributeType': 'S'},
            ],
            TableName=os.environ['RATE_LIMITING_TABLE_NAME'],
            KeySchema=[{'AttributeName': 'pk', 'KeyType': 'HASH'}, {'AttributeName': 'sk', 'KeyType': 'RANGE'}],
            BillingMode='PAY_PER_REQUEST',
        )

    def create_compact_configuration_table(self):
        """Create the compact configuration table for testing."""
        self._compact_configuration_table = boto3.resource('dynamodb').create_table(
            AttributeDefinitions=[
                {'AttributeName': 'pk', 'AttributeType': 'S'},
                {'AttributeName': 'sk', 'AttributeType': 'S'},
            ],
            TableName=os.environ['COMPACT_CONFIGURATION_TABLE_NAME'],
            KeySchema=[
                {'AttributeName': 'pk', 'KeyType': 'HASH'},
                {'AttributeName': 'sk', 'KeyType': 'RANGE'},
            ],
            BillingMode='PAY_PER_REQUEST',
        )

    def create_license_preprocessing_queue(self):
        self._license_preprocessing_queue = boto3.resource('sqs').create_queue(QueueName='workflow-queue')
        os.environ['LICENSE_PREPROCESSING_QUEUE_URL'] = self._license_preprocessing_queue.url

    def delete_resources(self):
        self._bucket.objects.delete()
        self._bucket.delete()
        self._provider_table.delete()
        self._staff_users_table.delete()
        self._ssn_table.delete()
        self._compact_configuration_table.delete()
        self._rate_limiting_table.delete()
        self._license_preprocessing_queue.delete()
        boto3.client('events').delete_event_bus(Name=os.environ['EVENT_BUS_NAME'])

        # Delete the Cognito user pool
        cognito_client = boto3.client('cognito-idp')
        cognito_client.delete_user_pool(UserPoolId=self._provider_user_pool_id)

    def _load_compact_configuration(self, overrides: dict):
        with open('../common/tests/resources/dynamo/compact.json') as f:
            compact_data = json.load(f, parse_float=Decimal)
            compact_data.update(overrides)
            self._compact_configuration_table.put_item(Item=compact_data)

    def _load_jurisdiction_configuration(self, overrides: dict):
        with open('../common/tests/resources/dynamo/jurisdiction.json') as f:
            jurisdiction_data = json.load(f, parse_float=Decimal)
            jurisdiction_data.update(overrides)
            self._compact_configuration_table.put_item(Item=jurisdiction_data)

    def _load_provider_data(self):
        """Use the canned test resources to load a basic provider to the DB"""
        test_resources = glob('../common/tests/resources/dynamo/*.json')

        def privilege_jurisdictions_to_set(obj: dict):
            if obj.get('type') == 'provider' and 'privilegeJurisdictions' in obj:
                obj['privilegeJurisdictions'] = set(obj['privilegeJurisdictions'])
            return obj

        for resource in test_resources:
            with open(resource) as f:
                if resource.endswith('user.json'):
                    # skip the staff user test data, as it is not stored in the provider table
                    continue
                record = json.load(f, object_hook=privilege_jurisdictions_to_set, parse_float=Decimal)

            logger.debug('Loading resource, %s: %s', resource, str(record))
            if record['type'] == 'provider-ssn':
                self._ssn_table.put_item(Item=record)
            else:
                self._provider_table.put_item(Item=record)

    def _generate_providers(
        self, *, home: str, privilege_jurisdiction: str | None, start_serial: int, names: tuple[tuple[str, str]] = ()
    ):
        """Generate 10 providers with one license and one privilege
        :param home: The jurisdiction for the license
        :param privilege_jurisdiction: The jurisdiction for the privilege
        :param start_serial: Starting number for last portion of the provider's SSN
        :param names: A list of tuples, each containing a family name and given name
        """
        from cc_common.data_model.data_client import DataClient
        from handlers.ingest import ingest_license_message, preprocess_license_ingest

        with open('../common/tests/resources/ingest/preprocessor-sqs-message.json') as f:
            preprocessing_sqs_message = json.load(f)

        with open('../common/tests/resources/ingest/event-bridge-message.json') as f:
            ingest_message = json.load(f)

        name_faker = Faker(['en_US', 'ja_JP', 'es_MX'])
        data_client = DataClient(self.config)

        # Generate 10 providers, each with a license and a privilege
        for name_idx, ssn_serial in enumerate(range(start_serial, start_serial - 10, -1)):
            # So we can mutate top-level fields without messing up subsequent iterations
            preprocessing_sqs_message_copy = json.loads(json.dumps(preprocessing_sqs_message))
            ingest_message_copy = json.loads(json.dumps(ingest_message))

            # Use a requested name, if provided
            try:
                family_name, given_name = names[name_idx]
            except IndexError:
                family_name = name_faker.unique.last_name()
                given_name = name_faker.unique.first_name()

            # Update both message copies with the same data
            ssn = f'{randint(100, 999)}-{randint(10, 99)}-{ssn_serial}'

            # Update preprocessing message with license data including SSN
            preprocessing_sqs_message_copy.update(
                {
                    'compact': 'aslp',
                    'jurisdiction': home,
                    'licenseNumber': f'TEST-{ssn_serial}',
                    'licenseType': 'speech-language pathologist',
                    'status': 'active',
                    'dateOfIssuance': '2020-01-01',
                    'dateOfExpiration': '2050-01-01',
                    'familyName': family_name,
                    'givenName': given_name,
                    'middleName': name_faker.unique.first_name(),
                    'ssn': ssn,
                    'dateOfBirth': '1980-01-01',
                    'homeAddressStreet1': '123 Test St',
                    'homeAddressCity': 'Test City',
                    'homeAddressState': 'TS',
                    'homeAddressPostalCode': '12345',
                }
            )

            # Update ingest message with the same data (minus SSN which will be handled by preprocessor)
            ingest_message_copy['detail'].update(
                {
                    'familyName': family_name,
                    'givenName': given_name,
                    'middleName': name_faker.unique.first_name(),
                    'compact': 'aslp',
                    'jurisdiction': home,
                    'licenseNumber': f'TEST-{ssn_serial}',
                    'licenseType': 'speech-language pathologist',
                    'status': 'active',
                    'dateOfIssuance': '2020-01-01',
                    'dateOfExpiration': '2050-01-01',
                    'dateOfBirth': '1980-01-01',
                    'homeAddressStreet1': '123 Test St',
                    'homeAddressCity': 'Test City',
                    'homeAddressState': 'TS',
                    'homeAddressPostalCode': '12345',
                    # Only include last 4 of SSN in the event bus message
                    'ssnLastFour': ssn[-4:],
                }
            )

            # This gives us some variation in dateOfUpdate values to sort by
            with patch(
                'cc_common.config._Config.current_standard_datetime',
                new_callable=lambda: datetime.now(tz=UTC).replace(microsecond=0) - timedelta(days=randint(1, 365)),
            ):
                # First call the preprocessor to handle the SSN data
                preprocess_license_ingest(
                    {'Records': [{'messageId': '123', 'body': json.dumps(preprocessing_sqs_message_copy)}]},
                    self.mock_context,
                )
                # we need to get the provider id from the ssn table so it can be used in the ingest message
                provider_id = self._ssn_table.get_item(Key={'pk': f'aslp#SSN#{ssn}', 'sk': f'aslp#SSN#{ssn}'})['Item'][
                    'providerId'
                ]

                # update the ingest message with the provider id
                ingest_message_copy['detail']['providerId'] = provider_id

                # Then call the ingest message handler to process the provider data
                ingest_license_message(
                    {'Records': [{'messageId': '123', 'body': json.dumps(ingest_message_copy)}]},
                    self.mock_context,
                )

            # Add a privilege
            provider_record = data_client.get_provider(
                compact='aslp',
                provider_id=provider_id,
                detail=False,
            )['items'][0]
            if privilege_jurisdiction:
                data_client.create_provider_privileges(
                    compact='aslp',
                    provider_id=provider_id,
                    provider_record=provider_record,
                    jurisdiction_postal_abbreviations=[privilege_jurisdiction],
                    license_expiration_date=date(2050, 6, 6),
                    compact_transaction_id='1234567890',
                    existing_privileges_for_license=[],
                    license_type='speech-language pathologist',
                    # This attestation id/version pair is defined in the 'privilege.json' file under the
                    # common/tests/resources/dynamo directory
                    attestations=[{'attestationId': 'jurisprudence-confirmation', 'version': '1'}],
                )

    def _create_cognito_user(self, *, email: str, attributes=None):
        """
        Create a Cognito user in the provider user pool.

        :param email: The email address for the user
        :param attributes: Optional additional user attributes
        :return: The Cognito sub (user ID)
        """
        from cc_common.utils import get_sub_from_user_attributes

        user_attributes = [{'Name': 'email', 'Value': email}, {'Name': 'email_verified', 'Value': 'true'}]

        if attributes:
            user_attributes.extend(attributes)

        user_data = self.config.cognito_client.admin_create_user(
            UserPoolId=self.config.provider_user_pool_id,
            Username=email,
            UserAttributes=user_attributes,
            DesiredDeliveryMediums=['EMAIL'],
        )
        return get_sub_from_user_attributes(user_data['User']['Attributes'])
