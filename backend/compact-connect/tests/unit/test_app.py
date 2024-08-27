import json
import os
from unittest import TestCase
from unittest.mock import patch

from aws_cdk import Stack
from aws_cdk.assertions import Annotations, Match, Template
from aws_cdk.aws_apigateway import CfnMethod
from aws_cdk.aws_cognito import CfnUserPoolClient

from app import CompactConnectApp
from stacks.api_stack import ApiStack
from stacks.persistent_stack import PersistentStack


class TestApp(TestCase):

    def test_no_compact_jurisdiction_name_clash(self):
        """
        Because compact and jurisdiction abbreviations share space in access token scopes, we need to ensure that
        there are no naming clashes between the two.
        """
        with open('cdk.json', 'r') as f:
            context = json.load(f)['context']
        jurisdictions = set(context['jurisdictions'])
        compacts = set(context['compacts'])
        # The '#' character is used in the composite identifiers in the database. In order to prevent confusion in
        # parsing the identifiers, we either have to carefully escape all '#' characters that might show up in compact
        # or jurisdiction abbreviations or simply not allow them. Since the abbreviations seem unlikely to include a #
        # character, the latter seems reasonable.
        for jurisdiction in jurisdictions:
            self.assertNotIn('#', jurisdiction, "'#' not allowed in jurisdiction abbreviations!")
        for compact in compacts:
            self.assertNotIn('#', compact, "'#' not allowed in compact abbreviations!")
        self.assertFalse(jurisdictions.intersection(compacts), 'Compact vs jurisdiction name clash!')

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
        with open('cdk.context.production-example.json', 'r') as f:
            context['ssm_context'] = json.load(f)['ssm_context']

        # Suppresses lambda bundling for tests
        context['aws:cdk:bundling-stacks'] = []

        app = CompactConnectApp(context=context)

        # Identify any findings from our AwsSolutions rule sets
        for stack in (
                app.pipeline_stack,
                app.pipeline_stack.test_stage.api_stack,
                app.pipeline_stack.test_stage.ui_stack,
                app.pipeline_stack.test_stage.ingest_stack,
                app.pipeline_stack.test_stage.persistent_stack,
                app.pipeline_stack.prod_stage.api_stack,
                app.pipeline_stack.prod_stage.ui_stack,
                app.pipeline_stack.prod_stage.persistent_stack,
                app.pipeline_stack.prod_stage.ingest_stack
        ):
            self._check_no_annotations(stack)

        for api_stack in (
            app.pipeline_stack.test_stage.api_stack,
            app.pipeline_stack.prod_stage.api_stack
        ):
            self._inspect_api_stack(api_stack)

        self._inspect_persistent_stack(
            app.pipeline_stack.test_stage.persistent_stack,
            domain_name='app.test.compactconnect.org',
            allow_local_ui=True
        )
        self._inspect_persistent_stack(
            app.pipeline_stack.prod_stage.persistent_stack,
            domain_name='app.compactconnect.org'
        )

    def test_synth_sandbox(self):
        """
        Test infrastructure as deployed in a developer's sandbox
        """
        with open('cdk.json', 'r') as f:
            context = json.load(f)['context']
        with open('cdk.context.sandbox-example.json', 'r') as f:
            context.update(json.load(f))

        # Suppresses lambda bundling for tests
        context['aws:cdk:bundling-stacks'] = []

        app = CompactConnectApp(context=context)

        # Identify any findings from our AwsSolutions rule sets
        self._check_no_annotations(app.sandbox_stage.persistent_stack)
        self._check_no_annotations(app.sandbox_stage.ui_stack)
        self._check_no_annotations(app.sandbox_stage.api_stack)
        self._check_no_annotations(app.sandbox_stage.ingest_stack)

        self._inspect_api_stack(app.sandbox_stage.api_stack)
        self._inspect_persistent_stack(
            app.sandbox_stage.persistent_stack,
            domain_name='app.justin.compactconnect.org',
            allow_local_ui=True
        )

    def test_synth_sandbox_no_domain(self):
        """
        Test infrastructure as deployed in a developer's sandbox:
        In the case where they opt _not_ to set up a hosted zone and domain name for their sandbox,
        we will skip setting up domain names and DNS records for the API and UI.
        """
        with open('cdk.json', 'r') as f:
            context = json.load(f)['context']
        with open('cdk.context.sandbox-example.json', 'r') as f:
            context.update(json.load(f))
        # Drop domain name to ensure we still handle the optional DNS setup
        del context['ssm_context']['environments'][context['environment_name']]['domain_name']

        # Suppresses lambda bundling for tests
        context['aws:cdk:bundling-stacks'] = []

        app = CompactConnectApp(context=context)

        # Identify any findings from our AwsSolutions rule sets
        self._check_no_annotations(app.sandbox_stage.persistent_stack)
        self._check_no_annotations(app.sandbox_stage.ui_stack)
        self._check_no_annotations(app.sandbox_stage.api_stack)
        self._check_no_annotations(app.sandbox_stage.ingest_stack)

        self._inspect_api_stack(app.sandbox_stage.api_stack)
        self._inspect_persistent_stack(
            app.sandbox_stage.persistent_stack,
            allow_local_ui=True
        )

    def test_synth_no_ui_raises_value_error(self):
        """
        If a developer tries to deploy this app without either a domain name or allowing a local UI, the app
        should fail to synthesize.
        """
        with open('cdk.json', 'r') as f:
            context = json.load(f)['context']
        with open('cdk.context.sandbox-example.json', 'r') as f:
            context.update(json.load(f))
        del context['ssm_context']['environments'][context['environment_name']]['domain_name']
        del context['ssm_context']['environments'][context['environment_name']]['allow_local_ui']

        # Suppresses lambda bundling for tests
        context['aws:cdk:bundling-stacks'] = []

        with self.assertRaises(ValueError):
            CompactConnectApp(context=context)

    def test_synth_local_ui_port_override(self):
        """
        Test infrastructure as deployed in a developer's sandbox
        """
        with open('cdk.json', 'r') as f:
            context = json.load(f)['context']
        with open('cdk.context.sandbox-example.json', 'r') as f:
            context.update(json.load(f))

        del context['ssm_context']['environments'][context['environment_name']]['domain_name']
        context['ssm_context']['environments'][context['environment_name']]['local_ui_port'] = '5432'

        # Suppresses lambda bundling for tests
        context['aws:cdk:bundling-stacks'] = []

        app = CompactConnectApp(context=context)

        # Identify any findings from our AwsSolutions rule sets
        self._check_no_annotations(app.sandbox_stage.persistent_stack)
        self._check_no_annotations(app.sandbox_stage.ui_stack)
        self._check_no_annotations(app.sandbox_stage.api_stack)
        self._check_no_annotations(app.sandbox_stage.ingest_stack)

        self._inspect_persistent_stack(
            app.sandbox_stage.persistent_stack,
            allow_local_ui=True,
            local_ui_port='5432'
        )
        self._inspect_api_stack(app.sandbox_stage.api_stack)

    def _inspect_persistent_stack(
            self,
            persistent_stack: PersistentStack, *,
            domain_name: str = None,
            allow_local_ui: bool = False,
            local_ui_port: str = None
    ):
        # Make sure our local port ui setting overrides the default
        persistent_stack_template = Template.from_stack(persistent_stack)

        callbacks = []
        if domain_name is not None:
            callbacks.append(f'https://{domain_name}/auth/callback')
        if allow_local_ui:
            # 3018 is default
            local_ui_port = '3018' if not local_ui_port else local_ui_port
            callbacks.append(f'http://localhost:{local_ui_port}/auth/callback')

        # Ensure our Staff user pool is configured with the expected callbacks
        persistent_stack_template.has_resource(
            type=CfnUserPoolClient.CFN_RESOURCE_TYPE_NAME,
            props={
                'Properties': {
                    'CallbackURLs': callbacks
                }
            }
        )

    def _inspect_api_stack(self, api_stack: ApiStack):
        api_template = Template.from_stack(api_stack)

        with self.assertRaises(RuntimeError):
            # This is an indicator of unintentional (and invalid) authorizer configuration in the API.
            # Not matching is desired in this case and raises a RuntimeError.
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
