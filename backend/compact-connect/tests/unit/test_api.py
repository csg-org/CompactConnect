import json
from unittest import TestCase

from aws_cdk.assertions import Template, Capture
from aws_cdk.aws_apigateway import CfnResource
from aws_cdk.aws_lambda import CfnFunction

from app import CompactConnectApp


class TestApi(TestCase):
    """
    These tests are focused on checking that the API stack is configured correctly.

    When adding or modifying API resources, a test should be added to ensure that the
    resource is created as expected.
    """

    def _when_testing_sandbox_stack_synth(self):
        with open('cdk.json', 'r') as f:
            context = json.load(f)['context']
        with open('cdk.context.sandbox-example.json', 'r') as f:
            context.update(json.load(f))

        # Suppresses lambda bundling for tests
        context['aws:cdk:bundling-stacks'] = []

        app = CompactConnectApp(context=context)
        api_stack_template = Template.from_stack(app.sandbox_stage.api_stack)

        return api_stack_template

    def test_synth_generates_provider_users_resource(self):
        api_stack_template = self._when_testing_sandbox_stack_synth()

        parent_id_capture = Capture()
        # Ensure the resource is created with expected path
        api_stack_template.has_resource_properties(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                "ParentId": parent_id_capture,
                "PathPart": "provider-users"
            })

        self.assertIn("LicenseApiv1", parent_id_capture.as_object()["Ref"])

    def test_synth_generates_get_provider_users_me_endpoint_resource(self):
        api_stack_template = self._when_testing_sandbox_stack_synth()

        parent_id_capture = Capture()
        # Ensure the resource is created with expected path
        api_stack_template.has_resource_properties(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                "ParentId": parent_id_capture,
                "PathPart": "me"
            })

        self.assertIn("LicenseApiv1providerusers", parent_id_capture.as_object()["Ref"])

        # ensure the handler is created
        api_stack_template.has_resource_properties(
            type=CfnFunction.CFN_RESOURCE_TYPE_NAME,
            props={
                "Handler": "handlers.provider_users.get_provider_user_me"
            })
