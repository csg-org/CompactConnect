import json

from aws_cdk import RemovalPolicy
from aws_cdk.aws_iam import Effect, PolicyStatement
from aws_cdk.aws_kms import IKey, Key
from aws_cdk.aws_sns import ITopic
from aws_cdk.aws_ssm import StringParameter
from common_constructs.access_logs_bucket import AccessLogsBucket
from common_constructs.alarm_topic import AlarmTopic
from common_constructs.stack import Stack
from constructs import Construct

from pipeline.backend_pipeline import BackendPipeline
from pipeline.backend_stage import BackendStage

TEST_ENVIRONMENT_NAME = 'test'
BETA_ENVIRONMENT_NAME = 'beta'
PROD_ENVIRONMENT_NAME = 'prod'

DEPLOY_ENVIRONMENT_NAME = 'deploy'


class DeploymentResourcesStack(Stack):
    """Stack that manages all shared resources for all pipeline stacks."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        **kwargs,
    ):
        super().__init__(scope, construct_id, environment_name='deploy', **kwargs)

        pipeline_context_parameter_name = f'{DEPLOY_ENVIRONMENT_NAME}-compact-connect-context'

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
            with open(f'cdk.context.{DEPLOY_ENVIRONMENT_NAME}-example.json') as f:
                self.ssm_context = json.load(f)['ssm_context']

        self.deploy_environment_context = self.ssm_context['environments'][DEPLOY_ENVIRONMENT_NAME]

        self.pipeline_shared_encryption_key = Key(
            self,
            'PipelineSharedEncryptionKey',
            enable_key_rotation=True,
            alias='pipeline-shared-encryption-key',
            removal_policy=RemovalPolicy.RETAIN,
        )

        notifications = self.deploy_environment_context.get('notifications', {})
        self.pipeline_alarm_topic = AlarmTopic(
            self,
            'AlarmTopic',
            master_key=self.pipeline_shared_encryption_key,
            email_subscriptions=notifications.get('email', []),
            slack_subscriptions=notifications.get('slack', []),
        )


class BasePipelineStack(Stack):
    """Base stack with shared resources for all pipeline stacks."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        environment_name: str,
        removal_policy: RemovalPolicy,
        **kwargs,
    ):
        super().__init__(scope, construct_id, environment_name='pipeline', **kwargs)

        pipeline_context_parameter_name = f'{environment_name}-compact-connect-context'

        self.removal_policy = removal_policy

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
        self.app_name = self.ssm_context['app_name']

        self.access_logs_bucket = AccessLogsBucket(
            self,
            'AccessLogsBucket',
            removal_policy=self.removal_policy,
            auto_delete_objects=self.removal_policy == RemovalPolicy.DESTROY,
        )


class TestPipelineStack(BasePipelineStack):
    """Pipeline stack for the test environment, triggered by the development branch."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        pipeline_shared_encryption_key: IKey,
        pipeline_alarm_topic: ITopic,
        cdk_path: str,
        **kwargs,
    ):
        super().__init__(
            scope,
            construct_id,
            environment_name=TEST_ENVIRONMENT_NAME,
            removal_policy=RemovalPolicy.DESTROY,
            **kwargs,
        )

        # Allows us to override the default branching scheme for the test environment, via context variable
        pre_prod_trigger_branch = self.pipeline_environment_context.get('pre_prod_trigger_branch', 'development')

        self.pre_prod_pipeline = BackendPipeline(
            self,
            'PreProdPipeline',
            github_repo_string=self.github_repo_string,
            cdk_path=cdk_path,
            connection_arn=self.connection_arn,
            trigger_branch=pre_prod_trigger_branch,
            encryption_key=pipeline_shared_encryption_key,
            alarm_topic=pipeline_alarm_topic,
            access_logs_bucket=self.access_logs_bucket,
            ssm_parameter=self.parameter,
            environment_context=self.pipeline_environment_context,
            self_mutation=True,
            removal_policy=self.removal_policy,
        )

        self.test_stage = BackendStage(
            self,
            'Test',
            app_name=self.app_name,
            environment_name=TEST_ENVIRONMENT_NAME,
            environment_context=self.ssm_context['environments'][TEST_ENVIRONMENT_NAME],
            github_repo_string=self.github_repo_string,
        )

        self.pre_prod_pipeline.add_stage(self.test_stage)
        self.pre_prod_pipeline.build_pipeline()
        self.pre_prod_pipeline.synth_project.add_to_role_policy(
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


class BetaPipelineStack(BasePipelineStack):
    """Pipeline stack for the beta environment, triggered by the main branch."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        pipeline_shared_encryption_key: IKey,
        pipeline_alarm_topic: ITopic,
        cdk_path: str,
        **kwargs,
    ):
        super().__init__(
            scope, construct_id, environment_name=BETA_ENVIRONMENT_NAME, removal_policy=RemovalPolicy.RETAIN, **kwargs
        )

        self.beta_pipeline = BackendPipeline(
            self,
            'BetaPipeline',
            github_repo_string=self.github_repo_string,
            cdk_path=cdk_path,
            connection_arn=self.connection_arn,
            trigger_branch='main',
            encryption_key=pipeline_shared_encryption_key,
            alarm_topic=pipeline_alarm_topic,
            access_logs_bucket=self.access_logs_bucket,
            ssm_parameter=self.parameter,
            environment_context=self.pipeline_environment_context,
            self_mutation=True,
            removal_policy=self.removal_policy,
        )

        self.beta_stage = BackendStage(
            self,
            'Beta',
            app_name=self.app_name,
            environment_name=BETA_ENVIRONMENT_NAME,
            environment_context=self.ssm_context['environments'][BETA_ENVIRONMENT_NAME],
            github_repo_string=self.github_repo_string,
        )

        self.beta_pipeline.add_stage(self.beta_stage)
        self.beta_pipeline.build_pipeline()
        self.beta_pipeline.synth_project.add_to_role_policy(
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


class ProdPipelineStack(BasePipelineStack):
    """Pipeline stack for the production environment, triggered by the main branch."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        pipeline_shared_encryption_key: IKey,
        pipeline_alarm_topic: ITopic,
        cdk_path: str,
        **kwargs,
    ):
        super().__init__(
            scope, construct_id, environment_name=PROD_ENVIRONMENT_NAME, removal_policy=RemovalPolicy.RETAIN, **kwargs
        )

        self.prod_pipeline = BackendPipeline(
            self,
            'ProdPipeline',
            github_repo_string=self.github_repo_string,
            cdk_path=cdk_path,
            connection_arn=self.connection_arn,
            trigger_branch='main',
            encryption_key=pipeline_shared_encryption_key,
            alarm_topic=pipeline_alarm_topic,
            access_logs_bucket=self.access_logs_bucket,
            ssm_parameter=self.parameter,
            environment_context=self.pipeline_environment_context,
            self_mutation=True,
            removal_policy=self.removal_policy,
        )

        self.prod_stage = BackendStage(
            self,
            'Prod',
            app_name=self.app_name,
            environment_name=PROD_ENVIRONMENT_NAME,
            environment_context=self.ssm_context['environments'][PROD_ENVIRONMENT_NAME],
            github_repo_string=self.github_repo_string,
        )

        self.prod_pipeline.add_stage(self.prod_stage)
        self.prod_pipeline.build_pipeline()
        self.prod_pipeline.synth_project.add_to_role_policy(
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
