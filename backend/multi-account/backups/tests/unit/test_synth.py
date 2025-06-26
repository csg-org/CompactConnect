import json
from unittest import TestCase

from app import BackupsApp
from aws_cdk.assertions import Match, Template
from stacks.backup_account_stack import BackupAccountStack


class TestSynth(TestCase):
    def test_synth(self):
        # Load the example context file
        with open('cdk.context.example.json') as f:
            test_context = json.load(f)

        # Create the app with our test context
        app = BackupsApp(context=test_context)

        # Synthesize the app to ensure it builds without errors
        assembly = app.synth()

        # Verify app synthesis produces exactly one stack
        self.assertEqual(len(assembly.stacks), 1, 'App should produce exactly one stack')

        # Verify the stack name is correct
        stack_names = [stack.stack_name for stack in assembly.stacks]
        self.assertIn('BackupAccountStack', stack_names, 'Should include BackupAccountStack')

        # Comprehensively inspect the backup account stack
        self._inspect_backup_account_stack(app.backup_account_stack)

    def _inspect_backup_account_stack(self, stack: BackupAccountStack):
        """Comprehensively validate the BackupAccountStack resources and configuration."""
        template = Template.from_stack(stack)

        # Validate basic resource counts
        self._validate_resource_counts(template)

        # Validate KMS encryption infrastructure
        self._validate_kms_infrastructure(template)

        # Validate backup vault infrastructure
        self._validate_backup_vault_infrastructure(template)

        # Validate cross-account access policies
        self._validate_cross_account_policies(template)

        # Validate SSN-specific security controls
        self._validate_ssn_security_controls(template)

        # Validate break-glass security measures
        self._validate_break_glass_controls(template)

        # Validate stack outputs for integration
        self._validate_stack_outputs(template)

    def _validate_resource_counts(self, template: Template):
        """Validate the correct number of each resource type."""
        # Should have exactly 2 KMS keys (general + SSN)
        template.resource_count_is('AWS::KMS::Key', 2)

        # Should have exactly 2 KMS aliases (general + SSN)
        template.resource_count_is('AWS::KMS::Alias', 2)

        # Should have exactly 2 backup vaults (general + SSN)
        template.resource_count_is('AWS::Backup::BackupVault', 2)

    def _validate_kms_infrastructure(self, template: Template):
        """Validate KMS key infrastructure for both general and SSN encryption."""
        # Validate general backup KMS key
        template.has_resource_properties(
            'AWS::KMS::Key',
            {
                'Description': 'KMS key for CompactConnect cross-account backup encryption',
                'KeyPolicy': {
                    'Statement': Match.array_with(
                        [
                            Match.object_like(
                                {
                                    'Sid': 'EnableInAccountPermissions',
                                    'Effect': 'Allow',
                                    'Principal': {'AWS': Match.any_value()},
                                    'Action': 'kms:*',
                                    'Resource': '*',
                                }
                            ),
                            Match.object_like(
                                {
                                    'Sid': 'AllowUseOfTheKey',
                                    'Effect': 'Allow',
                                    'Action': Match.array_with(['kms:DescribeKey', 'kms:Encrypt', 'kms:Decrypt']),
                                }
                            ),
                        ]
                    )
                },
            },
        )

        # Validate SSN backup KMS key with enhanced security
        template.has_resource_properties(
            'AWS::KMS::Key',
            {
                'Description': 'Dedicated KMS key for CompactConnect SSN data backup encryption',
                'KeyPolicy': {
                    'Statement': Match.array_with(
                        [
                            Match.object_like(
                                {
                                    'Sid': 'EnableInAccountPermissions',
                                    'Effect': 'Allow',
                                    'Principal': {'AWS': Match.any_value()},
                                    'Action': 'kms:*',
                                    'Resource': '*',
                                }
                            ),
                            Match.object_like(
                                {
                                    'Sid': 'AllowSSNBackupOperations',
                                    'Effect': 'Allow',
                                    'Condition': {
                                        'StringLike': {
                                            'kms:ViaService': Match.array_with(
                                                [
                                                    Match.string_like_regexp(r'backup\..*\.amazonaws\.com'),
                                                    Match.string_like_regexp(r'dynamodb\..*\.amazonaws\.com'),
                                                ]
                                            )
                                        }
                                    },
                                }
                            ),
                            # Break-glass DENY policy
                            Match.object_like(
                                {
                                    'Sid': 'DenySSNKeyDecryptOperations',
                                    'Effect': 'Deny',
                                    'Action': Match.array_with(['kms:Decrypt', 'kms:GenerateDataKey']),
                                }
                            ),
                        ]
                    )
                },
            },
        )

        # Validate KMS key aliases
        template.has_resource_properties('AWS::KMS::Alias', {'AliasName': 'alias/compactconnect-backup-key'})
        template.has_resource_properties('AWS::KMS::Alias', {'AliasName': 'alias/compactconnect-ssn-backup-key'})

    def _validate_backup_vault_infrastructure(self, template: Template):
        """Validate backup vault configuration and naming."""
        # Validate general backup vault
        template.has_resource_properties(
            'AWS::Backup::BackupVault',
            {
                'BackupVaultName': 'CompactConnectBackupVault',
                'EncryptionKeyArn': Match.any_value(),  # Should reference the general KMS key
            },
        )

        # Validate SSN backup vault
        template.has_resource_properties(
            'AWS::Backup::BackupVault',
            {
                'BackupVaultName': 'CompactConnectBackupVault-SSN',
                'EncryptionKeyArn': Match.any_value(),  # Should reference the SSN KMS key
            },
        )

    def _validate_cross_account_policies(self, template: Template):
        """Validate cross-account access policies for organization accounts."""
        # Validate general backup vault organization access with specific source account principals
        template.has_resource_properties(
            'AWS::Backup::BackupVault',
            {
                'BackupVaultName': 'CompactConnectBackupVault',
                'AccessPolicy': {
                    'Statement': Match.array_with(
                        [
                            Match.object_like(
                                {
                                    'Sid': 'EnableBackupVaultAccess',
                                    'Effect': 'Allow',
                                    'Action': 'backup:CopyIntoBackupVault',
                                    'Resource': '*',
                                    'Principal': {
                                        'AWS': [
                                            {
                                                'Fn::Join': [
                                                    '',
                                                    ['arn:', {'Ref': 'AWS::Partition'}, ':iam::000011115555:root'],
                                                ]
                                            },
                                            {
                                                'Fn::Join': [
                                                    '',
                                                    ['arn:', {'Ref': 'AWS::Partition'}, ':iam::000011116666:root'],
                                                ]
                                            },
                                            {
                                                'Fn::Join': [
                                                    '',
                                                    ['arn:', {'Ref': 'AWS::Partition'}, ':iam::000011117777:root'],
                                                ]
                                            },
                                        ]  # Exact CloudFormation intrinsic functions with partition reference
                                    },
                                    'Condition': {
                                        'StringEquals': {
                                            'aws:PrincipalOrgID': 'o-example123456'  # Exact org ID from example context
                                        }
                                    },
                                }
                            )
                        ]
                    )
                },
            },
        )

    def _validate_ssn_security_controls(self, template: Template):
        """Validate enhanced security controls specific to SSN data."""
        # Validate SSN backup vault has restrictive access policies with specific source account principals
        template.has_resource_properties(
            'AWS::Backup::BackupVault',
            {
                'BackupVaultName': 'CompactConnectBackupVault-SSN',
                'AccessPolicy': {
                    'Statement': Match.array_with(
                        [
                            # Allow access only for SSN table from specific source accounts
                            Match.object_like(
                                {
                                    'Sid': 'EnableSSNBackupVaultAccess',
                                    'Effect': 'Allow',
                                    'Action': 'backup:CopyIntoBackupVault',
                                    'Principal': {
                                        'AWS': [
                                            {
                                                'Fn::Join': [
                                                    '',
                                                    ['arn:', {'Ref': 'AWS::Partition'}, ':iam::000011115555:root'],
                                                ]
                                            },
                                            {
                                                'Fn::Join': [
                                                    '',
                                                    ['arn:', {'Ref': 'AWS::Partition'}, ':iam::000011116666:root'],
                                                ]
                                            },
                                            {
                                                'Fn::Join': [
                                                    '',
                                                    ['arn:', {'Ref': 'AWS::Partition'}, ':iam::000011117777:root'],
                                                ]
                                            },
                                        ]  # Exact CloudFormation intrinsic functions with partition reference
                                    },
                                    'Condition': {
                                        'StringEquals': {
                                            'aws:PrincipalOrgID': 'o-example123456'  # Exact org ID from example context
                                        }
                                    },
                                }
                            )
                        ]
                    )
                },
            },
        )

    def _validate_break_glass_controls(self, template: Template):
        """Validate break-glass security controls that require explicit policy modification."""
        # Note: Break-glass controls are enforced through KMS key policies only
        # AWS Backup vault policies do not support restore action controls

        # Validate SSN KMS key has break-glass decrypt denial
        template.has_resource_properties(
            'AWS::KMS::Key',
            {
                'Description': 'Dedicated KMS key for CompactConnect SSN data backup encryption',
                'KeyPolicy': {
                    'Statement': Match.array_with(
                        [
                            Match.object_like(
                                {
                                    'Sid': 'DenySSNKeyDecryptOperations',
                                    'Effect': 'Deny',
                                    'Action': Match.array_with(
                                        ['kms:Decrypt', 'kms:GenerateDataKey', 'kms:GenerateDataKeyWithoutPlaintext']
                                    ),
                                    'Principal': '*',  # StarPrincipal() generates string format for KMS
                                    'Condition': {
                                        'StringNotEquals': {
                                            'aws:PrincipalServiceName': Match.array_with(
                                                ['backup.amazonaws.com', 'dynamodb.amazonaws.com']
                                            )
                                        }
                                    },
                                }
                            )
                        ]
                    )
                },
            },
        )

    def _validate_stack_outputs(self, template: Template):
        """Validate that the stack produces the necessary outputs for integration."""
        # Find all outputs
        outputs = template.find_outputs('*')

        # Should have outputs for both backup vaults
        backup_vault_outputs = [name for name in outputs.keys() if 'BackupVault' in name]
        self.assertGreaterEqual(len(backup_vault_outputs), 2, 'Should have outputs for both backup vaults')

        # Should have outputs for both KMS keys
        kms_key_outputs = [name for name in outputs.keys() if 'Key' in name and 'Arn' in name]
        self.assertGreaterEqual(len(kms_key_outputs), 2, 'Should have outputs for both KMS key ARNs')

    def test_environment_account_integration_requirements(self):
        """Test that the stack provides everything needed for environment account integration."""
        # Load the example context file
        with open('cdk.context.example.json') as f:
            test_context = json.load(f)

        # Create the app with our test context
        app = BackupsApp(context=test_context)
        app.synth()

        # Get the stack instance
        stack = app.backup_account_stack

        # Validate that the stack exposes the required attributes for cross-account integration
        self.assertIsNotNone(stack.backup_vault, 'Stack should expose backup_vault attribute')
        self.assertIsNotNone(stack.ssn_backup_vault, 'Stack should expose ssn_backup_vault attribute')
        self.assertIsNotNone(stack.backup_key, 'Stack should expose backup_key attribute')
        self.assertIsNotNone(stack.ssn_backup_key, 'Stack should expose ssn_backup_key attribute')

        # Validate that these attributes are accessible (don't test token values)
        # CDK tokens will resolve to actual values at deployment time
        self.assertIsNotNone(stack.backup_vault.backup_vault_arn)
        self.assertIsNotNone(stack.ssn_backup_vault.backup_vault_arn)
        self.assertIsNotNone(stack.backup_key.key_arn)
        self.assertIsNotNone(stack.ssn_backup_key.key_arn)

    def test_context_configuration_validation(self):
        """Test that the app properly validates and uses context configuration."""
        # Load the example context file
        with open('cdk.context.example.json') as f:
            test_context = json.load(f)

        # Test with missing required context
        incomplete_context = test_context.copy()
        del incomplete_context['organization_id']

        with self.assertRaises(RuntimeError):
            app = BackupsApp(context=incomplete_context)
            app.synth()

        # Test with complete context
        app = BackupsApp(context=test_context)
        assembly = app.synth()

        # Should successfully synthesize
        self.assertEqual(len(assembly.stacks), 1)
