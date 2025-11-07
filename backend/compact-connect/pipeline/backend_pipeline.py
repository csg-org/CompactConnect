from __future__ import annotations

import json
import os
from textwrap import dedent

import common_constructs.base_pipeline_stack
from aws_cdk import ArnFormat, Fn, RemovalPolicy, Stack
from aws_cdk.aws_codebuild import BuildSpec, CfnProject
from aws_cdk.aws_codepipeline import CfnPipeline, PipelineType
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
    - Automatically triggered by git tags matching the specified pattern (e.g., 'prod-*')
    - Can be manually started, which will use the default_branch for source code
    - Triggers the Frontend Pipeline after successful deployment with the EXACT SAME commit ID
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
        Initialize the BackendPipeline.

        :param default_branch: The git branch to use when the pipeline is started manually.
                              This branch is NOT used for automatic triggers.
        :param git_tag_trigger_pattern: The git tag pattern (glob format) that will automatically
                                       trigger the pipeline (e.g., 'prod-*', 'beta-*', 'test-*').
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
                    branch=default_branch,
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
        self._git_tag_trigger_pattern = git_tag_trigger_pattern
        self._github_repo_string = github_repo_string
        self._pipeline_stack_name = pipeline_stack_name
        self._pipeline_name = pipeline_name

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
        self._configure_git_tag_trigger()
        self._replace_self_mutation_step()

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
        cfn_pipeline.add_property_override(
            'Triggers',
            [
                {
                    'ProviderType': 'CodeStarSourceConnection',
                    'GitConfiguration': {
                        'SourceActionName': self._github_repo_string.replace('/', '_'),
                        'Push': [{'Tags': {'Includes': [self._git_tag_trigger_pattern]}}],
                    },
                }
            ],
        )

        # Set DetectChanges to false in the source action
        # The source action is in Stages[0].Actions[0] (first action of Source stage)
        # This functionally overrides the corresponding `trigger_on_push=True` setting in the
        # CodePipelineSource.connection() call.
        cfn_pipeline.add_property_override('Stages.0.Actions.0.Configuration.DetectChanges', False)

    def _replace_self_mutation_step(self):
        """
        Replace the default self-mutation step with a custom implementation that preserves
        the git tag/commit ID when restarting the pipeline after self-mutation.

        The default CDK Pipeline self-mutation restarts the pipeline using the default branch,
        which is incompatible with tag-based deployments. This custom implementation:
        1. Deploys the pipeline stack and captures output
        2. Detects if changes were deployed
        3. If changes detected, triggers a new pipeline execution with the exact source revision
        4. Cancels the current pipeline execution
        """
        # Find the UpdatePipeline stage node
        update_pipeline_node = self.node.find_child('UpdatePipeline')

        # Find the SelfMutation node within UpdatePipeline
        self_mutation_node = update_pipeline_node.node.find_child('SelfMutation')

        # Get the CloudFormation resource for the CodeBuild project
        cfn_project: CfnProject = self_mutation_node.node.default_child
        if cfn_project is None:
            raise RuntimeError(
                f'CloudFormation resource not found for CdkBuildProject in pipeline {self._pipeline_name}. '
                'This indicates the pipeline structure is not as expected.'
            )

        # Get the source action name (used for source-revisions parameter)
        source_action_name = self._github_repo_string.replace('/', '_')

        # Create custom buildspec that:
        # 1. Installs CDK CLI
        # 2. Deploys the pipeline stack
        # 3. Checks if changes were made
        # 4. If changes detected, triggers new execution with source revision and cancels current
        custom_buildspec = {
            'version': '0.2',
            'env': {
                'shell': 'bash',
            },
            'phases': {
                'install': {
                    'commands': ['npm install -g aws-cdk@2'],
                },
                'build': {
                    'commands': [
                        dedent(f"""
                        set -o pipefail
                        cdk -a . deploy {self._pipeline_stack_name} --require-approval=never --verbose 2>&1 | tee deploy_output.log
                        DEPLOY_EXIT_CODE=$?
                        DEPLOY_OUTPUT=$(<deploy_output.log)
                        [ $DEPLOY_EXIT_CODE -eq 0 ] || exit $DEPLOY_EXIT_CODE
                        """),  # noqa: E501
                        (
                            # Assuming that, if we deploy _any_ changeset here, that's a change to restart on
                            'echo "$DEPLOY_OUTPUT" | grep -q "Initiating execution of changeset" && CHANGED=true || true'  # noqa: E501
                        ),
                        dedent(f"""
                        if [ -n "$CHANGED" ]; then
                          echo "Pipeline stack was updated. Triggering new execution with source revision: ${{SOURCE_COMMIT_ID}}"
                          aws codepipeline start-pipeline-execution \\
                            --name {self._pipeline_name} \\
                            --source-revisions actionName={source_action_name},revisionType=COMMIT_ID,revisionValue="${{SOURCE_COMMIT_ID}}"
                          START_EXIT_CODE=$?
                          if [ $START_EXIT_CODE -eq 0 ]; then
                            echo "New pipeline execution started successfully"
                          else
                            echo "Failed to start new pipeline execution"
                            exit $START_EXIT_CODE
                          fi
                          aws codepipeline stop-pipeline-execution \\
                            --pipeline-name {self._pipeline_name} \\
                            --pipeline-execution-id "${{PIPELINE_EXECUTION_ID}}"
                          echo "Current pipeline execution cancelled"
                        elif [ $DEPLOY_EXIT_CODE -eq 0 ]; then
                          echo "No changes detected in pipeline stack"
                        else
                          echo "Pipeline stack deployment failed"
                          exit $DEPLOY_EXIT_CODE
                        fi
                        """)  # noqa: E501
                    ],
                },
            },
        }

        # Replace the buildspec
        cfn_project.add_property_override('Source.BuildSpec', json.dumps(custom_buildspec, indent=2))

        # Add PipelineExecutionId as an environment variable to the CodePipeline action
        # This uses CodePipeline's variable syntax to pass the execution ID to the CodeBuild step
        # The UpdatePipeline stage is typically the 3rd stage (index 2: Source=0, Build=1,
        # UpdatePipeline=2). The SelfMutate action is the first action in that stage.
        cfn_pipeline: CfnPipeline = self.pipeline.node.default_child

        # Add a namespace to the source action so we can reference its output variables
        # The source action is in Stages[0].Actions[0] (first action of Source stage)
        cfn_pipeline.add_property_override('Stages.0.Actions.0.Namespace', 'SourceVariables')

        # Add the PipelineExecutionId and SOURCE_COMMIT_ID environment variables using CodePipeline variable syntax
        # Note: This will replace any existing environment variables in the action configuration.
        # CDK Pipeline typically adds a _PROJECT_CONFIG_HASH variable, but since we can't read
        # the existing value via escape hatches, we'll override it. The _PROJECT_CONFIG_HASH
        # is used for cache invalidation and is not critical for functionality.
        # TODO: investigate adding _PROJECT_CONFIG_HASH explicitly here
        env_vars = [
            {
                'name': 'PIPELINE_EXECUTION_ID',
                'type': 'PLAINTEXT',
                'value': '#{codepipeline.PipelineExecutionId}',
            },
            {
                'name': 'SOURCE_COMMIT_ID',
                'type': 'PLAINTEXT',
                'value': '#{SourceVariables.CommitId}',
            },
        ]

        cfn_pipeline.add_property_override(
            'Stages.2.Actions.0.Configuration.EnvironmentVariables',
            json.dumps(env_vars),
        )
        cfn_pipeline.add_property_override('RestartExecutionOnUpdate', False)

        # Add IAM permissions to the self-mutation role
        # Find the role associated with the CodeBuild project
        stack = Stack.of(self)
        self_mutation_role: Role = self_mutation_node.node.find_child('Role')

        # Add permissions to start and stop pipeline executions
        self_mutation_role.add_to_principal_policy(
            PolicyStatement(
                effect=Effect.ALLOW,
                actions=[
                    'codepipeline:StartPipelineExecution',
                    'codepipeline:StopPipelineExecution',
                    'codepipeline:GetPipelineExecution',
                    'codepipeline:ListPipelineExecutions',
                ],
                resources=[
                    stack.format_arn(
                        partition=stack.partition,
                        service='codepipeline',
                        region=stack.region,
                        account=stack.account,
                        resource=self._pipeline_name,
                    ),
                ],
            )
        )
