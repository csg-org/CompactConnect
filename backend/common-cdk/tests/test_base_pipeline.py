from unittest import TestCase

from aws_cdk import App, Environment
from aws_cdk.assertions import Match, Template
from aws_cdk.aws_codebuild import CfnProject
from aws_cdk.aws_codepipeline import CfnPipeline
from aws_cdk.aws_s3 import Bucket

from common_constructs.stack import Stack, StandardTags
from tests.test_context import TEST_ACCOUNT_ID, TEST_GITHUB_REPO_STRING, TEST_REGION
from tests.test_resources import ConcretePipeline


class TestBasePipeline(TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.app = App()
        self.env = Environment(account=TEST_ACCOUNT_ID, region=TEST_REGION)
        self.standard_tags = StandardTags(project='test', service='test-service', environment='pipeline')
        self.stack = Stack(
            self.app, 'TestStack', env=self.env, standard_tags=self.standard_tags, environment_name='pipeline'
        )
        self.artifact_bucket = Bucket(self.stack, 'ArtifactBucket')

    def test_creates_pipeline_with_self_mutation_enabled(self):
        """Test that BasePipeline creates a pipeline with custom self-mutation when enabled."""
        pipeline = ConcretePipeline(
            self.stack,
            'TestPipeline',
            pipeline_name='test-pipeline',
            pipeline_stack_name='TestStack',
            github_repo_string=TEST_GITHUB_REPO_STRING,
            self_mutation=True,
            artifact_bucket=self.artifact_bucket,
        )

        pipeline.build_pipeline()

        template = Template.from_stack(self.stack)

        # Verify pipeline is created with self-mutation disabled and source action namespace set
        template.has_resource_properties(
            CfnPipeline.CFN_RESOURCE_TYPE_NAME,
            {
                'Name': 'test-pipeline',
                'RestartExecutionOnUpdate': False,
                'Stages': Match.array_with(
                    [
                        Match.object_like(
                            {
                                'Name': 'Source',
                                'Actions': Match.array_with(
                                    [
                                        Match.object_like(
                                            {
                                                'Namespace': 'SourceVariables',
                                            }
                                        )
                                    ]
                                ),
                            }
                        )
                    ]
                ),
            },
        )

        # Verify self-mutation buildspec includes pipeline name and stack name
        self_mutation_projects = template.find_resources(
            CfnProject.CFN_RESOURCE_TYPE_NAME,
            props={'Properties': {'Name': 'test-pipeline-selfupdate'}},
        )
        self.assertEqual(len(self_mutation_projects), 1, 'Self-mutation CodeBuild project not found')
        project_resource = list(self_mutation_projects.values())[0]
        buildspec = project_resource['Properties']['Source']['BuildSpec']
        self.assertIn('test-pipeline', buildspec)
        self.assertIn('TestStack', buildspec)

        # Verify self-mutation role has pipeline execution permissions
        template.has_resource_properties(
            'AWS::IAM::Policy',
            {
                'PolicyDocument': {
                    'Statement': Match.array_with(
                        [
                            Match.object_like(
                                {
                                    'Effect': 'Allow',
                                    'Action': Match.array_with(
                                        [
                                            'codepipeline:StartPipelineExecution',
                                            'codepipeline:StopPipelineExecution',
                                        ]
                                    ),
                                }
                            )
                        ]
                    )
                }
            },
        )

    def test_creates_pipeline_without_self_mutation(self):
        """Test that BasePipeline creates a pipeline without custom self-mutation when disabled."""
        pipeline = ConcretePipeline(
            self.stack,
            'TestPipeline',
            pipeline_name='test-pipeline',
            self_mutation=False,
            artifact_bucket=self.artifact_bucket,
        )

        pipeline.build_pipeline()

        template = Template.from_stack(self.stack)

        # Verify pipeline is created
        template.has_resource(
            type=CfnPipeline.CFN_RESOURCE_TYPE_NAME,
            props={
                'Properties': {
                    'Name': 'test-pipeline',
                }
            },
        )

        # Verify self-mutation CodeBuild project does not exist when disabled
        # When self_mutation is False, there should be no self-mutation project
        self_mutation_projects = template.find_resources(
            CfnProject.CFN_RESOURCE_TYPE_NAME,
            props={'Properties': {'Name': 'test-pipeline-selfupdate'}},
        )
        self.assertEqual(len(self_mutation_projects), 0, 'Self-mutation project should not exist when disabled')

    def test_invalid_branch_name_used_in_source(self):
        """Test that the invalid branch name is used in the pipeline source action."""
        pipeline = ConcretePipeline(
            self.stack,
            'TestPipeline',
            pipeline_name='test-pipeline',
            self_mutation=False,
            artifact_bucket=self.artifact_bucket,
        )

        pipeline.build_pipeline()

        template = Template.from_stack(self.stack)

        # Verify source action uses invalid branch name
        template.has_resource_properties(
            CfnPipeline.CFN_RESOURCE_TYPE_NAME,
            {
                'Name': 'test-pipeline',
                'Stages': Match.array_with(
                    [
                        Match.object_like(
                            {
                                'Name': 'Source',
                                'Actions': Match.array_with(
                                    [
                                        Match.object_like(
                                            {
                                                'Configuration': Match.object_like(
                                                    {'BranchName': '--invalid-branch-4e4bf8'}
                                                )
                                            }
                                        )
                                    ]
                                ),
                            }
                        )
                    ]
                ),
            },
        )

    def test_replace_self_mutation_step_requires_pipeline_stack_name(self):
        """Test that _replace_self_mutation_step raises RuntimeError when pipeline_stack_name is missing."""
        pipeline = ConcretePipeline(
            self.stack,
            'TestPipeline',
            pipeline_name='test-pipeline',
            pipeline_stack_name=None,  # Missing required parameter
            github_repo_string=TEST_GITHUB_REPO_STRING,
            self_mutation=True,
            artifact_bucket=self.artifact_bucket,
        )

        # The error should be raised during build_pipeline when _replace_self_mutation_step is called
        with self.assertRaises(RuntimeError) as context:
            pipeline.build_pipeline()

        self.assertIn('Pipeline stack name must be set', str(context.exception))

    def test_pipeline_git_tag_triggers(self):
        """Test that pipelines can be configured with git tag triggers."""
        pipeline = ConcretePipeline(
            self.stack,
            'TestPipeline',
            pipeline_name='test-pipeline',
            self_mutation=False,
            artifact_bucket=self.artifact_bucket,
        )

        pipeline.build_pipeline()

        # Configure git tag trigger using escape hatch (simulating what BackendPipeline does)
        cfn_pipeline: CfnPipeline = pipeline.pipeline.node.default_child
        source_action_name = TEST_GITHUB_REPO_STRING.replace('/', '_')
        git_tag_pattern = 'test-*'

        cfn_pipeline.add_property_override(
            'Triggers',
            [
                {
                    'ProviderType': 'CodeStarSourceConnection',
                    'GitConfiguration': {
                        'SourceActionName': source_action_name,
                        'Push': [{'Tags': {'Includes': [git_tag_pattern]}}],
                    },
                }
            ],
        )
        cfn_pipeline.add_property_override('Stages.0.Actions.0.Configuration.DetectChanges', False)

        template = Template.from_stack(self.stack)

        # Verify all git tag trigger properties in a single call
        template.has_resource_properties(
            CfnPipeline.CFN_RESOURCE_TYPE_NAME,
            {
                'Triggers': [
                    {
                        'ProviderType': 'CodeStarSourceConnection',
                        'GitConfiguration': {
                            'SourceActionName': source_action_name,
                            'Push': [{'Tags': {'Includes': [git_tag_pattern]}}],
                        },
                    }
                ],
                'Stages': Match.array_with(
                    [
                        Match.object_like(
                            {
                                'Name': 'Source',
                                'Actions': Match.array_with(
                                    [
                                        Match.object_like(
                                            {
                                                'Configuration': Match.object_like(
                                                    {'DetectChanges': False, 'BranchName': Match.any_value()}
                                                )
                                            }
                                        )
                                    ]
                                ),
                            }
                        )
                    ]
                ),
            },
        )
