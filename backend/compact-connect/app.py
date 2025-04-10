#!/usr/bin/env python3
import os

from aws_cdk import App, Environment
from common_constructs.stack import StandardTags
from pipeline import (
    BetaBackendPipelineStack,
    BetaFrontendPipelineStack,
    DeploymentResourcesStack,
    ProdBackendPipelineStack,
    ProdFrontendPipelineStack,
    TestBackendPipelineStack,
    TestFrontendPipelineStack,
)
from pipeline.backend_stage import BackendStage
from pipeline.frontend_stage import FrontendStage


class CompactConnectApp(App):
    """
    CompactConnect CDK Application

    This application implements a two-pipeline deployment architecture:

    1. Backend Pipelines: Deploy infrastructure resources and backend components
    2. Frontend Pipelines: Deploy frontend applications that depend on backend resources

    Pipeline Execution Flow:
    - GitHub push → Backend Pipeline → Frontend Pipeline

    The application creates these pipeline stacks:
    - Backend Pipeline Stacks: TestBackendPipelineStack, BetaBackendPipelineStack, ProdBackendPipelineStack
    - Frontend Pipeline Stacks: TestFrontendPipelineStack, BetaFrontendPipelineStack, ProdFrontendPipelineStack

    Each pipeline type is in its own dedicated stack to avoid self-mutation conflicts.
    """

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

            self.sandbox_backend_stage = BackendStage(
                self,
                'Sandbox',
                app_name=app_name,
                environment_name=environment_name,
                environment_context=environment_context,
            )
            # NOTE: for first-time sandbox deployments, ensure you deploy the backend stage successfully first
            # by running `cdk deploy 'Sandbox/*'`, then if you want to deploy the UI for your sandbox environment, set
            # the 'deploy_sandbox_ui' field to true and deploy this stack by running `cdk deploy 'SandboxUI/*'. This
            # ensures the user pool values are configured to be bundled with the UI build artifact.
            if environment_context['deploy_sandbox_ui']:
                self.sandbox_frontend_stage = FrontendStage(
                    self,
                    'SandboxUI',
                    environment_name=environment_name,
                    environment_context=environment_context,
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

            # Test environment pipeline stacks
            self.test_backend_pipeline_stack = TestBackendPipelineStack(
                self,
                'TestBackendPipelineStack',
                pipeline_shared_encryption_key=self.deployment_resources_stack.pipeline_shared_encryption_key,
                pipeline_alarm_topic=self.deployment_resources_stack.pipeline_alarm_topic,
                pipeline_access_logs_bucket=self.deployment_resources_stack.pipeline_access_logs_bucket,
                env=environment,
                standard_tags=StandardTags(**tags, environment='pipeline'),
                cdk_path='backend/compact-connect',
            )

            self.test_frontend_pipeline_stack = TestFrontendPipelineStack(
                self,
                'TestFrontendPipelineStack',
                pipeline_shared_encryption_key=self.deployment_resources_stack.pipeline_shared_encryption_key,
                pipeline_alarm_topic=self.deployment_resources_stack.pipeline_alarm_topic,
                pipeline_access_logs_bucket=self.deployment_resources_stack.pipeline_access_logs_bucket,
                env=environment,
                standard_tags=StandardTags(**tags, environment='pipeline'),
                cdk_path='backend/compact-connect',
            )

            # Production environment pipeline stacks
            self.prod_backend_pipeline_stack = ProdBackendPipelineStack(
                self,
                'ProdBackendPipelineStack',
                pipeline_shared_encryption_key=self.deployment_resources_stack.pipeline_shared_encryption_key,
                pipeline_alarm_topic=self.deployment_resources_stack.pipeline_alarm_topic,
                pipeline_access_logs_bucket=self.deployment_resources_stack.pipeline_access_logs_bucket,
                env=environment,
                standard_tags=StandardTags(**tags, environment='pipeline'),
                cdk_path='backend/compact-connect',
            )

            self.prod_frontend_pipeline_stack = ProdFrontendPipelineStack(
                self,
                'ProdFrontendPipelineStack',
                pipeline_shared_encryption_key=self.deployment_resources_stack.pipeline_shared_encryption_key,
                pipeline_alarm_topic=self.deployment_resources_stack.pipeline_alarm_topic,
                pipeline_access_logs_bucket=self.deployment_resources_stack.pipeline_access_logs_bucket,
                env=environment,
                standard_tags=StandardTags(**tags, environment='pipeline'),
                cdk_path='backend/compact-connect',
            )

            # Beta environment pipeline stacks
            self.beta_backend_pipeline_stack = BetaBackendPipelineStack(
                self,
                'BetaBackendPipelineStack',
                pipeline_shared_encryption_key=self.deployment_resources_stack.pipeline_shared_encryption_key,
                pipeline_alarm_topic=self.deployment_resources_stack.pipeline_alarm_topic,
                pipeline_access_logs_bucket=self.deployment_resources_stack.pipeline_access_logs_bucket,
                env=environment,
                standard_tags=StandardTags(**tags, environment='pipeline'),
                cdk_path='backend/compact-connect',
            )

            self.beta_frontend_pipeline_stack = BetaFrontendPipelineStack(
                self,
                'BetaFrontendPipelineStack',
                pipeline_shared_encryption_key=self.deployment_resources_stack.pipeline_shared_encryption_key,
                pipeline_alarm_topic=self.deployment_resources_stack.pipeline_alarm_topic,
                pipeline_access_logs_bucket=self.deployment_resources_stack.pipeline_access_logs_bucket,
                env=environment,
                standard_tags=StandardTags(**tags, environment='pipeline'),
                cdk_path='backend/compact-connect',
            )


if __name__ == '__main__':
    app = CompactConnectApp()
    app.synth()
