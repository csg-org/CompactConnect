from aws_cdk import Environment, Stage
from constructs import Construct

from stacks.data_events_trail_stack import DataEventsTrailStack
from stacks.log_aggregation_stack import LogAggregationStack


class LogsAccountStage(Stage):
    """Stage for resources that need to be deployed to the logs account."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        env: Environment,
        tags: dict[str, str],
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, env=env, **kwargs)

        app_name = self.node.get_context('app_name')
        bucket_prefix = self.node.get_context('data_events_bucket_prefix')

        # Generate consistent bucket names for this deployment
        self.access_logs_bucket_name = f'{app_name}-access-logs-{env.account}-{env.region}'
        self.cloudtrail_logs_bucket_name = f'{app_name}-{bucket_prefix}-{env.account}-{env.region}'

        self.logs_stack = LogAggregationStack(
            self,
            'LogAggregationStack',
            env=env,
            access_logs_bucket_name=self.access_logs_bucket_name,
            cloudtrail_logs_bucket_name=self.cloudtrail_logs_bucket_name,
            tags=tags,
        )


class ManagementAccountStage(Stage):
    """Stage for resources that need to be deployed to the management account."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        env: Environment,
        cloudtrail_logs_bucket_name: str,
        tags: dict[str, str],
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, env=env, **kwargs)

        self.trail_stack = DataEventsTrailStack(
            self,
            'DataEventsTrailStack',
            env=env,
            cloudtrail_logs_bucket_name=cloudtrail_logs_bucket_name,
            tags=tags,
        )
