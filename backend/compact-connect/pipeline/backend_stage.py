from aws_cdk import Environment, Stage
from common_constructs.stack import StandardTags
from constructs import Construct

from stacks.api_lambda_stack import ApiLambdaStack
from stacks.api_stack import ApiStack
from stacks.data_migration_stack import DataMigrationStack
from stacks.disaster_recovery_stack import DisasterRecoveryStack
from stacks.event_listener_stack import EventListenerStack
from stacks.event_state_stack import EventStateStack
from stacks.feature_flag_stack import FeatureFlagStack
from stacks.ingest_stack import IngestStack
from stacks.managed_login_stack import ManagedLoginStack
from stacks.notification_stack import NotificationStack
from stacks.persistent_stack import PersistentStack
from stacks.provider_users import ProviderUsersStack
from stacks.reporting_stack import ReportingStack
from stacks.search_api_stack import SearchApiStack
from stacks.search_persistent_stack import SearchPersistentStack
from stacks.state_api_stack import StateApiStack
from stacks.state_auth import StateAuthStack
from stacks.transaction_monitoring_stack import TransactionMonitoringStack
from stacks.vpc_stack import VpcStack


class BackendStage(Stage):
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
    ):
        super().__init__(scope, construct_id, **kwargs)

        standard_tags = StandardTags(**self.node.get_context('tags'), environment=environment_name)

        environment = Environment(account=environment_context['account_id'], region=environment_context['region'])

        # VPC Stack - provides networking infrastructure for OpenSearch and Lambda functions
        self.vpc_stack = VpcStack(
            self,
            'VpcStack',
            env=environment,
            environment_context=environment_context,
            standard_tags=standard_tags,
            environment_name=environment_name,
        )

        self.persistent_stack = PersistentStack(
            self,
            'PersistentStack',
            env=environment,
            environment_context=environment_context,
            standard_tags=standard_tags,
            app_name=app_name,
            environment_name=environment_name,
            backup_config=backup_config,
        )

        # Backup infrastructure is now created as a nested stack within PersistentStack
        # if backups are enabled for this environment
        self.backup_infrastructure_stack = self.persistent_stack.backup_infrastructure_stack

        self.event_state_stack = EventStateStack(
            self,
            'EventStateStack',
            env=environment,
            environment_context=environment_context,
            standard_tags=standard_tags,
            environment_name=environment_name,
            persistent_stack=self.persistent_stack,
        )

        self.provider_users_stack = ProviderUsersStack(
            self,
            'ProviderUsersStack',
            env=environment,
            environment_context=environment_context,
            standard_tags=standard_tags,
            app_name=app_name,
            environment_name=environment_name,
            persistent_stack=self.persistent_stack,
        )

        self.state_auth_stack = StateAuthStack(
            self,
            'StateAuthStack',
            env=environment,
            environment_context=environment_context,
            standard_tags=standard_tags,
            app_name=app_name,
            environment_name=environment_name,
            persistent_stack=self.persistent_stack,
        )

        self.managed_login_stack = ManagedLoginStack(
            self,
            'ManagedLoginStack',
            env=environment,
            environment_context=environment_context,
            environment_name=environment_name,
            standard_tags=standard_tags,
            persistent_stack=self.persistent_stack,
            provider_users_stack=self.provider_users_stack,
        )

        self.ingest_stack = IngestStack(
            self,
            'IngestStack',
            env=environment,
            environment_context=environment_context,
            environment_name=environment_name,
            standard_tags=standard_tags,
            persistent_stack=self.persistent_stack,
        )

        self.api_lambda_stack = ApiLambdaStack(
            self,
            'ApiLambdaStack',
            env=environment,
            environment_context=environment_context,
            standard_tags=standard_tags,
            environment_name=environment_name,
            persistent_stack=self.persistent_stack,
            provider_users_stack=self.provider_users_stack,
        )

        self.api_stack = ApiStack(
            self,
            'APIStack',
            env=environment,
            environment_context=environment_context,
            standard_tags=standard_tags,
            environment_name=environment_name,
            persistent_stack=self.persistent_stack,
            provider_users_stack=self.provider_users_stack,
            api_lambda_stack=self.api_lambda_stack,
        )

        self.state_api_stack = StateApiStack(
            self,
            'StateAPIStack',
            env=environment,
            environment_context=environment_context,
            standard_tags=standard_tags,
            environment_name=environment_name,
            persistent_stack=self.persistent_stack,
            state_auth_stack=self.state_auth_stack,
        )

        self.event_listener_stack = EventListenerStack(
            self,
            'EventListenerStack',
            env=environment,
            environment_context=environment_context,
            standard_tags=standard_tags,
            environment_name=environment_name,
            persistent_stack=self.persistent_stack,
        )

        # Reporting and notifications depend on emails, which depend on having a domain name. If we don't configure
        # a HostedZone we won't bother with these whole stacks.
        if self.persistent_stack.hosted_zone:
            self.notification_stack = NotificationStack(
                self,
                'NotificationStack',
                env=environment,
                environment_context=environment_context,
                standard_tags=standard_tags,
                environment_name=environment_name,
                persistent_stack=self.persistent_stack,
                event_state_stack=self.event_state_stack,
            )

            self.reporting_stack = ReportingStack(
                self,
                'ReportingStack',
                env=environment,
                environment_context=environment_context,
                environment_name=environment_name,
                standard_tags=standard_tags,
                persistent_stack=self.persistent_stack,
            )

        self.transaction_monitoring_stack = TransactionMonitoringStack(
            self,
            'TransactionMonitoringStack',
            env=environment,
            environment_name=environment_name,
            environment_context=environment_context,
            standard_tags=standard_tags,
            persistent_stack=self.persistent_stack,
        )

        # Disaster recovery workflows for DynamoDB tables
        self.disaster_recovery_stack = DisasterRecoveryStack(
            self,
            'DisasterRecoveryStack',
            env=environment,
            environment_name=environment_name,
            environment_context=environment_context,
            standard_tags=standard_tags,
            persistent_stack=self.persistent_stack,
        )

        # Stack to create and manage feature flags
        self.feature_flag_stack = FeatureFlagStack(
            self,
            'FeatureFlagStack',
            env=environment,
            environment_name=environment_name,
            environment_context=environment_context,
            standard_tags=standard_tags,
        )

        # Stack to house data migration custom resources
        # This stack depends on the API and event listener stacks to ensure
        # all core infrastructure is in place before migrations run
        self.data_migration_stack = DataMigrationStack(
            self,
            'DataMigrationStack',
            env=environment,
            environment_name=environment_name,
            environment_context=environment_context,
            standard_tags=standard_tags,
            persistent_stack=self.persistent_stack,
        )
        # Explicitly declare the dependency to ensure proper deployment order
        self.data_migration_stack.add_dependency(self.api_stack)
        self.data_migration_stack.add_dependency(self.event_listener_stack)

        # Search Persistent Stack - OpenSearch Domain for advanced provider search
        # currently not deploying to prod or beta to reduce costs until search api functionality is completed
        # to reduce costs
        if environment_name != 'prod' and environment_name != 'beta':
            self.search_persistent_stack = SearchPersistentStack(
                self,
                'SearchPersistentStack',
                env=environment,
                environment_context=environment_context,
                standard_tags=standard_tags,
                environment_name=environment_name,
                vpc_stack=self.vpc_stack,
                persistent_stack=self.persistent_stack,
            )

            self.search_api_stack = SearchApiStack(
                self,
                'SearchAPIStack',
                env=environment,
                environment_context=environment_context,
                standard_tags=standard_tags,
                environment_name=environment_name,
                persistent_stack=self.persistent_stack,
                search_persistent_stack=self.search_persistent_stack,
            )
