from aws_cdk import Environment, RemovalPolicy
from aws_cdk.aws_iam import Effect, PolicyDocument, PolicyStatement, Role, ServicePrincipal
from aws_cdk.aws_kms import IKey
from aws_cdk.aws_s3 import IBucket
from aws_cdk.aws_sns import ITopic
from aws_cdk.pipelines import CodeBuildStep
from cdk_nag import NagSuppressions
from common_constructs.base_pipeline_stack import (
    ALLOWED_ENVIRONMENT_NAMES,
    BETA_ENVIRONMENT_NAME,
    PROD_ENVIRONMENT_NAME,
    TEST_ENVIRONMENT_NAME,
    BasePipelineStack,
    CCPipelineType,
)
from constructs import Construct

from pipeline.backend_pipeline import BackendPipeline
from pipeline.backend_stage import BackendStage
from pipeline.synth_substitute_stage import SynthSubstituteStage

# Action constants
ACTION_CONTEXT_KEY = 'action'
PIPELINE_STACK_CONTEXT_KEY = 'pipelineStack'
PIPELINE_SYNTH_ACTION = 'pipelineSynth'
BOOTSTRAP_DEPLOY_ACTION = 'bootstrapDeploy'


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
            pipeline_type=CCPipelineType.BACKEND,
            removal_policy=removal_policy,
            pipeline_access_logs_bucket=pipeline_access_logs_bucket,
            **kwargs,
        )

    def _get_backend_pipeline_name(self):
        if self.environment_name not in ALLOWED_ENVIRONMENT_NAMES:
            raise ValueError(f'Environment name must be one of {ALLOWED_ENVIRONMENT_NAMES}')

        return f'{self.environment_name}-compactConnect-backendPipeline'

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
            commands=[
                # Trigger frontend pipeline with the same commit ID
                f'aws codepipeline start-pipeline-execution --name {self._get_frontend_pipeline_name()} '
                f'--source-revisions actionName={self.github_repo_string.replace("/", "_")}'
                ',revisionType=COMMIT_ID,revisionValue=$CODEBUILD_RESOLVED_SOURCE_VERSION'
            ],
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

        default_branch = self.pipeline_environment_context['default_branch']
        git_tag_trigger_pattern = self.pipeline_environment_context['git_tag_trigger_pattern']

        self.pre_prod_pipeline = BackendPipeline(
            self,
            'TestBackendPipeline',
            pipeline_name=self._get_backend_pipeline_name(),
            github_repo_string=self.github_repo_string,
            cdk_path=cdk_path,
            connection_arn=self.connection_arn,
            default_branch=default_branch,
            git_tag_trigger_pattern=git_tag_trigger_pattern,
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
        # trigger_frontend_pipeline_step = self._generate_frontend_pipeline_trigger_step()
        self.pre_prod_pipeline.add_stage(self.test_stage)  # , post=[trigger_frontend_pipeline_step])
        self.pre_prod_pipeline.build_pipeline()
        self._add_pipeline_cdk_assume_role_policy(self.pre_prod_pipeline)
        # the following must be called after the pipeline is built
        # self._add_nag_suppressions_for_trigger_pipeline_step_role(trigger_frontend_pipeline_step)


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

        default_branch = self.pipeline_environment_context['default_branch']
        git_tag_trigger_pattern = self.pipeline_environment_context['git_tag_trigger_pattern']

        self.beta_backend_pipeline = BackendPipeline(
            self,
            'BetaBackendPipeline',
            pipeline_name=self._get_backend_pipeline_name(),
            github_repo_string=self.github_repo_string,
            cdk_path=cdk_path,
            connection_arn=self.connection_arn,
            default_branch=default_branch,
            git_tag_trigger_pattern=git_tag_trigger_pattern,
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
        # trigger_frontend_pipeline_step = self._generate_frontend_pipeline_trigger_step()
        self.beta_backend_pipeline.add_stage(self.beta_backend_stage)  # , post=[trigger_frontend_pipeline_step])
        self.beta_backend_pipeline.build_pipeline()
        # the following must be called after the pipeline is built
        self._add_pipeline_cdk_assume_role_policy(self.beta_backend_pipeline)
        # self._add_nag_suppressions_for_trigger_pipeline_step_role(trigger_frontend_pipeline_step)


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

        if not self.backup_config or not self.ssm_context['environments'][PROD_ENVIRONMENT_NAME].get('backup_enabled'):
            raise ValueError('Backups must be enabled for production environment.')

        default_branch = self.pipeline_environment_context['default_branch']
        git_tag_trigger_pattern = self.pipeline_environment_context['git_tag_trigger_pattern']

        self.prod_pipeline = BackendPipeline(
            self,
            'ProdBackendPipeline',
            pipeline_name=self._get_backend_pipeline_name(),
            github_repo_string=self.github_repo_string,
            cdk_path=cdk_path,
            connection_arn=self.connection_arn,
            default_branch=default_branch,
            git_tag_trigger_pattern=git_tag_trigger_pattern,
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
        # trigger_frontend_pipeline_step = self._generate_frontend_pipeline_trigger_step()
        self.prod_pipeline.add_stage(self.prod_stage)  #, post=[trigger_frontend_pipeline_step])
        self.prod_pipeline.build_pipeline()
        # the following must be called after the pipeline is built
        self._add_pipeline_cdk_assume_role_policy(self.prod_pipeline)
        # self._add_nag_suppressions_for_trigger_pipeline_step_role(trigger_frontend_pipeline_step)
