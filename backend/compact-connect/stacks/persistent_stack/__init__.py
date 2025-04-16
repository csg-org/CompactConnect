import os

import yaml
from aws_cdk import Duration, RemovalPolicy, aws_ssm
from aws_cdk.aws_cognito import SignInAliases, UserPoolEmail
from aws_cdk.aws_iam import Effect, PolicyStatement
from aws_cdk.aws_kms import Key
from aws_cdk.aws_lambda import Runtime
from aws_cdk.aws_lambda_python_alpha import PythonLayerVersion
from aws_cdk.aws_logs import QueryDefinition, QueryString
from cdk_nag import NagSuppressions
from common_constructs.access_logs_bucket import AccessLogsBucket
from common_constructs.alarm_topic import AlarmTopic
from common_constructs.data_migration import DataMigration
from common_constructs.frontend_app_config_utility import PersistentStackFrontendAppConfigUtility
from common_constructs.nodejs_function import NodejsFunction
from common_constructs.python_function import COMMON_PYTHON_LAMBDA_LAYER_SSM_PARAMETER_NAME
from common_constructs.security_profile import SecurityProfile
from common_constructs.ssm_parameter_utility import SSMParameterUtility
from common_constructs.stack import AppStack
from constructs import Construct

from stacks.persistent_stack.bulk_uploads_bucket import BulkUploadsBucket
from stacks.persistent_stack.compact_configuration_table import CompactConfigurationTable
from stacks.persistent_stack.compact_configuration_upload import CompactConfigurationUpload
from stacks.persistent_stack.data_event_table import DataEventTable
from stacks.persistent_stack.event_bus import EventBus
from stacks.persistent_stack.provider_table import ProviderTable
from stacks.persistent_stack.provider_users import ProviderUsers
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

        self.access_logs_bucket = AccessLogsBucket(
            self,
            'AccessLogsBucket',
            removal_policy=removal_policy,
            auto_delete_objects=removal_policy == RemovalPolicy.DESTROY,
        )
        # TODO: remove these exports after CloudFront Distribution has been moved over to frontend pipeline.
        self.export_value(self.access_logs_bucket.bucket_name)
        self.export_value(self.access_logs_bucket.bucket_arn)
        self.export_value(self.access_logs_bucket.bucket_regional_domain_name)

        # This resource should not be referenced directly as a cross stack reference, any reference should
        # be made through the SSM parameter
        self._data_event_bus = EventBus(self, 'DataEventBus', event_bus_name=f'{environment_name}-dataEventBus')
        # We Store the data event bus name in SSM Parameter Store
        # to avoid issues with cross stack references due to the fact that
        # you can't update a CloudFormation exported value that is being referenced by a resource in another stack.
        self.data_event_bus_arn_ssm_parameter = SSMParameterUtility.set_data_event_bus_arn_ssm_parameter(
            self, self._data_event_bus
        )

        self._add_data_resources(removal_policy=removal_policy)
        self._add_migrations()

        self.compact_configuration_upload = CompactConfigurationUpload(
            self,
            'CompactConfigurationUpload',
            table=self.compact_configuration_table,
            master_key=self.shared_encryption_key,
            environment_name=environment_name,
            environment_context=environment_context,
        )

        if self.hosted_zone:
            self.user_email_notifications = UserEmailNotifications(
                self,
                'UserEmailNotifications',
                environment_context=environment_context,
                hosted_zone=self.hosted_zone,
                master_key=self.shared_encryption_key,
            )
            user_pool_email_settings = UserPoolEmail.with_ses(
                from_email=f'no-reply@{self.hosted_zone.zone_name}',
                ses_verified_domain=self.hosted_zone.zone_name,
                configuration_set_name=self.user_email_notifications.config_set.configuration_set_name,
            )
        else:
            # if domain name is not provided, use the default cognito email settings
            user_pool_email_settings = UserPoolEmail.with_cognito()

        self._create_email_notification_service()

        security_profile = SecurityProfile[environment_context.get('security_profile', 'RECOMMENDED')]
        staff_prefix = f'{app_name}-staff'

        self.staff_users = StaffUsers(
            self,
            'StaffUsersGreen',
            cognito_domain_prefix=staff_prefix if environment_name == 'prod' else f'{staff_prefix}-{environment_name}',
            environment_name=environment_name,
            environment_context=environment_context,
            encryption_key=self.shared_encryption_key,
            user_pool_email=user_pool_email_settings,
            security_profile=security_profile,
            removal_policy=removal_policy,
        )

        # PROVIDER USER POOL MIGRATION PLAN:
        # 1. ✓ Create the blue user pool in all environments. (Deploy 1 of 3)
        # 2. Cut over to the blue user pool by: (Deploy 2 of 3)
        #   a. ✓ Update the API stack to use the blue user pool (just rename
        #      self.provider_users->self.provider_users_deprecated and
        #      self.provider_users_standby->self.provider_users below)
        #   b. ✓ Move the main provider prefix to the blue user pool (just use the provider_prefix in the other
        #      ProviderUsers constructor below)
        #   c. Deploy to all environments. You will have to manually delete the original user pool domain right before
        #      deploying to each environment. This will result in a deletion failure in the CFn events, but the overall
        #      deployment will succeed.
        # 3. Testers/users will need to re-register to get a new provider user in the blue user pool.
        # 4. Remove the original user pool. (Deploy 3 of 3)

        # This user pool is deprecated and will be removed once we've cut over to the blue user pool
        # across all environments.
        provider_prefix = f'{app_name}-provider'
        provider_prefix = provider_prefix if environment_name == 'prod' else f'{provider_prefix}-{environment_name}'
        self.provider_users_deprecated = ProviderUsers(
            self,
            'ProviderUsers',
            cognito_domain_prefix=None,
            environment_name=environment_name,
            environment_context=environment_context,
            encryption_key=self.shared_encryption_key,
            sign_in_aliases=None,
            user_pool_email=user_pool_email_settings,
            security_profile=security_profile,
            removal_policy=removal_policy,
        )
        # We explicitly export the user pool values so we can later move the API stack over to the
        # new user pool without putting our app into a cross-stack dependency 'deadly embrace':
        # https://www.endoflineblog.com/cdk-tips-03-how-to-unblock-cross-stack-references
        self.export_value(self.provider_users_deprecated.user_pool_id)
        self.export_value(self.provider_users_deprecated.user_pool_arn)

        # We have to use a different prefix so we don't have a naming conflict with the original user pool
        self.provider_users = ProviderUsers(
            self,
            'ProviderUsersBlue',
            cognito_domain_prefix=provider_prefix,
            environment_name=environment_name,
            environment_context=environment_context,
            encryption_key=self.shared_encryption_key,
            sign_in_aliases=SignInAliases(email=True, username=False),
            user_pool_email=user_pool_email_settings,
            security_profile=security_profile,
            removal_policy=removal_policy,
        )

        QueryDefinition(
            self,
            'UserCustomEmails',
            query_definition_name='UserCustomEmails/Lambdas',
            query_string=QueryString(
                fields=['@timestamp', '@log', 'level', 'message', '@message'],
                filter_statements=['level in ["INFO", "WARNING", "ERROR"]'],
                sort='@timestamp desc',
            ),
            log_groups=[
                self.provider_users.custom_message_lambda.log_group,
                self.staff_users.custom_message_lambda.log_group,
            ],
        )

        if self.hosted_zone:
            # The SES email identity needs to be created before the user pools
            # so that the domain address will be verified before being referenced
            # by the user pool email settings
            self.staff_users.node.add_dependency(self.user_email_notifications.email_identity)
            self.staff_users.node.add_dependency(self.user_email_notifications.dmarc_record)
            self.provider_users.node.add_dependency(self.user_email_notifications.email_identity)
            self.provider_users.node.add_dependency(self.user_email_notifications.dmarc_record)
            self.provider_users_deprecated.node.add_dependency(self.user_email_notifications.email_identity)
            self.provider_users_deprecated.node.add_dependency(self.user_email_notifications.dmarc_record)
            # the verification custom resource needs to be completed before the user pools are created
            # so that the user pools will be created after the SES identity is verified
            self.staff_users.node.add_dependency(self.user_email_notifications.verification_custom_resource)
            self.provider_users.node.add_dependency(self.user_email_notifications.verification_custom_resource)
            self.provider_users_deprecated.node.add_dependency(
                self.user_email_notifications.verification_custom_resource
            )

        # This parameter is used to store the frontend app config values for use in the frontend deployment stack
        self._create_frontend_app_config_parameter()

    def _add_data_resources(self, removal_policy: RemovalPolicy):
        # Create the ssn related resources before other resources which are dependent on them
        self.ssn_table = SSNTable(
            self,
            'SSNTable',
            removal_policy=removal_policy,
            data_event_bus=self._data_event_bus,
            alarm_topic=self.alarm_topic,
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
        # TODO - This dummy export is required until the api stack has been deployed # noqa: FIX002
        #  to stop referencing this bucket arn
        self.export_value(self.bulk_uploads_bucket.bucket_arn)

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
            self, 'ProviderTable', encryption_key=self.shared_encryption_key, removal_policy=removal_policy
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
        )

        self.compact_configuration_table = CompactConfigurationTable(
            scope=self,
            construct_id='CompactConfigurationTable',
            encryption_key=self.shared_encryption_key,
            removal_policy=removal_policy,
        )

        self.transaction_history_table = TransactionHistoryTable(
            scope=self,
            construct_id='TransactionHistoryTable',
            encryption_key=self.shared_encryption_key,
            removal_policy=removal_policy,
        )

        # bucket for holding documentation for providers
        self.provider_users_bucket = ProviderUsersBucket(
            self,
            'ProviderUsersBucket',
            access_logs_bucket=self.access_logs_bucket,
            encryption_key=self.shared_encryption_key,
            provider_table=self.provider_table,
            removal_policy=removal_policy,
        )

    def _add_migrations(self):
        """
        Whenever a change is introduced that requires a schema migration (ie a new GSI or removing a deprecated field)
        there should be an associated migration script that is run as part of the deployment. These are short-lived
        custom resources that should be removed from the CDK app once the migration has been run in all environments.
        """
        multi_license_migration = DataMigration(
            self,
            '569MultiLicense',
            migration_dir='569_multi_license',
            lambda_environment={
                'PROVIDER_TABLE_NAME': self.provider_table.table_name,
                'PROV_FAM_GIV_MID_INDEX_NAME': self.provider_table.provider_fam_giv_mid_index_name,
                **self.common_env_vars,
            },
        )
        self.provider_table.grant_read_write_data(multi_license_migration)
        NagSuppressions.add_resource_suppressions_by_path(
            self,
            f'{multi_license_migration.migration_function.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'This policy contains wild-carded actions and resources but they are scoped to the '
                    'specific actions, reporting Table and Key that this lambda specifically needs access to.',
                },
            ],
        )

        military_waiver_removal_migration = DataMigration(
            self,
            '618RemoveMilitaryWaiver',
            migration_dir='618_remove_military_waiver',
            lambda_environment={
                'PROVIDER_TABLE_NAME': self.provider_table.table_name,
                **self.common_env_vars,
            },
        )
        self.provider_table.grant_read_write_data(military_waiver_removal_migration)
        NagSuppressions.add_resource_suppressions_by_path(
            self,
            f'{military_waiver_removal_migration.migration_function.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'This policy contains wild-carded actions and resources but they are scoped to the '
                    'specific actions, Table and Key that this lambda needs access to in order to perform the'
                    'migration.',
                },
            ],
        )

        three_license_status_migration = DataMigration(
            self,
            '667ThreeLicenseStatus',
            migration_dir='667_three_license_status_fields',
            lambda_environment={
                'PROVIDER_TABLE_NAME': self.provider_table.table_name,
                **self.common_env_vars,
            },
        )
        self.provider_table.grant_read_write_data(three_license_status_migration)
        NagSuppressions.add_resource_suppressions_by_path(
            self,
            f'{three_license_status_migration.migration_function.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'This policy contains wild-carded actions and resources but they are scoped to the '
                    'specific actions, Table and Key that this lambda needs access to in order to perform the'
                    'migration.',
                },
            ],
        )

        deactivation_details_migration = DataMigration(
            self,
            '566DeactivationDetails',
            migration_dir='deactivation_details_566',
            lambda_environment={
                'PROVIDER_TABLE_NAME': self.provider_table.table_name,
                **self.common_env_vars,
            },
        )
        self.provider_table.grant_read_write_data(deactivation_details_migration)
        NagSuppressions.add_resource_suppressions_by_path(
            self,
            f'{deactivation_details_migration.migration_function.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'This policy contains wild-carded actions and resources but they are scoped to the '
                    'specific actions, Table and Key that this lambda needs access to in order to perform the'
                    'migration.',
                },
            ],
        )

        QueryDefinition(
            self,
            'Migrations',
            query_definition_name='Migrations/Lambdas',
            query_string=QueryString(
                fields=['@timestamp', 'level', 'compact', 'provider_id', 'message'],
                filter_statements=['level in ["INFO", "WARNING", "ERROR"]'],
                sort='@timestamp desc',
            ),
            log_groups=[
                multi_license_migration.migration_function.log_group,
                military_waiver_removal_migration.migration_function.log_group,
                three_license_status_migration.migration_function.log_group,
            ],
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

    def _configuration_is_active_for_environment(self, environment_name: str, active_environments: list[str]) -> bool:
        """Check if the compact configuration is active in the given environment."""
        return environment_name in active_environments or self.node.try_get_context('sandbox') is True

    def get_list_of_active_compacts_for_environment(self, environment_name: str) -> list[str]:
        """
        Currently, all configuration for compacts and jurisdictions is hardcoded in the compact-config directory.
        This reads the YAML configuration files and returns the list of compacts that are marked as
        active for the environment.
        """

        active_compacts = []
        # Read all compact configuration YAML files from top level compact-config directory
        for compact_config_file in os.listdir('compact-config'):
            if compact_config_file.endswith('.yml'):
                with open(os.path.join('compact-config', compact_config_file)) as f:
                    # convert YAML to JSON
                    formatted_compact = yaml.safe_load(f)
                    # only include the compact configuration if it is active in the environment
                    if self._configuration_is_active_for_environment(
                        environment_name,
                        formatted_compact['activeEnvironments'],
                    ):
                        active_compacts.append(formatted_compact['compactAbbr'])

        return active_compacts

    def get_list_of_active_jurisdictions_for_compact_environment(
        self, compact: str, environment_name: str
    ) -> list[str]:
        """
        Get the list of jurisdiction postal codes which are active within a compact and environment.

        Currently, all configuration for compacts and jurisdictions is hardcoded in the compact-config directory.
        This reads the YAML configuration files and returns the list of jurisdiction postal codes that are marked as
        active for the environment.
        """

        active_jurisdictions = []

        # Read all jurisdiction configuration YAML files from each active compact directory
        for jurisdiction_config_file in os.listdir(os.path.join('compact-config', compact)):
            if jurisdiction_config_file.endswith('.yml'):
                with open(os.path.join('compact-config', compact, jurisdiction_config_file)) as f:
                    formatted_jurisdiction = yaml.safe_load(f)
                    # only include the jurisdiction configuration if it is active in the environment
                    if self._configuration_is_active_for_environment(
                        environment_name,
                        formatted_jurisdiction['activeEnvironments'],
                    ):
                        active_jurisdictions.append(formatted_jurisdiction['postalAbbreviation'].lower())

        return active_jurisdictions

    def _create_frontend_app_config_parameter(self):
        """
        Creates and stores UI application configuration in SSM Parameter Store for use in the UI stack and 
        frontend deployment stack.
        """
        # Create and store UI application configuration in SSM Parameter Store for use in the UI stack
        frontend_app_config = PersistentStackFrontendAppConfigUtility()

        # Add staff user pool Cognito configuration
        frontend_app_config.set_staff_cognito_values(
            domain_name=self.staff_users.user_pool_domain.domain_name,
            client_id=self.staff_users.ui_client.user_pool_client_id,
        )

        # Add provider user pool Cognito configuration
        frontend_app_config.set_provider_cognito_values(
            domain_name=self.provider_users.user_pool_domain.domain_name,
            client_id=self.provider_users.ui_client.user_pool_client_id,
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
