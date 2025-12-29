# Staff User MFA Recovery Procedure

## Overview

When a staff user loses access to their Multi-Factor Authentication (MFA) device, they cannot log into the Compact Connect system. 

A staff user account consists of two parts: a Cognito user to track login information, and a DynamoDB record in the staff
users DynamoDB table to track permissions and other account data about the user.

Unfortunately, AWS Cognito does not provide a way to reset a user's MFA settings for recovery purposes. The Cognito user
account must be deleted and a new one created in order to set a new MFA device. Because the UUID of the DynamoDB record matches the id of the Cognito user, and we track the staff user id in several of our system events for auditing purposes (ie when a 
staff user deactivates or encumbers a privilege) when we recreate the Cognito user account, we must archive the old 
DynamoDB record so it may be referenced in the future if needed. 

This document provides step-by-step instructions to recover the user's access while preserving their historical record for audit and traceability purposes.

## Prerequisites

Before beginning this procedure, ensure you have:

1. **AWS Console Access**: Administrative access to the AWS account for the target environment (test, beta, or production)
2. **Cognito Access**: Permissions to manage users in the staff user pool
3. **DynamoDB Access**: Permissions to read and write items from the staff users table
4. **User Information**: You will need the user's email address to find their Cognito account

## Procedure

### Step 1: Retrieve the Current User Record

1. **Find the User in Cognito**
   - Navigate to AWS Console → Cognito → User Pools
   - Locate the staff user pool for your environment (prefixed with `StaffUsers`)
   - In the Cognito User Pool, search for the user by email address
   - Click on the user to view their details
   - Copy the `sub` (Subject) value - this is the user ID you'll need

2. **Retrieve the DynamoDB Record**
   - Navigate to the Staff Users table in the AWS Console → DynamoDB → Tables → `{environment}-PersistentStack-StaffUsers...`
   - Click on "Explore table items"
   - Search for an item where:
     - `pk` = `USER#{user_sub}` (where `user_sub` is the sub value from Cognito)
     - `sk` = `COMPACT#{compact}` (where `compact` is the user's compact, e.g., "aslp", "coun", "octp")
   - Click on the item to view its full contents

### Step 2: Archive the DynamoDB Record

Instead of deleting the record, we'll archive it by modifying the primary key to indicate it's archived:

1. **Create the Archived Record**
   - In the DynamoDB table, click "Create item"
   - Update the item pk with the following structure:
     - `pk` = `ARCHIVED_USER#{original_user_sub}`
     - **Add a new field**: `archivedDate` = current date (yyyy-mm-dd format)
     - **Add a new field**: `archivedReason` = "MFA recovery - user lost access to MFA device"
     - Click "Save" to create the archived record, this will delete the old record and create a new archived record
     - Verify the archived record was created successfully
     - Note the permissions of the archived user for when the user is re-invited into the system.

### Step 3: Delete the Cognito User Account

1. Navigate back to the user account in the staff Cognito User Pool
2. Deactivate the Cognito user
3. Delete the Cognito user

### Step 4: Staff user recreates user account
At this point, a staff admin with the needed permissions can recreate the staff user in CompactConnect using the UI. Notify management to 
create the account for the user as they did before with the appropriate permissions. The user should receive an email
with a new temporary password. When they log into the system and set their new password, they will also be prompted to
configure their new MFA using the authenticator app of their choice.

