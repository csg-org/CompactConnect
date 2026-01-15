import json
import os
from unittest import TestCase
from unittest.mock import patch

from aws_cdk.assertions import Match, Template
from aws_cdk.aws_cognito import (
    CfnUserPool,
    CfnUserPoolClient,
    CfnUserPoolResourceServer,
    CfnUserPoolRiskConfigurationAttachment,
)
from aws_cdk.aws_lambda import CfnLayerVersion
from aws_cdk.aws_ssm import CfnParameter

from app import CompactConnectApp
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

        self._inspect_state_auth_stack(
            self.app.test_backend_pipeline_stack.test_stage.state_auth_stack,
        )

        self._inspect_state_auth_stack(
            self.app.beta_backend_pipeline_stack.beta_backend_stage.state_auth_stack,
        )

        self._inspect_state_auth_stack(
            self.app.prod_backend_pipeline_stack.prod_stage.state_auth_stack,
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

        # Make sure user pool matches the security settings above
        user_pools = persistent_stack_template.find_resources(
            CfnUserPool.CFN_RESOURCE_TYPE_NAME,
            props={'Properties': {'UserPoolAddOns': {'AdvancedSecurityMode': 'ENFORCED'}, 'MfaConfiguration': 'ON'}},
        )
        number_of_user_pools = len(user_pools)

        # Check risk configurations
        risk_configurations = persistent_stack_template.find_resources(
            CfnUserPoolRiskConfigurationAttachment.CFN_RESOURCE_TYPE_NAME,
            props={
                'Properties': {
                    'AccountTakeoverRiskConfiguration': {
                        'Actions': {
                            'HighAction': {'EventAction': 'MFA_REQUIRED', 'Notify': True},
                            'LowAction': {'EventAction': 'MFA_REQUIRED', 'Notify': True},
                            'MediumAction': {'EventAction': 'MFA_REQUIRED', 'Notify': True},
                        }
                    },
                    'CompromisedCredentialsRiskConfiguration': {'Actions': {'EventAction': 'BLOCK'}},
                }
            },
        )
        # Every user pool should have this risk configuration
        self.assertEqual(number_of_user_pools, len(risk_configurations))

        # Verify that we're not allowing the implicit grant flow in any of our clients
        implicit_grant_clients = persistent_stack_template.find_resources(
            CfnUserPoolClient.CFN_RESOURCE_TYPE_NAME,
            props={'Properties': {'AllowedOAuthFlows': Match.array_with(['implicit'])}},
        )
        self.assertEqual(0, len(implicit_grant_clients))

    def test_cognito_risk_configuration_includes_notify_configuration_when_domain_configured(self):
        """
        Test that when a domain name is configured and security profile is RECOMMENDED,
        the user pool risk configurations include the notify_configuration with a non-null from_ email address.
        """
        # Test prod stage which has domain configured and RECOMMENDED security
        persistent_stack = self.app.prod_backend_pipeline_stack.prod_stage.persistent_stack
        persistent_stack_template = Template.from_stack(persistent_stack)

        # Get all risk configurations first
        all_risk_configurations = persistent_stack_template.find_resources(
            CfnUserPoolRiskConfigurationAttachment.CFN_RESOURCE_TYPE_NAME,
        )

        # Find risk configurations that include notify_configuration
        risk_configurations_with_notify = persistent_stack_template.find_resources(
            CfnUserPoolRiskConfigurationAttachment.CFN_RESOURCE_TYPE_NAME,
            props={
                'Properties': {
                    'AccountTakeoverRiskConfiguration': {
                        'Actions': {
                            'HighAction': {'EventAction': 'MFA_REQUIRED', 'Notify': True},
                            'LowAction': {'EventAction': 'MFA_REQUIRED', 'Notify': True},
                            'MediumAction': {'EventAction': 'MFA_REQUIRED', 'Notify': True},
                        },
                        'NotifyConfiguration': Match.object_like(
                            {
                                'SourceArn': Match.any_value(),
                                'BlockEmail': Match.any_value(),
                                'NoActionEmail': Match.any_value(),
                                'From': Match.any_value(),
                            }
                        ),
                    },
                    'CompromisedCredentialsRiskConfiguration': {'Actions': {'EventAction': 'BLOCK'}},
                }
            },
        )

        # Every risk configuration should include notify_configuration when domain is configured
        self.assertEqual(len(all_risk_configurations), len(risk_configurations_with_notify))

        # Verify that each risk configuration has a non-null from_ email address
        for logical_id, resource in risk_configurations_with_notify.items():
            properties = resource['Properties']
            notify_config = properties['AccountTakeoverRiskConfiguration']['NotifyConfiguration']
            self.assertIsNotNone(notify_config['From'], f'Risk configuration {logical_id} missing from_ email address')
            self.assertIn(
                '@',
                notify_config['From'],
                f'Risk configuration {logical_id} has invalid from_ email address: {notify_config["From"]}',
            )
            self.assertIsNotNone(notify_config['SourceArn'], f'Risk configuration {logical_id} missing source_arn')
            self.assertIsNotNone(
                notify_config['BlockEmail'], f'Risk configuration {logical_id} missing block_email configuration'
            )

    def test_synth_generates_python_lambda_layer_with_ssm_parameter(self):
        persistent_stack = self.app.test_backend_pipeline_stack.test_stage.persistent_stack
        persistent_stack_template = Template.from_stack(persistent_stack)

        # Ensure we have a layer and parameter referencing that layer for each expected runtime
        for runtime in ['python3.12', 'python3.14']:
            layers = persistent_stack_template.find_resources(
                type=CfnLayerVersion.CFN_RESOURCE_TYPE_NAME,
                props={
                    'Properties': {
                        'Description': 'A layer for common code shared between python lambdas',
                        'CompatibleRuntimes': [runtime],
                    }
                },
            )
            # We expect exactly one for each runtime
            self.assertEqual(1, len(layers))
            persistent_stack_template.has_resource_properties(
                type=CfnParameter.CFN_RESOURCE_TYPE_NAME,
                props={'Value': {'Ref': list(layers.keys())[0]}},
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
