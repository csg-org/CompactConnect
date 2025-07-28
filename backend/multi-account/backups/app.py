#!/usr/bin/env python3
from aws_cdk import App, Environment
from stacks.backup_account_stack import BackupAccountStack


class BackupsApp(App):
    def __init__(self, *args, **kwargs):
        """
        An app for deploying data retention backup destination infrastructure in the backup account.

        This application creates the environment-specific backup infrastructure that receives and stores
        backup copies from a specific CompactConnect environment account:
        - Cross-account backup vaults (general and SSN-specific)
        - Customer-managed KMS keys for backup encryption
        - Environment-specific access policies for secure cross-account backup operations

        Environment account backup infrastructure (local vaults, IAM roles, backup plans)
        is managed by the CompactConnect application deployment.
        """
        super().__init__(*args, **kwargs)

        # Get account IDs from context (backup account deployment only)
        required_context = [
            'backup_account_id',
            'organization_id',
            'backup_region',
            'source_account_ids',
            'source_regions',
            'tags',
        ]
        missing_context = [key for key in required_context if self.node.get_context(key) is None]
        if missing_context:
            raise ValueError(f'Missing required context parameters: {", ".join(missing_context)}')

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
            source_regions=self.node.get_context('source_regions'),
        )


if __name__ == '__main__':
    app = BackupsApp()
    app.synth()
