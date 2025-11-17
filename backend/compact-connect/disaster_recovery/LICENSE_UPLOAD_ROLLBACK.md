# License Upload Rollback Guide

## Overview

The License Upload Rollback system allows AWS account administrators to automatically revert invalid or corrupted license data that was uploaded by a specific jurisdiction within a defined time window.

The system will automatically determine which providers had their license records modified as a result of uploads during the time window, and confirm which license updates can be safely rolled back. A provider is eligible for automatic rollback if only license upload-related changes happened since the window. If any other updates have occurred since the start of the time window, the provider will be skipped and manual review will be required to determine which action should be taken for that individual. The rollback process will generate a full JSON report showing which providers had their licenses rolled back and which were skipped and require manual review.

## Step-by-Step Execution Guide

### Prerequisites

Before starting the rollback:

1. ✅ **Verify the Problem**: Confirm which jurisdiction uploaded bad data for which compact(s)
2. ✅ **Disable automated access for Jurisdiction**: If jurisdiction has API credentials for automated uploads, disable those credentials to prevent further data changes until system has been recovered. To do this, determine which Cognito app client(s) the jurisdiction is using for the compact(s) and delete the appropriate app client(s) from the State Auth Cognito user pool.
3. ✅ **Determine Time Window**: Identify the exact start and end times (UTC) of the problematic uploads
4. ✅ **Stakeholder Notification**: Coordinate with relevant state administrators and other stakeholders

### Step 1: Gather Required Information

You'll need the following information for the execution:

| Parameter | Description | Example |
|-----------|-------------|---------|
| `compact` | The compact abbreviation (lowercase) | `"aslp"`, `"octp"`, `"counseling"` |
| `jurisdiction` | The state/jurisdiction code (lowercase) | `"oh"`, `"ky"`, `"ne"` |
| `startDateTime` | UTC timestamp when problematic uploads began | `"2020-01-15T08:00:00Z"` |
| `endDateTime` | UTC timestamp when problematic uploads ended | `"2020-01-15T17:59:59Z"` |
| `rollbackReason` | Description for audit trail | `"Invalid license data uploaded by OH staff"` |

**Important Notes:**
- All timestamps must be in UTC
- Time window cannot exceed 7 days (604,800 seconds)

### Step 2: Locate the Step Function

1. Navigate to the AWS Console → Step Functions
2. Find the Step Function with the name prefix: **`LicenseUploadRollbackLicenseUploadRollbackStateMachine`**

### Step 3: Execute the Step Function

1. Click **"Start Execution"**
2. Enter a descriptive execution name (this will be used for the S3 results folder):
   ```
   rollback-aslp-oh-2025-01-15
   ```
   
3. Paste the following JSON input (replace values with your specific parameters):

```json
{
  "compact": "aslp",
  "jurisdiction": "oh",
  "startDateTime": "2020-01-15T08:00:00Z",
  "endDateTime": "2020-01-15T17:59:59Z",
  "rollbackReason": "Invalid license data uploaded - incorrect expiration dates"
}
```

4. Click **"Start Execution"**

### Step 4: Monitor Execution Progress

The Step Function will process providers in batches. Monitor the step function execution until it completes and verify the execution was successful.

### Step 5: Review Results

Once the execution completes, comprehensive results are stored in S3. The S3 key is returned as output from the lambda step of the step function

#### Accessing the Results File

1. Navigate to S3 in the AWS Console
2. Find the bucket with `disasterrecoveryrollbackresults` in the name.
3. Navigate to the folder matching your execution name: `rollback-aslp-oh-2025-01-15/`
4. Download the file: `results.json`

#### Understanding the Results Structure

The results file contains three main sections:

##### 1. Reverted Provider Summaries

Providers that were successfully rolled back (example):

```json
{
  "revertedProviderSummaries": [
    {
      "providerId": "01234567-89ab-cdef-0123-456789abcdef",
      "licensesReverted": [
        {
          "jurisdiction": "oh",
          "licenseType": "audiologist",
          "revisionId": "98765432-10ab-cdef-0123-456789abcdef",
          "action": "REVERT"
        }
      ],
      "privilegesReverted": [
        {
          "jurisdiction": "ky",
          "licenseType": "audiologist",
          "revisionId": "11111111-2222-3333-4444-555555555555",
          "action": "REACTIVATED"
        }
      ],
      "updatesDeleted": [
        <sort keys of update records that were deleted>
      ]
    }
  ]
}
```

**Actions Explained:**
- `"REVERT"`: License data was restored to its pre-upload state
- `"DELETE"`: License was newly created during the upload and has been removed
- `"REACTIVATED"`: Privilege was deactivated due to the upload and has been reactivated

##### 2. Skipped Provider Details

Providers that require manual review (example):

```json
{
  "skippedProviderDetails": [
    {
      "providerId": "12345678-90ab-cdef-0123-456789abcdef",
      "reason": "Provider has updates that are either unrelated to license upload or occurred after rollback end time. Manual review required.",
      "ineligibleUpdates": [
        {
          "recordType": "licenseUpdate",
          "typeOfUpdate": "encumbrance",
          "updateTime": "2025-01-16T10:30:00Z",
          "licenseType": "audiologist",
          "reason": "License was updated with a change unrelated to license upload or the update occurred after rollback end time. Manual review required."
        }
      ]
    }
  ]
}
```

##### 3. Failed Provider Details

Providers that encountered errors:

```json
{
  "failedProviderDetails": [
    {
      "providerId": "23456789-01ab-cdef-0123-456789abcdef",
      "error": "Failed to rollback updates for provider. Manual review required: ConditionalCheckFailedException"
    }
  ]
}
```

These require technical investigation to determine the cause.

#### Options for Skipped or Failed Providers

For providers requiring manual review, you have three options:

1. **Do Nothing**: If the subsequent updates are valid, the provider's current state is correct
2. **Manual Database Edit**: For complex cases, coordinate with stakeholders to manually adjust records and document manual edits made.
3. **Re-upload Data**: Have the state re-upload correct data for these specific providers through the normal upload process (often the simplest option)

## Technical Details

### How the System Identifies Affected Providers

The system uses the `licenseUploadDateGSI` Global Secondary Index to efficiently query for all license records uploaded during the specified time window. This index is structured as:

- **Partition Key**: `C#{compact}#J#{jurisdiction}#D#{year-month}`
- **Sort Key**: `TIME#{epoch}#LT#{license_type}#PID#{provider_id}`

The system queries each month in the time range and collects unique provider IDs.

### Event Publishing

For each successfully reverted provider, the system publishes events to the EventBridge event bus:

- `license.reverted` events for each reverted license
- `privilege.reverted` events for each reactivated privilege

These events include:
- The rollback reason
- Time window information
- Revision IDs for tracking
