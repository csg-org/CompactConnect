from aws_cdk import Environment, Stage
from common_constructs.stack import StandardTags
from constructs import Construct
from stacks.api_stack import ApiStack
from stacks.ingest_stack import IngestStack
from stacks.persistent_stack import PersistentStack
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
        )

        # Reporting depends on emails, which depend on having a domain name. If we don't configure a HostedZone
        # we won't bother with this whole stack.
        if self.persistent_stack.hosted_zone:
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
