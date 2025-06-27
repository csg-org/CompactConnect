from aws_cdk import ArnFormat, RemovalPolicy, Stack
from aws_cdk.aws_backup import BackupVault
from aws_cdk.aws_iam import (
    Effect,
    ManagedPolicy,
    PolicyDocument,
    PolicyStatement,
    Role,
    ServicePrincipal,
)
from aws_cdk.aws_kms import Alias, Key
from constructs import Construct


class BackupInfrastructureStack(Stack):
    """
    Stack that creates the backup infrastructure within each environment account.

    This stack provides the local backup infrastructure needed for CompactConnect
    data retention, including backup vaults, KMS keys, and IAM roles. Each
    environment account manages its own complete backup infrastructure, with
    copy actions replicating backups to the cross-account destination vaults
    created by the backup account stack.

    Resources Created:
    - Local backup vaults (general and SSN-specific)
    - Local KMS keys for backup encryption
    - IAM service roles for backup operations
    - Cross-account destination vault references from context
    """

    def __init__(
        self, scope: Construct, construct_id: str, environment_name: str, backup_config: dict, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.environment_name = environment_name

        # If we delete this stack, retain the resource (orphan but prevent data loss) or destroy it (clean up)?
        self.removal_policy = RemovalPolicy.RETAIN if environment_name == 'prod' else RemovalPolicy.DESTROY

        self.backup_config = backup_config

        # Create local backup encryption keys
        self._create_local_backup_encryption_key()
        self._create_local_ssn_backup_encryption_key()

        # Create IAM roles for backup operations
        self._create_backup_service_role()
        self._create_ssn_backup_service_role()

        # Create local backup vaults
        self._create_local_backup_vault()
        self._create_local_ssn_backup_vault()

    def _create_local_backup_encryption_key(self) -> None:
        """Create a local KMS key for general backup encryption."""
        self.local_backup_key = Key(
            self,
            'LocalBackupEncryptionKey',
            description=f'Local KMS key for CompactConnect {self.environment_name} backup encryption',
            removal_policy=self.removal_policy,
        )

        # Add an alias for the local backup key
        Alias(
            self,
            'LocalBackupEncryptionKeyAlias',
            alias_name=f'alias/compactconnect-{self.environment_name}-backup-key',
            target_key=self.local_backup_key,
        )

    def _create_local_ssn_backup_encryption_key(self) -> None:
        """Create a dedicated local KMS key for SSN backup encryption."""
        self.local_ssn_backup_key = Key(
            self,
            'LocalSSNBackupEncryptionKey',
            description=f'Local KMS key for CompactConnect {self.environment_name} SSN backup encryption',
            removal_policy=self.removal_policy,
        )

        # Add an alias for the local SSN backup key
        Alias(
            self,
            'LocalSSNBackupEncryptionKeyAlias',
            alias_name=f'alias/compactconnect-{self.environment_name}-ssn-backup-key',
            target_key=self.local_ssn_backup_key,
        )

    def _create_backup_service_role(self) -> None:
        """Create the standard AWS Backup service role for general backup operations."""
        self.backup_service_role = Role(
            self,
            'BackupServiceRole',
            role_name=f'CompactConnect-{self.environment_name}-BackupServiceRole',
            assumed_by=ServicePrincipal('backup.amazonaws.com'),
            managed_policies=[
                ManagedPolicy.from_aws_managed_policy_name('service-role/AWSBackupServiceRolePolicyForBackup'),
                ManagedPolicy.from_aws_managed_policy_name('service-role/AWSBackupServiceRolePolicyForRestores'),
            ],
        )

    def _create_ssn_backup_service_role(self) -> None:
        """Create a specialized backup service role for SSN data with enhanced security controls."""
        # Create a policy that restricts cross-account copy operations to only our approved backup account
        # This provides security controls while allowing necessary backup and restore operations
        restrict_cross_account_policy_statement = PolicyStatement(
            sid='RestrictCrossAccountOperations',
            effect=Effect.DENY,
            actions=['backup:CopyIntoBackupVault', 'backup:StartCopyJob'],
            resources=['*'],
            conditions={'StringNotEquals': {'backup:CopyTargets': [self.cross_account_ssn_backup_vault_arn]}},
        )

        self.ssn_backup_service_role = Role(
            self,
            'SSNBackupServiceRole',
            role_name=f'CompactConnect-{self.environment_name}-SSNBackupRole',
            assumed_by=ServicePrincipal('backup.amazonaws.com'),
            managed_policies=[
                ManagedPolicy.from_aws_managed_policy_name('service-role/AWSBackupServiceRolePolicyForBackup'),
                ManagedPolicy.from_aws_managed_policy_name('service-role/AWSBackupServiceRolePolicyForRestores'),
            ],
            inline_policies={
                'SSNBackupSecurityPolicy': PolicyDocument(statements=[restrict_cross_account_policy_statement])
            },
        )

    def _create_local_backup_vault(self) -> None:
        """Create the local backup vault for general backup operations."""
        self.local_backup_vault = BackupVault(
            self,
            'LocalBackupVault',
            backup_vault_name=f'CompactConnect-{self.environment_name}-BackupVault',
            encryption_key=self.local_backup_key,
            removal_policy=self.removal_policy,
        )

    def _create_local_ssn_backup_vault(self) -> None:
        """Create the dedicated local backup vault for SSN data."""
        self.local_ssn_backup_vault = BackupVault(
            self,
            'LocalSSNBackupVault',
            backup_vault_name=f'CompactConnect-{self.environment_name}-SSNBackupVault',
            encryption_key=self.local_ssn_backup_key,
            removal_policy=self.removal_policy,
        )

    @property
    def cross_account_backup_vault_arn(self) -> str:
        """Get the cross-account backup vault ARN from context configuration."""
        return self.format_arn(
            account=self.backup_config['backup_account_id'],
            region=self.backup_config['backup_region'],
            service='backup',
            resource='backup-vault',
            resource_name=self.backup_config['general_vault_name'],
            arn_format=ArnFormat.COLON_RESOURCE_NAME,
        )

    @property
    def cross_account_ssn_backup_vault_arn(self) -> str:
        """Get the cross-account SSN backup vault ARN from context configuration."""
        return self.format_arn(
            account=self.backup_config['backup_account_id'],
            region=self.backup_config['backup_region'],
            service='backup',
            resource='backup-vault',
            resource_name=self.backup_config['ssn_vault_name'],
            arn_format=ArnFormat.COLON_RESOURCE_NAME,
        )
