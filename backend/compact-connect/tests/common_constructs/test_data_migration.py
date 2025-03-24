from unittest import TestCase

from aws_cdk import App, Stack
from aws_cdk.assertions import Template
from aws_cdk.aws_iam import Role, ServicePrincipal
from aws_cdk.aws_lambda import CfnFunction

# Use the dummy migration directory for testing
MIGRATION_DIR = 'dummy_migration'


class TestDataMigration(TestCase):
    def test_data_migration_synthesizes(self):
        from common_constructs.data_migration import DataMigration

        # Suppresses lambda bundling for tests
        context = {'aws:cdk:bundling-stacks': []}
        app = App(context=context)
        stack = Stack(app, 'Stack')

        # Create a role for the migration function
        role = Role(stack, 'MigrationRole', assumed_by=ServicePrincipal('lambda.amazonaws.com'))

        # Create environment variables for the lambda
        lambda_environment = {'ENV_VAR1': 'value1', 'ENV_VAR2': 'value2'}

        # Create custom resource properties
        custom_resource_properties = {'TestProperty': 'test-value', 'AnotherProperty': 123}

        # Create the DataMigration construct
        data_migration = DataMigration(
            stack,
            'TestMigration',
            migration_dir=MIGRATION_DIR,
            lambda_environment=lambda_environment,
            role=role,
            custom_resource_properties=custom_resource_properties,
        )

        # Generate the CloudFormation template
        template = Template.from_stack(stack)

        # Test that the migration function is created with the correct properties
        template.has_resource(
            CfnFunction.CFN_RESOURCE_TYPE_NAME,
            props={
                'Properties': {
                    'Handler': 'dummy_migration.main.on_event',
                    'Timeout': 900,  # 15 minutes in seconds
                    'Environment': {'Variables': lambda_environment},
                    'Role': {'Fn::GetAtt': [stack.get_logical_id(role.node.default_child), 'Arn']},
                }
            },
        )

        # Test that the custom resource is created with the correct properties
        template.has_resource(
            'Custom::DataMigration',
            props={
                'Properties': {
                    'ServiceToken': {
                        'Fn::GetAtt': [
                            stack.get_logical_id(
                                data_migration.provider.node.find_child('framework-onEvent').node.default_child
                            ),
                            'Arn',
                        ]
                    },
                    'TestProperty': 'test-value',
                    'AnotherProperty': 123,
                }
            },
        )

        # Test that the grant_principal property returns the migration function's grant_principal
        self.assertEqual(data_migration.grant_principal, data_migration.migration_function.grant_principal)
