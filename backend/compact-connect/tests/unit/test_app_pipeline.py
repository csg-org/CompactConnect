import json
import os
from unittest import TestCase
from unittest.mock import patch

from aws_cdk.assertions import Template, Match
from aws_cdk.aws_cognito import CfnUserPool, CfnUserPoolRiskConfigurationAttachment, CfnUserPoolClient

from app import CompactConnectApp
from tests.unit.base import TstCompactConnectABC


class TestPipeline(TstCompactConnectABC, TestCase):
    @classmethod
    def get_context(cls):
        with open('cdk.json', 'r') as f:
            context = json.load(f)['context']
        with open('cdk.context.production-example.json', 'r') as f:
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

        for api_stack in (
            self.app.pipeline_stack.test_stage.api_stack,
            self.app.pipeline_stack.prod_stage.api_stack
        ):
            with self.subTest(api_stack.stack_name):
                self._inspect_api_stack(api_stack)

        self._inspect_persistent_stack(
            self.app.pipeline_stack.test_stage.persistent_stack,
            domain_name='app.test.compactconnect.org',
            allow_local_ui=True
        )
        self._inspect_persistent_stack(
            self.app.pipeline_stack.prod_stage.persistent_stack,
            domain_name='app.compactconnect.org'
        )

    def test_cognito_using_recommended_security_in_prod(self):
        stack = self.app.pipeline_stack.prod_stage.persistent_stack
        template = Template.from_stack(stack)

        # Make sure both user pools match the security settings above
        user_pools = template.find_resources(
            CfnUserPool.CFN_RESOURCE_TYPE_NAME,
            props={
                'Properties': {
                    'UserPoolAddOns': {
                        'AdvancedSecurityMode': 'ENFORCED'
                    },
                    'MfaConfiguration': 'ON'
                }
            }
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
                            'HighAction': {
                                'EventAction': 'BLOCK',
                                'Notify': True
                            },
                            'LowAction': {
                                'EventAction': 'BLOCK',
                                'Notify': True
                            },
                            'MediumAction': {
                                'EventAction': 'BLOCK',
                                'Notify': True
                            }
                        }
                    },
                    'CompromisedCredentialsRiskConfiguration': {
                        'Actions': {
                            'EventAction': 'BLOCK'
                        }
                    }
                }
            }
        )
        # One for each of two user pools
        self.assertEqual(2, len(risk_configurations))

        # Verify that we're not allowing the implicit grant flow in any of our clients
        implicit_grant_clients = template.find_resources(
            CfnUserPoolClient.CFN_RESOURCE_TYPE_NAME,
            props={
                'Properties': {
                    'AllowedOAuthFlows': Match.array_with([
                        'implicit'
                    ])
                }
            }
        )
        self.assertEqual(0, len(implicit_grant_clients))


class TestPipelineVulnerable(TestCase):
    @patch.dict(os.environ, {
        'CDK_DEFAULT_ACCOUNT': '000000000000',
        'CDK_DEFAULT_REGION': 'us-east-1'
    })
    def test_app_refuses_to_synth_with_prod_vulnerable(self):
        with open('cdk.json', 'r') as f:
            context = json.load(f)['context']
        with open('cdk.context.production-example.json', 'r') as f:
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
            f':region={pipeline_context['region']}'] = json.dumps(ssm_context)

        with self.assertRaises(ValueError):
            CompactConnectApp(context=context)
