from unittest import TestCase

from aws_cdk import App, Environment
from aws_cdk.assertions import Match, Template
from aws_cdk.aws_kms import CfnKey
from aws_cdk.aws_s3 import CfnBucket
from aws_cdk.aws_sns import CfnTopic

from common_constructs.base_pipeline_stack import DEPLOY_ENVIRONMENT_NAME
from common_constructs.deployment_resources_stack import DeploymentResourcesStack
from common_constructs.stack import StandardTags
from tests.test_context import TEST_ACCOUNT_ID, TEST_REGION, get_deploy_context


class TestDeploymentResourcesStack(TestCase):
    def test_creates_backend_resources(self):
        """Test that DeploymentResourcesStack creates expected resources for backend pipeline type."""
        # Provide SSM lookup context to the App constructor
        context = get_deploy_context('backend')
        app = App(context=context)
        env = Environment(account=TEST_ACCOUNT_ID, region=TEST_REGION)
        standard_tags = StandardTags(project='test', service='test-service', environment='deploy')

        # Create DeploymentResourcesStack as a top-level stack
        deployment_stack = DeploymentResourcesStack(
            app,
            'DeploymentResources',
            pipeline_context_parameter_name=f'{DEPLOY_ENVIRONMENT_NAME}-compact-connect-context',
            standard_tags=standard_tags,
            env=env,
        )

        # Synthesize the app
        app.synth()

        template = Template.from_stack(deployment_stack)

        # Verify encryption key is created with rotation enabled
        template.has_resource_properties(
            CfnKey.CFN_RESOURCE_TYPE_NAME,
            {
                'EnableKeyRotation': True,
            },
        )

        # Verify access logs bucket is created with versioning enabled
        template.has_resource_properties(
            CfnBucket.CFN_RESOURCE_TYPE_NAME,
            {
                'VersioningConfiguration': {'Status': 'Enabled'},
            },
        )

        # Verify alarm topic is created with KMS encryption
        template.has_resource_properties(
            CfnTopic.CFN_RESOURCE_TYPE_NAME,
            {
                'KmsMasterKeyId': Match.any_value(),
            },
        )

        # Verify alarm topic is created with KMS encryption
        template.has_resource_properties(
            CfnTopic.CFN_RESOURCE_TYPE_NAME,
            {
                'KmsMasterKeyId': Match.any_value(),
            },
        )

    def test_creates_frontend_resources(self):
        """Test that DeploymentResourcesStack creates expected resources for frontend pipeline type."""
        # Provide SSM lookup context to the App constructor
        context = get_deploy_context('frontend')
        app = App(context=context)
        env = Environment(account=TEST_ACCOUNT_ID, region=TEST_REGION)
        standard_tags = StandardTags(project='test', service='test-service', environment='deploy')

        # Create DeploymentResourcesStack as a top-level stack
        deployment_stack = DeploymentResourcesStack(
            app,
            'DeploymentResources',
            pipeline_context_parameter_name=f'{DEPLOY_ENVIRONMENT_NAME}-ui-compact-connect-context',
            standard_tags=standard_tags,
            env=env,
        )

        # Synthesize the app
        app.synth()

        template = Template.from_stack(deployment_stack)

        # Verify encryption key is created with rotation enabled
        template.has_resource_properties(
            CfnKey.CFN_RESOURCE_TYPE_NAME,
            {
                'EnableKeyRotation': True,
            },
        )

        # Verify access logs bucket is created with versioning enabled
        template.has_resource_properties(
            CfnBucket.CFN_RESOURCE_TYPE_NAME,
            {
                'VersioningConfiguration': {'Status': 'Enabled'},
            },
        )

        # Verify alarm topic is created with KMS encryption
        template.has_resource_properties(
            CfnTopic.CFN_RESOURCE_TYPE_NAME,
            {
                'KmsMasterKeyId': Match.any_value(),
            },
        )
