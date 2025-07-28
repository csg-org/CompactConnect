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
        Test infrastructure as deployed via the pipeline
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
            # Check resource counts and emit warnings/errors if thresholds are exceeded
            self._check_backend_stage_resource_counts(stage)

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

        self._inspect_provider_users_stack(
            self.app.test_backend_pipeline_stack.test_stage.provider_users_stack,
            domain_name='app.test.compactconnect.org',
            allow_local_ui=True,
        )

        self._inspect_provider_users_stack(
            self.app.beta_backend_pipeline_stack.beta_backend_stage.provider_users_stack,
            domain_name='app.beta.compactconnect.org',
            allow_local_ui=False,
        )

        self._inspect_provider_users_stack(
            self.app.prod_backend_pipeline_stack.prod_stage.provider_users_stack,
            domain_name='app.compactconnect.org',
        )

    def _when_testing_compact_resource_servers(self, persistent_stack):
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
        persistent_stack = self.app.beta_backend_pipeline_stack.beta_backend_stage.persistent_stack
        self._when_testing_compact_resource_servers(persistent_stack)

    def test_synth_generates_compact_resource_servers_with_expected_scopes_for_staff_users_prod_stage(self):
        persistent_stack = self.app.prod_backend_pipeline_stack.prod_stage.persistent_stack
        self._when_testing_compact_resource_servers(persistent_stack)

    def _when_testing_jurisdiction_resource_servers(self, persistent_stack, snapshot_name, overwrite_snapshot):
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
        Test that the jurisdiction resource servers are created with the expected scopes
        for the staff users. This setup is now environment agnostic, so whatever is shown
        in this snapshot will be applied to all environments.
        """
        persistent_stack = self.app.prod_backend_pipeline_stack.prod_stage.persistent_stack
        self._when_testing_jurisdiction_resource_servers(
            persistent_stack=persistent_stack,
            snapshot_name='JURISDICTION_RESOURCE_SERVER_CONFIGURATION',
            overwrite_snapshot=False,
        )

    def test_cognito_using_recommended_security_in_prod(self):
        persistent_stack = self.app.prod_backend_pipeline_stack.prod_stage.persistent_stack
        persistent_stack_template = Template.from_stack(persistent_stack)
        provider_users_stack = self.app.prod_backend_pipeline_stack.prod_stage.provider_users_stack
        provider_users_stack_template = Template.from_stack(provider_users_stack)

        for template in [persistent_stack_template, provider_users_stack_template]:
            # Make sure both user pools match the security settings above
            user_pools = template.find_resources(
                CfnUserPool.CFN_RESOURCE_TYPE_NAME,
                props={
                    'Properties': {'UserPoolAddOns': {'AdvancedSecurityMode': 'ENFORCED'}, 'MfaConfiguration': 'ON'}
                },
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
