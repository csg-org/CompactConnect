from aws_cdk import Environment, RemovalPolicy
from aws_cdk.aws_kms import IKey
from aws_cdk.aws_s3 import IBucket
from aws_cdk.aws_sns import ITopic
from common_constructs.base_pipeline_stack import (
    BETA_ENVIRONMENT_NAME,
    PROD_ENVIRONMENT_NAME,
    TEST_ENVIRONMENT_NAME,
    BasePipelineStack,
    CCPipelineType,
)
from constructs import Construct

from pipeline.frontend_pipeline import FrontendPipeline
from pipeline.frontend_stage import FrontendStage
from pipeline.synth_substitute_stage import SynthSubstituteStage

# Action constants
ACTION_CONTEXT_KEY = 'action'
PIPELINE_STACK_CONTEXT_KEY = 'pipelineStack'
PIPELINE_SYNTH_ACTION = 'pipelineSynth'
BOOTSTRAP_DEPLOY_ACTION = 'bootstrapDeploy'


class BaseFrontendPipelineStack(BasePipelineStack):
    """
    Base class for frontend pipeline stacks.
    Implements common functionality for all frontend pipeline stacks.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        environment_name: str,
        env: Environment,
        removal_policy: RemovalPolicy,
        pipeline_access_logs_bucket: IBucket,
        **kwargs,
    ):
        super().__init__(
            scope,
            construct_id,
            environment_name=environment_name,
            env=env,
            pipeline_type=CCPipelineType.FRONTEND,
            removal_policy=removal_policy,
            pipeline_access_logs_bucket=pipeline_access_logs_bucket,
            **kwargs,
        )

    def _determine_frontend_stage(self, construct_id, environment_name, environment_context):
        """
        Return either a real FrontendStage or a SynthSubstituteStage depending on pipeline synthesis context.

        This method centralizes the stage creation logic to conditionally create a lightweight substitute
        stage during pipeline synthesis when the stage is not part of the pipeline being synthesized.
        """
        # Check if we're in pipeline synthesis mode and if we're synthesizing this specific pipeline
        action = self.node.try_get_context('action')
        pipeline_stack_name = self.node.try_get_context('pipelineStack')

        # If we're in pipeline synthesis mode and this is not the pipeline being synthesized,
        # use a lightweight substitute stage
        if (
            action == PIPELINE_SYNTH_ACTION and pipeline_stack_name != self.stack_name
        ) or action == BOOTSTRAP_DEPLOY_ACTION:
            return SynthSubstituteStage(
                self,
                'SubstituteFrontendStage',
                environment_context=environment_context,
            )

        # Otherwise, use the real stage for deployment
        return FrontendStage(
            self,
            construct_id,
            environment_name=environment_name,
            environment_context=environment_context,
        )


class TestFrontendPipelineStack(BaseFrontendPipelineStack):
    """Pipeline stack for the test frontend environment."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        pipeline_shared_encryption_key: IKey,
        pipeline_alarm_topic: ITopic,
        pipeline_access_logs_bucket: IBucket,
        cdk_path: str,
        **kwargs,
    ):
        super().__init__(
            scope,
            construct_id,
            environment_name=TEST_ENVIRONMENT_NAME,
            removal_policy=RemovalPolicy.DESTROY,
            pipeline_access_logs_bucket=pipeline_access_logs_bucket,
            **kwargs,
        )

        # Allows us to override the default branching scheme for the test environment, via context variable
        pre_prod_trigger_branch = self.pipeline_environment_context.get('pre_prod_trigger_branch', 'development')

        self.pre_prod_frontend_pipeline = FrontendPipeline(
            self,
            'TestFrontendPipeline',
            pipeline_name=self._get_frontend_pipeline_name(),
            github_repo_string=self.github_repo_string,
            cdk_path=cdk_path,
            connection_arn=self.connection_arn,
            source_branch=pre_prod_trigger_branch,
            encryption_key=pipeline_shared_encryption_key,
            alarm_topic=pipeline_alarm_topic,
            access_logs_bucket=self.access_logs_bucket,
            ssm_parameter=self.parameter,
            pipeline_stack_name=self.stack_name,
            environment_context=self.pipeline_environment_context,
            self_mutation=True,
            removal_policy=self.removal_policy,
        )

        self.pre_prod_frontend_stage = self._determine_frontend_stage(
            construct_id='TestFrontend',
            environment_name=TEST_ENVIRONMENT_NAME,
            environment_context=self.ssm_context['environments'][TEST_ENVIRONMENT_NAME],
        )

        self.pre_prod_frontend_pipeline.add_stage(self.pre_prod_frontend_stage)
        self.pre_prod_frontend_pipeline.build_pipeline()
        self._add_pipeline_cdk_assume_role_policy(self.pre_prod_frontend_pipeline)


class BetaFrontendPipelineStack(BaseFrontendPipelineStack):
    """Pipeline stack for the beta frontend environment."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        pipeline_shared_encryption_key: IKey,
        pipeline_alarm_topic: ITopic,
        pipeline_access_logs_bucket: IBucket,
        cdk_path: str,
        **kwargs,
    ):
        super().__init__(
            scope,
            construct_id,
            environment_name=BETA_ENVIRONMENT_NAME,
            removal_policy=RemovalPolicy.RETAIN,
            pipeline_access_logs_bucket=pipeline_access_logs_bucket,
            **kwargs,
        )

        self.beta_frontend_pipeline = FrontendPipeline(
            self,
            'BetaFrontendPipeline',
            pipeline_name=self._get_frontend_pipeline_name(),
            github_repo_string=self.github_repo_string,
            cdk_path=cdk_path,
            connection_arn=self.connection_arn,
            source_branch='main',
            encryption_key=pipeline_shared_encryption_key,
            alarm_topic=pipeline_alarm_topic,
            access_logs_bucket=self.access_logs_bucket,
            ssm_parameter=self.parameter,
            pipeline_stack_name=self.stack_name,
            environment_context=self.pipeline_environment_context,
            self_mutation=True,
            removal_policy=self.removal_policy,
        )

        self.beta_frontend_stage = self._determine_frontend_stage(
            construct_id='BetaFrontend',
            environment_name=BETA_ENVIRONMENT_NAME,
            environment_context=self.ssm_context['environments'][BETA_ENVIRONMENT_NAME],
        )

        self.beta_frontend_pipeline.add_stage(self.beta_frontend_stage)
        self.beta_frontend_pipeline.build_pipeline()
        self._add_pipeline_cdk_assume_role_policy(self.beta_frontend_pipeline)


class ProdFrontendPipelineStack(BaseFrontendPipelineStack):
    """Pipeline stack for the production frontend environment."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        pipeline_shared_encryption_key: IKey,
        pipeline_alarm_topic: ITopic,
        pipeline_access_logs_bucket: IBucket,
        cdk_path: str,
        **kwargs,
    ):
        super().__init__(
            scope,
            construct_id,
            environment_name=PROD_ENVIRONMENT_NAME,
            removal_policy=RemovalPolicy.RETAIN,
            pipeline_access_logs_bucket=pipeline_access_logs_bucket,
            **kwargs,
        )

        self.prod_frontend_pipeline = FrontendPipeline(
            self,
            'ProdFrontendPipeline',
            pipeline_name=self._get_frontend_pipeline_name(),
            github_repo_string=self.github_repo_string,
            cdk_path=cdk_path,
            connection_arn=self.connection_arn,
            source_branch='main',
            encryption_key=pipeline_shared_encryption_key,
            alarm_topic=pipeline_alarm_topic,
            access_logs_bucket=self.access_logs_bucket,
            ssm_parameter=self.parameter,
            pipeline_stack_name=self.stack_name,
            environment_context=self.pipeline_environment_context,
            self_mutation=True,
            removal_policy=self.removal_policy,
        )

        self.prod_frontend_stage = self._determine_frontend_stage(
            construct_id='ProdFrontend',
            environment_name=PROD_ENVIRONMENT_NAME,
            environment_context=self.ssm_context['environments'][PROD_ENVIRONMENT_NAME],
        )

        self.prod_frontend_pipeline.add_stage(self.prod_frontend_stage)
        self.prod_frontend_pipeline.build_pipeline()
        self._add_pipeline_cdk_assume_role_policy(self.prod_frontend_pipeline)
