import json
import os
from typing import Any

import boto3
from aws_cdk import Duration, RemovalPolicy, aws_ssm
from aws_cdk.aws_cognito import UserPoolEmail
from aws_cdk.aws_iam import Effect, PolicyStatement
from aws_cdk.aws_kms import Key
from aws_cdk.aws_lambda import Runtime
from aws_cdk.aws_lambda_python_alpha import PythonLayerVersion
from aws_cdk.aws_logs import QueryDefinition, QueryString
from aws_cdk.aws_route53 import ARecord, RecordTarget
from botocore.exceptions import ClientError
from cdk_nag import NagSuppressions
from common_constructs.access_logs_bucket import AccessLogsBucket
from common_constructs.alarm_topic import AlarmTopic
from common_constructs.frontend_app_config_utility import PersistentStackFrontendAppConfigUtility
from common_constructs.security_profile import SecurityProfile
from common_constructs.stack import AppStack
from constructs import Construct

from common_constructs.nodejs_function import NodejsFunction
from common_constructs.python_function import COMMON_PYTHON_LAMBDA_LAYER_SSM_PARAMETER_NAME
from common_constructs.ssm_parameter_utility import SSMParameterUtility
from stacks.backup_infrastructure_stack import BackupInfrastructureStack
from stacks.persistent_stack.bulk_uploads_bucket import BulkUploadsBucket
from stacks.persistent_stack.compact_configuration_table import CompactConfigurationTable
from stacks.persistent_stack.compact_configuration_upload import CompactConfigurationUpload
from stacks.persistent_stack.data_event_table import DataEventTable
from stacks.persistent_stack.event_bus import EventBus
from stacks.persistent_stack.provider_table import ProviderTable
from stacks.persistent_stack.provider_users_bucket import ProviderUsersBucket
from stacks.persistent_stack.rate_limiting_table import RateLimitingTable
from stacks.persistent_stack.ssn_table import SSNTable
from stacks.persistent_stack.staff_users import StaffUsers
from stacks.persistent_stack.transaction_history_table import TransactionHistoryTable
from stacks.persistent_stack.transaction_reports_bucket import TransactionReportsBucket
from stacks.persistent_stack.user_email_notifications import UserEmailNotifications


# cdk leverages instance attributes to make resource exports accessible to other stacks
class PersistentStack(AppStack):
    """
    The stack that holds long-lived resources such as license data and other things that should probably never
    be destroyed in production
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        app_name: str,
        environment_name: str,
        environment_context: dict,
        backup_config: dict,
        **kwargs,
    ) -> None:
        super().__init__(
            scope, construct_id, environment_context=environment_context, environment_name=environment_name, **kwargs
        )
        # If we delete this stack, retain the resource (orphan but prevent data loss) or destroy it (clean up)?
        removal_policy = RemovalPolicy.RETAIN if environment_name == 'prod' else RemovalPolicy.DESTROY

        # Add the common python lambda layer for use in all python lambdas
        # NOTE: this is to only be referenced directly in this stack!
        # All external references should use the ssm parameter to get the value of the layer arn.
        # attempting to reference this layer directly in another stack will cause this stack
        # to be stuck in an UPDATE_ROLLBACK_FAILED state which will require DELETION of stacks
        # that reference the layer directly. See https://github.com/aws/aws-cdk/issues/1972
        self.common_python_lambda_layer = PythonLayerVersion(
            self,
            'CompactConnectCommonPythonLayer',
            entry=os.path.join('lambdas', 'python', 'common'),
            compatible_runtimes=[Runtime.PYTHON_3_12],
            description='A layer for common code shared between python lambdas',
            # We retain the layer versions in our environments, to avoid a situation where a consuming stack is unable
            # to roll back because old versions are destroyed. This means that over time, these versions
            # will accumulate in prod, and given the AWS limit of 75 GB for all layer and lambda code storage
            # we will likely need to add a custom resource to track these versions, and clean up versions that are
            # older than a certain date. That is out of scope for our current effort, but we're leaving this comment
            # here to remind us that this will need to be addressed at a later date.
            removal_policy=removal_policy.RETAIN
            if not self.node.try_get_context('sandbox')
            else removal_policy.DESTROY,
        )

        # We Store the layer ARN in SSM Parameter Store
        # since lambda layers can't be shared across stacks
        # directly due to the fact that you can't update a CloudFormation
        # exported value that is being referenced by a resource in another stack
        self.lambda_layer_ssm_parameter = aws_ssm.StringParameter(
            self,
            'CommonPythonLayerArnParameter',
            parameter_name=COMMON_PYTHON_LAMBDA_LAYER_SSM_PARAMETER_NAME,
            string_value=self.common_python_lambda_layer.layer_version_arn,
        )

        self.shared_encryption_key = Key(
            self,
            'SharedEncryptionKey',
            enable_key_rotation=True,
            alias=f'{self.stack_name}-shared-encryption-key',
            removal_policy=removal_policy,
        )

        notifications = environment_context.get('notifications', {})
        self.alarm_topic = AlarmTopic(
            self,
            'AlarmTopic',
            master_key=self.shared_encryption_key,
            email_subscriptions=notifications.get('email', []),
            slack_subscriptions=notifications.get('slack', []),
        )

        # Check if backups are enabled for this environment
        backup_enabled = environment_context['backup_enabled']

        if backup_enabled:
            # Create backup infrastructure as a nested stack
            self.backup_infrastructure_stack = BackupInfrastructureStack(
                self,
                'BackupInfrastructureStack',
                environment_name=environment_name,
                backup_config=backup_config,
                alarm_topic=self.alarm_topic,
            )
        else:
            self.backup_infrastructure_stack = None

        self.access_logs_bucket = AccessLogsBucket(
            self,
            'AccessLogsBucket',
            removal_policy=removal_policy,
            auto_delete_objects=removal_policy == RemovalPolicy.DESTROY,
        )

        # This resource should not be referenced directly as a cross stack reference, any reference should
        # be made through the SSM parameter
        # IMPORTANT NOTE: changing the name of the event bus will result in a BREAKING CHANGE (ie downtime). If the name
        # must be changed for whatever reason, you must create another event bus and SSM parameter and perform a
        # blue/green cut over to safely migrate consumers to the new event bus before deleting the original one in order
        # to prevent downtime.
        self._data_event_bus = EventBus(self, 'DataEventBus', event_bus_name=f'{environment_name}-dataEventBus')
        # We Store the data event bus name in SSM Parameter Store
        # to avoid issues with cross stack references due to the fact that
        # you can't update a CloudFormation exported value that is being referenced by a resource in another stack.
        self.data_event_bus_arn_ssm_parameter = SSMParameterUtility.set_data_event_bus_arn_ssm_parameter(
            self, self._data_event_bus
        )

        self._add_data_resources(
            removal_policy=removal_policy, backup_infrastructure_stack=self.backup_infrastructure_stack
        )

        self.compact_configuration_upload = CompactConfigurationUpload(
            self,
            'CompactConfigurationUpload',
            table=self.compact_configuration_table,
            master_key=self.shared_encryption_key,
        )

        if self.hosted_zone:
            self.user_email_notifications = UserEmailNotifications(
                self,
                'UserEmailNotifications',
                environment_context=environment_context,
                hosted_zone=self.hosted_zone,
                master_key=self.shared_encryption_key,
            )
            notification_from_email = f'no-reply@{self.hosted_zone.zone_name}'
            user_pool_email_settings = UserPoolEmail.with_ses(
                from_email=notification_from_email,
                ses_verified_domain=self.hosted_zone.zone_name,
                configuration_set_name=self.user_email_notifications.config_set.configuration_set_name,
            )

            if not environment_name == 'prod':
                # Retrieve compact connect
                compact_connect_ip = environment_context.get('compact_connect_org_ip')

                # Needed for cognito subdomains
                self.record = ARecord(
                    self,
                    'BaseARecord',
                    zone=self.hosted_zone,
                    target=RecordTarget.from_ip_addresses(compact_connect_ip),
                )
        else:
            # if domain name is not provided, use the default cognito email settings
            notification_from_email = None
            user_pool_email_settings = UserPoolEmail.with_cognito()

        self._create_email_notification_service()

        security_profile = SecurityProfile[environment_context.get('security_profile', 'RECOMMENDED')]
        staff_prefix = f'{app_name}-staff'
        non_custom_domain_prefix = staff_prefix if environment_name == 'prod' else f'{staff_prefix}-{environment_name}'

        self.staff_users = StaffUsers(
            self,
            'StaffUsersGreen',
            environment_name=environment_name,
            environment_context=environment_context,
            encryption_key=self.shared_encryption_key,
            user_pool_email=user_pool_email_settings,
            notification_from_email=notification_from_email,
            ses_identity_arn=self.user_email_notifications.email_identity.email_identity_arn
            if self.hosted_zone
            else None,
            non_custom_domain_prefix=non_custom_domain_prefix
            if not self.hosted_zone
            else None,
            security_profile=security_profile,
            removal_policy=removal_policy,
            backup_infrastructure_stack=self.backup_infrastructure_stack,
        )

        QueryDefinition(
            self,
            'StaffUserCustomEmails',
            query_definition_name='StaffUserCustomEmails/Lambdas',
            query_string=QueryString(
                fields=['@timestamp', '@log', 'level', 'message', '@message'],
                filter_statements=['level in ["INFO", "WARNING", "ERROR"]'],
                sort='@timestamp desc',
            ),
            log_groups=[
                self.staff_users.custom_message_lambda.log_group,
            ],
        )

        if self.hosted_zone:
            # The SES email identity needs to be created before the user pools
            # so that the domain address will be verified before being referenced
            # by the user pool email settings
            self.staff_users.node.add_dependency(self.user_email_notifications.email_identity)
            self.staff_users.node.add_dependency(self.user_email_notifications.dmarc_record)
            # the verification custom resource needs to be completed before the user pools are created
            # so that the user pools will be created after the SES identity is verified
            self.staff_users.node.add_dependency(self.user_email_notifications.verification_custom_resource)

        # This parameter is used to store the frontend app config values for use in the frontend deployment stack
        self._create_frontend_app_config_parameter()

    def _add_data_resources(
        self, removal_policy: RemovalPolicy, backup_infrastructure_stack: BackupInfrastructureStack | None
    ):
        # Create the ssn related resources before other resources which are dependent on them
        self.ssn_table = SSNTable(
            self,
            'SSNTable',
            removal_policy=removal_policy,
            data_event_bus=self._data_event_bus,
            alarm_topic=self.alarm_topic,
            backup_infrastructure_stack=backup_infrastructure_stack,
            environment_context=self.environment_context,
        )

        self.bulk_uploads_bucket = BulkUploadsBucket(
            self,
            'BulkUploadsBucket',
            access_logs_bucket=self.access_logs_bucket,
            # Note that we're using the ssn key here, which has a much more restrictive policy.
            # The messages in this bucket include SSN, so we want it just as locked down as our
            # permanent storage of SSN data.
            bucket_encryption_key=self.ssn_table.key,
            removal_policy=removal_policy,
            auto_delete_objects=removal_policy == RemovalPolicy.DESTROY,
            event_bus=self._data_event_bus,
            license_preprocessing_queue=self.ssn_table.preprocessor_queue.queue,
            license_upload_role=self.ssn_table.license_upload_role,
        )

        self.transaction_reports_bucket = TransactionReportsBucket(
            self,
            'TransactionReportsBucket',
            access_logs_bucket=self.access_logs_bucket,
            encryption_key=self.shared_encryption_key,
            removal_policy=removal_policy,
        )

        self.rate_limiting_table = RateLimitingTable(
            self,
            'RateLimitingTable',
            encryption_key=self.shared_encryption_key,
            removal_policy=removal_policy,
        )

        self.provider_table = ProviderTable(
            self,
            'ProviderTable',
            encryption_key=self.shared_encryption_key,
            removal_policy=removal_policy,
            backup_infrastructure_stack=backup_infrastructure_stack,
            environment_context=self.environment_context,
        )

        # The api query role needs access to the provider table to associate a provider with
        # its jurisdictions, so it can make authorization decisions for the requester.
        self.provider_table.grant_read_data(self.ssn_table.api_query_role)
        NagSuppressions.add_resource_suppressions_by_path(
            self,
            f'{self.ssn_table.api_query_role.node.path}/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': """This policy contains wild-carded actions and resources but they are scoped to the
                              specific actions, Table, and KMS Key that this lambda specifically needs access to.
                              """,
                },
            ],
        )

        self.data_event_table = DataEventTable(
            scope=self,
            construct_id='DataEventTable',
            encryption_key=self.shared_encryption_key,
            event_bus=self._data_event_bus,
            alarm_topic=self.alarm_topic,
            removal_policy=removal_policy,
            backup_infrastructure_stack=backup_infrastructure_stack,
            environment_context=self.environment_context,
        )

        self.compact_configuration_table = CompactConfigurationTable(
            scope=self,
            construct_id='CompactConfigurationTable',
            encryption_key=self.shared_encryption_key,
            removal_policy=removal_policy,
            backup_infrastructure_stack=backup_infrastructure_stack,
            environment_context=self.environment_context,
        )

        self.transaction_history_table = TransactionHistoryTable(
            scope=self,
            construct_id='TransactionHistoryTable',
            encryption_key=self.shared_encryption_key,
            removal_policy=removal_policy,
            backup_infrastructure_stack=backup_infrastructure_stack,
            environment_context=self.environment_context,
        )

        # bucket for holding documentation for providers
        self.provider_users_bucket = ProviderUsersBucket(
            self,
            'ProviderUsersBucket',
            access_logs_bucket=self.access_logs_bucket,
            encryption_key=self.shared_encryption_key,
            provider_table=self.provider_table,
            removal_policy=removal_policy,
            backup_infrastructure_stack=backup_infrastructure_stack,
            environment_context=self.environment_context,
        )

    def _create_email_notification_service(self) -> None:
        """This lambda is intended to be a general purpose email notification service.

        It can be invoked directly to send an email if the lambda is deployed in an environment that has a domain name.
        If the lambda is deployed in an environment that does not have a domain name, it will perform a no-op as there
        is no FROM address to use.
        """
        # If there is no hosted zone, we don't have a domain name to send from
        # so we'll use a placeholder value which will cause the lambda to perform a no-op
        from_address = 'NONE'
        if self.hosted_zone:
            from_address = f'noreply@{self.user_email_notifications.email_identity.email_identity_name}'

        self.email_notification_service_lambda = NodejsFunction(
            self,
            'EmailNotificationService',
            description='Generic email notification service',
            lambda_dir='email-notification-service',
            handler='sendEmail',
            timeout=Duration.minutes(5),
            memory_size=1024,
            environment={
                'FROM_ADDRESS': from_address,
                'COMPACT_CONFIGURATION_TABLE_NAME': self.compact_configuration_table.table_name,
                'TRANSACTION_REPORTS_BUCKET_NAME': self.transaction_reports_bucket.bucket_name,
                'UI_BASE_PATH_URL': self.get_ui_base_path_url(),
                **self.common_env_vars,
            },
        )

        # Grant permissions to read compact configurations
        self.compact_configuration_table.grant_read_data(self.email_notification_service_lambda)
        # Grant permissions to get report files for emailing reports
        self.transaction_reports_bucket.grant_read(self.email_notification_service_lambda)
        # if there is no domain name, we can't set up SES permissions
        # in this case the lambda will perform a no-op when invoked.
        if self.hosted_zone:
            self.setup_ses_permissions_for_lambda(self.email_notification_service_lambda)

        NagSuppressions.add_resource_suppressions_by_path(
            self,
            f'{self.email_notification_service_lambda.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': """
                              This policy contains wild-carded actions and resources but they are scoped to the
                              specific actions, reporting Bucket, Table, and Email Identity that this lambda
                              specifically needs access to.
                              """,
                },
            ],
        )

    def setup_ses_permissions_for_lambda(self, lambda_function: NodejsFunction):
        """Used to allow a lambda to send emails using the user email notification SES identity."""
        ses_resources = [
            self.user_email_notifications.email_identity.email_identity_arn,
            self.format_arn(
                partition=self.partition,
                service='ses',
                region=self.region,
                account=self.account,
                resource='configuration-set',
                resource_name=self.user_email_notifications.config_set.configuration_set_name,
            ),
        ]

        # We'll assume that, if it is a sandbox environment, they're in the Simple Email Service (SES) sandbox
        if self.node.try_get_context('sandbox'):
            # SES Sandboxed accounts require that the sending principal also be explicitly granted permission to send
            # emails to the SES identity they configured for testing. Because we don't know that identity in advance,
            # we'll have to allow the principal to use any SES identity configured in the account.
            # arn:aws:ses:{region}:{account}:identity/*
            ses_resources.append(
                self.format_arn(
                    partition=self.partition,
                    service='ses',
                    region=self.region,
                    account=self.account,
                    resource='identity',
                    resource_name='*',
                ),
            )

        lambda_function.role.add_to_principal_policy(
            PolicyStatement(
                actions=['ses:SendEmail', 'ses:SendRawEmail'],
                resources=ses_resources,
                effect=Effect.ALLOW,
                conditions={
                    # To mitigate the pretty open resources section for sandbox environments, we'll restrict the use of
                    # this action by specifying what From address and display name the principal must use.
                    'StringEquals': {
                        'ses:FromAddress': f'noreply@{self.user_email_notifications.email_identity.email_identity_name}',  # noqa: E501 line too long
                        'ses:FromDisplayName': 'Compact Connect',
                    }
                },
            )
        )

    def get_ui_base_path_url(self) -> str:
        """Returns the base URL for the UI."""
        if self.ui_domain_name is not None:
            return f'https://{self.ui_domain_name}'

        # default to csg test environment
        return 'https://app.test.compactconnect.org'

    def get_list_of_compact_abbreviations(self) -> list[str]:
        """
        Get the list of all compact abbreviations for compacts configured in the cdk.json file
        """
        return self.node.get_context('compacts')

    def get_list_of_active_jurisdictions_for_compact_environment(self, compact: str) -> list[str]:
        """
        Get the list of jurisdiction postal abbreviations which are active within a compact.

        This reads the active_compact_member_jurisdictions from the context in cdk.json and returns
        the list of jurisdiction postal abbreviations for the specified compact.

        For sandbox environments, it will use sandbox_active_compact_member_jurisdictions. This is because
        We have more than 25 active jurisdictions, but Cognito has a default limit of 25 resource servers per user pool,
        and we need to create a resource server for each active jurisdiction.
        We set the number of active jurisdictions to less than 25 in the sandbox environment so developers don't have
        to request a quota increase in order to deploy the sandbox environment.
        """
        # Check if this is a sandbox environment
        is_sandbox = self.node.try_get_context('sandbox')

        if is_sandbox:
            # Try to get sandbox-specific configuration
            active_member_jurisdictions = self.node.get_context('sandbox_active_compact_member_jurisdictions')
        else:
            # Use regular configuration for non-sandbox environments
            active_member_jurisdictions = self.node.get_context('active_compact_member_jurisdictions')

        if not active_member_jurisdictions:
            raise ValueError(
                f'No active member jurisdictions found in context for compact {compact}. '
                'If this is a sandbox environment, make sure to set the '
                'sandbox_active_compact_member_jurisdictions context variable in your cdk.context.json file.'
            )

        # Get the jurisdictions for the specified compact and ensure all are lowercase
        jurisdictions = active_member_jurisdictions[compact]
        return [j.lower() for j in jurisdictions]

    def _create_frontend_app_config_parameter(self):
        """
        Creates and stores UI application configuration in SSM Parameter Store for use in the UI stack and
        frontend deployment stack.
        """
        # Create and store UI application configuration in SSM Parameter Store for use in the UI stack
        frontend_app_config = PersistentStackFrontendAppConfigUtility()

        # Add staff user pool Cognito configuration
        frontend_app_config.set_staff_cognito_values(
            domain_name=self.staff_users.app_client_custom_domain.domain_name,
            client_id=self.staff_users.ui_client.user_pool_client_id,
        )

        # Add UI and API domain names
        frontend_app_config.set_domain_names(ui_domain_name=self.ui_domain_name, api_domain_name=self.api_domain_name)

        # Add bucket names needed for CSP Lambda
        frontend_app_config.set_license_bulk_uploads_bucket_name(bucket_name=self.bulk_uploads_bucket.bucket_name)
        frontend_app_config.set_provider_users_bucket_name(bucket_name=self.provider_users_bucket.bucket_name)

        # Generate the SSM parameter
        self.frontend_app_config_parameter = frontend_app_config.generate_ssm_parameter(
            self, 'FrontendAppConfigParameter'
        )
