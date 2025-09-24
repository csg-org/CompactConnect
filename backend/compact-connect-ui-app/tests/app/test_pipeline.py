import json
from unittest import TestCase

from aws_cdk.assertions import Match, Template

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

    def test_predictable_pipeline_role_names_created(self):
        """Test that pipelines create roles with predictable names for bootstrap trust policies."""
        # Test frontend pipeline role naming - roles are environment-specific
        frontend_test_cases = [
            (self.app.test_frontend_pipeline_stack, 'CompactConnect-test-Frontend-CrossAccountRole'),
            (self.app.beta_frontend_pipeline_stack, 'CompactConnect-beta-Frontend-CrossAccountRole'),
            (self.app.prod_frontend_pipeline_stack, 'CompactConnect-prod-Frontend-CrossAccountRole'),
        ]

        for frontend_stack, expected_role_name in frontend_test_cases:
            with self.subTest(role=expected_role_name):
                frontend_template = Template.from_stack(frontend_stack)

                # Look for the predictable frontend pipeline role
                frontend_roles = frontend_template.find_resources(
                    'AWS::IAM::Role', props={'Properties': {'RoleName': expected_role_name}}
                )
                self.assertEqual(
                    len(frontend_roles),
                    1,
                    f'Should have exactly one frontend pipeline role with name {expected_role_name}',
                )

    def test_pipeline_role_trust_policies(self):
        """Test that pipeline roles have correct trust policies for CodePipeline service."""
        # Test that all pipeline roles trust the CodePipeline service
        # Note: Roles are environment-specific to avoid naming conflicts
        test_cases = [
            (self.app.test_frontend_pipeline_stack, 'CompactConnect-test-Frontend-CrossAccountRole'),
            (self.app.beta_frontend_pipeline_stack, 'CompactConnect-beta-Frontend-CrossAccountRole'),
            (self.app.prod_frontend_pipeline_stack, 'CompactConnect-prod-Frontend-CrossAccountRole'),
        ]

        for stack, expected_role_name in test_cases:
            with self.subTest(role=expected_role_name):
                template = Template.from_stack(stack)

                # Verify pipeline role trusts CodePipeline service
                template.has_resource_properties(
                    'AWS::IAM::Role',
                    {
                        'RoleName': expected_role_name,
                        'AssumeRolePolicyDocument': {
                            'Statement': Match.array_with(
                                [
                                    {
                                        'Effect': 'Allow',
                                        'Principal': {'Service': 'codepipeline.amazonaws.com'},
                                        'Action': 'sts:AssumeRole',
                                    }
                                ]
                            )
                        },
                    },
                )

    def test_pipeline_uses_predictable_roles_for_actions(self):
        """Test that pipelines are configured to use predictable roles for all actions."""
        # Test that pipelines use the role parameter and use_pipeline_role_for_actions=True
        frontend_pipeline_stack = self.app.test_frontend_pipeline_stack
        frontend_template = Template.from_stack(frontend_pipeline_stack)

        # The pipeline should reference the predictable cross-account role
        # This validates that our role parameter is being used
        frontend_template.has_resource_properties(
            'AWS::CodePipeline::Pipeline',
            {'RoleArn': {'Fn::GetAtt': [Match.string_like_regexp('.*FrontendCrossAccountRole.*'), 'Arn']}},
        )
