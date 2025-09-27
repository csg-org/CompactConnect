#!/usr/bin/env python3
import os
import sys

from aws_cdk import App, Environment

# Make the `common_constructs` namespace package under `common-cdk` available to Python
sys.path.insert(0, os.path.abspath(os.path.join('..', 'common-cdk')))

from common_constructs.deployment_resources_stack import DeploymentResourcesStack
from common_constructs.stack import StandardTags

from pipeline import (
    ACTION_CONTEXT_KEY,
    PIPELINE_STACK_CONTEXT_KEY,
    PIPELINE_SYNTH_ACTION,
    BetaFrontendPipelineStack,
    ProdFrontendPipelineStack,
    TestFrontendPipelineStack,
)
from pipeline.frontend_stage import FrontendStage

# Pipeline stack name constants for DRY code
TEST_FRONTEND_PIPELINE_STACK = 'TestFrontendPipelineStack'
BETA_FRONTEND_PIPELINE_STACK = 'BetaFrontendPipelineStack'
PROD_FRONTEND_PIPELINE_STACK = 'ProdFrontendPipelineStack'
DEPLOYMENT_RESOURCES_STACK = 'FrontendDeploymentResourcesStack'

# CDK path
CDK_PATH = 'backend/compact-connect-ui-app'


class CompactConnectApp(App):
    """
    CompactConnect CDK Application

    This application implements a CDK Pipeline deployment architecture with
    performance optimizations for faster synthesis and deployment workflows.

    Pipeline Execution Flow:
    ----------------------
    - GitHub push → Frontend Pipeline
    - GitHub push → Backend Pipeline → Frontend Pipeline

    Stack Structure:
    ---------------
    - Frontend Pipeline Stacks: TestFrontendPipelineStack, BetaFrontendPipelineStack, ProdFrontendPipelineStack
    - DeploymentResourcesStack: Shared resources needed by all pipeline stacks

    Each pipeline type is in its own dedicated stack to avoid self-mutation conflicts.

    Environment Deployments:
    -------------------------------
    see README.md for instructions on how to deploy to a sandbox or pipeline environment.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sandbox_environment = self.node.try_get_context('sandbox')

        # Toggle for developers to deploy to a sandbox account without the pipeline
        if self.sandbox_environment:
            self._setup_sandbox_environment()
        else:
            self._setup_pipeline_environment()

    def _setup_sandbox_environment(self):
        """Set up sandbox environment stacks"""
        # ssm_context must be provided locally for a sandbox deploy
        ssm_context = self.node.get_context('ssm_context')
        environment_name = self.node.get_context('environment_name')
        environment_context = ssm_context['environments'][environment_name]

        if not environment_context.get('domain_name'):
            raise ValueError(
                'Cannot deploy sandbox UI if domain name is not configured for your environment. '
                'You may still run the app from localhost. See README.md in the webroot folder for '
                'more information about running the app from localhost.'
            )

        self.sandbox_frontend_stage = FrontendStage(
            self,
            'SandboxUI',
            environment_name=environment_name,
            environment_context=environment_context,
        )

    def _setup_pipeline_environment(self):
        """
        Set up pipeline environment stacks based on action and pipeline stack context

        This method implements the conditional stack creation pattern that is key to optimizing
        synthesis performance in the CI/CD pipelines. It follows these rules:

        1. For bootstrapDeploy: Creates all stacks to ensure permissions are correctly set when deploying resources
        2. For pipelineSynth: Creates only the specific stack requested to minimize synthesis time

        This approach dramatically reduces synthesis time in the pipeline while maintaining
        all necessary permissions and relationships between stacks during bootstrap deployments.
        """
        self.tags = self.node.get_context('tags')
        self.action = self.node.try_get_context(ACTION_CONTEXT_KEY)
        self.pipeline_stack_name = self.node.try_get_context(PIPELINE_STACK_CONTEXT_KEY)

        # Validate when in pipeline synth mode
        if self.action == PIPELINE_SYNTH_ACTION and not self.pipeline_stack_name:
            raise ValueError(
                f"When action is '{PIPELINE_SYNTH_ACTION}', '{PIPELINE_STACK_CONTEXT_KEY}' context must be specified."
            )

        self.environment = Environment(
            account=os.environ['CDK_DEFAULT_ACCOUNT'],
            region=os.environ['CDK_DEFAULT_REGION'],
        )

        self.add_all_pipeline_stacks()

    def add_all_pipeline_stacks(self):
        """
        add all pipeline stacks for deployment

        This is needed so that permissions set by the DeploymentResourcesStack are properly added for the pipeline
        stack resources in every environment.
        """
        # This stack must be declared first, as all other pipeline stacks depend on it.
        self.add_deployment_resources_stack()

        self.add_test_frontend_pipeline_stack()
        self.add_beta_frontend_pipeline_stack()
        self.add_prod_frontend_pipeline_stack()

    def add_deployment_resources_stack(self):
        """add the deployment resources stack"""
        self.deployment_resources_stack = DeploymentResourcesStack(
            self,
            DEPLOYMENT_RESOURCES_STACK,
            env=self.environment,
            standard_tags=StandardTags(**self.tags, environment='deploy'),
        )

    def add_test_frontend_pipeline_stack(self):
        """add and return the Test Frontend Pipeline Stack"""
        self.test_frontend_pipeline_stack = TestFrontendPipelineStack(
            self,
            TEST_FRONTEND_PIPELINE_STACK,
            pipeline_shared_encryption_key=self.deployment_resources_stack.pipeline_shared_encryption_key,
            pipeline_alarm_topic=self.deployment_resources_stack.pipeline_alarm_topic,
            pipeline_access_logs_bucket=self.deployment_resources_stack.pipeline_access_logs_bucket,
            env=self.environment,
            standard_tags=StandardTags(**self.tags, environment='pipeline'),
            cdk_path=CDK_PATH,
        )
        return self.test_frontend_pipeline_stack

    def add_beta_frontend_pipeline_stack(self):
        """add and return the Beta Frontend Pipeline Stack"""
        self.beta_frontend_pipeline_stack = BetaFrontendPipelineStack(
            self,
            BETA_FRONTEND_PIPELINE_STACK,
            pipeline_shared_encryption_key=self.deployment_resources_stack.pipeline_shared_encryption_key,
            pipeline_alarm_topic=self.deployment_resources_stack.pipeline_alarm_topic,
            pipeline_access_logs_bucket=self.deployment_resources_stack.pipeline_access_logs_bucket,
            env=self.environment,
            standard_tags=StandardTags(**self.tags, environment='pipeline'),
            cdk_path=CDK_PATH,
        )
        return self.beta_frontend_pipeline_stack

    def add_prod_frontend_pipeline_stack(self):
        """add and return the Production Frontend Pipeline Stack"""
        self.prod_frontend_pipeline_stack = ProdFrontendPipelineStack(
            self,
            PROD_FRONTEND_PIPELINE_STACK,
            pipeline_shared_encryption_key=self.deployment_resources_stack.pipeline_shared_encryption_key,
            pipeline_alarm_topic=self.deployment_resources_stack.pipeline_alarm_topic,
            pipeline_access_logs_bucket=self.deployment_resources_stack.pipeline_access_logs_bucket,
            env=self.environment,
            standard_tags=StandardTags(**self.tags, environment='pipeline'),
            cdk_path=CDK_PATH,
        )
        return self.prod_frontend_pipeline_stack


if __name__ == '__main__':
    app = CompactConnectApp()
    app.synth()
