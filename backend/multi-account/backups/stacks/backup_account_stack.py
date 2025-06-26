from aws_cdk import CfnOutput, RemovalPolicy, Stack
from aws_cdk.aws_backup import BackupVault
from aws_cdk.aws_iam import (
    AccountPrincipal,
    AccountRootPrincipal,
    Effect,
    PolicyDocument,
    PolicyStatement,
    StarPrincipal,
)
from aws_cdk.aws_kms import Alias, Key
from constructs import Construct


class BackupAccountStack(Stack):
    """
    Stack deployed to the backup account that creates the cross-account backup infrastructure
    for CompactConnect data retention. This serves as the secure destination for backups from
    all environment accounts.

    Creates:
    - Cross-account backup vaults (general and SSN-specific)
    - Customer-managed KMS keys for backup encryption
    - Organization-level access policies
    - Break-glass security controls for SSN data

    Based on AWS best practices for cross-account backup architecture as described in:
    "How to secure recovery with cross-account backup and cross-Region copy using AWS Backup"
    """

    def __init__(
        self, scope: Construct, construct_id: str, organization_id: str, source_account_ids: list[str], **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.organization_id = organization_id
        self.source_account_ids = source_account_ids

        # Create the KMS key for backup encryption
        self._create_backup_encryption_key()

        # Create the dedicated SSN KMS key for enhanced security
        self._create_ssn_backup_encryption_key()

        # Create the backup vault
        self._create_backup_vault()

        # Create the dedicated SSN backup vault
        self._create_ssn_backup_vault()

        # Create outputs
        self._create_outputs()

    def _create_backup_encryption_key(self) -> None:
        """
        Create a customer-managed KMS key for backup encryption with cross-account access.
        """
        # Build the key policy statements
        key_policy_statements = [
            PolicyStatement(
                sid='EnableInAccountPermissions',
                effect=Effect.ALLOW,
                principals=[AccountRootPrincipal()],
                actions=['kms:*'],
                resources=['*'],
            ),
            # Allow use of the key from source accounts
            PolicyStatement(
                sid='AllowUseOfTheKey',
                effect=Effect.ALLOW,
                principals=[AccountPrincipal(account_id) for account_id in self.source_account_ids],
                actions=[
                    'kms:DescribeKey',
                    'kms:Encrypt',
                    'kms:Decrypt',
                    'kms:ReEncrypt*',
                    'kms:GenerateDataKey',
                    'kms:GenerateDataKeyWithoutPlaintext',
                ],
                resources=['*'],
            ),
            # Allow attachment of persistent resources
            PolicyStatement(
                sid='AllowAttachmentOfPersistentResources',
                effect=Effect.ALLOW,
                principals=[AccountPrincipal(account_id) for account_id in self.source_account_ids],
                actions=[
                    'kms:CreateGrant',
                    'kms:ListGrants',
                    'kms:RevokeGrant',
                ],
                resources=['*'],
                conditions={'Bool': {'kms:GrantIsForAWSResource': 'true'}},
            ),
        ]

        self.backup_key = Key(
            self,
            'BackupEncryptionKey',
            description='KMS key for CompactConnect cross-account backup encryption',
            policy=PolicyDocument(statements=key_policy_statements),
            removal_policy=RemovalPolicy.DESTROY,  # Allow deletion during development/testing
        )

        # Add an alias for the key
        Alias(
            self,
            'BackupEncryptionKeyAlias',
            alias_name='alias/compactconnect-backup-key',
            target_key=self.backup_key,
        )

    def _create_ssn_backup_encryption_key(self) -> None:
        """
        Create a dedicated customer-managed KMS key for SSN backup encryption with enhanced security controls.
        """
        # Build the key policy statements for SSN data with restricted access
        ssn_key_policy_statements = [
            # Enable IAM User Permissions for backup account
            PolicyStatement(
                sid='EnableInAccountPermissions',
                effect=Effect.ALLOW,
                principals=[AccountRootPrincipal()],
                actions=['kms:*'],
                resources=['*'],
            ),
            # Allow use of the key from source accounts (only for SSN table operations)
            PolicyStatement(
                sid='AllowSSNBackupOperations',
                effect=Effect.ALLOW,
                principals=[AccountPrincipal(account_id) for account_id in self.source_account_ids],
                actions=[
                    'kms:DescribeKey',
                    'kms:Encrypt',
                    'kms:Decrypt',
                    'kms:ReEncrypt*',
                    'kms:GenerateDataKey',
                    'kms:GenerateDataKeyWithoutPlaintext',
                ],
                resources=['*'],
                conditions={
                    'StringLike': {
                        'kms:ViaService': [
                            f'backup.{self.region}.amazonaws.com',
                            f'dynamodb.{self.region}.amazonaws.com',
                        ]
                    }
                },
            ),
            # Allow attachment of persistent resources with strict conditions
            PolicyStatement(
                sid='AllowSSNGrantCreation',
                effect=Effect.ALLOW,
                principals=[AccountPrincipal(account_id) for account_id in self.source_account_ids],
                actions=[
                    'kms:CreateGrant',
                    'kms:ListGrants',
                    'kms:RevokeGrant',
                ],
                resources=['*'],
                conditions={'Bool': {'kms:GrantIsForAWSResource': 'true'}},
            ),
            # Deny all decrypt/restore operations except for AWS services - break-glass approach
            # This requires explicit policy modification for emergency SSN data restoration
            PolicyStatement(
                sid='DenySSNKeyDecryptOperations',
                effect=Effect.DENY,
                actions=['kms:Decrypt', 'kms:GenerateDataKey', 'kms:GenerateDataKeyWithoutPlaintext'],
                principals=[StarPrincipal()],
                resources=['*'],
                conditions={
                    'StringNotEquals': {'aws:PrincipalServiceName': ['backup.amazonaws.com', 'dynamodb.amazonaws.com']}
                },
            ),
        ]

        self.ssn_backup_key = Key(
            self,
            'SSNBackupEncryptionKey',
            description='Dedicated KMS key for CompactConnect SSN data backup encryption',
            policy=PolicyDocument(statements=ssn_key_policy_statements),
            removal_policy=RemovalPolicy.DESTROY,  # Allow deletion during development/testing
        )

        # Add an alias for the SSN backup key
        Alias(
            self,
            'SSNBackupEncryptionKeyAlias',
            alias_name='alias/compactconnect-ssn-backup-key',
            target_key=self.ssn_backup_key,
        )

    def _create_backup_vault(self) -> None:
        """
        Create the backup vault with cross-account access policy.
        """
        # Create access policy for the backup vault
        vault_access_policy = PolicyDocument(
            statements=[
                PolicyStatement(
                    sid='EnableBackupVaultAccess',
                    effect=Effect.ALLOW,
                    actions=['backup:CopyIntoBackupVault'],
                    resources=['*'],
                    principals=[AccountPrincipal(account_id) for account_id in self.source_account_ids],
                    conditions={'StringEquals': {'aws:PrincipalOrgID': self.organization_id}},
                )
            ]
        )

        # Get vault name from context or use default
        vault_name = self.node.get_context('backup_vault_name')

        self.backup_vault = BackupVault(
            self,
            'CompactConnectBackupVault',
            backup_vault_name=vault_name,
            encryption_key=self.backup_key,
            access_policy=vault_access_policy,
            removal_policy=RemovalPolicy.DESTROY,  # Allow deletion during development/testing
        )

    def _create_ssn_backup_vault(self) -> None:
        """
        Create the dedicated SSN backup vault with enhanced access controls for SSN data protection.
        """
        # Create enhanced access policy for the SSN backup vault
        ssn_vault_access_policy = PolicyDocument(
            statements=[
                PolicyStatement(
                    sid='EnableSSNBackupVaultAccess',
                    effect=Effect.ALLOW,
                    actions=['backup:CopyIntoBackupVault'],
                    resources=['*'],
                    principals=[AccountPrincipal(account_id) for account_id in self.source_account_ids],
                    conditions={'StringEquals': {'aws:PrincipalOrgID': self.organization_id}},
                )
            ]
        )

        # Get SSN vault name from context or use default
        ssn_vault_name = self.node.get_context('ssn_backup_vault_name')

        self.ssn_backup_vault = BackupVault(
            self,
            'SSNBackupVault',
            backup_vault_name=ssn_vault_name,
            encryption_key=self.ssn_backup_key,
            access_policy=ssn_vault_access_policy,
            removal_policy=RemovalPolicy.DESTROY,  # Allow deletion during development/testing
        )

    def _create_outputs(self) -> None:
        """
        Create CloudFormation outputs for the created resources.
        """
        CfnOutput(
            self,
            'BackupVaultName',
            value=self.backup_vault.backup_vault_name,
            description='Name of the cross-account backup vault',
        )

        CfnOutput(
            self,
            'BackupVaultArn',
            value=self.backup_vault.backup_vault_arn,
            description='ARN of the cross-account backup vault',
        )

        CfnOutput(
            self,
            'BackupEncryptionKeyId',
            value=self.backup_key.key_id,
            description='ID of the backup encryption key',
        )

        CfnOutput(
            self,
            'BackupEncryptionKeyArn',
            value=self.backup_key.key_arn,
            description='ARN of the backup encryption key',
        )

        # SSN-specific outputs
        CfnOutput(
            self,
            'SSNBackupVaultName',
            value=self.ssn_backup_vault.backup_vault_name,
            description='Name of the dedicated SSN backup vault',
        )

        CfnOutput(
            self,
            'SSNBackupVaultArn',
            value=self.ssn_backup_vault.backup_vault_arn,
            description='ARN of the dedicated SSN backup vault',
        )

        CfnOutput(
            self,
            'SSNBackupEncryptionKeyId',
            value=self.ssn_backup_key.key_id,
            description='ID of the dedicated SSN backup encryption key',
        )

        CfnOutput(
            self,
            'SSNBackupEncryptionKeyArn',
            value=self.ssn_backup_key.key_arn,
            description='ARN of the dedicated SSN backup encryption key',
        )
