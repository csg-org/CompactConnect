from __future__ import annotations

import os

import common_constructs.base_pipeline_stack
from aws_cdk import ArnFormat, Fn, RemovalPolicy, Stack
from aws_cdk.aws_codebuild import BuildSpec, CfnProject
from aws_cdk.aws_codepipeline import PipelineType
from aws_cdk.aws_codestarnotifications import NotificationRule
from aws_cdk.aws_iam import Effect, PolicyStatement, Role, ServicePrincipal
from aws_cdk.aws_kms import IKey
from aws_cdk.aws_s3 import BucketEncryption, IBucket
from aws_cdk.aws_sns import ITopic
from aws_cdk.aws_ssm import IParameter
from aws_cdk.pipelines import CodeBuildOptions, CodeBuildStep, CodePipelineSource
from aws_cdk.pipelines import CodePipeline as CdkCodePipeline
from cdk_nag import NagSuppressions
from common_constructs.base_pipeline_stack import CCPipelineType
from common_constructs.bucket import Bucket


class FrontendPipeline(CdkCodePipeline):
    """
    Stack for creating the Frontend CodePipeline resources.

    This pipeline is part of a two-pipeline architecture where:
    1. The Backend Pipeline deploys infrastructure and creates required resources
    2. This Frontend Pipeline then deploys the frontend application using those resources

    Deployment Flow:
    1. Backend Pipeline completes deployment of infrastructure resources
    2. Backend Pipeline triggers this Frontend Pipeline via AWS CLI command with specific commit ID
    3. This pipeline pulls the EXACT SAME source code revision that triggered the backend
    4. Frontend application deploys using configuration values created by the Backend Pipeline
    and stored in SSM Parameter Store
    """

    def __init__(
        self,
        scope: common_constructs.base_pipeline_stack.BasePipelineStack,
        construct_id: str,
        *,
        pipeline_name: str,
        github_repo_string: str,
        cdk_path: str,
        connection_arn: str,
        default_branch: str,
        git_tag_trigger_pattern: str,
        access_logs_bucket: IBucket,
        encryption_key: IKey,
        alarm_topic: ITopic,
        ssm_parameter: IParameter,
        pipeline_stack_name: str,
        environment_context: dict,
        removal_policy: RemovalPolicy,
        **kwargs,
    ):
        """
        Initialize the FrontendPipeline.

        :param default_branch: The git branch to use as the source for manual starts only.
                               When triggered by backend pipeline, the specific commit ID is used instead.
        :param git_tag_trigger_pattern: The git tag pattern for trigger configuration. Note: This pipeline
                                        does not automatically trigger on git events (trigger_on_push=False),
                                        but the pattern is configured for consistency with the backend pipeline.
        """
        artifact_bucket = Bucket(
            scope,
            f'{construct_id}ArtifactsBucket',
            encryption_key=encryption_key,
            encryption=BucketEncryption.KMS,
            versioned=True,
            server_access_logs_bucket=access_logs_bucket,
            removal_policy=removal_policy,
            auto_delete_objects=removal_policy == RemovalPolicy.DESTROY,
        )
        NagSuppressions.add_resource_suppressions(
            artifact_bucket,
            suppressions=[
                {
                    'id': 'HIPAA.Security-S3BucketReplicationEnabled',
                    'reason': 'These artifacts are reproduced on deploy, so the resilience from replication is not'
                    ' necessary',
                },
            ],
        )

        # Create predictable pipeline role before initializing the pipeline
        pipeline_role = scope.create_predictable_pipeline_role(CCPipelineType.FRONTEND)

        super().__init__(
            scope,
            construct_id,
            pipeline_name=pipeline_name,
            pipeline_type=PipelineType.V2,
            artifact_bucket=artifact_bucket,
            role=pipeline_role,
            use_pipeline_role_for_actions=True,
            synth=CodeBuildStep(
                'Synth',
                input=CodePipelineSource.connection(
                    repo_string=github_repo_string,
                    branch=default_branch,
                    # This pipeline is triggered by the backend pipeline, so we don't
                    # want push events to trigger it. This prevents duplicate deployments
                    # since both pipelines use the same source code.
                    trigger_on_push=False,
                    # Arn format:
                    # arn:aws:codeconnections:us-east-1:111122223333:connection/<uuid>
                    connection_arn=connection_arn,
                ),
                env={
                    'CDK_DEFAULT_ACCOUNT': environment_context['account_id'],
                    'CDK_DEFAULT_REGION': environment_context['region'],
                },
                primary_output_directory=os.path.join(cdk_path, 'cdk.out'),
                commands=[
                    f'cd {cdk_path}',
                    'npm install -g aws-cdk',
                    'python -m pip install -r requirements.txt',
                    '( cd lambdas/nodejs; yarn install --frozen-lockfile )',
                    # Only synthesize the specific pipeline stack needed
                    f'cdk synth --context pipelineStack={pipeline_stack_name} --context action=pipelineSynth',
                ],
                role=pipeline_role,
            ),
            synth_code_build_defaults=CodeBuildOptions(
                partial_build_spec=BuildSpec.from_object(
                    {
                        'phases': {
                            'install': {
                                'runtime-versions': {'python': '3.12', 'nodejs': '22.x'},
                            }
                        }
                    }
                ),
            ),
            cross_account_keys=True,
            enable_key_rotation=True,
            publish_assets_in_parallel=False,
            **kwargs,
        )
        self._ssm_parameter = ssm_parameter
        self._git_tag_trigger_pattern = git_tag_trigger_pattern
        self._github_repo_string = github_repo_string

        self._encryption_key = encryption_key
        self._alarm_topic = alarm_topic

    def build_pipeline(self) -> None:
        super().build_pipeline()

        self._ssm_parameter.grant_read(self.synth_project)

        stack = Stack.of(self)

        # Add NAG suppressions for the cross-account role's default policy
        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            f'{stack.node.path}/FrontendCrossAccountRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': (
                        'Pipeline role requires wildcard permissions for CodePipeline service operations '
                        'including S3 artifact access and cross-account role assumptions.'
                    ),
                },
            ],
        )

        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            self.node.path,
            suppressions=[
                {
                    'id': 'HIPAA.Security-CodeBuildProjectSourceRepoUrl',
                    'reason': 'This resource uses a secure integration by virtue of the CodeStar connection',
                },
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The wildcarded actions and resources are still scoped to the specific actions, bucket,'
                    ' key, and codebuild resources it specifically needs access to.',
                },
            ],
            apply_to_children=True,
        )

        self._add_alarms()
        self._add_codebuild_pipeline_role_override()
        self._configure_git_tag_trigger()

    def _add_alarms(self):
        NotificationRule(
            self,
            'NotificationRule',
            source=self.pipeline,
            events=[
                'codepipeline-pipeline-pipeline-execution-started',
                'codepipeline-pipeline-pipeline-execution-failed',
                'codepipeline-pipeline-pipeline-execution-succeeded',
                'codepipeline-pipeline-manual-approval-needed',
            ],
            targets=[self._alarm_topic],
        )

        # Grant CodeStar permission to use the key that encrypts the alarm topic
        code_star_principal = ServicePrincipal('codestar-notifications.amazonaws.com')
        self._encryption_key.grant_encrypt_decrypt(code_star_principal)

    def _add_codebuild_pipeline_role_override(self):
        """
        CodePipeline does not support automatically using the pipeline role for the CodeBuild steps it generates.
        To allow the Assets step to assume roles into the environment accounts, we need to force it to use the
        CodePipeline role for the Assets step.

        This is done by overriding the CodeBuild role with the pipeline role for the Assets step.
        """
        assets_node = self.node.try_find_child('Assets')
        # The pipeline won't _always_ build an Assets step (like for the substitution stack), so we need to handle
        # it not existing
        if assets_node is not None:
            # Override the role used
            stack = Stack.of(self)
            pipeline_role: Role = self.pipeline.role
            file_asset_node: CfnProject = assets_node.node.try_find_child('FileAsset').node.default_child
            file_asset_node.add_property_override('ServiceRole', pipeline_role.role_arn)

            # Add the permissions this role will need for the Assets step
            # Note: many of the permissions needed for this step are already granted by virtue of being
            # passed into the Synth CodeBuildStep, which automatically configures it with permissions.
            # We don't duplicate those here.
            pipeline_role.add_to_principal_policy(
                PolicyStatement(
                    effect=Effect.ALLOW,
                    actions=[
                        'logs:CreateLogGroup',
                        'logs:CreateLogStream',
                        'logs:PutLogEvents',
                    ],
                    resources=[
                        stack.format_arn(
                            partition=stack.partition,
                            service='logs',
                            region=stack.region,
                            account=stack.account,
                            resource='log-group',
                            resource_name=Fn.join(
                                '', ['/aws/codebuild/', Fn.ref(stack.get_logical_id(file_asset_node)), ':*']
                            ),
                            arn_format=ArnFormat.COLON_RESOURCE_NAME,
                        ),
                    ],
                )
            )
            pipeline_role.add_to_principal_policy(
                PolicyStatement(
                    effect=Effect.ALLOW,
                    actions=[
                        'sts:AssumeRole',
                    ],
                    resources=[
                        stack.format_arn(
                            partition=stack.partition,
                            service='iam',
                            region='',
                            account='*',
                            resource='role',
                            resource_name=f'cdk-hnb659fds-file-publishing-role-*-{stack.region}',
                        ),
                    ],
                )
            )
            pipeline_role.add_to_principal_policy(
                PolicyStatement(
                    effect=Effect.ALLOW,
                    actions=[
                        'codebuild:BatchPutCodeCoverages',
                        'codebuild:BatchPutTestCases',
                        'codebuild:CreateReport',
                        'codebuild:CreateReportGroup',
                        'codebuild:UpdateReport',
                    ],
                    resources=[
                        Fn.join(
                            '',
                            [
                                stack.format_arn(
                                    partition=stack.partition,
                                    service='codebuild',
                                    region=stack.region,
                                    account=stack.account,
                                    resource='report-group',
                                    resource_name='',
                                ),
                                Fn.ref(stack.get_logical_id(file_asset_node)),
                                '-*',
                            ],
                        ),
                    ],
                )
            )

            # Now, remove the unused role and default policy
            assets_node.node.try_remove_child('FileRole')

    def _configure_git_tag_trigger(self):
        """
        Configure git tag-based trigger using CDK escape hatch.

        When triggers with filters are configured, AWS requires DetectChanges to be false
        in the source action configuration. The trigger configuration replaces the default
        change detection mechanism.

        The source action's branch (default_branch) is still used when the pipeline is
        started manually, but automatic triggers are controlled by the git tag pattern.
        """
        cfn_pipeline = self.pipeline.node.default_child

        # Add the Triggers property
        cfn_pipeline.add_property_override('Triggers', [
            {
                'ProviderType': 'CodeStarSourceConnection',
                'GitConfiguration': {
                    'SourceActionName': self._github_repo_string.replace('/', '_'),
                    'Push': [
                        {
                            'Tags': {
                                'Includes': [self._git_tag_trigger_pattern]
                            }
                        }
                    ]
                }
            }
        ])

        # Set DetectChanges to false in the source action
        # The source action is in Stages[0].Actions[0] (first action of Source stage)
        # This functionally overrides the corresponding `trigger_on_push=True` setting in the
        # CodePipelineSource.connection() call.
        cfn_pipeline.add_property_override(
            'Stages.0.Actions.0.Configuration.DetectChanges',
            False
        )
