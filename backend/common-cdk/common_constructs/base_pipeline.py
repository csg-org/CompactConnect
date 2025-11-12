from __future__ import annotations

import json
from textwrap import dedent

from aws_cdk import Stack
from aws_cdk.aws_codebuild import CfnProject
from aws_cdk.aws_codepipeline import CfnPipeline
from aws_cdk.aws_iam import Effect, PolicyStatement, Role
from aws_cdk.pipelines import CodePipeline as CdkCodePipeline
from constructs import Construct


class BasePipeline(CdkCodePipeline):
    """
    Base pipeline class with common functionality for both backend and frontend pipelines.

    This class provides:
    - Custom self-mutation step that preserves git tag/commit ID when restarting pipelines
    - Common pipeline configuration patterns
    """

    # Use an invalid branch name to ensure the pipeline can only be executed with explicit
    # git tag/commit ID specifications. This prevents accidental deployments from default
    # branches and enforces tag-based deployments only.
    _INVALID_BRANCH_NAME = '--invalid-branch-4e4bf8'

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        pipeline_name: str,
        pipeline_stack_name: str | None = None,
        github_repo_string: str | None = None,
        git_tag_trigger_pattern: str | None = None,
        self_mutation: bool = True,
        **kwargs,
    ):
        """
        Initialize the BasePipeline.

        :param scope: The parent construct.
        :param construct_id: The construct ID for this pipeline.
        :param pipeline_name: The name of the CodePipeline pipeline. This is required and will be
                              passed to the parent CdkCodePipeline constructor.
        :param pipeline_stack_name: The name of the CloudFormation stack that contains this pipeline.
                                   Used by the custom self-mutation step to deploy pipeline changes.
                                   Required if self_mutation is enabled.
        :param github_repo_string: The GitHub repository string in the format 'owner/repo'.
                                  Used by the custom self-mutation step to reference the source action
                                  when restarting the pipeline. Required if self_mutation is enabled.
        :param git_tag_trigger_pattern: The git tag pattern (glob format) that will automatically
                                       trigger the pipeline.
                                       If provided, the pipeline will be configured with git tag triggers.
        :param self_mutation: Whether to enable self-mutation for this pipeline. When enabled, the
                             pipeline will automatically update itself when its definition changes,
                             preserving the git tag/commit ID when restarting. Defaults to True.
        :param **kwargs: Additional keyword arguments passed to the parent CdkCodePipeline constructor.
        """
        # Store self_mutation flag - parent needs it to create the UpdatePipeline stage, which we'll then customize
        self._self_mutation_enabled = self_mutation
        # Store pipeline name, stack name, and github repo string for self-mutation step
        self._pipeline_name = pipeline_name
        self._pipeline_stack_name = pipeline_stack_name
        self._github_repo_string = github_repo_string
        self._git_tag_trigger_pattern = git_tag_trigger_pattern

        super().__init__(scope, construct_id, pipeline_name=pipeline_name, self_mutation=self_mutation, **kwargs)

    def build_pipeline(self) -> None:
        """Build the pipeline and apply custom self-mutation if enabled."""
        super().build_pipeline()

        # Only apply custom self-mutation if self_mutation is enabled
        if self._self_mutation_enabled:
            self._replace_self_mutation_step()

        # Configure git tag triggers if pattern is provided
        if self._git_tag_trigger_pattern:
            self._configure_git_tag_trigger()

    def _replace_self_mutation_step(self):
        """
        Replace the default self-mutation step with a custom implementation that preserves the git tag/commit ID when
        restarting the pipeline after self-mutation.

        The default Pipeline self-mutation step restarts the pipeline on changes, but it relies on the default
        CloudFormation behavior, which invokes the pipeline using the default branch. This is incompatible with
        tag-based deployments. Instead, this custom implementation:
        1. Deploys the pipeline stack and captures output
        2. Detects if changes were deployed
        3. If changes detected, triggers a new pipeline execution with the exact source revision
        4. Cancels the current pipeline execution, if it was not already stopped

        This method requires:
        - self._pipeline_stack_name: The name of the pipeline stack to deploy
        - self._pipeline_name: The name of the CodePipeline pipeline
        - self._github_repo_string: The GitHub repository string (e.g., 'owner/repo')
        """
        if not self._pipeline_stack_name:
            raise RuntimeError(
                'Pipeline stack name must be set. Ensure pipeline_stack_name is passed to the pipeline constructor.'
            )
        if not self._pipeline_name:
            raise RuntimeError('Pipeline name must be set. Ensure pipeline_name is passed to the pipeline constructor.')
        if not self._github_repo_string:
            raise RuntimeError(
                'GitHub repo string must be set. Ensure github_repo_string is passed to the pipeline constructor.'
            )

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
                          echo "Attempting to stop the current pipeline execution - it may already be stopping, which is fine."
                          aws codepipeline stop-pipeline-execution \\
                            --pipeline-name {self._pipeline_name} \\
                            --pipeline-execution-id "${{PIPELINE_EXECUTION_ID}}" | true
                          echo "Current pipeline execution cancelled"
                        elif [ $DEPLOY_EXIT_CODE -eq 0 ]; then
                          echo "No changes detected in pipeline stack"
                        else
                          echo "Pipeline stack deployment failed"
                          exit $DEPLOY_EXIT_CODE
                        fi
                        """),  # noqa: E501
                    ],
                },
            },
        }

        # Replace the buildspec
        cfn_project.add_property_override('Source.BuildSpec', json.dumps(custom_buildspec, indent=2))

        # Add a namespace to the source action so we can reference its output variables
        # The source action is in Stages[0].Actions[0] (first action of Source stage)
        cfn_pipeline: CfnPipeline = self.pipeline.node.default_child
        cfn_pipeline.add_property_override('Stages.0.Actions.0.Namespace', 'SourceVariables')

        # Add the PIPELINE_EXECUTION_ID and SOURCE_COMMIT_ID environment variables using CodePipeline variable syntax
        # Note: This will replace any existing environment variables in the action configuration.
        # CDK Pipeline typically adds a _PROJECT_CONFIG_HASH variable, but since we can't read
        # the existing value via escape hatches, we'll override it. The _PROJECT_CONFIG_HASH
        # is used for triggering pipeline restarts, which we implement differently, so it is not critical anymore.
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
        # Force this off, since we handle the pipeline restarts explicitly, now
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

    def _configure_git_tag_trigger(self):
        """
        Configure git tag-based trigger using CDK escape hatch.

        When triggers with filters are configured, AWS requires DetectChanges to be false
        in the source action configuration. The trigger configuration replaces the default
        change detection mechanism.

        The source action uses an invalid branch name to ensure the pipeline can only be
        executed with explicit git tag/commit ID specifications, enforcing tag-based deployments.

        This method requires:
        - self._github_repo_string: The GitHub repository string (e.g., 'owner/repo')
        - self._git_tag_trigger_pattern: The git tag pattern (glob format) for triggers
        """
        if not self._github_repo_string:
            raise RuntimeError(
                'GitHub repo string must be set. Ensure github_repo_string is passed to the pipeline constructor.'
            )
        if not self._git_tag_trigger_pattern:
            raise RuntimeError(
                'Git tag trigger pattern must be set. Ensure git_tag_trigger_pattern is passed to the pipeline '
                'constructor.'
            )

        cfn_pipeline: CfnPipeline = self.pipeline.node.default_child

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
