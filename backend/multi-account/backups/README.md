# CompactConnect Data Retention Infrastructure

This CDK application deploys the backup destination infrastructure for CompactConnect's data retention feature. It creates secure, cross-account backup storage that receives backup copies from a specific CompactConnect environment account.

## Architecture Overview

This application creates the dedicated backup infrastructure for a single environment account:

### Environment-Specific Backup Account Infrastructure
Deployed to a dedicated backup account in `us-west-2` region for each environment (Test Secondary and Prod Secondary):
- **Cross-account backup vault**: Secure destination for backup copies from the specific environment account (`CompactConnectBackupVault`)
- **Dedicated SSN backup vault**: Separate vault (`CompactConnectBackupVault-SSN`) with enhanced access controls for SSN data
- **Customer-managed KMS keys**: Encryption keys for backup data with cross-account access policies
- **Dedicated SSN KMS key**: Separate encryption key for SSN backup data with restricted cross-account access
- **Environment-specific access policies**: Allow only the specific environment account to copy backups while maintaining security
- **Break-glass security policies**: DENY policies on SSN vault and KMS key requiring explicit modification for emergency access

### Environment Account Integration
Environment account backup infrastructure is managed by the CompactConnect application:
- CompactConnect deployments create local backup vaults and IAM service roles
- Backup plans include copy actions that replicate data to this secondary backup account
- Local KMS keys handle initial backup encryption
- Cross-account replication provides disaster recovery capability

## Prerequisites

1. AWS Organizations with backup and environment accounts configured
2. Dedicated backup account created and accessible
3. Python 3.12+ and AWS CDK CLI installed

## Configuration

Copy `cdk.context.example.json` to `cdk.context.json` and update the values:

```json
{
  "backup_account_id": "YOUR_ENVIRONMENT_BACKUP_ACCOUNT_ID",
  "organization_id": "YOUR_ORG_ID",
  "backup_region": "us-west-2",
  "source_account_ids": [
    "YOUR_ENVIRONMENT_ACCOUNT_ID"
  ],
  "source_regions": [
    "us-east-1"
  ],
  "backup_vault_name": "CompactConnectBackupVault",
  "ssn_backup_vault_name": "CompactConnectBackupVault-SSN",
  "tags": {
    "Project": "CompactConnect",
    "Environment": "DataRetention"
  }
}
```

## Deployment

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Bootstrap CDK in us-west-2 region** (if not already done. Make sure the AWS cli is logged into the appropriate backup account and set to us-west-2 region):
   ```bash
   cdk bootstrap
   ```

3. **Deploy to backup account** (Make sure the AWS cli is logged into the appropriate backup account and set to the us-west-2 region):
   ```bash
   cdk deploy BackupAccountStack
   ```

## Security Features

- **Cross-account isolation**: Backup account is separate from operational account
- **Environment-specific isolation**: Each environment has its own dedicated backup account
- **Regional separation**: Backups stored in different region (`us-west-2`) than primary operations (`us-east-1`)
- **Encryption**: All backup data encrypted with customer-managed KMS keys
- **Enhanced SSN Security**: Dedicated infrastructure for SSN data protection:
  - Separate backup vault exclusively for SSN table backups
  - Dedicated KMS key with restricted cross-account access for SSN encryption
  - **Break-glass access controls**: Both the SSN backup vault and KMS key use DENY policies that block all restore/decrypt operations except for AWS services, requiring explicit policy modification for emergency restoration
- **Environment-specific policies**: Access restricted to only the specific environment account within the AWS Organization
- **Least privilege**: Vault access policies follow principle of least privilege

## Integration with Environment Accounts

Once deployed, this infrastructure provides destination vaults for the specific environment account to:
1. Create its own local backup infrastructure via CompactConnect app deployment
2. Configure backup plans with copy actions that reference these cross-account vault ARNs
3. Automatically replicate backups to this environment-specific backup account for disaster recovery

The environment account will need the following ARNs from this deployment:
- General backup vault ARN: `arn:aws:backup:us-west-2:BACKUP_ACCOUNT:backup-vault:CompactConnectBackupVault`
- SSN backup vault ARN: `arn:aws:backup:us-west-2:BACKUP_ACCOUNT:backup-vault:CompactConnectBackupVault-SSN`
- General KMS key ARN: Output from `BackupEncryptionKeyArn`
- SSN KMS key ARN: Output from `SSNBackupEncryptionKeyArn`

## Testing

Run unit tests:
```bash
python -m pytest tests/
```

## Troubleshooting

### Cross-Account Access Issues
- Verify organization ID is correct in context configuration
- Check that source account ID matches the specific environment account
- Confirm backup account has proper resource policies
- Ensure environment account is using the correct destination vault ARNs

## Emergency SSN Data Restoration (Break-Glass Procedure)

The SSN backup infrastructure implements a "break-glass" security model. By default, **all restore operations for SSN backup data are blocked** by explicit DENY policies.

### When Emergency Restoration is Needed

During disaster recovery scenarios requiring SSN data restoration:

1. **Identify the required resources**:
   - SSN backup vault: `CompactConnectBackupVault-SSN`
   - SSN KMS key: `alias/compactconnect-ssn-backup-key`

2. **Modify the SSN backup vault policy**:
   - Remove or modify the `DenyEmergencyRestoreOperations` policy statement
   - Add temporary ALLOW statements for the specific restore operations needed
   - Include conditions to limit access to authorized principals and time windows

3. **Modify the SSN KMS key policy**:
   - Remove or modify the `DenySSNKeyDecryptOperations` policy statement
   - Add temporary ALLOW statements for decrypt operations needed for restoration
   - Include conditions to limit access to authorized principals

4. **Perform restoration operations** using the temporarily modified policies

5. **Restore original deny policies** immediately after restoration is complete

### Audit Trail

All policy modifications are logged in CloudTrail, providing a complete audit trail of:
- Who modified the policies
- When the modifications were made
- What specific changes were made
- When the original security posture was restored

This approach ensures that emergency access is:
- **Explicit**: Requires deliberate policy modification
- **Auditable**: All changes are logged in CloudTrail
- **Temporary**: Policies should be restored after use
- **Controlled**: Only principals with policy modification permissions can enable access

## Related Documentation

- [AWS Backup Cross-Account Documentation](https://docs.aws.amazon.com/aws-backup/latest/devguide/cross-account-backup.html)
- [CompactConnect Data Retention Implementation Plan](../../../working-resources/246-data-retention.md)
