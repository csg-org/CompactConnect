# Staff User MFA Recovery Procedure

## Overview

When a staff user loses access to their Multi-Factor Authentication (MFA) device, they cannot log into the Compact Connect system. 

A staff user account consists of two parts: a Cognito user to track login information, and a DynamoDB record in the staff
users DynamoDB table to track permissions and other account data about the user.

Unfortunately, AWS Cognito does not provide a way to reset or recover a user’s MFA configuration. If a staff user loses access to their MFA device, the Cognito user account must be deleted and recreated in order to enroll a new MFA device. In CompactConnect, the DynamoDB staff-user record is keyed by the Cognito user ID (sub), and that identifier is referenced by system audit events (for example, when a staff user deactivates or encumbers a privilege). 

Recreating a Cognito user always generates a new sub. Reusing or mutating the existing DynamoDB staff-user record would retroactively change the meaning of historical audit events. To preserve audit integrity and traceability, the DynamoDB record with the original sub must therefore be archived, and a new staff-user record must be created for the newly recreated Cognito user. In the future, staff-user records should be decoupled from Cognito sub values (for example, by referencing email). Until that migration is completed and the process is automated, support staff must assist with deleting Cognito accounts and archiving staff-user records when a staff user loses access to their MFA device.

This document provides step-by-step instructions to recover the user's access while preserving their historical record for audit and traceability purposes.

## Prerequisites

Before beginning this procedure, ensure you have:

1. **AWS Console Access**: Administrative access to the AWS account for the target environment (test, beta, or production)
2. **User Information**: You will need the user's email address to find their Cognito account

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

In the DynamoDB console, if you change the partition key (pk) value of a existing DynamoDB item, it automatically deletes the old record with the old pk and creates a new one with the new pk, effectively archiving the user record. Perform the following steps:

1. **Create the Archived Record**
   - In the DynamoDB table, find the existing staff user record and select it to open the 'Edit item' view.
   - Update the item pk with the following structure:
     - `pk` = `ARCHIVED_USER#{staff user email}`
     - **Add a new field**: `archivedDate` = current date (yyyy-mm-dd format)
     - **Add a new field**: `archivedReason` = "MFA recovery - user lost access to MFA device"
     - A box should appear at the bottom that states the item will be deleted and recreated, click the box.
     - Click the 'Recreate item' button to create the archived record, this will delete the old record and create a new archived record
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
