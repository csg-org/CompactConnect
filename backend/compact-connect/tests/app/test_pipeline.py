import json
import os
from unittest import TestCase
from unittest.mock import patch

from app import CompactConnectApp
from aws_cdk.assertions import Match, Template
from aws_cdk.aws_cognito import (
    CfnUserPool,
    CfnUserPoolClient,
    CfnUserPoolResourceServer,
    CfnUserPoolRiskConfigurationAttachment,
)
from aws_cdk.aws_lambda import CfnFunction, CfnLayerVersion
from aws_cdk.aws_ssm import CfnParameter

from tests.app.base import TstAppABC


class TestBackendPipeline(TstAppABC, TestCase):
    @classmethod
    def get_context(cls):
        with open('cdk.json') as f:
            context = json.load(f)['context']
        # For pipeline deployments, we do not have a cdk.context.json file to extend context:
        # ssm_context is actually pulled from SSM Parameter Store

        # Suppresses lambda bundling for tests
        context['aws:cdk:bundling-stacks'] = []

        return context

    def test_synth_pipeline(self):
        """
        Validates the synthesized backend pipeline infrastructure for compliance and correctness.
        
        Checks that all backend pipeline and deployment stacks have no AWS Solutions rule violations or stage annotations, inspects API stacks for each environment, and verifies persistent stack configurations for test, beta, and prod environments.
        """
        # Identify any findings from our AwsSolutions rule sets
        self._check_no_stack_annotations(self.app.deployment_resources_stack)
        self._check_no_stack_annotations(self.app.test_backend_pipeline_stack)
        self._check_no_stack_annotations(self.app.prod_backend_pipeline_stack)
        for stage in (
            self.app.test_backend_pipeline_stack.test_stage,
            self.app.beta_backend_pipeline_stack.beta_backend_stage,
            self.app.prod_backend_pipeline_stack.prod_stage,
        ):
            self._check_no_backend_stage_annotations(stage)

        for api_stack in (
            self.app.test_backend_pipeline_stack.test_stage.api_stack,
            self.app.beta_backend_pipeline_stack.beta_backend_stage.api_stack,
            self.app.prod_backend_pipeline_stack.prod_stage.api_stack,
        ):
            with self.subTest(api_stack.stack_name):
                self._inspect_api_stack(api_stack)

        self._inspect_persistent_stack(
            self.app.test_backend_pipeline_stack.test_stage.persistent_stack,
            domain_name='app.test.compactconnect.org',
            allow_local_ui=True,
        )
        self._inspect_persistent_stack(
            self.app.beta_backend_pipeline_stack.beta_backend_stage.persistent_stack,
            domain_name='app.beta.compactconnect.org',
            allow_local_ui=False,
        )
        self._inspect_persistent_stack(
            self.app.prod_backend_pipeline_stack.prod_stage.persistent_stack, domain_name='app.compactconnect.org'
        )

    def _when_testing_compact_resource_servers(self, persistent_stack):
        """
        Validates that each compact resource server in the persistent stack is created for every compact abbreviation and includes the expected set of scopes.
        
        Args:
            persistent_stack: The stack containing staff user resource servers to validate.
        
        Asserts:
            - All compact abbreviations have corresponding resource servers.
            - Each resource server defines exactly the scopes: 'admin', 'write', 'readGeneral', and 'readSSN'.
        """
        persistent_stack_template = Template.from_stack(persistent_stack)

        # Get the resource servers created in the persistent stack
        resource_servers = persistent_stack.staff_users.compact_resource_servers
        # We must confirm that these scopes are being explicitly created for each compact marked as active in the
        # environment, which are absolutely critical for the system to function as expected.
        self.assertEqual(
            sorted(persistent_stack.get_list_of_compact_abbreviations()),
            sorted(list(resource_servers.keys())),
        )

        for compact, resource_server in resource_servers.items():
            resource_server_properties = self.get_resource_properties_by_logical_id(
                persistent_stack.get_logical_id(resource_server.node.default_child),
                persistent_stack_template.find_resources(CfnUserPoolResourceServer.CFN_RESOURCE_TYPE_NAME),
            )
            # Ensure the compact resource servers are created with the expected scopes
            self.assertEqual(
                ['admin', 'write', 'readGeneral', 'readSSN'],
                [scope['ScopeName'] for scope in resource_server_properties['Scopes']],
                msg=f'Expected scopes for compact {compact} not found',
            )

    def test_synth_generates_compact_resource_servers_with_expected_scopes_for_staff_users_beta_stage(self):
        """
        Validates that compact resource servers for staff users in the beta stage have the expected scopes.
        
        Asserts that each compact resource server in the beta persistent stack includes only the allowed scopes for staff users.
        """
        persistent_stack = self.app.beta_backend_pipeline_stack.beta_backend_stage.persistent_stack
        self._when_testing_compact_resource_servers(persistent_stack)

    def test_synth_generates_compact_resource_servers_with_expected_scopes_for_staff_users_prod_stage(self):
        """
        Validates that compact resource servers in the prod persistent stack have the expected scopes for staff users.
        """
        persistent_stack = self.app.prod_backend_pipeline_stack.prod_stage.persistent_stack
        self._when_testing_compact_resource_servers(persistent_stack)

    def _when_testing_jurisdiction_resource_servers(self, persistent_stack, snapshot_name, overwrite_snapshot):
        """
        Validates that jurisdiction resource servers in the persistent stack have the expected scopes.
        
        Extracts and normalizes the configuration of jurisdiction resource servers from the stack,
        removes dynamic properties, sorts for consistency, and compares the result against a stored
        snapshot to ensure correctness. Updates the snapshot if overwrite is enabled.
        
        Args:
            persistent_stack: The stack containing the jurisdiction resource servers.
            snapshot_name: The name of the snapshot file for comparison.
            overwrite_snapshot: If True, overwrites the existing snapshot with the current configuration.
        """
        persistent_stack_template = Template.from_stack(persistent_stack)

        # Get the jurisdiction resource servers created in the persistent stack
        resource_servers = persistent_stack.staff_users.jurisdiction_resource_servers
        # We must confirm that these scopes are being explicitly created for each active jurisdiction
        # which are absolutely critical for the system to function as expected.
        # If a new jurisdiction is made active within the system, this test will need to be updated
        jurisdiction_resource_server_config = []
        for _jurisdiction, resource_server in resource_servers.items():
            resource_server_properties = self.get_resource_properties_by_logical_id(
                persistent_stack.get_logical_id(resource_server.node.default_child),
                persistent_stack_template.find_resources(CfnUserPoolResourceServer.CFN_RESOURCE_TYPE_NAME),
            )
            # remove dynamic user pool id
            del resource_server_properties['UserPoolId']
            jurisdiction_resource_server_config.append(resource_server_properties)

        # sort the resource server list by jurisdiction for consistency
        jurisdiction_resource_server_config.sort(key=lambda jurisdiction: jurisdiction['Identifier'])
        # sort the scopes within the resource server by name for consistency
        for resource_server in jurisdiction_resource_server_config:
            resource_server['Scopes'].sort(key=lambda scope: scope['ScopeName'])
        # this will only include resource server scopes for compacts/jurisdictions that are marked as active
        # for the environment
        self.compare_snapshot(
            jurisdiction_resource_server_config,
            snapshot_name,
            overwrite_snapshot=overwrite_snapshot,
        )

    def test_synth_generates_jurisdiction_resource_servers_with_expected_scopes_for_staff_users(self):
        """
        Verifies that jurisdiction resource servers for staff users are created with the expected scopes.
        
        This test compares the synthesized configuration against a stored snapshot, ensuring consistency across all environments.
        """
        persistent_stack = self.app.prod_backend_pipeline_stack.prod_stage.persistent_stack
        self._when_testing_jurisdiction_resource_servers(
            persistent_stack=persistent_stack,
            snapshot_name='JURISDICTION_RESOURCE_SERVER_CONFIGURATION',
            overwrite_snapshot=False,
        )

    def test_cognito_using_recommended_security_in_prod(self):
        """
        Validates that Cognito user pools in the production stack enforce recommended security settings.
        
        Ensures all user pools have advanced security mode and MFA enabled, each has a risk configuration blocking account takeover and compromised credentials, and no user pool clients allow the implicit OAuth grant flow.
        """
        stack = self.app.prod_backend_pipeline_stack.prod_stage.persistent_stack
        template = Template.from_stack(stack)

        # Make sure both user pools match the security settings above
        user_pools = template.find_resources(
            CfnUserPool.CFN_RESOURCE_TYPE_NAME,
            props={'Properties': {'UserPoolAddOns': {'AdvancedSecurityMode': 'ENFORCED'}, 'MfaConfiguration': 'ON'}},
        )
        number_of_user_pools = len(user_pools)

        # Check risk configurations
        risk_configurations = template.find_resources(
            CfnUserPoolRiskConfigurationAttachment.CFN_RESOURCE_TYPE_NAME,
            props={
                'Properties': {
                    'AccountTakeoverRiskConfiguration': {
                        'Actions': {
                            'HighAction': {'EventAction': 'BLOCK', 'Notify': True},
                            'LowAction': {'EventAction': 'BLOCK', 'Notify': True},
                            'MediumAction': {'EventAction': 'BLOCK', 'Notify': True},
                        }
                    },
                    'CompromisedCredentialsRiskConfiguration': {'Actions': {'EventAction': 'BLOCK'}},
                }
            },
        )
        # Every user pool should have this risk configuration
        self.assertEqual(number_of_user_pools, len(risk_configurations))

        # Verify that we're not allowing the implicit grant flow in any of our clients
        implicit_grant_clients = template.find_resources(
            CfnUserPoolClient.CFN_RESOURCE_TYPE_NAME,
            props={'Properties': {'AllowedOAuthFlows': Match.array_with(['implicit'])}},
        )
        self.assertEqual(0, len(implicit_grant_clients))

    def test_synth_generates_python_lambda_layer_with_ssm_parameter(self):
        """
        Verifies that the Python Lambda layer SSM parameter and its associated Lambda layer version are correctly defined in the test persistent stack.
        
        Asserts that the SSM parameter for the Lambda layer ARN has the expected name and that the referenced Lambda layer version supports the Python 3.12 runtime.
        """
        persistent_stack = self.app.test_backend_pipeline_stack.test_stage.persistent_stack
        persistent_stack_template = Template.from_stack(persistent_stack)

        # Ensure our provider user pool is created with expected custom attributes
        lambda_layer_parameter_properties = self.get_resource_properties_by_logical_id(
            persistent_stack.get_logical_id(persistent_stack.lambda_layer_ssm_parameter.node.default_child),
            persistent_stack_template.find_resources(CfnParameter.CFN_RESOURCE_TYPE_NAME),
        )

        # assert that the parameter name matches expected
        self.assertEqual('/deployment/lambda/layers/common-python-layer-arn', lambda_layer_parameter_properties['Name'])

        lambda_layer_parameter_properties = self.get_resource_properties_by_logical_id(
            lambda_layer_parameter_properties['Value']['Ref'],
            persistent_stack_template.find_resources(CfnLayerVersion.CFN_RESOURCE_TYPE_NAME),
        )

        # the other properties are dynamic, so here we just check to make sure it exists
        self.assertEqual(['python3.12'], lambda_layer_parameter_properties['CompatibleRuntimes'])

    def test_synth_generates_provider_users_bucket_with_event_handler(self):
        """
        Verifies that the provider users S3 bucket is configured with an event handler Lambda.
        
        Asserts that a custom resource sets up S3 bucket notifications for object creation events to trigger the correct Lambda function, and that the Lambda handler is set to 'handlers.provider_s3_events.process_provider_s3_events'.
        """
        persistent_stack = self.app.test_backend_pipeline_stack.test_stage.persistent_stack
        persistent_stack_template = Template.from_stack(persistent_stack)

        provider_users_bucket_event_lambda_logical_id = persistent_stack.get_logical_id(
            persistent_stack.provider_users_bucket.process_events_handler.node.default_child
        )

        persistent_stack_template.has_resource(
            type='Custom::S3BucketNotifications',
            props={
                'Properties': {
                    'BucketName': {
                        'Ref': persistent_stack.get_logical_id(
                            persistent_stack.provider_users_bucket.node.default_child
                        )
                    },
                    'NotificationConfiguration': {
                        'LambdaFunctionConfigurations': [
                            {
                                'Events': ['s3:ObjectCreated:*'],
                                'LambdaFunctionArn': {
                                    'Fn::GetAtt': [provider_users_bucket_event_lambda_logical_id, 'Arn']
                                },
                            }
                        ]
                    },
                }
            },
        )

        # ensure lambda points to expected handler
        provider_users_bucket_handler = self.get_resource_properties_by_logical_id(
            provider_users_bucket_event_lambda_logical_id,
            persistent_stack_template.find_resources(CfnFunction.CFN_RESOURCE_TYPE_NAME),
        )

        self.assertEqual(
            'handlers.provider_s3_events.process_provider_s3_events', provider_users_bucket_handler['Handler']
        )


class TestBackendPipelineVulnerable(TestCase):
    @patch.dict(os.environ, {'CDK_DEFAULT_ACCOUNT': '000000000000', 'CDK_DEFAULT_REGION': 'us-east-1'})
    def test_app_refuses_to_synth_with_prod_vulnerable(self):
        with open('cdk.json') as f:
            context = json.load(f)['context']
        with open('cdk.context.prod-example.json') as f:
            ssm_context = json.load(f)['ssm_context']

        # Suppresses lambda bundling for tests
        context['aws:cdk:bundling-stacks'] = []

        # Try to set VULNERABLE testing security profile in prod
        ssm_context['environments']['prod']['security_profile'] = 'VULNERABLE'
        context['ssm_context'] = ssm_context
        # The PipelineStack will read `ssm_context` from Systems Manager (SSM) ParameterStore.
        # To simulate the context being retrieved from SSM, we will package the context in the way
        # it is persisted to local context after being retrieved from SSM:
        pipeline_context = context['ssm_context']['environments']['pipeline']
        context[
            f'ssm:account={pipeline_context["account_id"]}'
            ':parameterName=prod-compact-connect-context'
            f':region={pipeline_context["region"]}'
        ] = json.dumps(ssm_context)

        with self.assertRaises(ValueError):
            CompactConnectApp(context=context)


class TestFrontendPipeline(TstAppABC, TestCase):
    @classmethod
    def get_context(cls):
        with open('cdk.json') as f:
            context = json.load(f)['context']
        # For pipeline deployments, the pipelines pull their CDK context values from SSM Parameter Store, rather
        # than the cdk.context.json files used in local development. We can override the context values used in the
        # tests by adding values here.

        # Suppresses lambda bundling for tests
        context['aws:cdk:bundling-stacks'] = []

        return context

    def test_synth_pipeline(self):
        """
        Test infrastructure as deployed via the pipeline
        """
        # Identify any findings from our AwsSolutions rule sets
        self._check_no_stack_annotations(self.app.deployment_resources_stack)
        self._check_no_stack_annotations(self.app.test_frontend_pipeline_stack)
        self._check_no_stack_annotations(self.app.prod_frontend_pipeline_stack)
        for stage in (
            self.app.test_frontend_pipeline_stack.pre_prod_frontend_stage,
            self.app.beta_frontend_pipeline_stack.beta_frontend_stage,
            self.app.prod_frontend_pipeline_stack.prod_frontend_stage,
        ):
            self._check_no_frontend_stage_annotations(stage)

        for frontend_deployment_stack in (
            self.app.test_frontend_pipeline_stack.pre_prod_frontend_stage.frontend_deployment_stack,
            self.app.beta_frontend_pipeline_stack.beta_frontend_stage.frontend_deployment_stack,
            self.app.prod_frontend_pipeline_stack.prod_frontend_stage.frontend_deployment_stack,
        ):
            self._inspect_frontend_deployment_stack(frontend_deployment_stack)
