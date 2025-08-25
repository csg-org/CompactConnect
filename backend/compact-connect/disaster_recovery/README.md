# DynamoDB Disaster Recovery System

## Overview

The Disaster Recovery (DR) system provides automated recovery capabilities for critical DynamoDB tables in the CompactConnect system. This system allows administrators to perform Point-in-Time Recovery (PITR) operations when tables become corrupted or require rollback to a previous state.

**⚠️ WARNING: This system performs a HARD RESET of the target table, permanently deleting all current data before restoring from the specified timestamp.**

## When to Use

This Disaster Recovery process should only be run in the event that the system experiences an event that causes
system-wide failures, such as the following scenarios:

1. **Data Corruption**: When a table contains corrupted or invalid data that cannot be fixed through normal operations
2. **Accidental Data Loss**: When critical data has been accidentally deleted or modified
3. **Failed Deployments**: When a deployment has caused data integrity issues
4. **Security Incidents**: When unauthorized modifications require rolling back to a clean state
5. **System-wide Issues**: When multiple tables need to be restored to a consistent point in time

## Architecture

### Two-Phase Recovery Process
DynamoDB PITR cannot directly restore data into your production database. Instead, it creates a new table with data matching the exact values you had in your production database at the specified timestamp. You as the owner of the database must decide what to do with that data from that point in time. For the purposes of disaster recovery rollback, we have determined to get the data into the production table by performing a 'hard reset', meaning **all the current data in the production table is deleted**, then we copy over the data from the temporary table into the production table. This process includes the following step functions.

1. **RestoreDynamoDbTable Step Function** (Parent)
   - Creates a backup of the current table for post-incident analysis
   - Restores a temporary table from the specified PITR timestamp
   - Invokes the SyncTableData Step Function

2. **SyncTableData Step Function** (Child)
   - **Delete Phase**: Removes all records from the production table
   - **Copy Phase**: Copies all records from the temporary table to the production table

Once this process is complete, the data in the target table will be restored with the data from the specified point in time.

### Per-Table Isolation

Each DynamoDB table has its own dedicated pair of Step Functions:

- `DRRestoreDynamoDbTable{TableName}StateMachine`
- `{TableName}DRSyncTableDataStateMachine`

This design allows for:
- **Targeted Recovery**: Restore only the affected table(s)
- **Granular Permissions**: Each Step Function has minimal, table-specific permissions

## Supported Tables

The following tables are configured for disaster recovery:

| Table Name | Step Function Prefix | Purpose | Recovery Notes |
|------------|---------------------|---------|----------------|
| TransactionHistoryTable | `TransactionHistoryTable` | transaction data from authorize.net | Can be rolled back independently. After DR rollback, run the Transaction History Processing Workflow Step Function for each compact for every day where data was lost to restore all transaction data from Authorize.net accounts. The Transaction History Processing Workflow step functions are idempotent. They can be run multiple times without producing duplicate transaction items in the table. |
| ProviderTable | `ProviderTable` | Provider information and GSIs | **Dependent on SSN table** - Can be rolled back without updating SSN table since SSN table does not have a dependency on the provider table. **⚠️ WARNING**: If SSN table needs rollback, the provider table will likely need to be restored to same point in time as SSN table. Otherwise new provider IDs may be generated for existing SSNs causing data inconsistency/orphaned providers that won't receive license updates. After DR rollback, consider that the transaction history table will have a list of all privileges purchased as recorded in Authorize.net, and can be used as a data source for repopulating any privilege records that may have been lost as a result of the rollback.|
| CompactConfigurationTable | `CompactConfigurationTable` | System configuration data | Can be rolled back independently of other tables. Contains configuration set by compact and state admins. Admins may need to reset configurations that were lost as a result of the rollback. |
| DataEventTable | `DataEventTable` | License data events | Used for downstream processing events  triggered by Event Bridge event bus. In the event of recovery, many of these events can likely be restored by replaying events placed on the event bus. See https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-archive.html |
| UsersTable | `UsersTable` | Staff user permissions and account data | Can be rolled back independently. Contains staff user permissions and account information. Admins may need to re-invite new users or reset permissions that were lost as a result of the rollback. |

> **Note**: The SSN table is excluded due to additional security requirements and will be handled in a future implementation.

## Running the Disaster Recovery Workflow

## Pre-Execution Checklist

1. ✅ **Verify Impact**: Confirm which applications/users will be affected
2. ✅ **Communication**: Notify stakeholders of the planned recovery
3. ✅ **Timestamp Selection**: Determine the UTC timestamp to restore to (must be within 35 days)
4. ✅ **Access Verification**: Confirm you have necessary permissions (Currently only AWS account admins can trigger a DR)

### Step 1: Start Recovery Mode

Before executing the DR Step Function, you must throttle all Lambda functions to prevent other data operations from occurring while attempting to roll any databases back. There is a script provided to perform this action:

```bash
# Navigate to the disaster_recovery directory
cd backend/compact-connect/disaster_recovery

# Start recovery mode for the environment (replace "Prod" with your target environment)
python start_recovery_mode.py --environment Prod
```

This will put the system into recovery mode by:
- Setting reserved concurrency to 0 for all environment Lambda functions, so they can't be invoked
- Leaving Disaster Recovery functions operational
- **Important**: If any functions failed to throttle, you may rerun the script or manually check their reserved concurrency settings if needed. The script is idempotent and can be run multiple times.

### Step 2: Execute Disaster Recovery Step Function For Specific Tables
#### Prerequisites
- Identify the exact table name from the DynamoDB console (needed for `tableNameRecoveryConfirmation`)
- Verify the PITR timestamp is correct
- Create a unique incident ID for tracking (see [Execution Request Parameter Details](#execution-request-parameter-details))

When you are ready to perform a rollback, find the step function for the specific table you need to rollback (`DRRestoreDynamoDbTable{TableName}StateMachine`) and start an execution with the following input (replace placeholders with your values)

```json
{
  "incidentId": "<YOUR INCIDENT ID HERE>",
  "pitrBackupTime": "<ISO 8601 UTC datetime string>",
  "tableNameRecoveryConfirmation": "<TABLE NAME YOU ARE TRYING TO RECOVER>"
}
```

#### Execution Request Parameter Details

- **`incidentId`** (required)
  - Purpose: Unique identifier for tracking this recovery operation
  - Format: String (80 chars or less, allows alphanumeric and hyphens)
  - Example: `"incident-2025-001"`, `"corruption-fix-20250115"`
  - Used in: Backup names, restored table names, execution tracking

- **`pitrBackupTime`** (required)
  - Purpose: The timestamp to restore the table to
  - Format: ISO 8601 UTC datetime string
  - Example: `"2030-01-15T12:39:46+00:00"`
  - Constraints: Must be within the PITR retention window (35 days)

- **`tableNameRecoveryConfirmation`** (required)
  - Purpose: Security guard rail to prevent accidental execution
  - Format: Exact table name being recovered (you can copy this from the DynamoDB console)
  - Example: `"Prod-PersistentStack-DataEventTable00A96798-C6VX9JVDOYGN"`
  - Validation: Must match the actual destination table name

example:
```json
{
  "incidentId": "transaction-corruption-20250115",
  "pitrBackupTime": "2025-01-15T09:00:00+00:00",
  "tableNameRecoveryConfirmation": "Prod-PersistentStack-TransactionHistoryTable00A96798-C6VX9JVDOYGN"
}
```

#### Running Step Functions from AWS Console

1. Navigate to Step Functions in the AWS Console
2. Find the appropriate Step Function(s) for the table(s) you need to recover (e.g., `DRRestoreDynamoDbTableTransactionHistoryTableStateMachine`)
3. For each step function you need to run, Click "Start Execution"
4. Enter the JSON payload in the input field
5. Click "Start Execution" and wait for completion (multiple Step functions can be run concurrently if you are restoring multiple tables)

### Step 3: End Recovery Mode

**⚠️CRITICAL**: Only proceed after ALL recovery Step Functions you have run have completed successfully.

After the DR Step Function completes successfully for each table you need to restore, end the recovery mode to restore normal operations:

```bash
# End recovery mode for the environment
python end_recovery_mode.py --environment Prod
```

This will:
- Remove reserved concurrency throttling from all Lambda functions
- Restore normal application operations
- Complete the disaster recovery process
- **Important**: If any functions failed to unthrottle, you may rerun the script or manually check their reserved concurrency settings if needed. The script is idempotent and can be run multiple times.

### Post-Execution

1. **Verify Recovery**: Confirm data integrity and completeness
2. **Application Testing**: Test critical application functions
3. **Documentation**: Update incident documentation with recovery details
4. **Cleanup Review**: Cleanup temporary resources after post-incident analysis.

### Operational Constraints

- **Data Loss**: All data newer than the PITR timestamp will be permanently lost. The backup snapshot may be restored post-recovery to determine which records can potentially be recovered.
- **Dependencies**: Related tables may need coordinated restoration for consistency.

## Monitoring and Troubleshooting
### Common Issues and Solutions

#### Invalid table name
- **Cause**: `tableNameRecoveryConfirmation` doesn't match actual table name (this parameter is used to prevent accidental recovery on a database)
- **Solution**: Copy exact table name from DynamoDB console

#### Restore timestamp out of range
- **Cause**: PITR timestamp is outside the 35-day retention window
- **Solution**: Choose a more recent timestamp within the retention period

## Complete Table Deletion Recovery (Manual Backup Restoration)

**⚠️ CRITICAL**: This section applies ONLY when a DynamoDB table has been completely deleted and PITR is not available. This requires manual intervention and cannot use the automated Step Functions.

### Recovery Steps
Depending on how the table was deleted, there may be a latest 'snapshot' backup in the DynamoDB console that you can recover from. If that snapshot is not available, the system performs daily backups of our tables and store them in the AWS Backup service that you can recover from.

#### Step 1: Locate the Latest Backup

##### Option A: DynamoDB Console
1. Navigate to DynamoDB Console → Backups
2. Find the most recent backup for the deleted table
3. Note the backup name and creation time

##### Option B: AWS Backup Console
1. Navigate to AWS Backup Console → Backup Vaults
2. Find the most recent recovery point for the deleted table
3. **CRITICAL**: Note the "Original table name" from the recovery point details

#### Step 2: Restore Table from Backup

1. **From DynamoDB Console**:
   - Go to DynamoDB → Backups
   - Select the backup → "Restore"
   - **CRITICAL Configuration**:
     - **Table Name**: Must match EXACTLY the original deleted table name
     - **Encryption**: Select "Customer managed key"
     - **KMS Key**: Choose `<environment>-PersistentStack-shared-encryption-key` for non-ssn tables, `ssn-key` for the SSN table
       - Example: `Prod-PersistentStack-shared-encryption-key`
     - **Global Secondary Indexes (GSIs)**: Ensure ALL original GSIs are included in the restore by selecting 'Restore the entire table'
     - Select 'Restore'

2. **From AWS Backup Console**:
   - Navigate to Recovery Points → Select the backup
   - Click "Restore"
   - **CRITICAL Configuration**:
     - **New Table Name**: Use the EXACT "Original table name" from the recovery point
     - **Encryption**: Choose an AWS KMS key -> `<environment>-PersistentStack-shared-encryption-key` for non-ssn tables, `ssn-key` for the SSN table
     - **GSIs**: Verify all original GSIs are restored
     - Select 'Restore Backup'

#### Step 3: Verify Restoration

1. **Table Configuration**:
   - ✅ Table name matches exactly (including environment prefix and suffix)
   - ✅ All Global Secondary Indexes are present
   - ✅ Encryption is set to the correct KMS key
   - ✅ Table status is "ACTIVE"

2. **Data Verification**:
   - Spot-check critical records
   - Verify record counts are reasonable
   - Verify application functionality with the restored table
