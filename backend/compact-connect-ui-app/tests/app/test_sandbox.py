import json
from unittest import TestCase

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

    def test_synth_pipeline(self):
        """
        Test infrastructure as deployed to a sandbox
        """
        # Identify any findings from our AwsSolutions rule sets
        self._check_no_frontend_stage_annotations(self.app.sandbox_frontend_stage)
        self._inspect_frontend_deployment_stack(self.app.sandbox_frontend_stage.frontend_deployment_stack)
