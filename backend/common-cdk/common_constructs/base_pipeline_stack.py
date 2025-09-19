import json

from aws_cdk import Environment, RemovalPolicy
from aws_cdk.aws_iam import Effect, PolicyStatement, Role, ServicePrincipal
from aws_cdk.aws_s3 import IBucket
from aws_cdk.aws_ssm import StringParameter
from aws_cdk.pipelines import CodePipeline as CdkCodePipeline
from constructs import Construct

from common_constructs.stack import Stack

TEST_ENVIRONMENT_NAME = 'test'
BETA_ENVIRONMENT_NAME = 'beta'
PROD_ENVIRONMENT_NAME = 'prod'
ALLOWED_ENVIRONMENT_NAMES = [TEST_ENVIRONMENT_NAME, BETA_ENVIRONMENT_NAME, PROD_ENVIRONMENT_NAME]

class BasePipelineStack(Stack):
    """Base stack with common functionality for all pipeline stacks (both backend and frontend)."""

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
        super().__init__(scope, construct_id, environment_name='pipeline', env=env, **kwargs)

        self.env = env
        self.environment_name = environment_name
        self.removal_policy = removal_policy
        self.access_logs_bucket = pipeline_access_logs_bucket

        pipeline_context_parameter_name = f'{self.environment_name}-compact-connect-context'

        # Fetch ssm_context if not provided locally
        self.parameter = StringParameter.from_string_parameter_name(
            self,
            'PipelineContext',
            string_parameter_name=pipeline_context_parameter_name,
        )
        value = StringParameter.value_from_lookup(self, self.parameter.parameter_name)
        # When CDK runs for the first time, it synthesizes fully without actually retrieving the SSM Parameter
        # value. It, instead, populates parameters and other look-ups with dummy values, synthesizes, collects all
        # the look-ups together, populates them for real, then re-synthesizes with real values.
        # To accommodate this pattern, we have to replace this dummy value with one that will actually
        # let CDK complete its first round of synthesis, so that it can get to its second, real, synthesis.
        if value != f'dummy-value-for-{pipeline_context_parameter_name}':
            self.ssm_context = json.loads(value)
        else:
            with open(f'cdk.context.{environment_name}-example.json') as f:
                self.ssm_context = json.load(f)['ssm_context']

        self.pipeline_environment_context = self.ssm_context['environments']['pipeline']
        self.connection_arn = self.pipeline_environment_context['connection_arn']
        self.github_repo_string = self.ssm_context['github_repo_string']
        self.backup_config = self.ssm_context.get('backup_config', {})
        self.app_name = self.ssm_context['app_name']

    def _get_predictable_role_name(self, pipeline_type: str, role_type: str) -> str:
        """Generate predictable role name for bootstrap template integration.

        :param pipeline_type: 'Backend' or 'Frontend'
        :param role_type: 'Synth', 'SelfMutation', 'AssetPublishing', 'Deploy'
        :return: Predictable role name following pattern: CompactConnect-{env}-{pipeline}-{role}Role
        """
        if self.environment_name not in ALLOWED_ENVIRONMENT_NAMES:
            raise ValueError(f'Environment name must be one of {ALLOWED_ENVIRONMENT_NAMES}')

        return f'CompactConnect-{self.environment_name}-{pipeline_type}-{role_type}Role'

    def create_predictable_pipeline_role(self, pipeline_type: str) -> Role:
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
            assumed_by=ServicePrincipal('codepipeline.amazonaws.com'),
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

    def _get_frontend_pipeline_name(self):
        if self.environment_name not in ALLOWED_ENVIRONMENT_NAMES:
            raise ValueError(f'Environment name must be one of {ALLOWED_ENVIRONMENT_NAMES}')

        return f'{self.environment_name}-compactConnect-frontendPipeline'

    def _get_frontend_pipeline_arn(self):
        pipeline_name = self._get_frontend_pipeline_name()

        return self.format_arn(
            partition=self.partition,
            service='codepipeline',
            region=self.env.region,
            account=self.env.account,
            resource=pipeline_name,
        )


DEPLOY_ENVIRONMENT_NAME = 'deploy'
