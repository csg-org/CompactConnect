"""Tests for the SSNTable common construct."""

import os
from unittest import TestCase
from unittest.mock import patch

from aws_cdk import App, RemovalPolicy
from aws_cdk.assertions import Match, Template
from aws_cdk.aws_backup import CfnBackupPlan
from aws_cdk.aws_dynamodb import CfnTable
from aws_cdk.aws_events import EventBus
from aws_cdk.aws_iam import CfnPolicy, CfnRole
from aws_cdk.aws_kms import CfnKey
from aws_cdk.aws_lambda import Runtime
from aws_cdk.aws_sns import Topic

from common_constructs.ssn_table import (
    SSNTable,
)
from common_constructs.stack import AppStack, StandardTags
from common_stacks.backup_infrastructure_stack import BackupInfrastructureStack

_FIXTURES_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')
_os_path_join = os.path.join

_CDK_CONTEXT = {
    'compacts': ['aslp', 'octp', 'coun'],
    'jurisdictions': ['al', 'ak', 'az'],
    'license_types': {
        'aslp': [{'name': 'audiologist', 'abbreviation': 'aud'}],
        'octp': [{'name': 'occupational therapist', 'abbreviation': 'ot'}],
        'coun': [{'name': 'licensed professional counselor', 'abbreviation': 'lpc'}],
    },
    'aws:cdk:bundling-stacks': [],
}

_APP_ENV_CONTEXT = {'allow_local_ui': True, 'local_ui_port': '3018'}

_BACKUP_CONFIG = {
    'backup_account_id': '123456789012',
    'backup_region': 'us-east-1',
    'general_vault_name': 'test-general-vault',
    'ssn_vault_name': 'test-ssn-vault',
}

_BACKUP_POLICY = {
    'schedule': {'hour': '5', 'minute': '0'},
    'delete_after_days': 180,
    'cold_storage_after_days': 30,
}

_ENVIRONMENT_CONTEXT_NO_BACKUP = {
    'backup_enabled': False,
    'backup_policies': {'general_data': _BACKUP_POLICY},
}

_ENVIRONMENT_CONTEXT_WITH_BACKUP = {
    'backup_enabled': True,
    'backup_policies': {'general_data': _BACKUP_POLICY},
}

_STANDARD_TAGS = StandardTags(project='test', service='test', environment='test')

_DR_LAMBDA_ROLE_DESCRIPTION = 'Dedicated role for SSN table disaster recovery Lambda operations'
_DR_STEP_FUNCTION_ROLE_DESCRIPTION = 'Dedicated role for SSN table disaster recovery Step Function operations'


def _get_ssn_table_logical_id(template: Template) -> str:
    tables = template.find_resources(CfnTable.CFN_RESOURCE_TYPE_NAME)
    if len(tables) != 1:
        raise AssertionError(f'Expected exactly one DynamoDB table, found {len(tables)}')
    return next(iter(tables.keys()))


def _get_ssn_key_logical_id(template: Template) -> str:
    keys = template.find_resources(CfnKey.CFN_RESOURCE_TYPE_NAME)
    if len(keys) != 1:
        raise AssertionError(f'Expected exactly one KMS key, found {len(keys)}')
    return next(iter(keys.keys()))


def _get_ssn_key_policy_document(template: Template) -> dict:
    keys = template.find_resources(CfnKey.CFN_RESOURCE_TYPE_NAME)
    if len(keys) != 1:
        raise AssertionError(f'Expected exactly one KMS key, found {len(keys)}')
    (key,) = keys.values()
    return key['Properties']['KeyPolicy']


def _get_role_logical_id_by_description(template: Template, description: str) -> str:
    roles = template.find_resources(CfnRole.CFN_RESOURCE_TYPE_NAME)
    matches = [lid for lid, role in roles.items() if role['Properties'].get('Description') == description]
    if len(matches) != 1:
        raise AssertionError(f'Expected exactly one role with description {description!r}, found {len(matches)}')
    return matches[0]


def _policy_attached_to_role(role_logical_id: str, roles_property: list) -> bool:
    for role in roles_property:
        if role == role_logical_id:
            return True
        if isinstance(role, dict) and role.get('Ref') == role_logical_id:
            return True
    return False


def _get_role_policy_document_by_description(template: Template, description: str) -> dict:
    role_logical_id = _get_role_logical_id_by_description(template, description)
    policies = template.find_resources(CfnPolicy.CFN_RESOURCE_TYPE_NAME)
    matches = [
        policy['Properties']['PolicyDocument']
        for policy in policies.values()
        if _policy_attached_to_role(role_logical_id, policy['Properties'].get('Roles', []))
    ]
    if len(matches) != 1:
        raise AssertionError(f'Expected exactly one inline policy for role {description!r}, found {len(matches)}')
    return matches[0]


def _get_ssn_table_resource_policy_document(template: Template) -> dict:
    tables = template.find_resources(CfnTable.CFN_RESOURCE_TYPE_NAME)
    if len(tables) != 1:
        raise AssertionError(f'Expected exactly one DynamoDB table, found {len(tables)}')
    (table,) = tables.values()
    return table['Properties']['ResourcePolicy']['PolicyDocument']


def _dynamodb_ssn_index_not_resource_arn_join() -> dict:
    return {
        'Fn::Join': [
            '',
            [
                'arn:',
                {'Ref': 'AWS::Partition'},
                ':dynamodb:',
                {'Ref': 'AWS::Region'},
                ':',
                {'Ref': 'AWS::AccountId'},
                ':table/ssn-table-DataEventsLog/index/ssnIndex',
            ],
        ],
    }


def _join_with_python_fixtures(*parts: str) -> str:
    """Redirect lambdas/python paths to tests/fixtures so CDK asset bundling resolves correctly."""
    if len(parts) >= 2 and parts[0] == 'lambdas' and parts[1] == 'python':
        return _os_path_join(_FIXTURES_DIR, *parts)
    return _os_path_join(*parts)


def _make_ssn_table(
    stack,
    removal_policy: RemovalPolicy = RemovalPolicy.DESTROY,
    backup_infrastructure_stack=None,
    environment_context: dict = None,
) -> SSNTable:
    from common_constructs.python_common_layer_versions import PythonCommonLayerVersions
    from common_constructs.python_function import PythonFunction

    if environment_context is None:
        environment_context = _ENVIRONMENT_CONTEXT_NO_BACKUP

    alarm_topic = Topic(stack, 'AlarmTopic')
    data_event_bus = EventBus(stack, 'DataEventBus')

    with (
        patch('common_constructs.python_function.os.path.join', side_effect=_join_with_python_fixtures),
        patch('common_constructs.python_common_layer_versions.os.path.join', side_effect=_join_with_python_fixtures),
    ):
        # Reset per-test so layers are always created in the current stack (avoids cross-App references).
        PythonFunction._common_layer_versions = None  # noqa: SLF001
        PythonCommonLayerVersions(stack, 'CommonLayers', compatible_runtimes=[Runtime.PYTHON_3_14])

        return SSNTable(
            stack,
            'SSNTable',
            removal_policy=removal_policy,
            data_event_bus=data_event_bus,
            alarm_topic=alarm_topic,
            backup_infrastructure_stack=backup_infrastructure_stack,
            environment_context=environment_context,
        )


class TestSSNTableConfig(TestCase):
    @classmethod
    def setUpClass(cls):
        app = App(context=_CDK_CONTEXT)
        cls.stack = AppStack(
            app,
            'TestStack',
            standard_tags=_STANDARD_TAGS,
            environment_name='sandbox',
            environment_context=_APP_ENV_CONTEXT,
        )
        _make_ssn_table(cls.stack)
        cls.template = Template.from_stack(cls.stack)

    def test_table_name_is_ssn_table_data_events_log(self):
        self.template.has_resource_properties(
            CfnTable.CFN_RESOURCE_TYPE_NAME,
            {'TableName': 'ssn-table-DataEventsLog'},
        )

    def test_billing_mode_is_pay_per_request(self):
        self.template.has_resource_properties(
            CfnTable.CFN_RESOURCE_TYPE_NAME,
            {'BillingMode': 'PAY_PER_REQUEST'},
        )

    def test_customer_managed_kms_encryption(self):
        self.template.has_resource_properties(
            CfnTable.CFN_RESOURCE_TYPE_NAME,
            {
                'SSESpecification': {
                    'SSEEnabled': True,
                    'SSEType': 'KMS',
                }
            },
        )

    def test_pitr_enabled(self):
        self.template.has_resource_properties(
            CfnTable.CFN_RESOURCE_TYPE_NAME,
            {'PointInTimeRecoverySpecification': {'PointInTimeRecoveryEnabled': True}},
        )

    def test_deletion_protection_enabled_when_retain(self):
        app = App(context=_CDK_CONTEXT)
        stack = AppStack(
            app,
            'RetainStack',
            standard_tags=_STANDARD_TAGS,
            environment_name='sandbox',
            environment_context=_APP_ENV_CONTEXT,
        )
        _make_ssn_table(stack, removal_policy=RemovalPolicy.RETAIN)

        template = Template.from_stack(stack)
        template.has_resource_properties(
            CfnTable.CFN_RESOURCE_TYPE_NAME,
            {'DeletionProtectionEnabled': True},
        )

    def test_ssn_index_gsi_exists(self):
        self.template.has_resource_properties(
            CfnTable.CFN_RESOURCE_TYPE_NAME,
            {
                'GlobalSecondaryIndexes': Match.array_with(
                    [
                        Match.object_like(
                            {
                                'IndexName': 'ssnIndex',
                                'KeySchema': Match.array_with(
                                    [Match.object_like({'AttributeName': 'providerIdGSIpk'})]
                                ),
                            }
                        )
                    ]
                )
            },
        )


class TestSSNTableResourcePolicy(TestCase):
    @classmethod
    def setUpClass(cls):
        app = App(context=_CDK_CONTEXT)
        cls.stack = AppStack(
            app,
            'TestStack',
            standard_tags=_STANDARD_TAGS,
            environment_name='sandbox',
            environment_context=_APP_ENV_CONTEXT,
        )
        _make_ssn_table(cls.stack)
        cls.template = Template.from_stack(cls.stack)

    def test_table_resource_policy_document(self):
        """Snapshot of the full DynamoDB resource policy; any intentional change should update this test."""
        dr_lambda_role_id = _get_role_logical_id_by_description(self.template, _DR_LAMBDA_ROLE_DESCRIPTION)

        expected = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Action': 'dynamodb:CreateBackup',
                    'Condition': {
                        'StringNotEquals': {
                            'aws:PrincipalServiceName': 'dynamodb.amazonaws.com',
                        }
                    },
                    'Effect': 'Deny',
                    'Principal': '*',
                    'Resource': '*',
                },
                {
                    'Action': [
                        'dynamodb:BatchGetItem',
                        'dynamodb:BatchWriteItem',
                        'dynamodb:PartiQL*',
                        'dynamodb:Scan',
                    ],
                    'Condition': {
                        'StringNotEquals': {
                            'aws:PrincipalArn': [{'Fn::GetAtt': [dr_lambda_role_id, 'Arn']}],
                            'aws:PrincipalServiceName': 'dynamodb.amazonaws.com',
                        }
                    },
                    'Effect': 'Deny',
                    'Principal': '*',
                    'Resource': '*',
                },
                {
                    'Action': [
                        'dynamodb:GetItem',
                        'dynamodb:Query',
                        'dynamodb:ConditionCheckItem',
                    ],
                    'Effect': 'Deny',
                    'NotResource': _dynamodb_ssn_index_not_resource_arn_join(),
                    'Principal': '*',
                },
            ],
        }

        self.assertEqual(expected, _get_ssn_table_resource_policy_document(self.template))


class TestSSNTableKMSKey(TestCase):
    @classmethod
    def setUpClass(cls):
        app = App(context=_CDK_CONTEXT)
        cls.stack = AppStack(
            app,
            'TestStack',
            standard_tags=_STANDARD_TAGS,
            environment_name='sandbox',
            environment_context=_APP_ENV_CONTEXT,
        )
        _make_ssn_table(cls.stack)
        cls.template = Template.from_stack(cls.stack)

    def test_kms_key_rotation_enabled(self):
        self.template.has_resource_properties(
            CfnKey.CFN_RESOURCE_TYPE_NAME,
            {'EnableKeyRotation': True},
        )

    def test_kms_key_alias_is_ssn_key(self):
        self.template.has_resource_properties(
            'AWS::KMS::Alias',
            {'AliasName': 'alias/ssn-key'},
        )

    def test_ssn_key_policy_document(self):
        """Snapshot of the full SSN KMS key policy; any intentional change should update this test."""
        expected = {
            'Statement': [
                {
                    'Action': 'kms:*',
                    'Effect': 'Allow',
                    'Principal': {
                        'AWS': {
                            'Fn::Join': [
                                '',
                                ['arn:', {'Ref': 'AWS::Partition'}, ':iam::', {'Ref': 'AWS::AccountId'}, ':root'],
                            ]
                        }
                    },
                    'Resource': '*',
                },
                {
                    'Action': ['kms:Decrypt', 'kms:Encrypt', 'kms:GenerateDataKey*', 'kms:ReEncrypt*'],
                    'Condition': {
                        'StringNotEquals': {
                            'aws:PrincipalArn': [
                                {'Fn::GetAtt': ['SSNTableLicenseIngestRoleC883020F', 'Arn']},
                                {'Fn::GetAtt': ['SSNTableLicenseUploadRole46F85F47', 'Arn']},
                                {'Fn::GetAtt': ['DisasterRecoveryLambdaRole4BDEAE6F', 'Arn']},
                                {'Fn::GetAtt': ['SSNTableDisasterRecoveryStepFunctionRoleCE265991', 'Arn']},
                            ],
                            'aws:PrincipalServiceName': ['dynamodb.amazonaws.com', 'events.amazonaws.com'],
                        }
                    },
                    'Effect': 'Deny',
                    'Principal': '*',
                    'Resource': '*',
                },
            ],
            'Version': '2012-10-17',
        }
        self.assertEqual(expected, _get_ssn_key_policy_document(self.template))


class TestSSNTableRoles(TestCase):
    @classmethod
    def setUpClass(cls):
        app = App(context=_CDK_CONTEXT)
        cls.stack = AppStack(
            app,
            'TestStack',
            standard_tags=_STANDARD_TAGS,
            environment_name='sandbox',
            environment_context=_APP_ENV_CONTEXT,
        )
        _make_ssn_table(cls.stack)
        cls.template = Template.from_stack(cls.stack)

    def _get_role_names(self) -> set[str]:
        roles = self.template.find_resources(CfnRole.CFN_RESOURCE_TYPE_NAME)
        return {r['Properties'].get('Description', '') for r in roles.values()}

    def test_license_ingest_role_exists(self):
        template_json = self.template.to_json()
        self.assertIn('Dedicated role for license ingest', str(template_json))

    def test_license_upload_role_exists(self):
        template_json = self.template.to_json()
        self.assertIn('Dedicated role for lambdas that upload license records', str(template_json))

    def test_disaster_recovery_lambda_role_assumes_lambda(self):
        self.template.has_resource_properties(
            CfnRole.CFN_RESOURCE_TYPE_NAME,
            {
                'AssumeRolePolicyDocument': Match.object_like(
                    {
                        'Statement': Match.array_with(
                            [Match.object_like({'Principal': {'Service': 'lambda.amazonaws.com'}})]
                        )
                    }
                ),
                'Description': 'Dedicated role for SSN table disaster recovery Lambda operations',
            },
        )

    def test_disaster_recovery_step_function_role_assumes_states(self):
        self.template.has_resource_properties(
            CfnRole.CFN_RESOURCE_TYPE_NAME,
            {
                'AssumeRolePolicyDocument': Match.object_like(
                    {
                        'Statement': Match.array_with(
                            [Match.object_like({'Principal': {'Service': 'states.amazonaws.com'}})]
                        )
                    }
                )
            },
        )

    def test_disaster_recovery_step_function_role_policy_document(self):
        """Snapshot of the full inline policy for the DR Step Function role."""
        table_id = _get_ssn_table_logical_id(self.template)
        key_id = _get_ssn_key_logical_id(self.template)

        expected = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Action': [
                        'dynamodb:RestoreTableToPointInTime',
                        'dynamodb:DescribeTable',
                        'dynamodb:BatchWriteItem',
                        'dynamodb:DeleteItem',
                        'dynamodb:GetItem',
                        'dynamodb:PutItem',
                        'dynamodb:Query',
                        'dynamodb:Scan',
                        'dynamodb:UpdateItem',
                    ],
                    'Effect': 'Allow',
                    'Resource': [
                        {'Fn::GetAtt': [table_id, 'Arn']},
                        {
                            'Fn::Join': [
                                '',
                                [{'Fn::GetAtt': [table_id, 'Arn']}, '/backup/*'],
                            ]
                        },
                        {
                            'Fn::Join': [
                                '',
                                [
                                    'arn:aws:dynamodb:',
                                    {'Ref': 'AWS::Region'},
                                    ':',
                                    {'Ref': 'AWS::AccountId'},
                                    ':table/DR-TEMP-SSN-*',
                                ],
                            ]
                        },
                        {
                            'Fn::Join': [
                                '',
                                [
                                    'arn:aws:dynamodb:',
                                    {'Ref': 'AWS::Region'},
                                    ':',
                                    {'Ref': 'AWS::AccountId'},
                                    ':table/DR-TEMP-SSN-*/index/*',
                                ],
                            ]
                        },
                    ],
                },
                {
                    'Action': 'states:StartExecution',
                    'Effect': 'Allow',
                    'Resource': {
                        'Fn::Join': [
                            '',
                            [
                                'arn:',
                                {'Ref': 'AWS::Partition'},
                                ':states:',
                                {'Ref': 'AWS::Region'},
                                ':',
                                {'Ref': 'AWS::AccountId'},
                                ':stateMachine:SSNTable-SSNSyncTableData',
                            ],
                        ],
                    },
                },
                {
                    'Action': [
                        'events:PutTargets',
                        'events:PutRule',
                        'events:DescribeRule',
                    ],
                    'Effect': 'Allow',
                    'Resource': {
                        'Fn::Join': [
                            '',
                            [
                                'arn:aws:events:',
                                {'Ref': 'AWS::Region'},
                                ':',
                                {'Ref': 'AWS::AccountId'},
                                ':rule/StepFunctionsGetEventsForStepFunctionsExecutionRule',
                            ],
                        ],
                    },
                },
                {
                    'Action': [
                        'kms:DescribeKey',
                        'kms:CreateGrant',
                        'kms:Decrypt',
                        'kms:Encrypt',
                        'kms:GenerateDataKey*',
                        'kms:ReEncrypt*',
                    ],
                    'Effect': 'Allow',
                    'Resource': {'Fn::GetAtt': [key_id, 'Arn']},
                },
            ],
        }

        actual = _get_role_policy_document_by_description(self.template, _DR_STEP_FUNCTION_ROLE_DESCRIPTION)
        self.assertEqual(expected, actual)


class TestSSNTableBackupEnabled(TestCase):
    @classmethod
    def setUpClass(cls):
        app = App(context=_CDK_CONTEXT)
        cls.main_stack = AppStack(
            app,
            'MainStack',
            standard_tags=_STANDARD_TAGS,
            environment_name='sandbox',
            environment_context=_APP_ENV_CONTEXT,
        )
        backup_alarm_topic = Topic(cls.main_stack, 'BackupAlarmTopic')

        cls.backup_infrastructure_stack = BackupInfrastructureStack(
            cls.main_stack,
            'BackupInfrastructure',
            environment_name='sandbox',
            backup_config=_BACKUP_CONFIG,
            alarm_topic=backup_alarm_topic,
            removal_policy=RemovalPolicy.DESTROY,
        )

        _make_ssn_table(
            cls.main_stack,
            backup_infrastructure_stack=cls.backup_infrastructure_stack,
            environment_context=_ENVIRONMENT_CONTEXT_WITH_BACKUP,
        )
        cls.template = Template.from_stack(cls.main_stack)

    def test_backup_plan_created_when_backup_enabled(self):
        backup_plans = self.template.find_resources(CfnBackupPlan.CFN_RESOURCE_TYPE_NAME)
        self.assertGreaterEqual(len(backup_plans), 1)

    def test_ssn_key_policy_document_when_backup_enabled(self):
        """Snapshot of the SSN KMS key policy with backup enabled (backup role on DENY allowlist)."""
        expected = {
            'Statement': [
                {
                    'Action': 'kms:*',
                    'Effect': 'Allow',
                    'Principal': {
                        'AWS': {
                            'Fn::Join': [
                                '',
                                ['arn:', {'Ref': 'AWS::Partition'}, ':iam::', {'Ref': 'AWS::AccountId'}, ':root'],
                            ]
                        }
                    },
                    'Resource': '*',
                },
                {
                    'Action': ['kms:Decrypt', 'kms:Encrypt', 'kms:GenerateDataKey*', 'kms:ReEncrypt*'],
                    'Condition': {
                        'StringNotEquals': {
                            'aws:PrincipalArn': [
                                {'Fn::GetAtt': ['SSNTableLicenseIngestRoleC883020F', 'Arn']},
                                {'Fn::GetAtt': ['SSNTableLicenseUploadRole46F85F47', 'Arn']},
                                {'Fn::GetAtt': ['DisasterRecoveryLambdaRole4BDEAE6F', 'Arn']},
                                {'Fn::GetAtt': ['SSNTableDisasterRecoveryStepFunctionRoleCE265991', 'Arn']},
                                {
                                    'Fn::GetAtt': [
                                        'BackupInfrastructureNestedStackBackupInfrastructureNestedStackResource71C96FBD',
                                        'Outputs.MainStackBackupInfrastructureSSNBackupServiceRoleEB4E841DArn',
                                    ]
                                },
                            ],
                            'aws:PrincipalServiceName': ['dynamodb.amazonaws.com', 'events.amazonaws.com'],
                        }
                    },
                    'Effect': 'Deny',
                    'Principal': '*',
                    'Resource': '*',
                },
            ],
            'Version': '2012-10-17',
        }
        self.assertEqual(expected, _get_ssn_key_policy_document(self.template))
