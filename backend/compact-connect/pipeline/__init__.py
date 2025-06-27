import json

from aws_cdk import Environment, RemovalPolicy
from aws_cdk.aws_iam import Effect, PolicyDocument, PolicyStatement, Role, ServicePrincipal
from aws_cdk.aws_kms import IKey, Key
from aws_cdk.aws_s3 import IBucket
from aws_cdk.aws_sns import ITopic
from aws_cdk.aws_ssm import StringParameter
from aws_cdk.pipelines import CodeBuildStep
from aws_cdk.pipelines import CodePipeline as CdkCodePipeline
from cdk_nag import NagSuppressions
from common_constructs.access_logs_bucket import AccessLogsBucket
from common_constructs.alarm_topic import AlarmTopic
from common_constructs.stack import Stack
from constructs import Construct

from pipeline.backend_pipeline import BackendPipeline
from pipeline.backend_stage import BackendStage
from pipeline.frontend_pipeline import FrontendPipeline
from pipeline.frontend_stage import FrontendStage
from pipeline.synth_substitute_stage import SynthSubstituteStage

TEST_ENVIRONMENT_NAME = 'test'
BETA_ENVIRONMENT_NAME = 'beta'
PROD_ENVIRONMENT_NAME = 'prod'

ALLOWED_ENVIRONMENT_NAMES = [TEST_ENVIRONMENT_NAME, BETA_ENVIRONMENT_NAME, PROD_ENVIRONMENT_NAME]

DEPLOY_ENVIRONMENT_NAME = 'deploy'

# Action constants
ACTION_CONTEXT_KEY = 'action'
PIPELINE_STACK_CONTEXT_KEY = 'pipelineStack'
PIPELINE_SYNTH_ACTION = 'pipelineSynth'
BOOTSTRAP_DEPLOY_ACTION = 'bootstrapDeploy'


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

        self.pipeline_access_logs_bucket = AccessLogsBucket(
            self,
            'AccessLogsBucket',
            removal_policy=RemovalPolicy.RETAIN,
            auto_delete_objects=False,
        )

        NagSuppressions.add_resource_suppressions_by_path(
            self,
            f'{self.pipeline_access_logs_bucket.node.path}/Resource',
            suppressions=[
                {
                    'id': 'HIPAA.Security-S3BucketLoggingEnabled',
                    'reason': 'This is the access logging bucket.',
                },
            ],
        )


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
        self.backup_config = self.ssm_context['backup_config']
        self.app_name = self.ssm_context['app_name']

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

    def _get_backend_pipeline_name(self):
        if self.environment_name not in ALLOWED_ENVIRONMENT_NAMES:
            raise ValueError(f'Environment name must be one of {ALLOWED_ENVIRONMENT_NAMES}')

        return f'{self.environment_name}-compactConnect-backendPipeline'

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


class BaseBackendPipelineStack(BasePipelineStack):
    """
    Base class for backend pipeline stacks.
    Implements common functionality for all backend pipeline stacks.
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
            removal_policy=removal_policy,
            pipeline_access_logs_bucket=pipeline_access_logs_bucket,
            **kwargs,
        )

    def _determine_backend_stage(self, construct_id, app_name, environment_name, environment_context):
        """
        Return either a real BackendStage or a SynthSubstituteStage depending on pipeline synthesis context.

        This method centralizes the stage creation logic to conditionally create a lightweight substitute
        stage during pipeline synthesis when the stage is not part of the pipeline being deployed.
        """
        # Check if we're in pipeline synthesis mode and if we're synthesizing this specific pipeline
        action = self.node.try_get_context('action')
        pipeline_stack_name = self.node.try_get_context('pipelineStack')

        # If we're in pipeline synthesis mode and this is not the pipeline being synthesized,
        # use a lightweight substitute stage. Likewise, during a bootstrap deployment of the pipeline, we don't need
        # to synth the application stack resources, since that will be performed when the pipeline self-mutates on the
        # first deployment.
        if (
            action == PIPELINE_SYNTH_ACTION and pipeline_stack_name != self.stack_name
        ) or action == BOOTSTRAP_DEPLOY_ACTION:
            return SynthSubstituteStage(
                self,
                'SubstituteBackendStage',
                environment_context=environment_context,
            )

        # Otherwise, use the real stage for deployment
        return BackendStage(
            self,
            construct_id,
            app_name=app_name,
            environment_name=environment_name,
            environment_context=environment_context,
            backup_config=self.backup_config,
        )

    def _generate_frontend_pipeline_trigger_step(self):
        """
        Creates a CodeBuild step that triggers the frontend pipeline after backend deployment completes.

        This is a critical part of the deployment orchestration:
        1. The backend pipeline creates necessary infrastructure
        2. This step executes after successful backend deployment
        3. It uses AWS CLI to trigger the frontend pipeline
        4. The frontend pipeline then deploys UI components that depend on backend resources

        The step uses a dedicated IAM role with permission to start the frontend pipeline execution.
        Pipeline names are determined through convention rather than direct CDK references to
        avoid circular dependencies during synthesis.
        """
        # create a role with the needed permission to trigger the frontend pipeline
        trigger_frontend_pipeline_role = Role(
            self,
            'TriggerFrontendPipelineRole',
            assumed_by=ServicePrincipal('codebuild.amazonaws.com'),
            inline_policies={
                'TriggerFrontendPipelinePolicy': PolicyDocument(
                    statements=[
                        PolicyStatement(
                            effect=Effect.ALLOW,
                            actions=['codepipeline:StartPipelineExecution'],
                            resources=[self._get_frontend_pipeline_arn()],
                        )
                    ]
                )
            },
        )
        return CodeBuildStep(
            'TriggerFrontendPipeline',
            commands=[f'aws codepipeline start-pipeline-execution --name {self._get_frontend_pipeline_name()}'],
            role=trigger_frontend_pipeline_role,
        )

    def _add_nag_suppressions_for_trigger_pipeline_step_role(self, trigger_pipeline_step: CodeBuildStep):
        """
        This method must be called after the pipeline is built, else it results in an error as the role does
        not exist until then.
        """
        # add cdk nag suppressions for the role
        NagSuppressions.add_resource_suppressions_by_path(
            self,
            f'{trigger_pipeline_step.role.node.path}/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': """This policy contains wild-carded actions set by CDK to access the needed artifacts and
                                      pipeline resources as part of deployment.
                                      """,
                },
            ],
        )


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


class TestBackendPipelineStack(BaseBackendPipelineStack):
    """Pipeline stack for the test backend environment, triggered by the development branch."""

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

        self.pre_prod_pipeline = BackendPipeline(
            self,
            'TestBackendPipeline',
            pipeline_name=self._get_backend_pipeline_name(),
            github_repo_string=self.github_repo_string,
            cdk_path=cdk_path,
            connection_arn=self.connection_arn,
            trigger_branch=pre_prod_trigger_branch,
            encryption_key=pipeline_shared_encryption_key,
            alarm_topic=pipeline_alarm_topic,
            access_logs_bucket=self.access_logs_bucket,
            ssm_parameter=self.parameter,
            pipeline_stack_name=self.stack_name,
            environment_context=self.pipeline_environment_context,
            self_mutation=True,
            removal_policy=self.removal_policy,
        )

        self.test_stage = self._determine_backend_stage(
            # NOTE: it is critical that the construct_id stays the same, as all the underlying stacks
            # are named based on this construct_id
            construct_id='Test',
            app_name=self.app_name,
            environment_name=TEST_ENVIRONMENT_NAME,
            environment_context=self.ssm_context['environments'][TEST_ENVIRONMENT_NAME],
        )

        # Add a post step to trigger the frontend pipeline
        trigger_frontend_pipeline_step = self._generate_frontend_pipeline_trigger_step()
        self.pre_prod_pipeline.add_stage(self.test_stage, post=[trigger_frontend_pipeline_step])
        self.pre_prod_pipeline.build_pipeline()
        self._add_pipeline_cdk_assume_role_policy(self.pre_prod_pipeline)
        # the following must be called after the pipeline is built
        self._add_nag_suppressions_for_trigger_pipeline_step_role(trigger_frontend_pipeline_step)


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


class BetaBackendPipelineStack(BaseBackendPipelineStack):
    """Pipeline stack for the beta backend environment, triggered by the main branch."""

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

        self.beta_backend_pipeline = BackendPipeline(
            self,
            'BetaBackendPipeline',
            pipeline_name=self._get_backend_pipeline_name(),
            github_repo_string=self.github_repo_string,
            cdk_path=cdk_path,
            connection_arn=self.connection_arn,
            trigger_branch='main',
            encryption_key=pipeline_shared_encryption_key,
            alarm_topic=pipeline_alarm_topic,
            access_logs_bucket=self.access_logs_bucket,
            ssm_parameter=self.parameter,
            pipeline_stack_name=self.stack_name,
            environment_context=self.pipeline_environment_context,
            self_mutation=True,
            removal_policy=self.removal_policy,
        )

        self.beta_backend_stage = self._determine_backend_stage(
            # NOTE: it is critical that the construct_id stays the same, as all the underlying stacks
            # are named based on this construct_id
            construct_id='Beta',
            app_name=self.app_name,
            environment_name=BETA_ENVIRONMENT_NAME,
            environment_context=self.ssm_context['environments'][BETA_ENVIRONMENT_NAME],
        )

        # Add a post step to trigger the frontend pipeline
        trigger_frontend_pipeline_step = self._generate_frontend_pipeline_trigger_step()
        self.beta_backend_pipeline.add_stage(self.beta_backend_stage, post=[trigger_frontend_pipeline_step])
        self.beta_backend_pipeline.build_pipeline()
        # the following must be called after the pipeline is built
        self._add_pipeline_cdk_assume_role_policy(self.beta_backend_pipeline)
        self._add_nag_suppressions_for_trigger_pipeline_step_role(trigger_frontend_pipeline_step)


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


class ProdBackendPipelineStack(BaseBackendPipelineStack):
    """Pipeline stack for the production backend environment, triggered by the main branch."""

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

        self.prod_pipeline = BackendPipeline(
            self,
            'ProdBackendPipeline',
            pipeline_name=self._get_backend_pipeline_name(),
            github_repo_string=self.github_repo_string,
            cdk_path=cdk_path,
            connection_arn=self.connection_arn,
            trigger_branch='main',
            encryption_key=pipeline_shared_encryption_key,
            alarm_topic=pipeline_alarm_topic,
            access_logs_bucket=self.access_logs_bucket,
            ssm_parameter=self.parameter,
            pipeline_stack_name=self.stack_name,
            environment_context=self.pipeline_environment_context,
            self_mutation=True,
            removal_policy=self.removal_policy,
        )

        self.prod_stage = self._determine_backend_stage(
            # NOTE: it is critical that the construct_id stays the same, as all the underlying stacks
            # are named based on this construct_id
            construct_id='Prod',
            app_name=self.app_name,
            environment_name=PROD_ENVIRONMENT_NAME,
            environment_context=self.ssm_context['environments'][PROD_ENVIRONMENT_NAME],
        )

        # Add a post step to trigger the frontend pipeline
        trigger_frontend_pipeline_step = self._generate_frontend_pipeline_trigger_step()
        self.prod_pipeline.add_stage(self.prod_stage, post=[trigger_frontend_pipeline_step])
        self.prod_pipeline.build_pipeline()
        # the following must be called after the pipeline is built
        self._add_pipeline_cdk_assume_role_policy(self.prod_pipeline)
        self._add_nag_suppressions_for_trigger_pipeline_step_role(trigger_frontend_pipeline_step)


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
