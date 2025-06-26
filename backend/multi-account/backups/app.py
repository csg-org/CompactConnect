#!/usr/bin/env python3
from aws_cdk import App, Environment
from stacks.backup_account_stack import BackupAccountStack


class BackupsApp(App):
    def __init__(self, *args, **kwargs):
        """
        An app for deploying data retention backup destination infrastructure in the backup account.

        This application creates the centralized backup infrastructure that receives and stores
        backup copies from CompactConnect environment accounts:
        - Cross-account backup vaults (general and SSN-specific)
        - Customer-managed KMS keys for backup encryption
        - Organization-level access policies for secure cross-account backup operations

        Environment account backup infrastructure (local vaults, IAM roles, backup plans)
        is managed by the CompactConnect application deployment.
        """
        super().__init__(*args, **kwargs)

        # Get account IDs from context (backup account deployment only)
        backup_account_id = self.node.get_context('backup_account_id')
        organization_id = self.node.get_context('organization_id')
        backup_region = self.node.get_context('backup_region')
        tags = self.node.get_context('tags')

        # Create backup account environment
        backup_env = Environment(account=backup_account_id, region=backup_region)

        # Deploy only the backup account stack (destination vaults and KMS keys)
        self.backup_account_stack = BackupAccountStack(
            self,
            'BackupAccountStack',
            env=backup_env,
            tags=tags,
            organization_id=organization_id,
            source_account_ids=self.node.get_context('source_account_ids'),
        )


if __name__ == '__main__':
    app = BackupsApp()
    app.synth()
