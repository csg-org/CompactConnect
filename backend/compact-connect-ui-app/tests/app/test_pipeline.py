import json
from unittest import TestCase

from tests.app.base import TstAppABC


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
