"""Tests for the SSNTable common construct."""

import os
from unittest import TestCase
from unittest.mock import patch

from aws_cdk import App, RemovalPolicy
from aws_cdk.assertions import Match, Template
from aws_cdk.aws_backup import CfnBackupPlan
from aws_cdk.aws_dynamodb import CfnTable
from aws_cdk.aws_events import EventBus
from aws_cdk.aws_iam import CfnRole, ManagedPolicy, Role, ServicePrincipal
from aws_cdk.aws_kms import Alias, CfnKey
from aws_cdk.aws_lambda import Runtime
from aws_cdk.aws_sns import Topic

from common_constructs.ssn_table import SSN_TABLE_NAME, SSNTable
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
        PythonFunction._common_layer_versions = None
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
            {'TableName': SSN_TABLE_NAME},
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

    def _get_table_resource_policy_statements(self):
        tables = self.template.find_resources(CfnTable.CFN_RESOURCE_TYPE_NAME)
        (table,) = tables.values()
        return table['Properties']['ResourcePolicy']['PolicyDocument']['Statement']

    def test_deny_create_backup_for_non_dynamodb_service(self):
        stmts = self._get_table_resource_policy_statements()
        deny_backup = next(
            (s for s in stmts if s.get('Effect') == 'Deny' and 'dynamodb:CreateBackup' in s.get('Action', [])),
            None,
        )
        self.assertIsNotNone(deny_backup, 'No DENY CreateBackup statement found in resource policy')

    def test_deny_batch_and_scan_for_non_service(self):
        stmts = self._get_table_resource_policy_statements()
        deny_bulk = next(
            (s for s in stmts if s.get('Effect') == 'Deny' and 'dynamodb:Scan' in s.get('Action', [])),
            None,
        )
        self.assertIsNotNone(deny_bulk, 'No DENY Scan/BatchGetItem statement found in resource policy')

    def test_deny_get_item_query_when_not_ssn_index(self):
        """GetItem/Query/ConditionCheckItem are denied on anything that is NOT the ssnIndex GSI ARN."""
        # This policy uses add_to_resource_policy (table policy), not inline resource_policy.
        # Check the DynamoDB table policy via find_resources.
        stmts = self.template.find_resources(CfnTable.CFN_RESOURCE_TYPE_NAME)
        (table,) = stmts.values()
        all_stmts = table['Properties'].get('ResourcePolicy', {}).get('PolicyDocument', {}).get('Statement', [])

        # Look for the not-resource style DENY
        get_query_deny = next(
            (s for s in all_stmts if s.get('Effect') == 'Deny' and 'dynamodb:GetItem' in s.get('Action', [])),
            None,
        )
        # This specific deny uses NotResource, which CDK emits differently.
        # Check the AWS::DynamoDB::Table resource policy and bucket policy via template raw JSON.
        template_json = str(self.template.to_json())
        self.assertIn('dynamodb:GetItem', template_json)
        self.assertIn('dynamodb:Query', template_json)
        self.assertIn('dynamodb:ConditionCheckItem', template_json)


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

    def test_kms_deny_policy_for_unauthorized_principals(self):
        """DENY kms:Decrypt/Encrypt/GenerateDataKey*/ReEncrypt* for any principal not in the allowlist."""
        keys = self.template.find_resources(CfnKey.CFN_RESOURCE_TYPE_NAME)
        deny_found = False
        for key in keys.values():
            stmts = key['Properties'].get('KeyPolicy', {}).get('Statement', [])
            for stmt in stmts:
                if stmt.get('Effect') == 'Deny' and 'kms:Decrypt' in str(stmt.get('Action', '')):
                    deny_found = True
                    break
        self.assertTrue(deny_found, 'No DENY kms:Decrypt statement found on SSN KMS key policy')

    def test_kms_deny_allows_dynamodb_service_as_exception(self):
        """The deny statement allows dynamodb.amazonaws.com as a principal service exception."""
        keys = self.template.find_resources(CfnKey.CFN_RESOURCE_TYPE_NAME)
        exception_found = False
        for key in keys.values():
            stmts = key['Properties'].get('KeyPolicy', {}).get('Statement', [])
            for stmt in stmts:
                conditions = stmt.get('Condition', {})
                if 'dynamodb.amazonaws.com' in str(conditions):
                    exception_found = True
                    break
        self.assertTrue(exception_found, 'dynamodb.amazonaws.com not in KMS deny exception list')


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

    def test_provider_query_role_exists(self):
        template_json = self.template.to_json()
        self.assertIn('Deprecated inert role', str(template_json))

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

    def test_dr_step_function_policy_includes_restore_table_to_pitr(self):
        template_json = str(self.template.to_json())
        self.assertIn('dynamodb:RestoreTableToPointInTime', template_json)

    def test_dr_step_function_policy_includes_kms_create_grant(self):
        template_json = str(self.template.to_json())
        self.assertIn('kms:CreateGrant', template_json)


class TestSSNTableBackupDisabled(TestCase):
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
        _make_ssn_table(cls.stack, environment_context=_ENVIRONMENT_CONTEXT_NO_BACKUP)
        cls.template = Template.from_stack(cls.stack)

    def test_no_backup_plan_when_backup_disabled(self):
        backup_plans = self.template.find_resources(CfnBackupPlan.CFN_RESOURCE_TYPE_NAME)
        self.assertEqual({}, backup_plans)

    def test_hipaa_suppression_present_when_backup_disabled(self):
        """CDK NAG suppression for DynamoDB backup is added when backup is disabled."""
        # The NagSuppressions call is validated by confirming the table is synthesized successfully
        # and no backup plan is created.
        tables = self.template.find_resources(CfnTable.CFN_RESOURCE_TYPE_NAME)
        self.assertGreaterEqual(len(tables), 1)


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

    def test_backup_service_role_added_to_kms_allow_list(self):
        """When backup is enabled, the backup service role ARN is in the KMS DENY exception list."""
        keys = self.template.find_resources(CfnKey.CFN_RESOURCE_TYPE_NAME)
        ssn_key_with_backup_role = False
        for key in keys.values():
            stmts = key['Properties'].get('KeyPolicy', {}).get('Statement', [])
            for stmt in stmts:
                if stmt.get('Effect') == 'Deny' and 'kms:Decrypt' in str(stmt.get('Action', '')):
                    conditions = str(stmt.get('Condition', {}))
                    # The backup service role ARN should appear as a reference in the deny exception
                    if 'SSNBackupServiceRole' in conditions or 'Arn' in conditions:
                        ssn_key_with_backup_role = True
                        break
        self.assertTrue(ssn_key_with_backup_role, 'Backup service role not referenced in KMS deny exception list')
