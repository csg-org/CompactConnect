"""
Common test resources for CDK construct tests.

This module provides concrete implementations of abstract base classes for testing purposes.
"""

from aws_cdk.pipelines import CodeBuildStep, CodePipelineSource

from common_constructs.base_pipeline import BasePipeline
from tests.test_context import TEST_CONNECTION_ARN, TEST_GITHUB_REPO_STRING


class ConcretePipeline(BasePipeline):
    """Concrete subclass of BasePipeline for testing purposes."""

    def __init__(
        self,
        scope,
        construct_id,
        *,
        pipeline_name,
        pipeline_stack_name=None,
        github_repo_string=None,
        git_tag_trigger_pattern=None,
        self_mutation=True,
        artifact_bucket=None,
        synth=None,
        **kwargs,
    ):
        """
        Initialize ConcretePipeline with default source configuration using invalid branch name.

        :param scope: The parent construct.
        :param construct_id: The construct ID for this pipeline.
        :param pipeline_name: The name of the CodePipeline pipeline.
        :param pipeline_stack_name: The name of the CloudFormation stack that contains this pipeline.
        :param github_repo_string: The GitHub repository string.
        :param self_mutation: Whether to enable self-mutation for this pipeline.
        :param artifact_bucket: The S3 bucket for pipeline artifacts.
        :param synth: The synth step. If not provided, a default one will be created.
        :param **kwargs: Additional keyword arguments passed to the parent BasePipeline constructor.
        """
        # Create default synth step if not provided, using the invalid branch name
        if synth is None:
            synth = CodeBuildStep(
                'Synth',
                input=CodePipelineSource.connection(
                    repo_string=github_repo_string or TEST_GITHUB_REPO_STRING,
                    branch=self._INVALID_BRANCH_NAME,
                    trigger_on_push=False,
                    connection_arn=TEST_CONNECTION_ARN,
                ),
                commands=['echo "synth"'],
            )

        super().__init__(
            scope,
            construct_id,
            pipeline_name=pipeline_name,
            pipeline_stack_name=pipeline_stack_name,
            github_repo_string=github_repo_string,
            git_tag_trigger_pattern=git_tag_trigger_pattern,
            self_mutation=self_mutation,
            artifact_bucket=artifact_bucket,
            synth=synth,
            **kwargs,
        )
