from enum import StrEnum

from aws_cdk import Environment, RemovalPolicy
from aws_cdk.aws_iam import CompositePrincipal, Effect, PolicyStatement, Role, ServicePrincipal
from aws_cdk.aws_s3 import IBucket
from aws_cdk.pipelines import CodePipeline as CdkCodePipeline
from constructs import Construct

from common_constructs.ssm_context import SSMContext
from common_constructs.stack import Stack

TEST_ENVIRONMENT_NAME = 'test'
BETA_ENVIRONMENT_NAME = 'beta'
PROD_ENVIRONMENT_NAME = 'prod'
DEPLOY_ENVIRONMENT_NAME = 'deploy'

ALLOWED_ENVIRONMENT_NAMES = [TEST_ENVIRONMENT_NAME, BETA_ENVIRONMENT_NAME, PROD_ENVIRONMENT_NAME]


class CCPipelineType(StrEnum):
    BACKEND = 'Backend'
    FRONTEND = 'Frontend'
    COSMETOLOGY = 'Cosmetology'


class BasePipelineStack(Stack):
    """Base stack with common functionality for all pipeline stacks."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        environment_name: str,
        env: Environment,
        pipeline_context_parameter_name: str,
        removal_policy: RemovalPolicy,
        pipeline_access_logs_bucket: IBucket,
        **kwargs,
    ):
        super().__init__(scope, construct_id, environment_name='pipeline', env=env, **kwargs)

        # Note: self.env is already set by the parent Stack.__init__() call above
        # In newer CDK versions, env is read-only after construction, so we don't reassign it
        self.environment_name = environment_name
        self.removal_policy = removal_policy
        self.access_logs_bucket = pipeline_access_logs_bucket

        ssm_context = SSMContext(
            self,
            'PipelineContext',
            pipeline_context_parameter_name,
            f'cdk.context.{environment_name}-example.json',
        )
        self.parameter = ssm_context.parameter
        self.ssm_context = ssm_context.context

        self.pipeline_environment_context = self.ssm_context['environments']['pipeline']
        self.connection_arn = self.pipeline_environment_context['connection_arn']
        self.github_repo_string = self.ssm_context['github_repo_string']
        self.backup_config = self.ssm_context.get('backup_config', {})
        self.app_name = self.ssm_context['app_name']

    def create_predictable_pipeline_role(self, pipeline_type: CCPipelineType) -> Role:
        """Create a predictable cross-account role that will be trusted by bootstrap roles.

        :param pipeline_type: 'Backend' or 'Frontend'
        :return: The cross-account role with predictable name for bootstrap trust policies
        """
        # Create environment and pipeline-type specific cross-account roles
        cross_account_role_name = f'CompactConnect-{self.environment_name}-{pipeline_type}-CrossAccountRole'

        return Role(
            self,
            f'{pipeline_type}CrossAccountRole',
            role_name=cross_account_role_name,
            assumed_by=CompositePrincipal(
                ServicePrincipal('codepipeline.amazonaws.com'),
                ServicePrincipal('codebuild.amazonaws.com'),
            ),
            description=f'Cross-account role for {self.environment_name} {pipeline_type.lower()}'
            'pipeline bootstrap trust policies',
        )

    def _add_pipeline_cdk_assume_role_policy(self, pipeline: CdkCodePipeline):
        pipeline.synth_project.add_to_role_policy(
            PolicyStatement(
                effect=Effect.ALLOW,
                actions=['sts:AssumeRole'],
                resources=[
                    self.format_arn(
                        partition=self.partition,
                        service='iam',
                        region='',
                        account='*',
                        resource='role',
                        resource_name='cdk-hnb659fds-lookup-role-*',
                    ),
                ],
            ),
        )
