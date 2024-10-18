import json
import os
from unittest import TestCase
from unittest.mock import patch

from app import CompactConnectApp
from aws_cdk.assertions import Match, Template
from aws_cdk.aws_cognito import CfnUserPool, CfnUserPoolClient, CfnUserPoolRiskConfigurationAttachment
from aws_cdk.aws_lambda import CfnFunction, CfnLayerVersion
from aws_cdk.aws_ssm import CfnParameter

from tests.app.base import TstAppABC


class TestPipeline(TstAppABC, TestCase):
    @classmethod
    def get_context(cls):
        with open('cdk.json') as f:
            context = json.load(f)['context']
        with open('cdk.context.production-example.json') as f:
            context['ssm_context'] = json.load(f)['ssm_context']

        # Suppresses lambda bundling for tests
        context['aws:cdk:bundling-stacks'] = []

        return context

    def test_synth_pipeline(self):
        """
        Test infrastructure as deployed via the pipeline
        """
        # Identify any findings from our AwsSolutions rule sets
        self._check_no_stack_annotations(self.app.pipeline_stack)
        for stage in (
            self.app.pipeline_stack.test_stage,
            self.app.pipeline_stack.prod_stage,
        ):
            self._check_no_stage_annotations(stage)

        for api_stack in (self.app.pipeline_stack.test_stage.api_stack, self.app.pipeline_stack.prod_stage.api_stack):
            with self.subTest(api_stack.stack_name):
                self._inspect_api_stack(api_stack)

        self._inspect_persistent_stack(
            self.app.pipeline_stack.test_stage.persistent_stack,
            domain_name='app.test.compactconnect.org',
            allow_local_ui=True,
        )
        self._inspect_persistent_stack(
            self.app.pipeline_stack.prod_stage.persistent_stack, domain_name='app.compactconnect.org'
        )

    def test_cognito_using_recommended_security_in_prod(self):
        stack = self.app.pipeline_stack.prod_stage.persistent_stack
        template = Template.from_stack(stack)

        # Make sure both user pools match the security settings above
        user_pools = template.find_resources(
            CfnUserPool.CFN_RESOURCE_TYPE_NAME,
            props={'Properties': {'UserPoolAddOns': {'AdvancedSecurityMode': 'ENFORCED'}, 'MfaConfiguration': 'ON'}},
        )
        # Two user pools, we should find two matches
        self.assertEqual(2, len(user_pools))

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
        # One for each of two user pools
        self.assertEqual(2, len(risk_configurations))

        # Verify that we're not allowing the implicit grant flow in any of our clients
        implicit_grant_clients = template.find_resources(
            CfnUserPoolClient.CFN_RESOURCE_TYPE_NAME,
            props={'Properties': {'AllowedOAuthFlows': Match.array_with(['implicit'])}},
        )
        self.assertEqual(0, len(implicit_grant_clients))

    def test_synth_generates_compact_configuration_upload_custom_resource_with_expected_configuration_data(self):
        persistent_stack = self.app.pipeline_stack.test_stage.persistent_stack
        persistent_stack_template = Template.from_stack(persistent_stack)

        # Ensure our provider user pool is created with expected custom attributes
        compact_configuration_uploader_custom_resource = self.get_resource_properties_by_logical_id(
            persistent_stack.get_logical_id(
                persistent_stack.compact_configuration_upload.compact_configuration_uploader_custom_resource.node.default_child
            ),
            persistent_stack_template.find_resources('Custom::CompactConfigurationUpload'),
        )
        # we don't care about ordering of the jurisdictions, but the snapshot is sensitive to the order,
        # so we ensure to sort the jurisdictions before comparing
        sorted_compact_configuration = self._sort_compact_configuration_input(
            json.loads(compact_configuration_uploader_custom_resource['compact_configuration'])
        )

        # Assert that the compact_configuration property is set to the expected values
        # If the configuration values for any jurisdiction changes, the snapshot will need to be updated.
        self.compare_snapshot(
            actual=sorted_compact_configuration,
            snapshot_name='COMPACT_CONFIGURATION_UPLOADER_INPUT',
            overwrite_snapshot=False,
        )

    def test_synth_generates_python_lambda_layer_with_ssm_parameter(self):
        persistent_stack = self.app.pipeline_stack.test_stage.persistent_stack
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
        persistent_stack = self.app.pipeline_stack.test_stage.persistent_stack
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

    @staticmethod
    def _sort_compact_configuration_input(compact_configuration_input: dict) -> dict:
        """
        Sort the compact configuration input by compact name and then by jurisdiction postal abbreviation.
        This ensures the snapshot comparison is consistent.
        """
        compact_configuration_input['compacts'] = sorted(
            compact_configuration_input['compacts'], key=lambda compact: compact['compactName']
        )
        for compact_name, jurisdictions in compact_configuration_input['jurisdictions'].items():
            compact_configuration_input['jurisdictions'][compact_name] = sorted(
                jurisdictions, key=lambda jurisdiction: jurisdiction['postalAbbreviation']
            )

        return compact_configuration_input


class TestPipelineVulnerable(TestCase):
    @patch.dict(os.environ, {'CDK_DEFAULT_ACCOUNT': '000000000000', 'CDK_DEFAULT_REGION': 'us-east-1'})
    def test_app_refuses_to_synth_with_prod_vulnerable(self):
        with open('cdk.json') as f:
            context = json.load(f)['context']
        with open('cdk.context.production-example.json') as f:
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
            f'ssm:account={pipeline_context['account_id']}'
            ':parameterName=compact-connect-context'
            f':region={pipeline_context['region']}'
        ] = json.dumps(ssm_context)

        with self.assertRaises(ValueError):
            CompactConnectApp(context=context)
