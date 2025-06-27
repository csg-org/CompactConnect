from aws_cdk import Environment, Stage
from common_constructs.stack import StandardTags
from constructs import Construct
from stacks.api_stack import ApiStack
from stacks.backup_infrastructure_stack import BackupInfrastructureStack
from stacks.event_listener_stack import EventListenerStack
from stacks.ingest_stack import IngestStack
from stacks.managed_login_stack import ManagedLoginStack
from stacks.notification_stack import NotificationStack
from stacks.persistent_stack import PersistentStack
from stacks.provider_users import ProviderUsersStack
from stacks.reporting_stack import ReportingStack
from stacks.transaction_monitoring_stack import TransactionMonitoringStack


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

        self.persistent_stack = PersistentStack(
            self,
            'PersistentStack',
            env=environment,
            environment_context=environment_context,
            standard_tags=standard_tags,
            app_name=app_name,
            environment_name=environment_name,
        )

        # Create backup infrastructure for data retention
        self.backup_infrastructure_stack = BackupInfrastructureStack(
            self,
            'BackupInfrastructureStack',
            env=environment,
            environment_name=environment_name,
            backup_config=backup_config,
            tags=standard_tags,
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

        self.api_stack = ApiStack(
            self,
            'APIStack',
            env=environment,
            environment_context=environment_context,
            standard_tags=standard_tags,
            environment_name=environment_name,
            persistent_stack=self.persistent_stack,
            provider_users_stack=self.provider_users_stack,
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
