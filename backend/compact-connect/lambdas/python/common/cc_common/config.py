import json
import logging
import os
from datetime import UTC, datetime, timedelta, timezone
from functools import cached_property

import boto3
from aws_lambda_powertools import Metrics
from aws_lambda_powertools.logging import Logger
from botocore.config import Config as BotoConfig

logging.basicConfig()
logger = Logger()
logger.setLevel(logging.DEBUG if os.environ.get('DEBUG', 'false').lower() == 'true' else logging.INFO)

metrics = Metrics(namespace='compact-connect', service='common')


class _Config:
    presigned_post_ttl_seconds = 3600
    default_page_size = 100

    @cached_property
    def cognito_client(self):
        return boto3.client('cognito-idp')

    @cached_property
    def users_table(self):
        return boto3.resource('dynamodb').Table(self.users_table_name)

    @cached_property
    def s3_client(self):
        return boto3.client('s3', config=BotoConfig(signature_version='s3v4'))

    @cached_property
    def dynamodb_client(self):
        return boto3.client('dynamodb')

    @cached_property
    def data_client(self):
        from cc_common.data_model.data_client import DataClient

        return DataClient(self)

    @cached_property
    def compact_configuration_client(self):
        from cc_common.data_model.compact_configuration_client import CompactConfigurationClient

        return CompactConfigurationClient(self)

    @cached_property
    def user_client(self):
        from cc_common.data_model.user_client import UserClient

        return UserClient(self)

    @cached_property
    def compact_configuration_table(self):
        return boto3.resource('dynamodb').Table(self.compact_configuration_table_name)

    @cached_property
    def secrets_manager_client(self):
        return boto3.client('secretsmanager')

    @cached_property
    def events_client(self):
        return boto3.client('events', config=BotoConfig(retries={'mode': 'standard'}))

    @cached_property
    def event_bus_name(self):
        return os.environ['EVENT_BUS_NAME']

    @cached_property
    def provider_table(self):
        return boto3.resource('dynamodb').Table(self.provider_table_name)

    @cached_property
    def ssn_table(self):
        return boto3.resource('dynamodb').Table(self.ssn_table_name)

    @property
    def compact_configuration_table_name(self):
        return os.environ['COMPACT_CONFIGURATION_TABLE_NAME']

    @property
    def environment_name(self):
        return os.environ['ENVIRONMENT_NAME']

    @property
    def compacts(self):
        return json.loads(os.environ['COMPACTS'])

    @property
    def jurisdictions(self):
        return json.loads(os.environ['JURISDICTIONS'])

    @property
    def license_types(self):
        """
        Reshapes the new LICENSE_TYPES format into the previous format for backward compatibility.
        The new format is:
        {
            "aslp": [
                {"abbreviation": "aud", "name": "audiologist"},
                {"abbreviation": "slp", "name": "speech-language pathologist"}
            ]
        }
        The returned format is:
        {
            "aslp": ["audiologist", "speech-language pathologist"]
        }
        """
        raw_license_types = json.loads(os.environ['LICENSE_TYPES'])
        return {compact: [lt['name'] for lt in license_types] for compact, license_types in raw_license_types.items()}

    @property
    def license_type_abbreviations(self):
        """
        Creates a lookup dictionary for license type abbreviations based on compact and full name.
        Returns a structure like:
        {
            "aslp": {
                "audiologist": "aud",
                "speech-language pathologist": "slp"
            }
        }
        """
        raw_license_types = json.loads(os.environ['LICENSE_TYPES'])
        return {
            compact: {lt['name']: lt['abbreviation'] for lt in license_types}
            for compact, license_types in raw_license_types.items()
        }

    def license_types_for_compact(self, compact):
        return self.license_types[compact]

    @property
    def provider_table_name(self):
        return os.environ['PROVIDER_TABLE_NAME']

    @property
    def ssn_table_name(self):
        return os.environ['SSN_TABLE_NAME']

    @property
    def fam_giv_mid_index_name(self):
        return os.environ['PROV_FAM_GIV_MID_INDEX_NAME']

    @property
    def date_of_update_index_name(self):
        return os.environ['PROV_DATE_OF_UPDATE_INDEX_NAME']

    @property
    def license_gsi_name(self):
        return os.environ['LICENSE_GSI_NAME']

    @property
    def ssn_inverted_index_name(self):
        return os.environ['SSN_INVERTED_INDEX_NAME']

    @property
    def bulk_bucket_name(self):
        return os.environ['BULK_BUCKET_NAME']

    @property
    def provider_user_bucket_name(self):
        return os.environ['PROVIDER_USER_BUCKET_NAME']

    @property
    def user_pool_id(self):
        return os.environ['USER_POOL_ID']

    @property
    def provider_user_pool_id(self):
        return os.environ['PROVIDER_USER_POOL_ID']

    @property
    def users_table_name(self):
        return os.environ['USERS_TABLE_NAME']

    @property
    def fam_giv_index_name(self):
        return os.environ['FAM_GIV_INDEX_NAME']

    @property
    def expiration_date_resolution_timezone(self):
        """
        This is the timezone used to determine the expiration dates of licenses and privileges.
        This is currently set to UTC-4. We anticipate that this may change in the future,
        so we have a configuration value for it.
        """
        return timezone(offset=timedelta(hours=-4))

    @cached_property
    def data_events_table(self):
        return boto3.resource('dynamodb').Table(self.data_events_table_name)

    @property
    def data_events_table_name(self):
        return os.environ['DATA_EVENT_TABLE_NAME']

    @property
    def event_ttls(self):
        """
        Event type-specific TTLs
        """
        return {'license.validation-error': timedelta(days=90), 'license.ingest-failure': timedelta(days=90)}

    @property
    def default_event_ttl(self):
        """
        If we don't define a TTL specific for an event type, use this TTL
        """
        return timedelta(days=366)

    @property
    def current_standard_datetime(self):
        """
        Standardized way to get the current datetime with the microseconds stripped off.
        """
        return datetime.now(tz=UTC).replace(microsecond=0)

    @cached_property
    def transaction_client(self):
        from cc_common.data_model.transaction_client import TransactionClient

        return TransactionClient(self)

    @property
    def transaction_history_table_name(self):
        return os.environ['TRANSACTION_HISTORY_TABLE_NAME']

    @property
    def transaction_history_table(self):
        return boto3.resource('dynamodb').Table(self.transaction_history_table_name)

    @property
    def rate_limiting_table_name(self):
        return os.environ['RATE_LIMITING_TABLE_NAME']

    @property
    def rate_limiting_table(self):
        return boto3.resource('dynamodb').Table(self.rate_limiting_table_name)

    @cached_property
    def allowed_origins(self):
        return json.loads(os.environ['ALLOWED_ORIGINS'])

    @cached_property
    def lambda_client(self):
        return boto3.client('lambda')

    @property
    def email_notification_service_lambda_name(self):
        return os.environ['EMAIL_NOTIFICATION_SERVICE_LAMBDA_NAME']


config = _Config()
