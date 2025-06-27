import json
from unittest import TestCase

from aws_cdk import ArnFormat
from aws_cdk.assertions import Match, Template
from aws_cdk.aws_backup import CfnBackupVault
from aws_cdk.aws_cloudwatch import CfnAlarm
from aws_cdk.aws_events import CfnRule
from aws_cdk.aws_iam import CfnRole
from aws_cdk.aws_kms import CfnAlias, CfnKey

from tests.app.base import TstAppABC


class TestBackupInfrastructureStack(TstAppABC, TestCase):
    @classmethod
    def get_context(cls):
        with open('cdk.json') as f:
            context = json.load(f)['context']
        with open('cdk.context.sandbox-example.json') as f:
            context.update(json.load(f))

        # Suppresses lambda bundling for tests
        context['aws:cdk:bundling-stacks'] = []

        return context

    def setUp(self):
        """Set up test fixtures."""
        # Use the sandbox backend stage for testing backup infrastructure
        self.backup_stack = self.app.sandbox_backend_stage.backup_infrastructure_stack
        self.template = Template.from_stack(self.backup_stack)

    def test_stack_creates_expected_resources(self):
        """Test that the stack creates all expected backup infrastructure resources."""
        # Should create 2 KMS keys (general and SSN)
        self.template.resource_count_is(CfnKey.CFN_RESOURCE_TYPE_NAME, 2)

        # Should create 2 KMS aliases
        self.template.resource_count_is(CfnAlias.CFN_RESOURCE_TYPE_NAME, 2)

        # Should create 2 backup vaults (general and SSN)
        self.template.resource_count_is(CfnBackupVault.CFN_RESOURCE_TYPE_NAME, 2)

        # Should create 2 IAM roles (general backup service role and SSN backup service role)
        self.template.resource_count_is(CfnRole.CFN_RESOURCE_TYPE_NAME, 2)

        # Should create monitoring resources (alarms and EventBridge rules)
        self.template.resource_count_is(CfnAlarm.CFN_RESOURCE_TYPE_NAME, 6)  # 6 CloudWatch alarms
        self.template.resource_count_is(CfnRule.CFN_RESOURCE_TYPE_NAME, 6)  # 6 EventBridge rules

    def test_general_backup_vault_configuration(self):
        """Test the general backup vault is configured correctly."""
        environment_name = self.app.sandbox_backend_stage.backup_infrastructure_stack.environment_name
        self.template.has_resource_properties(
            CfnBackupVault.CFN_RESOURCE_TYPE_NAME,
            {
                'BackupVaultName': f'CompactConnect-{environment_name}-BackupVault',
                'EncryptionKeyArn': Match.any_value(),
            },
        )

    def test_ssn_backup_vault_configuration(self):
        """Test the SSN backup vault is configured correctly."""
        environment_name = self.app.sandbox_backend_stage.backup_infrastructure_stack.environment_name
        self.template.has_resource_properties(
            CfnBackupVault.CFN_RESOURCE_TYPE_NAME,
            {
                'BackupVaultName': f'CompactConnect-{environment_name}-SSNBackupVault',
                'EncryptionKeyArn': Match.any_value(),
            },
        )

    def test_kms_keys_have_correct_aliases(self):
        """Test that KMS keys have the correct aliases."""
        environment_name = self.app.sandbox_backend_stage.backup_infrastructure_stack.environment_name

        # General backup key alias
        self.template.has_resource_properties(
            CfnAlias.CFN_RESOURCE_TYPE_NAME,
            {'AliasName': f'alias/compactconnect-{environment_name}-backup-key', 'TargetKeyId': Match.any_value()},
        )

        # SSN backup key alias
        self.template.has_resource_properties(
            CfnAlias.CFN_RESOURCE_TYPE_NAME,
            {'AliasName': f'alias/compactconnect-{environment_name}-ssn-backup-key', 'TargetKeyId': Match.any_value()},
        )

    def test_backup_service_roles_configuration(self):
        """Test that backup service roles are configured correctly."""
        environment_name = self.app.sandbox_backend_stage.backup_infrastructure_stack.environment_name

        # General backup service role
        self.template.has_resource_properties(
            CfnRole.CFN_RESOURCE_TYPE_NAME,
            {
                'RoleName': f'CompactConnect-{environment_name}-BackupServiceRole',
                'AssumeRolePolicyDocument': {
                    'Statement': [
                        {
                            'Effect': 'Allow',
                            'Principal': {'Service': 'backup.amazonaws.com'},
                            'Action': 'sts:AssumeRole',
                        }
                    ]
                },
                'ManagedPolicyArns': Match.array_with([Match.object_like({'Fn::Join': Match.any_value()})]),
            },
        )

        # SSN backup service role with enhanced security controls
        self.template.has_resource_properties(
            CfnRole.CFN_RESOURCE_TYPE_NAME,
            {
                'RoleName': f'CompactConnect-{environment_name}-SSNBackupRole',
                'AssumeRolePolicyDocument': {
                    'Statement': [
                        {
                            'Effect': 'Allow',
                            'Principal': {'Service': 'backup.amazonaws.com'},
                            'Action': 'sts:AssumeRole',
                        }
                    ]
                },
                'ManagedPolicyArns': Match.array_with(
                    [
                        Match.object_like({'Fn::Join': Match.any_value()}),
                        Match.object_like({'Fn::Join': Match.any_value()}),
                    ]
                ),
            },
        )

    def test_ssn_backup_role_has_cross_account_restrictions(self):
        """Test that the SSN backup role restricts cross-account copy operations."""
        environment_name = self.app.sandbox_backend_stage.backup_infrastructure_stack.environment_name

        # Verify the SSN backup role exists and has the inline policy with cross-account restrictions
        self.template.has_resource_properties(
            CfnRole.CFN_RESOURCE_TYPE_NAME,
            {
                'RoleName': f'CompactConnect-{environment_name}-SSNBackupRole',
                'Policies': Match.array_with(
                    [
                        {
                            'PolicyName': 'SSNBackupSecurityPolicy',
                            'PolicyDocument': {
                                'Version': '2012-10-17',
                                'Statement': Match.array_with(
                                    [
                                        {
                                            'Sid': 'RestrictCrossAccountOperations',
                                            'Effect': 'Deny',
                                            'Action': ['backup:CopyIntoBackupVault', 'backup:StartCopyJob'],
                                            'Resource': '*',
                                            'Condition': {'StringNotEquals': {'backup:CopyTargets': Match.any_value()}},
                                        }
                                    ]
                                ),
                            },
                        }
                    ]
                ),
            },
        )

    def test_cross_account_vault_references(self):
        """Test that cross-account vault references are correctly created."""
        # Test that the vault objects are created and have the expected ARNs
        backup_config = self.backup_stack.backup_config
        expected_general_arn = self.backup_stack.format_arn(
            arn_format=ArnFormat.COLON_RESOURCE_NAME,
            service='backup',
            region=backup_config['backup_region'],
            account=backup_config['backup_account_id'],
            resource='backup-vault',
            resource_name=backup_config['general_vault_name'],
        )
        expected_ssn_arn = self.backup_stack.format_arn(
            arn_format=ArnFormat.COLON_RESOURCE_NAME,
            service='backup',
            region=backup_config['backup_region'],
            account=backup_config['backup_account_id'],
            resource='backup-vault',
            resource_name=backup_config['ssn_vault_name'],
        )

        # Test that the vault objects exist and have the correct ARNs
        self.assertIsNotNone(self.backup_stack.cross_account_backup_vault)
        self.assertIsNotNone(self.backup_stack.cross_account_ssn_backup_vault)
        self.assertEqual(expected_general_arn, self.backup_stack.cross_account_backup_vault.backup_vault_arn)
        self.assertEqual(expected_ssn_arn, self.backup_stack.cross_account_ssn_backup_vault.backup_vault_arn)

    def test_removal_policy_set_for_sandbox_environment(self):
        """Test that all resources have RemovalPolicy.DESTROY in sandbox environment for development cleanup."""
        # Since we're testing with sandbox context (non-prod), resources should have DESTROY policy
        environment_name = self.app.sandbox_backend_stage.backup_infrastructure_stack.environment_name
        self.assertNotEqual(environment_name, 'prod', 'Test should be using non-prod environment')

        # KMS keys should have DeletionPolicy: Delete (DESTROY)
        kms_keys = self.template.find_resources(CfnKey.CFN_RESOURCE_TYPE_NAME)
        for key_id, key_props in kms_keys.items():
            self.assertEqual(
                key_props.get('DeletionPolicy'),
                'Delete',
                f'KMS key {key_id} should have Delete deletion policy in {environment_name} environment',
            )

        # Backup vaults should have DeletionPolicy: Delete (DESTROY)
        backup_vaults = self.template.find_resources(CfnBackupVault.CFN_RESOURCE_TYPE_NAME)
        for vault_id, vault_props in backup_vaults.items():
            self.assertEqual(
                vault_props.get('DeletionPolicy'),
                'Delete',
                f'Backup vault {vault_id} should have Delete deletion policy in {environment_name} environment',
            )

    def test_backend_stage_integration(self):
        """Test that the backup infrastructure stack integrates correctly with the backend stage."""
        # The backup infrastructure stack should be present in the sandbox backend stage
        self.assertIsNotNone(self.app.sandbox_backend_stage.backup_infrastructure_stack)

        # Validate that the stack is properly configured as a nested stack
        # NestedStacks have token-based names so we check that it's not None instead of exact match
        self.assertIsNotNone(self.backup_stack.stack_name)
        
        # Validate that all expected backup infrastructure resources are created
        self._check_no_backend_stage_annotations(self.app.sandbox_backend_stage)

    def test_backup_monitoring_configuration(self):
        """Test that backup monitoring alarms and rules are correctly configured."""
        environment_name = self.app.sandbox_backend_stage.backup_infrastructure_stack.environment_name

        # Test general backup vault failure alarm (uses CloudFormation reference for vault name)
        self.template.has_resource_properties(
            CfnAlarm.CFN_RESOURCE_TYPE_NAME,
            {
                'MetricName': 'NumberOfBackupJobsFailed',
                'Namespace': 'AWS/Backup',
                'Dimensions': [{'Name': 'BackupVaultName', 'Value': Match.any_value()}],
                'Threshold': 1,
                'ComparisonOperator': 'GreaterThanOrEqualToThreshold',
            },
        )

        # Test SSN backup vault failure alarm (critical) (uses CloudFormation reference for vault name)
        self.template.has_resource_properties(
            CfnAlarm.CFN_RESOURCE_TYPE_NAME,
            {
                'MetricName': 'NumberOfBackupJobsFailed',
                'Namespace': 'AWS/Backup',
                'Dimensions': [
                    {'Name': 'BackupVaultName', 'Value': Match.any_value()}
                ],
                'Threshold': 1,
                'ComparisonOperator': 'GreaterThanOrEqualToThreshold',
                'AlarmDescription': Match.string_like_regexp('.*CRITICAL.*'),
            },
        )

        # Test copy job failure alarm
        self.template.has_resource_properties(
            CfnAlarm.CFN_RESOURCE_TYPE_NAME,
            {
                'MetricName': 'NumberOfCopyJobsFailed',
                'Namespace': 'AWS/Backup',
                'Threshold': 1,
                'ComparisonOperator': 'GreaterThanOrEqualToThreshold',
            },
        )

        # Test backup job failure EventBridge rule
        self.template.has_resource_properties(
            CfnRule.CFN_RESOURCE_TYPE_NAME,
            {
                'EventPattern': {
                    'source': ['aws.backup'],
                    'detail-type': ['Backup Job State Change'],
                    'detail': {'state': ['FAILED', 'ABORTED']},
                },
                'Targets': Match.any_value(),
            },
        )

        # Test copy job failure EventBridge rule
        self.template.has_resource_properties(
            CfnRule.CFN_RESOURCE_TYPE_NAME,
            {
                'EventPattern': {
                    'source': ['aws.backup'],
                    'detail-type': ['Copy Job State Change'],
                    'detail': {'state': ['FAILED']},
                },
                'Targets': Match.any_value(),
            },
        )


class TestBackupInfrastructureStackProduction(TstAppABC, TestCase):
    """Test backup infrastructure stack behavior in production environment."""

    @classmethod
    def get_context(cls):
        with open('cdk.json') as f:
            context = json.load(f)['context']
        with open('cdk.context.prod-example.json') as f:
            context.update(json.load(f))

        # Suppresses lambda bundling for tests
        context['aws:cdk:bundling-stacks'] = []

        return context

    def setUp(self):
        """Set up test fixtures."""
        # Use the production backend stage for testing backup infrastructure
        self.backup_stack = self.app.prod_backend_pipeline_stack.prod_stage.backup_infrastructure_stack
        self.template = Template.from_stack(self.backup_stack)

    def test_removal_policy_set_for_production_environment(self):
        """Test that all resources have RemovalPolicy.RETAIN in production environment for data protection."""
        from aws_cdk import RemovalPolicy

        # Verify that the removal policy is set to RETAIN for production
        self.assertEqual(
            self.backup_stack.removal_policy,
            RemovalPolicy.RETAIN,
            'Production environment should have RETAIN removal policy',
        )

        # Verify environment name is 'prod'
        self.assertEqual(self.backup_stack.environment_name, 'prod', 'Should be testing production environment')

        # KMS keys should have DeletionPolicy: Retain
        kms_keys = self.template.find_resources(CfnKey.CFN_RESOURCE_TYPE_NAME)
        self.assertGreater(len(kms_keys), 0, 'Should have KMS keys in the template')
        for key_id, key_props in kms_keys.items():
            self.assertEqual(
                key_props.get('DeletionPolicy'),
                'Retain',
                f'KMS key {key_id} should have Retain deletion policy in prod environment',
            )

        # Backup vaults should have DeletionPolicy: Retain
        backup_vaults = self.template.find_resources(CfnBackupVault.CFN_RESOURCE_TYPE_NAME)
        self.assertGreater(len(backup_vaults), 0, 'Should have backup vaults in the template')
        for vault_id, vault_props in backup_vaults.items():
            self.assertEqual(
                vault_props.get('DeletionPolicy'),
                'Retain',
                f'Backup vault {vault_id} should have Retain deletion policy in prod environment',
            )
