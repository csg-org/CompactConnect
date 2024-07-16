import json
import os
from unittest import TestCase
from unittest.mock import patch

from aws_cdk import Stack
from aws_cdk.assertions import Annotations, Match, Template
from aws_cdk.aws_apigateway import CfnMethod

from app import CompactConnectApp
from stacks.api_stack import ApiStack


class TestApp(TestCase):

    @patch.dict(os.environ, {
        'CDK_DEFAULT_ACCOUNT': '000000000000',
        'CDK_DEFAULT_REGION': 'us-east-1'
    })
    def test_synth_pipeline(self):
        """
        Test infrastructure as deployed via the pipeline
        """
        with open('cdk.json', 'r') as f:
            context = json.load(f)['context']
        with open('cdk.context.example.json', 'r') as f:
            context['ssm_context'] = json.load(f)['ssm_context']

        # Suppresses lambda bundling for tests
        context['aws:cdk:bundling-stacks'] = []

        app = CompactConnectApp(context=context)

        # Identify any findings from our AwsSolutions or HIPAASecurity rule sets
        for stack in (
                app.pipeline_stack,
                app.pipeline_stack.test_stage.api_stack,
                app.pipeline_stack.test_stage.ui_stack,
                app.pipeline_stack.test_stage.persistent_stack,
                app.pipeline_stack.prod_stage.api_stack,
                app.pipeline_stack.prod_stage.ui_stack,
                app.pipeline_stack.prod_stage.persistent_stack
        ):
            self._check_no_annotations(stack)

        for api_stack in (
            app.pipeline_stack.test_stage.api_stack,
            app.pipeline_stack.prod_stage.api_stack
        ):
            self._inspect_api_stack(api_stack)

    def test_synth_sandbox(self):
        """
        Test infrastructure as deployed in a developer's sandbox
        """
        with open('cdk.json', 'r') as f:
            context = json.load(f)['context']
        with open('cdk.context.example.json', 'r') as f:
            context.update(json.load(f))
        context['sandbox'] = True
        context['environment_name'] = 'justin'
        context['ssm_context']['environments']['justin'] = {
            'account_id': '012345678901',
            'region': 'us-east-1'
        }

        # Suppresses lambda bundling for tests
        context['aws:cdk:bundling-stacks'] = []

        app = CompactConnectApp(context=context)

        # Identify any findings from our AwsSolutions or HIPAASecurity rule sets
        self._check_no_annotations(app.sandbox_stage.persistent_stack)
        self._check_no_annotations(app.sandbox_stage.ui_stack)
        self._check_no_annotations(app.sandbox_stage.api_stack)

        self._inspect_api_stack(app.sandbox_stage.api_stack)

    def _inspect_api_stack(self, api_stack: ApiStack):
        api_template = Template.from_stack(api_stack)

        with self.assertRaises(RuntimeError):
            # This is an indicator of unintentional (and invalid) authorizer configuration in the API
            # not matching is desired in this case and raises a RuntimeError
            api_template.has_resource(
                type=CfnMethod.CFN_RESOURCE_TYPE_NAME,
                props={
                    'Properties': {
                        'AuthorizationScopes': Match.any_value(),
                        'AuthorizationType': 'NONE'
                    }
                }
            )

    def _check_no_annotations(self, stack: Stack):
        errors = Annotations.from_stack(stack).find_error(
            '*',
            Match.string_like_regexp('.*')
        )
        self.assertEqual(0,
                         len(errors),
                         msg='\n'.join((f'{err.id}: {err.entry.data.strip()}' for err in errors)))

        warnings = Annotations.from_stack(stack).find_warning(
            '*',
            Match.string_like_regexp('.*')
        )
        self.assertEqual(0,
                         len(warnings),
                         msg='\n'.join((f'{warn.id}: {warn.entry.data.strip()}' for warn in warnings)))
