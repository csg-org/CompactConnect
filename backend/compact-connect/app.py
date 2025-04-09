#!/usr/bin/env python3
import os

from aws_cdk import App, Environment
from common_constructs.stack import StandardTags
from pipeline import BetaPipelineStack, DeploymentResourcesStack, ProdPipelineStack, TestPipelineStack
from pipeline.backend_stage import BackendStage


class CompactConnectApp(App):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        sandbox_environment = self.node.try_get_context('sandbox')

        # Toggle for developers to deploy to a sandbox account without the pipeline
        if sandbox_environment:
            # ssm_context must be provided locally for a sandbox deploy
            ssm_context = self.node.get_context('ssm_context')
            environment_name = self.node.get_context('environment_name')
            environment_context = ssm_context['environments'][environment_name]
            app_name = ssm_context['app_name']

            self.sandbox_stage = BackendStage(
                self,
                'Sandbox',
                app_name=app_name,
                environment_name=environment_name,
                environment_context=environment_context,
                github_repo_string=ssm_context['github_repo_string'],
            )
        else:
            tags = self.node.get_context('tags')
            environment = Environment(
                account=os.environ['CDK_DEFAULT_ACCOUNT'],
                region=os.environ['CDK_DEFAULT_REGION'],
            )

            self.deployment_resources_stack = DeploymentResourcesStack(
                self,
                'DeploymentResourcesStack',
                env=environment,
                standard_tags=StandardTags(**tags, environment='deploy'),
            )

            self.test_pipeline_stack = TestPipelineStack(
                self,
                'TestPipelineStack',
                pipeline_shared_encryption_key=self.deployment_resources_stack.pipeline_shared_encryption_key,
                pipeline_alarm_topic=self.deployment_resources_stack.pipeline_alarm_topic,
                env=environment,
                standard_tags=StandardTags(**tags, environment='pipeline'),
                cdk_path='backend/compact-connect',
            )

            self.prod_pipeline_stack = ProdPipelineStack(
                self,
                'ProdPipelineStack',
                pipeline_shared_encryption_key=self.deployment_resources_stack.pipeline_shared_encryption_key,
                pipeline_alarm_topic=self.deployment_resources_stack.pipeline_alarm_topic,
                env=environment,
                standard_tags=StandardTags(**tags, environment='pipeline'),
                cdk_path='backend/compact-connect',
            )

            self.beta_pipeline_stack = BetaPipelineStack(
                self,
                'BetaPipelineStack',
                pipeline_shared_encryption_key=self.deployment_resources_stack.pipeline_shared_encryption_key,
                pipeline_alarm_topic=self.deployment_resources_stack.pipeline_alarm_topic,
                env=environment,
                standard_tags=StandardTags(**tags, environment='pipeline'),
                cdk_path='backend/compact-connect',
            )


if __name__ == '__main__':
    app = CompactConnectApp()
    app.synth()
