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


class BackendPipeline(CdkCodePipeline):
    """
    Stack for creating the Backend CodePipeline resources.

    This pipeline is part of a two-pipeline architecture where:
    1. This Backend Pipeline deploys infrastructure and creates required resources
    2. The Frontend Pipeline then deploys the frontend application using those resources

    Deployment Flow:
    - IS triggered by GitHub pushes (trigger_on_push=True)
    - Triggers the Frontend Pipeline after successful deployment
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
        trigger_branch: str,
        access_logs_bucket: IBucket,
        encryption_key: IKey,
        alarm_topic: ITopic,
        ssm_parameter: IParameter,
        pipeline_stack_name: str,
        environment_context: dict,
        removal_policy: RemovalPolicy,
        **kwargs,
    ):
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
        pipeline_role = scope.create_predictable_pipeline_role(CCPipelineType.BACKEND)
        artifact_bucket.grant_read(pipeline_role)

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
                    branch=trigger_branch,
                    trigger_on_push=True,
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
                                'runtime-versions': {'python': '3.13', 'nodejs': '22.x'},
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

        self._encryption_key = encryption_key
        self._alarm_topic = alarm_topic

    def build_pipeline(self) -> None:
        super().build_pipeline()

        self._ssm_parameter.grant_read(self.synth_project)

        stack = Stack.of(self)

        # Add NAG suppressions for the cross-account role's default policy
        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            f'{stack.node.path}/BackendCrossAccountRole/DefaultPolicy/Resource',
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
