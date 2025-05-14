import json
from unittest import TestCase

from app import CompactConnectApp

from tests.app.base import TstAppABC


class TstSandbox(TstAppABC, TestCase):
    @classmethod
    def get_context(cls):
        with open('cdk.json') as f:
            context = json.load(f)['context']
        with open('cdk.context.sandbox-example.json') as f:
            context.update(json.load(f))

        # Suppresses lambda bundling for tests
        context['aws:cdk:bundling-stacks'] = []

        return context


class TestSandbox(TstSandbox):
    def test_synth_security(self):
        """
        Test infrastructure as deployed in a developer's sandbox
        """
        # Identify any findings from our AwsSolutions rule sets
        self._check_no_backend_stage_annotations(self.app.sandbox_backend_stage)

    def test_api_stack(self):
        self._inspect_api_stack(self.app.sandbox_backend_stage.api_stack)

        self._inspect_persistent_stack(
            self.app.sandbox_backend_stage.persistent_stack,
            domain_name='app.justin.compactconnect.org',
            allow_local_ui=True,
        )


class TestSandboxNoDomain(TstSandbox):
    """
    Test infrastructure as deployed in a developer's sandbox:
    In the case where they opt _not_ to set up a hosted zone and domain name for their sandbox,
    we will skip setting up domain names and DNS records for the API and UI.
    """

    @classmethod
    def get_context(cls):
        context = super().get_context()

        # Drop domain name to ensure we still handle the optional DNS setup
        del context['ssm_context']['environments'][context['environment_name']]['domain_name']
        return context

    def test_synth_sandbox_no_domain(self):
        self._check_no_backend_stage_annotations(self.app.sandbox_backend_stage)

        self._inspect_api_stack(self.app.sandbox_backend_stage.api_stack)

        self._inspect_persistent_stack(self.app.sandbox_backend_stage.persistent_stack, allow_local_ui=True)


class TestSandboxLocalUiPortOverride(TstSandbox):
    """
    Test infrastructure as deployed in a developer's sandbox
    """

    @classmethod
    def get_context(cls):
        context = super().get_context()

        # Drop domain name to ensure we still handle the optional DNS setup
        del context['ssm_context']['environments'][context['environment_name']]['domain_name']
        context['ssm_context']['environments'][context['environment_name']]['local_ui_port'] = '5432'

        return context

    def test_synth_local_ui_port_override(self):
        self._check_no_backend_stage_annotations(self.app.sandbox_backend_stage)

        self._inspect_api_stack(self.app.sandbox_backend_stage.api_stack)

        self._inspect_persistent_stack(
            self.app.sandbox_backend_stage.persistent_stack, allow_local_ui=True, local_ui_port='5432'
        )


class TestSandboxNoUi(TestCase):
    """
    If a developer tries to deploy this app without either a domain name or allowing a local UI, the app
    should fail to synthesize.
    """

    def test_synth_no_ui_raises_value_error(self):
        with open('cdk.json') as f:
            context = json.load(f)['context']
        with open('cdk.context.sandbox-example.json') as f:
            context.update(json.load(f))

        # Suppresses lambda bundling for tests
        context['aws:cdk:bundling-stacks'] = []

        del context['ssm_context']['environments'][context['environment_name']]['domain_name']
        del context['ssm_context']['environments'][context['environment_name']]['allow_local_ui']

        with self.assertRaises(ValueError):
            CompactConnectApp(context=context)
