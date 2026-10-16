import json
from unittest import TestCase

from aws_cdk.aws_events import CfnRule
from aws_cdk.aws_iam import CfnPolicy
from aws_cdk.aws_lambda import CfnFunction
from aws_cdk.assertions import Template

from tests.app.base import TstAppABC


class TestReportingStack(TstAppABC, TestCase):
    """Invoice reporter resources on the reporting stack."""

    @classmethod
    def get_context(cls):
        with open('cdk.json') as f:
            context = json.load(f)['context']
        with open('cdk.context.sandbox-example.json') as f:
            context.update(json.load(f))

        # Suppresses lambda bundling for tests
        context['aws:cdk:bundling-stacks'] = []
        return context

    def _reporting_template(self) -> Template:
        return Template.from_stack(self.app.sandbox_backend_stage.reporting_stack)

    def _invoice_reporter_function(self) -> tuple[str, dict]:
        functions = self._reporting_template().find_resources(CfnFunction.CFN_RESOURCE_TYPE_NAME)
        matches = {
            logical_id: resource
            for logical_id, resource in functions.items()
            if resource['Properties'].get('Handler') == 'index.generateInvoice'
        }
        self.assertEqual(1, len(matches), 'Expected exactly one invoice reporter lambda')
        return next(iter(matches.items()))

    def _invoice_reporter_policy_statements(self) -> list[dict]:
        logical_id, resource = self._invoice_reporter_function()
        role_logical_id = resource['Properties']['Role']['Fn::GetAtt'][0]
        policies = self._reporting_template().find_resources(CfnPolicy.CFN_RESOURCE_TYPE_NAME)

        statements = []
        for policy in policies.values():
            roles = policy['Properties'].get('Roles', [])
            if any(role.get('Ref') == role_logical_id for role in roles if isinstance(role, dict)):
                statements.extend(policy['Properties']['PolicyDocument']['Statement'])
        self.assertTrue(statements, f'Expected IAM statements for {logical_id}')
        return statements

    @staticmethod
    def _actions_of(statement: dict) -> list[str]:
        action = statement.get('Action', [])
        return [action] if isinstance(action, str) else action

    def test_invoice_reporter_lambda_is_created(self):
        _logical_id, resource = self._invoice_reporter_function()
        env_vars = resource['Properties']['Environment']['Variables']

        self.assertEqual('index.generateInvoice', resource['Properties']['Handler'])
        self.assertIn('PROVIDER_TABLE_NAME', env_vars)
        self.assertIn('COMPACT_CONFIGURATION_TABLE_NAME', env_vars)
        self.assertEqual('25', env_vars['FEE_PER_LICENSE'])

    def test_invoice_reporter_monthly_eventbridge_rule_is_created(self):
        function_logical_id, _resource = self._invoice_reporter_function()
        rules = self._reporting_template().find_resources(CfnRule.CFN_RESOURCE_TYPE_NAME)
        monthly_rules = [
            resource['Properties']
            for resource in rules.values()
            if 'monthly' in json.dumps(resource['Properties'].get('Targets', []))
        ]

        self.assertEqual(1, len(monthly_rules), 'Expected one monthly invoice schedule')
        rule = monthly_rules[0]
        self.assertEqual('cron(0 6 2 * ? *)', rule['ScheduleExpression'])
        self.assertEqual('ENABLED', rule['State'])
        self.assertIn('{"eventType":"monthly"}', json.dumps(rule['Targets']))
        self.assertIn(function_logical_id, json.dumps(rule['Targets']))

    def test_invoice_reporter_has_provider_table_read_permissions(self):
        statements = self._invoice_reporter_policy_statements()
        provider_reads = [
            statement
            for statement in statements
            if {'dynamodb:Query', 'dynamodb:GetItem', 'dynamodb:BatchGetItem'}.issubset(self._actions_of(statement))
            and 'ProviderTable' in json.dumps(statement.get('Resource'))
        ]

        self.assertEqual(1, len(provider_reads), 'Expected read access to the provider table')

    def test_invoice_reporter_has_compact_configuration_table_read_permissions(self):
        statements = self._invoice_reporter_policy_statements()
        configuration_reads = [
            statement
            for statement in statements
            if {'dynamodb:Query', 'dynamodb:GetItem'}.issubset(self._actions_of(statement))
            and 'CompactConfigurationTable' in json.dumps(statement.get('Resource'))
        ]

        self.assertEqual(
            1,
            len(configuration_reads),
            'Expected read access to the compact configuration table',
        )

    def test_invoice_reporter_has_ses_send_permissions(self):
        statements = self._invoice_reporter_policy_statements()
        ses_statements = [
            statement
            for statement in statements
            if {'ses:SendEmail', 'ses:SendRawEmail'}.issubset(self._actions_of(statement))
        ]

        self.assertEqual(1, len(ses_statements), 'Expected SES send permissions for the invoice reporter')
