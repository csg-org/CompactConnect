from aws_cdk import ArnFormat, Duration, NestedStack, RemovalPolicy
from aws_cdk.aws_backup import BackupVault
from aws_cdk.aws_cloudwatch import Alarm, ComparisonOperator, Metric, TreatMissingData
from aws_cdk.aws_cloudwatch_actions import SnsAction
from aws_cdk.aws_events import EventPattern, Rule
from aws_cdk.aws_events_targets import SnsTopic
from aws_cdk.aws_iam import (
    AccountPrincipal,
    Effect,
    ManagedPolicy,
    PolicyDocument,
    PolicyStatement,
    Role,
    ServicePrincipal,
    StarPrincipal,
)
from aws_cdk.aws_kms import Alias, Key
from aws_cdk.aws_sns import ITopic
from cdk_nag import NagSuppressions
from constructs import Construct


class BackupInfrastructureStack(NestedStack):
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
        self,
        scope: Construct,
        construct_id: str,
        environment_name: str,
        backup_config: dict,
        alarm_topic: ITopic,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.environment_name = environment_name
        self.alarm_topic = alarm_topic

        # If we delete this stack, retain the resource (orphan but prevent data loss) or destroy it (clean up)?
        self.removal_policy = RemovalPolicy.RETAIN if environment_name == 'prod' else RemovalPolicy.DESTROY

        self.backup_config = backup_config

        # Create local backup encryption keys
        self._create_local_backup_encryption_key()
        self._create_local_ssn_backup_encryption_key()

        # Create references to cross-account backup vaults (needed for SSN backup service role policy)
        self._create_cross_account_vault_references()

        # Create IAM roles for backup operations
        self._create_backup_service_role()
        self._create_ssn_backup_service_role()

        # Create local backup vaults
        self._create_local_backup_vault()
        self._create_local_ssn_backup_vault()

        # Create backup monitoring alarms and EventBridge rules
        self._create_backup_monitoring()

        # Add CDK NAG suppressions for expected AWS managed policies in backup service roles
        self._add_cdk_nag_suppressions()

    def _create_local_backup_encryption_key(self) -> None:
        """Create a local KMS key for general backup encryption."""
        self.local_backup_key = Key(
            self,
            'LocalBackupEncryptionKey',
            description=f'Local KMS key for CompactConnect {self.environment_name} backup encryption',
            enable_key_rotation=True,
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
            enable_key_rotation=True,
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
            # Create a policy that restricts cross-account copy operations to only our approved backup vault
            # This provides security controls while allowing necessary backup and restore operations
            inline_policies={
                'SSNBackupSecurityPolicy': PolicyDocument(
                    statements=[
                        PolicyStatement(
                            sid='RestrictCrossAccountOperations',
                            effect=Effect.DENY,
                            actions=['backup:CopyIntoBackupVault', 'backup:StartCopyJob'],
                            resources=['*'],
                            conditions={
                                'ForAnyValue:ArnNotEquals': {
                                    'backup:CopyTargets': [self.cross_account_ssn_backup_vault.backup_vault_arn]
                                }
                            },
                        )
                    ]
                )
            },
        )

    def _create_ssn_backup_service_role(self) -> None:
        """Create a specialized backup service role for SSN data with enhanced security controls."""
        self.ssn_backup_service_role = Role(
            self,
            'SSNBackupServiceRole',
            role_name=f'CompactConnect-{self.environment_name}-SSNBackupRole',
            assumed_by=ServicePrincipal('backup.amazonaws.com'),
            managed_policies=[
                ManagedPolicy.from_aws_managed_policy_name('service-role/AWSBackupServiceRolePolicyForBackup'),
                ManagedPolicy.from_aws_managed_policy_name('service-role/AWSBackupServiceRolePolicyForRestores'),
            ],
            # Create a policy that restricts cross-account copy operations to only our approved backup vault
            # This provides security controls while allowing necessary backup and restore operations
            inline_policies={
                'SSNBackupSecurityPolicy': PolicyDocument(
                    statements=[
                        PolicyStatement(
                            sid='RestrictCrossAccountOperations',
                            effect=Effect.DENY,
                            actions=['backup:CopyIntoBackupVault', 'backup:StartCopyJob'],
                            resources=['*'],
                            conditions={
                                'ForAnyValue:ArnNotEquals': {
                                    'backup:CopyTargets': [self.cross_account_ssn_backup_vault.backup_vault_arn]
                                }
                            },
                        )
                    ]
                )
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
            access_policy=PolicyDocument(
                statements=[
                    PolicyStatement(
                        sid='EnableBackupVaultAccess',
                        effect=Effect.ALLOW,
                        actions=['backup:CopyIntoBackupVault'],
                        resources=['*'],
                        principals=[AccountPrincipal(self.account)],
                    ),
                    # We only allow copies from this vault, to our approved backup account vault
                    PolicyStatement(
                        sid='OnlyCopyIntoApprovedVault',
                        effect=Effect.DENY,
                        actions=['backup:CopyIntoBackupVault', 'backup:StartCopyJob'],
                        resources=['*'],
                        principals=[StarPrincipal()],
                        conditions={
                            'ForAnyValue:ArnNotEquals': {
                                'backup:CopyTargets': [self.cross_account_backup_vault.backup_vault_arn]
                            }
                        },
                    ),
                ]
            ),
        )

    def _create_local_ssn_backup_vault(self) -> None:
        """Create the dedicated local backup vault for SSN data."""
        self.local_ssn_backup_vault = BackupVault(
            self,
            'LocalSSNBackupVault',
            backup_vault_name=f'CompactConnect-{self.environment_name}-SSNBackupVault',
            encryption_key=self.local_ssn_backup_key,
            removal_policy=self.removal_policy,
            access_policy=PolicyDocument(
                statements=[
                    PolicyStatement(
                        sid='EnableBackupVaultAccess',
                        effect=Effect.ALLOW,
                        actions=['backup:CopyIntoBackupVault'],
                        resources=['*'],
                        principals=[AccountPrincipal(self.account)],
                    ),
                    # We only allow copies from this vault, to our approved backup account vault
                    PolicyStatement(
                        sid='OnlyCopyIntoApprovedVault',
                        effect=Effect.DENY,
                        actions=['backup:CopyIntoBackupVault', 'backup:StartCopyJob'],
                        resources=['*'],
                        principals=[StarPrincipal()],
                        conditions={
                            'ForAnyValue:ArnNotEquals': {
                                'backup:CopyTargets': [self.cross_account_ssn_backup_vault.backup_vault_arn]
                            }
                        },
                    ),
                ]
            ),
        )

    def _create_cross_account_vault_references(self) -> None:
        """Create references to cross-account backup vaults."""
        # Create reference to general cross-account backup vault
        general_vault_arn = self.format_arn(
            account=self.backup_config['backup_account_id'],
            region=self.backup_config['backup_region'],
            service='backup',
            resource='backup-vault',
            resource_name=self.backup_config['general_vault_name'],
            arn_format=ArnFormat.COLON_RESOURCE_NAME,
        )
        self.cross_account_backup_vault = BackupVault.from_backup_vault_arn(
            self, 'CrossAccountBackupVault', general_vault_arn
        )

        # Create reference to SSN cross-account backup vault
        ssn_vault_arn = self.format_arn(
            account=self.backup_config['backup_account_id'],
            region=self.backup_config['backup_region'],
            service='backup',
            resource='backup-vault',
            resource_name=self.backup_config['ssn_vault_name'],
            arn_format=ArnFormat.COLON_RESOURCE_NAME,
        )
        self.cross_account_ssn_backup_vault = BackupVault.from_backup_vault_arn(
            self, 'CrossAccountSSNBackupVault', ssn_vault_arn
        )

    def _create_backup_monitoring(self) -> None:
        """Create comprehensive backup monitoring using CloudWatch alarms and EventBridge rules."""

        # CloudWatch Metric-based Alarms
        self._create_backup_job_failure_alarms()
        self._create_copy_job_failure_alarms()
        self._create_recovery_point_alarms()

        # EventBridge Rules for real-time monitoring
        self._create_backup_event_rules()
        self._create_operational_security_rules()

    def _create_backup_job_failure_alarms(self) -> None:
        """Create alarms for backup job failures across all backup vaults."""

        # General backup job failures
        general_backup_failures = Alarm(
            self,
            'GeneralBackupJobFailures',
            metric=Metric(
                namespace='AWS/Backup',
                metric_name='NumberOfBackupJobsFailed',
                dimensions_map={'BackupVaultName': self.local_backup_vault.backup_vault_name},
                statistic='Sum',
                period=Duration.minutes(5),
            ),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
            alarm_description='One or more backup jobs have failed in the general backup vault. '
            'Investigation required to ensure data protection is maintained.',
        )
        general_backup_failures.add_alarm_action(SnsAction(self.alarm_topic))

        # SSN backup job failures (critical)
        ssn_backup_failures = Alarm(
            self,
            'SSNBackupJobFailures',
            metric=Metric(
                namespace='AWS/Backup',
                metric_name='NumberOfBackupJobsFailed',
                dimensions_map={'BackupVaultName': self.local_ssn_backup_vault.backup_vault_name},
                statistic='Sum',
                period=Duration.minutes(5),
            ),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
            alarm_description='CRITICAL: SSN backup job has failed. Immediate investigation required '
            'as this affects sensitive data protection compliance.',
        )
        ssn_backup_failures.add_alarm_action(SnsAction(self.alarm_topic))

        # Backup job expiration monitoring
        backup_job_expired = Alarm(
            self,
            'BackupJobsExpired',
            metric=Metric(
                namespace='AWS/Backup',
                metric_name='NumberOfBackupJobsExpired',
                statistic='Sum',
                period=Duration.hours(1),
            ),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
            alarm_description='Backup jobs have expired without starting. This may indicate '
            'resource conflicts or scheduling issues.',
        )
        backup_job_expired.add_alarm_action(SnsAction(self.alarm_topic))

    def _create_copy_job_failure_alarms(self) -> None:
        """Create alarms for cross-account copy job failures."""

        copy_job_failures = Alarm(
            self,
            'CrossAccountCopyJobFailures',
            metric=Metric(
                namespace='AWS/Backup',
                metric_name='NumberOfCopyJobsFailed',
                statistic='Sum',
                period=Duration.minutes(15),
            ),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
            alarm_description='Cross-account copy jobs have failed. This affects disaster recovery '
            'capability and requires immediate investigation.',
        )
        copy_job_failures.add_alarm_action(SnsAction(self.alarm_topic))

    def _create_recovery_point_alarms(self) -> None:
        """Create alarms for recovery point issues."""

        # Partial recovery points
        partial_recovery_points = Alarm(
            self,
            'PartialRecoveryPoints',
            metric=Metric(
                namespace='AWS/Backup',
                metric_name='NumberOfRecoveryPointsPartial',
                statistic='Sum',
                period=Duration.hours(1),
            ),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
            alarm_description='Partial recovery points detected. These backups may be incomplete '
            'and could affect restore capabilities.',
        )
        partial_recovery_points.add_alarm_action(SnsAction(self.alarm_topic))

        # Expired recovery points that couldn't be deleted
        expired_recovery_points = Alarm(
            self,
            'ExpiredRecoveryPoints',
            metric=Metric(
                namespace='AWS/Backup',
                metric_name='NumberOfRecoveryPointsExpired',
                statistic='Sum',
                period=Duration.hours(24),
            ),
            threshold=5,
            evaluation_periods=1,
            comparison_operator=ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
            alarm_description='Multiple recovery points have expired but could not be deleted. '
            'This may cause unexpected storage costs.',
        )
        expired_recovery_points.add_alarm_action(SnsAction(self.alarm_topic))

    def _create_backup_event_rules(self) -> None:
        """Create EventBridge rules for real-time backup failure events."""

        # Backup job failure events
        Rule(
            self,
            'BackupJobFailureRule',
            event_pattern=EventPattern(
                source=['aws.backup'],
                detail_type=['Backup Job State Change'],
                detail={
                    'state': ['FAILED', 'ABORTED'],
                },
            ),
            targets=[SnsTopic(self.alarm_topic)],
        )

        # Copy job failure events
        Rule(
            self,
            'CopyJobFailureRule',
            event_pattern=EventPattern(
                source=['aws.backup'],
                detail_type=['Copy Job State Change'],
                detail={
                    'state': ['FAILED'],
                },
            ),
            targets=[SnsTopic(self.alarm_topic)],
        )

        # Recovery point partial/failed events
        Rule(
            self,
            'RecoveryPointIssuesRule',
            event_pattern=EventPattern(
                source=['aws.backup'],
                detail_type=['Recovery Point State Change'],
                detail={
                    'status': ['PARTIAL', 'EXPIRED'],
                },
            ),
            targets=[SnsTopic(self.alarm_topic)],
        )

    def _create_operational_security_rules(self) -> None:
        """Create EventBridge rules for operational security monitoring."""

        # Manual backup deletion monitoring
        Rule(
            self,
            'ManualBackupDeletionRule',
            event_pattern=EventPattern(
                source=['aws.backup'],
                detail_type=['Recovery Point State Change'],
                detail={
                    'status': ['DELETED'],
                    # Monitor for manual deletions which may indicate security issues
                },
            ),
            targets=[SnsTopic(self.alarm_topic)],
        )

        # Backup vault modifications
        Rule(
            self,
            'BackupVaultModificationRule',
            event_pattern=EventPattern(
                source=['aws.backup'],
                detail_type=['Backup Vault State Change'],
                detail={
                    'state': ['MODIFIED', 'DELETED'],
                },
            ),
            targets=[SnsTopic(self.alarm_topic)],
        )

        # Backup plan modifications/deletions
        Rule(
            self,
            'BackupPlanChangesRule',
            event_pattern=EventPattern(
                source=['aws.backup'],
                detail_type=['Backup Plan State Change'],
                detail={
                    'state': ['MODIFIED', 'DELETED'],
                },
            ),
            targets=[SnsTopic(self.alarm_topic)],
        )

    def _add_cdk_nag_suppressions(self) -> None:
        """Add CDK NAG suppressions for expected patterns in backup infrastructure."""

        # Add stack-level suppression for inline policies (same reasoning as main Stack class)
        NagSuppressions.add_stack_suppressions(
            self,
            [
                {
                    'id': 'HIPAA.Security-IAMNoInlinePolicy',
                    'reason': (
                        'CDK allows for granular permissions crafting that is attached to policies '
                        'directly to each resource, by virtue of its Resource.grant_* methods. '
                        'This approach results in an improvement in the principle of least privilege, '
                        'because each resource has permissions specifically crafted for that resource '
                        'and only allows exactly what it needs to do, rather than sharing more coarse managed policies.'
                    ),
                },
            ],
        )

        # Suppress AWS managed policy warnings for backup service roles
        # These are the standard AWS managed policies required for AWS Backup service functionality
        NagSuppressions.add_resource_suppressions(
            self.backup_service_role,
            [
                {
                    'id': 'AwsSolutions-IAM4',
                    'reason': (
                        'AWS Backup service requires these standard AWS managed policies for backup '
                        'and restore operations. These are the minimal required permissions for '
                        'backup service functionality.'
                    ),
                },
            ],
        )

        NagSuppressions.add_resource_suppressions(
            self.ssn_backup_service_role,
            [
                {
                    'id': 'AwsSolutions-IAM4',
                    'reason': (
                        'AWS Backup service requires these standard AWS managed policies for backup '
                        'and restore operations. SSN backup role uses the same base policies with '
                        'additional customer-managed security restrictions.'
                    ),
                },
            ],
        )
