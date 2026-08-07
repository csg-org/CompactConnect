import json
from unittest import TestCase

from aws_cdk.assertions import Template
from aws_cdk.aws_iam import CfnPolicy
from aws_cdk.aws_lambda import CfnFunction

from tests.app.base import TstAppABC

LICENSE_NUMBER_GSI_NAME = 'licenseNumberGSI'


class TestLicenseUploadWithoutSsn(TstAppABC, TestCase):
    """
    Test cases for the infrastructure backing license uploads that omit the SSN: the two upload lambdas
    need the license number index name, read access scoped to that index, and permission to publish
    ingest events directly to the data event bus.
    """

    @classmethod
    def get_context(cls):
        with open('cdk.json') as f:
            context = json.load(f)['context']
        with open('cdk.context.sandbox-example.json') as f:
            context.update(json.load(f))

        # Suppresses lambda bundling for tests
        context['aws:cdk:bundling-stacks'] = []
        return context

    def _post_licenses_handler_properties(self) -> dict:
        state_api_stack = self.app.sandbox_backend_stage.state_api_stack
        return self.get_resource_properties_by_logical_id(
            state_api_stack.get_logical_id(
                state_api_stack.api.v1_api.post_licenses.post_license_handler.node.default_child
            ),
            Template.from_stack(state_api_stack).find_resources(CfnFunction.CFN_RESOURCE_TYPE_NAME),
        )

    def _parse_objects_handler_properties(self) -> dict:
        persistent_stack = self.app.sandbox_backend_stage.persistent_stack
        functions = Template.from_stack(persistent_stack).find_resources(CfnFunction.CFN_RESOURCE_TYPE_NAME)
        parse_objects_handlers = [
            properties
            for properties in functions.values()
            if properties['Properties']['Handler'] == 'handlers.bulk_upload.parse_bulk_upload_file'
        ]
        self.assertEqual(1, len(parse_objects_handlers), 'Expected exactly one bulk upload parse handler')
        return parse_objects_handlers[0]['Properties']

    def test_post_licenses_handler_can_resolve_license_numbers_and_publish_ingest_events(self):
        env_vars = self._post_licenses_handler_properties()['Environment']['Variables']

        # needed to query the license number index
        self.assertIn('PROVIDER_TABLE_NAME', env_vars)
        self.assertEqual(LICENSE_NUMBER_GSI_NAME, env_vars['LICENSE_NUMBER_GSI_NAME'])
        # needed to publish license.ingest events, bypassing the SSN preprocessor
        self.assertIn('EVENT_BUS_NAME', env_vars)
        # the feature flag client calls the internal API, so a missing base url would silently disable
        # the feature by falling back to the flag check's default
        self.assertIn('API_BASE_URL', env_vars)

    def test_parse_objects_handler_can_resolve_license_numbers(self):
        env_vars = self._parse_objects_handler_properties()['Environment']['Variables']

        self.assertIn('PROVIDER_TABLE_NAME', env_vars)
        self.assertEqual(LICENSE_NUMBER_GSI_NAME, env_vars['LICENSE_NUMBER_GSI_NAME'])
        # this handler already published failure events before this feature
        self.assertIn('EVENT_BUS_NAME', env_vars)
        self.assertIn('API_BASE_URL', env_vars)

    def _license_upload_role_policy_statements(self) -> list[dict]:
        persistent_stack = self.app.sandbox_backend_stage.persistent_stack
        policies = Template.from_stack(persistent_stack).find_resources(CfnPolicy.CFN_RESOURCE_TYPE_NAME)
        role_logical_id = persistent_stack.get_logical_id(
            persistent_stack.ssn_table.license_upload_role.node.default_child
        )

        statements = []
        for properties in policies.values():
            roles = properties['Properties'].get('Roles', [])
            if any(role.get('Ref') == role_logical_id for role in roles if isinstance(role, dict)):
                statements.extend(properties['Properties']['PolicyDocument']['Statement'])
        return statements

    def test_license_upload_role_can_query_the_license_number_index(self):
        """
        The upload lambdas share the SSN-handling license upload role. It is granted Query on the license
        number index only -- not on the table -- so it cannot read full license records.
        """
        statements = self._license_upload_role_policy_statements()

        index_query_statements = [
            statement
            for statement in statements
            if 'dynamodb:Query' in self._actions_of(statement)
            # the resource is an Fn::Join over the table arn, so match against its serialized form
            and LICENSE_NUMBER_GSI_NAME in json.dumps(statement.get('Resource'))
        ]

        self.assertEqual(
            1,
            len(index_query_statements),
            'Expected exactly one statement granting Query on the license number index',
        )
        self.assertEqual(['dynamodb:Query'], self._actions_of(index_query_statements[0]))

    def test_license_upload_role_cannot_read_the_provider_table_directly(self):
        """Guard against a future change swapping the scoped grant for a full table read grant."""
        statements = self._license_upload_role_policy_statements()

        provider_table_logical_id = self.app.sandbox_backend_stage.persistent_stack.get_logical_id(
            self.app.sandbox_backend_stage.persistent_stack.provider_table.node.default_child
        )

        for statement in statements:
            actions = self._actions_of(statement)
            forbidden = {'dynamodb:GetItem', 'dynamodb:Scan', 'dynamodb:BatchGetItem'}
            if not forbidden.intersection(actions):
                continue
            for resource in self._resources_of(statement):
                self.assertNotIn(
                    provider_table_logical_id,
                    str(resource),
                    f'license upload role must not be granted {forbidden.intersection(actions)} on the provider table',
                )

    def test_license_upload_role_can_publish_events(self):
        statements = self._license_upload_role_policy_statements()

        put_events_statements = [
            statement for statement in statements if 'events:PutEvents' in self._actions_of(statement)
        ]

        self.assertGreaterEqual(
            len(put_events_statements),
            1,
            'license upload role must be able to publish license.ingest events',
        )

    @staticmethod
    def _actions_of(statement: dict) -> list[str]:
        action = statement.get('Action', [])
        return [action] if isinstance(action, str) else action

    @staticmethod
    def _resources_of(statement: dict) -> list:
        resource = statement.get('Resource', [])
        return [resource] if not isinstance(resource, list) else resource
