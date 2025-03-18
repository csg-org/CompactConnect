#!/usr/bin/env python3
from aws_cdk import App, Environment
from stacks.stages import LogsAccountStage, ManagementAccountStage


class LogAggregationApp(App):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Get account IDs from context (all fields are required)
        management_account_id = self.node.get_context('management_account_id')
        logs_account_id = self.node.get_context('logs_account_id')
        region = self.node.get_context('region')
        tags = self.node.get_context('tags')

        # Create environment objects
        management_env = Environment(account=management_account_id, region=region)
        logs_env = Environment(account=logs_account_id, region=region)

        # Deploy the logs account stage
        self.logs_stage = LogsAccountStage(
            self,
            'LogsAccountStage',
            env=logs_env,
            tags=tags,
        )

        # Deploy the management account stage
        self.management_stage = ManagementAccountStage(
            self,
            'ManagementAccountStage',
            env=management_env,
            cloudtrail_logs_bucket_name=self.logs_stage.cloudtrail_logs_bucket_name,
            tags=tags,
        )


if __name__ == '__main__':
    app = LogAggregationApp()
    app.synth()
