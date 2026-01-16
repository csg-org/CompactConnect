from unittest import TestCase

from aws_cdk import App, Environment, RemovalPolicy
from aws_cdk.assertions import Match, Template
from aws_cdk.aws_s3 import Bucket

from common_constructs.access_logs_bucket import AccessLogsBucket
from common_constructs.base_pipeline_stack import (
    TEST_ENVIRONMENT_NAME,
    BasePipelineStack,
    CCPipelineType,
)
from common_constructs.stack import Stack, StandardTags
from tests.test_context import (
    TEST_ACCOUNT_ID,
    TEST_APP_NAME,
    TEST_CONNECTION_ARN,
    TEST_GITHUB_REPO_STRING,
    TEST_REGION,
    get_test_context,
)
from tests.test_resources import ConcretePipeline


class ConcretePipelineStack(BasePipelineStack):
    """Concrete subclass of BasePipelineStack for testing purposes."""

    def __init__(
        self,
        scope,
        construct_id,
        *,
        environment_name,
        env,
        pipeline_context_parameter_name,
        removal_policy,
        pipeline_access_logs_bucket,
        standard_tags,
        **kwargs,
    ):
        """
        Initialize ConcretePipelineStack with a test pipeline.

        :param scope: The parent construct.
        :param construct_id: The construct ID for this stack.
        :param environment_name: The environment name.
        :param env: The AWS environment.
        :param pipeline_context_parameter_name: The SSM parameter name for the pipeline context.
        :param removal_policy: The removal policy.
        :param pipeline_access_logs_bucket: The access logs bucket.
        :param standard_tags: Standard tags for the stack.
        :param **kwargs: Additional keyword arguments passed to the parent BasePipelineStack constructor.
        """
        super().__init__(
            scope,
            construct_id,
            environment_name=environment_name,
            env=env,
            pipeline_context_parameter_name=pipeline_context_parameter_name,
            removal_policy=removal_policy,
            pipeline_access_logs_bucket=pipeline_access_logs_bucket,
            standard_tags=standard_tags,
            **kwargs,
        )

        # Create a test pipeline to exercise _add_pipeline_cdk_assume_role_policy
        artifact_bucket = Bucket(self, 'ArtifactBucket')
        self.test_pipeline = ConcretePipeline(
            self,
            'TestPipeline',
            pipeline_name='test-pipeline',
            pipeline_stack_name=self.stack_name,
            github_repo_string=self.github_repo_string,
            self_mutation=False,
            artifact_bucket=artifact_bucket,
        )
        self.test_pipeline.build_pipeline()
        self._add_pipeline_cdk_assume_role_policy(self.test_pipeline)


class TestBasePipelineStackBackend(TestCase):
    def setUp(self):
        """Set up test fixtures."""
        # Provide SSM lookup context to the App constructor
        # Use test context by default, individual tests can override
        context = get_test_context('backend')
        self.app = App(context=context)
        self.env = Environment(account=TEST_ACCOUNT_ID, region=TEST_REGION)
        self.standard_tags = StandardTags(project='test', service='test-service', environment='pipeline')
        access_logs_stack = Stack(
            self.app,
            'AccessLogsStack',
            env=self.env,
            standard_tags=StandardTags(project='test', service='test-service', environment='deploy'),
            environment_name='deploy',
        )
        self.access_logs_bucket = AccessLogsBucket(
            access_logs_stack,
            'AccessLogsBucket',
            removal_policy=RemovalPolicy.RETAIN,
        )

    def test_creates_backend_pipeline_stack(self):
        """Test that BasePipelineStack creates expected resources for backend pipeline type."""
        pipeline_stack = ConcretePipelineStack(
            self.app,
            'TestPipelineStack',
            environment_name=TEST_ENVIRONMENT_NAME,
            env=self.env,
            pipeline_context_parameter_name=f'{TEST_ENVIRONMENT_NAME}-compact-connect-context',
            removal_policy=RemovalPolicy.DESTROY,
            pipeline_access_logs_bucket=self.access_logs_bucket,
            standard_tags=self.standard_tags,
        )

        # Synthesize to get template
        self.app.synth()

        # Verify stack has expected attributes
        self.assertEqual(pipeline_stack.environment_name, TEST_ENVIRONMENT_NAME)
        self.assertEqual(pipeline_stack.removal_policy, RemovalPolicy.DESTROY)

        # Verify stack attributes are set correctly (validated through successful synthesis)
        # The SSM parameter is a reference, not a created resource, so we verify through attributes
        self.assertIsNotNone(pipeline_stack.parameter)
        self.assertEqual(pipeline_stack.connection_arn, TEST_CONNECTION_ARN)
        self.assertEqual(pipeline_stack.github_repo_string, TEST_GITHUB_REPO_STRING)
        self.assertEqual(pipeline_stack.app_name, TEST_APP_NAME)

    def test_create_predictable_pipeline_role_backend(self):
        """Test that create_predictable_pipeline_role creates a role with expected properties for backend."""
        pipeline_stack = ConcretePipelineStack(
            self.app,
            'TestPipelineStackBackend',
            environment_name=TEST_ENVIRONMENT_NAME,
            env=self.env,
            pipeline_context_parameter_name=f'{TEST_ENVIRONMENT_NAME}-compact-connect-context',
            removal_policy=RemovalPolicy.DESTROY,
            pipeline_access_logs_bucket=self.access_logs_bucket,
            standard_tags=self.standard_tags,
        )

        pipeline_stack.create_predictable_pipeline_role(CCPipelineType.BACKEND)

        # Synthesize to get template
        self.app.synth()
        template = Template.from_stack(pipeline_stack)

        # Verify role is created with expected name and trust policy
        # Match both services in the order they appear (codepipeline first, then codebuild)
        template.has_resource_properties(
            'AWS::IAM::Role',
            {
                'RoleName': 'CompactConnect-test-Backend-CrossAccountRole',
                'AssumeRolePolicyDocument': {
                    'Statement': Match.array_with(
                        [
                            Match.object_like(
                                {
                                    'Effect': 'Allow',
                                    'Principal': {'Service': 'codepipeline.amazonaws.com'},
                                    'Action': 'sts:AssumeRole',
                                }
                            ),
                            Match.object_like(
                                {
                                    'Effect': 'Allow',
                                    'Principal': {'Service': 'codebuild.amazonaws.com'},
                                    'Action': 'sts:AssumeRole',
                                }
                            ),
                        ]
                    )
                },
            },
        )

    def test_add_pipeline_cdk_assume_role_policy(self):
        """Test that _add_pipeline_cdk_assume_role_policy adds expected IAM policy."""
        pipeline_stack = ConcretePipelineStack(
            self.app,
            'TestPipelineStack',
            environment_name=TEST_ENVIRONMENT_NAME,
            env=self.env,
            pipeline_context_parameter_name=f'{TEST_ENVIRONMENT_NAME}-compact-connect-context',
            removal_policy=RemovalPolicy.DESTROY,
            pipeline_access_logs_bucket=self.access_logs_bucket,
            standard_tags=self.standard_tags,
        )

        # Synthesize to get template
        self.app.synth()
        template = Template.from_stack(pipeline_stack)

        # Verify the synth project role has the CDK lookup role assume policy
        # The policy should have a statement allowing sts:AssumeRole for CDK lookup roles
        # The Resource is an Fn::Join that contains the pattern 'cdk-hnb659fds-lookup-role-*'
        template.has_resource_properties(
            'AWS::IAM::Policy',
            {
                'PolicyDocument': {
                    'Statement': Match.array_with(
                        [
                            Match.object_like(
                                {
                                    'Effect': 'Allow',
                                    'Action': 'sts:AssumeRole',
                                    'Resource': Match.object_like(
                                        {
                                            'Fn::Join': [
                                                '',
                                                Match.array_with(
                                                    [
                                                        'arn:',
                                                        Match.object_like({'Ref': 'AWS::Partition'}),
                                                        Match.string_like_regexp(r'.*cdk-hnb659fds-lookup-role-\*'),
                                                    ]
                                                ),
                                            ],
                                        }
                                    ),
                                }
                            )
                        ]
                    )
                },
                'Roles': Match.array_with(
                    [
                        Match.object_like(
                            {
                                'Ref': Match.string_like_regexp(r'.*Synth.*BuildProject.*'),
                            }
                        )
                    ]
                ),
            },
        )

    def test_pipeline_uses_predictable_roles_for_actions_backend(self):
        """Test that backend pipelines are configured to use predictable roles for all actions."""
        pipeline_stack = ConcretePipelineStack(
            self.app,
            'TestPipelineStackBackend',
            environment_name=TEST_ENVIRONMENT_NAME,
            env=self.env,
            pipeline_context_parameter_name=f'{TEST_ENVIRONMENT_NAME}-compact-connect-context',
            removal_policy=RemovalPolicy.DESTROY,
            pipeline_access_logs_bucket=self.access_logs_bucket,
            standard_tags=self.standard_tags,
        )

        # Create the predictable role
        pipeline_role = pipeline_stack.create_predictable_pipeline_role(CCPipelineType.BACKEND)

        # Create a test pipeline that uses the role
        # Create a separate artifact bucket for this test pipeline
        artifact_bucket = Bucket(pipeline_stack, 'TestArtifactBucket')
        test_pipeline = ConcretePipeline(
            pipeline_stack,
            'TestPipelineWithRole',
            pipeline_name='test-pipeline-with-role',
            self_mutation=False,
            artifact_bucket=artifact_bucket,
            role=pipeline_role,
        )
        test_pipeline.build_pipeline()

        # Synthesize to get template
        self.app.synth()
        template = Template.from_stack(pipeline_stack)

        # The pipeline should reference the predictable cross-account role
        # This validates that our role parameter is being used
        template.has_resource_properties(
            'AWS::CodePipeline::Pipeline',
            {'RoleArn': {'Fn::GetAtt': [Match.string_like_regexp(r'.*BackendCrossAccountRole.*'), 'Arn']}},
        )


class TestBasePipelineStackFrontend(TestCase):
    def setUp(self):
        """Set up test fixtures."""
        # Provide SSM lookup context to the App constructor
        # Use test context by default, individual tests can override
        context = get_test_context('frontend')
        self.app = App(context=context)
        self.env = Environment(account=TEST_ACCOUNT_ID, region=TEST_REGION)
        self.standard_tags = StandardTags(project='test', service='test-service', environment='pipeline')
        access_logs_stack = Stack(
            self.app,
            'AccessLogsStack',
            env=self.env,
            standard_tags=StandardTags(project='test', service='test-service', environment='deploy'),
            environment_name='deploy',
        )
        self.access_logs_bucket = AccessLogsBucket(
            access_logs_stack,
            'AccessLogsBucket',
            removal_policy=RemovalPolicy.RETAIN,
        )

    def test_creates_frontend_pipeline_stack(self):
        """Test that BasePipelineStack creates expected resources for frontend pipeline type."""

        pipeline_stack = ConcretePipelineStack(
            self.app,
            'TestPipelineStack',
            environment_name=TEST_ENVIRONMENT_NAME,
            env=self.env,
            pipeline_context_parameter_name=f'{TEST_ENVIRONMENT_NAME}-ui-compact-connect-context',
            removal_policy=RemovalPolicy.RETAIN,
            pipeline_access_logs_bucket=self.access_logs_bucket,
            standard_tags=self.standard_tags,
        )

        # Synthesize to get template
        self.app.synth()

        # Verify stack has expected attributes
        self.assertEqual(pipeline_stack.environment_name, TEST_ENVIRONMENT_NAME)
        self.assertEqual(pipeline_stack.removal_policy, RemovalPolicy.RETAIN)

        # Verify stack attributes are set correctly (validated through successful synthesis)
        # The SSM parameter is a reference, not a created resource, so we verify through attributes
        self.assertIsNotNone(pipeline_stack.parameter)
        self.assertEqual(pipeline_stack.connection_arn, TEST_CONNECTION_ARN)
        self.assertEqual(pipeline_stack.github_repo_string, TEST_GITHUB_REPO_STRING)
        self.assertEqual(pipeline_stack.app_name, TEST_APP_NAME)

    def test_create_predictable_pipeline_role_frontend(self):
        """Test that create_predictable_pipeline_role creates a role with expected properties for frontend."""
        pipeline_stack = ConcretePipelineStack(
            self.app,
            'TestPipelineStackFrontend',
            environment_name=TEST_ENVIRONMENT_NAME,
            env=self.env,
            pipeline_context_parameter_name=f'{TEST_ENVIRONMENT_NAME}-ui-compact-connect-context',
            removal_policy=RemovalPolicy.DESTROY,
            pipeline_access_logs_bucket=self.access_logs_bucket,
            standard_tags=self.standard_tags,
        )

        pipeline_stack.create_predictable_pipeline_role(CCPipelineType.FRONTEND)

        # Synthesize to get template
        self.app.synth()
        template = Template.from_stack(pipeline_stack)

        # Verify role is created with expected name and trust policy
        # Match both services in the order they appear (codepipeline first, then codebuild)
        template.has_resource_properties(
            'AWS::IAM::Role',
            {
                'RoleName': 'CompactConnect-test-Frontend-CrossAccountRole',
                'AssumeRolePolicyDocument': {
                    'Statement': Match.array_with(
                        [
                            Match.object_like(
                                {
                                    'Effect': 'Allow',
                                    'Principal': {'Service': 'codepipeline.amazonaws.com'},
                                    'Action': 'sts:AssumeRole',
                                }
                            ),
                            Match.object_like(
                                {
                                    'Effect': 'Allow',
                                    'Principal': {'Service': 'codebuild.amazonaws.com'},
                                    'Action': 'sts:AssumeRole',
                                }
                            ),
                        ]
                    )
                },
            },
        )

    def test_pipeline_uses_predictable_roles_for_actions_frontend(self):
        """Test that frontend pipelines are configured to use predictable roles for all actions."""
        pipeline_stack = ConcretePipelineStack(
            self.app,
            'TestPipelineStackFrontend',
            environment_name=TEST_ENVIRONMENT_NAME,
            env=self.env,
            pipeline_context_parameter_name=f'{TEST_ENVIRONMENT_NAME}-ui-compact-connect-context',
            removal_policy=RemovalPolicy.DESTROY,
            pipeline_access_logs_bucket=self.access_logs_bucket,
            standard_tags=self.standard_tags,
        )

        # Create the predictable role
        pipeline_role = pipeline_stack.create_predictable_pipeline_role(CCPipelineType.FRONTEND)

        # Create a test pipeline that uses the role
        # Create a separate artifact bucket for this test pipeline
        artifact_bucket = Bucket(pipeline_stack, 'TestArtifactBucket')
        test_pipeline = ConcretePipeline(
            pipeline_stack,
            'TestPipelineWithRole',
            pipeline_name='test-pipeline-with-role',
            self_mutation=False,
            artifact_bucket=artifact_bucket,
            role=pipeline_role,
        )
        test_pipeline.build_pipeline()

        # Synthesize to get template
        self.app.synth()
        template = Template.from_stack(pipeline_stack)

        # The pipeline should reference the predictable cross-account role
        # This validates that our role parameter is being used
        template.has_resource_properties(
            'AWS::CodePipeline::Pipeline',
            {'RoleArn': {'Fn::GetAtt': [Match.string_like_regexp(r'.*FrontendCrossAccountRole.*'), 'Arn']}},
        )
