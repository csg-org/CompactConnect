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

The DR system uses a two-step approach for each table:

1. **RestoreDynamoDbTable Step Function** (Parent)
   - Creates a backup of the current table for forensic analysis
   - Restores a temporary table from the specified PITR timestamp
   - Invokes the SyncTableData Step Function

2. **SyncTableData Step Function** (Child)
   - **Delete Phase**: Removes all records from the destination table
   - **Copy Phase**: Copies all records from the restored table to the destination table

### Per-Table Isolation

Each DynamoDB table has its own dedicated pair of Step Functions:

- `DRRestoreDynamoDbTable{TableName}StateMachine`
- `{TableName}DRSyncTableDataStateMachine`

This design allows for:
- **Targeted Recovery**: Restore only the affected table(s)
- **Granular Permissions**: Each Step Function has minimal, table-specific permissions

## Supported Tables

The following tables are configured for disaster recovery:

| Table Name | Step Function Prefix | Purpose                                 |
|------------|---------------------|-----------------------------------------|
| TransactionHistoryTable | `TransactionHistoryTable` | transaction data from authorize.net     |
| ProviderTable | `ProviderTable` | Provider information and GSIs           |
| CompactConfigurationTable | `CompactConfigurationTable` | System configuration data               |
| DataEventTable | `DataEventTable` | License data events                     |
| UsersTable | `UsersTable` | Staff user permissions and account data |

> **Note**: The SSN table is excluded due to additional security requirements and will be handled in a future implementation.

## Execution Process

### Step-by-Step Flow

1. **Input Validation**
   - Validates required parameters (incident ID, PITR timestamp, table confirmation)
   - Generates unique restored table name using incident ID

2. **Parallel Operations** (Phase 1)
   - **Backup Branch**: Creates an on-demand backup of the current table
   - **Restore Branch**: Initiates PITR restore to a temporary table
   - Both operations poll for completion with exponential backoff

3. **Data Synchronization** (Phase 2)
   - **Delete Phase**: Scans and deletes all records from the destination table
   - **Copy Phase**: Scans and copies all records from the restored table
   - Both phases use pagination to handle large datasets

4. **Cleanup**
   - Temporary restored table is automatically cleaned up
   - Execution logs are retained for audit purposes

## Required Input Parameters

### Primary Parameters

```json
{
  "incidentId": "string",
  "pitrBackupTime": "ISO 8601 datetime string",
  "tableNameRecoveryConfirmation": "string"
}
```

#### Parameter Details

- **`incidentId`** (required)
  - Purpose: Unique identifier for tracking this recovery operation
  - Format: String (alphanumeric, hyphens allowed)
  - Example: `"incident-2025-001"`, `"corruption-fix-20250115"`
  - Used in: Backup names, restored table names, execution tracking

- **`pitrBackupTime`** (required)
  - Purpose: The timestamp to restore the table to
  - Format: ISO 8601 datetime string
  - Example: `"2030-01-15T12:39:46+00:00"`
  - Constraints: Must be within the PITR retention window (35 days)

- **`tableNameRecoveryConfirmation`** (required)
  - Purpose: Security guard rail to prevent accidental execution
  - Format: Exact table name being recovered (you can copy this from the DynamoDB console)
  - Example: `"Prod-PersistentStack-DataEventTable00A96798-C6VX9JVDOYGN"`
  - Validation: Must match the actual destination table name

## Example Execution

### Example: Transaction History Recovery

```json
{
  "incidentId": "transaction-corruption-20250115",
  "pitrBackupTime": "2025-01-15T09:00:00+00:00",
  "tableNameRecoveryConfirmation": "Prod-PersistentStack-TransactionHistoryTable00A96798-C6VX9JVDOYGN"
}
```
## Complete Disaster Recovery Workflow

### Step 1: Start Recovery Mode

Before executing the DR Step Function, you must throttle all Lambda functions to prevent other data operations from occurring while attempting to roll any databases back. There is a script provided to perform this action:

```bash
# Navigate to the disaster_recovery directory
cd backend/compact-connect/disaster_recovery

# Start recovery mode for the environment
python start_recovery_mode.py --environment Prod
```

This will put the system into recovery mode by:
- Setting reserved concurrency to 0 for all environment Lambda functions, so they can't be invoked
- Leaving Disaster Recovery functions operational

### Step 2: Execute Disaster Recovery Step Function For Specific Tables

#### AWS Console Method

1. Navigate to Step Functions in the AWS Console
2. Find the appropriate Step Function for the table you need to recover (e.g., `DRRestoreDynamoDbTableTransactionHistoryTableStateMachine`)
3. Click "Start Execution"
4. Enter the JSON payload in the input field
5. Click "Start Execution" and wait for completion

### Step 3: End Recovery Mode

After the DR Step Function completes successfully for each table you need to restore, end the recovery mode to restore
normal operations:

```bash
# End recovery mode for the environment
python end_recovery_mode.py --environment Prod
```

This will:
- Remove reserved concurrency throttling from all Lambda functions
- Restore normal application operations
- Complete the disaster recovery process

## Pre-Execution Checklist

1. ✅ **Verify Impact**: Confirm which applications/users will be affected
2. ✅ **Communication**: Notify stakeholders of the planned recovery
3. ✅ **Backup Verification**: Ensure current backups are available
4. ✅ **Timestamp Validation**: Verify the PITR timestamp is correct
5. ✅ **Access Verification**: Confirm you have necessary permissions

### During Execution

1. **Monitor Progress**: Watch Step Function execution in real-time
2. **Check Logs**: Monitor CloudWatch logs for any warnings
3. **Validate Data**: Spot-check data integrity during copy phase
4. **Communicate Status**: Keep stakeholders informed of progress

### Post-Execution

1. **Verify Recovery**: Confirm data integrity and completeness
2. **Application Testing**: Test critical application functions
3. **Documentation**: Update incident documentation with recovery details
4. **Cleanup Review**: Verify temporary resources were cleaned up after forensic analysis.

### Operational Constraints

- **Downtime**: Applications using the table will be unavailable during restoration
- **Data Loss**: All data newer than the PITR timestamp will be permanently lost. The backup snapshot may be restored post-recovery to determine which records can potentially be recovered.
- **Dependencies**: Related tables may need coordinated restoration for consistency


## Monitoring and Troubleshooting
### Common Issues and Solutions

#### Invalid table name
- **Cause**: `tableNameRecoveryConfirmation` doesn't match actual table name
- **Solution**: Verify exact table name spelling and case

#### Restore timestamp out of range
- **Cause**: PITR timestamp is outside the 35-day retention window
- **Solution**: Choose a more recent timestamp within the retention period
