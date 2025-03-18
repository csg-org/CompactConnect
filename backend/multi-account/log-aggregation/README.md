# Log Aggregation Infrastructure

This CDK project automates the setup of log aggregation infrastructure for the CompactConnect multi-account
architecture. It includes a CloudTrail Organizational trail that logs DynamoDB data read events for tables with the
`-DataEventsLog` suffix. That trail, however, due to the sensitive nature of the data being logged, is not normally
readable by anyone. It is intended to be used for 'in case of emergency' forensics or for future audits, with
future enhancements to faciliate safe reading, if necesary.

## Architecture

The infrastructure is split across two AWS accounts:

1. **Logs Account**: Contains S3 buckets for storing CloudTrail logs
2. **Management Account**: Contains the CloudTrail organization trail and KMS key for encryption

## Prerequisites

- AWS CLI configured with appropriate credentials
- Python 3.8 or higher
- AWS CDK v2 installed
- Access to both the Management and Logs accounts via IAM Identity Center

## Setup

1. Copy `cdk.context.example.json` to `cdk.context.json`
2. Update the account IDs and other configuration in `cdk.context.json`. All fields are required.

## Deployment

The deployment is a multi-step process due to the cross-account nature of the resources:

### Step 1: Deploy the Logs Account Resources

1. Configure your AWS CLI to use the Logs account credentials
2. Deploy the Logs Account stage:
   ```bash
   cdk deploy 'LogsAccountStage/*'
   ```

### Step 2: Deploy the Management Account Resources

1. Configure your AWS CLI to use the Management account credentials:
2. Deploy the Management Account stage:
   ```bash
   cdk deploy 'ManagementAccountStage/*'
   ```

The application automatically uses the bucket name and ARN based on the context values provided in `cdk.context.json`.

## Verification

After deployment, you can verify the setup by:

1. Creating a DynamoDB table with the `-DataEventsLog` suffix in any account within the organization (like as deployed
   in the CompactConnect app).
2. Performing read operations on the table (like revealing the full SSN for a provider in the Test environment).
3. Checking the CloudTrail logs in the S3 bucket in the Logs account to confirm the events are being recorded. Note
   that, as deployed, no AWS principals other than CloudTrail can decrypt these events, due to the policy on the KMS
   key used to encrypt them. In order to read these events from S3, you would have to modify the KMS key policy from
   the Management account, to allow it. After initial validation, this should probably not be done unless you _really_
   know what you're doing, especially after any real data is uploaded to Production.

## Cleanup

To remove the resources:

1. Delete the Management Account resources first:
   ```bash
   cdk destroy 'ManagementAccountStage/*'
   ```

2. Then delete the Logs Account resources:
   ```bash
   cdk destroy 'LogsAccountStage/*'
   ```

Note: The S3 buckets and KMS key have a `RemovalPolicy.RETAIN` setting, so they will not be automatically deleted.
You'll need to manually empty and delete them if desired.
