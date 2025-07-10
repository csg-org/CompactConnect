# App Client Management for Staff Users

## Overview
This document is a guide for technical staff for managing Cognito app clients for machine-to-machine authentication in the Staff Users pool. All app clients must be documented in the external 'Compact Connect App Client Registry' Google Sheet (If you do not have access to said registry, contact a maintainer of the project and request access).

## Creating a New App Client

### 1. Prerequisites
Before creating a new app client, ensure you have:
- Jurisdiction requirements documented (compact and state)
- Contact information for the consuming team
- Approval to grant the app client with the requested scopes
- AWS credentials configured with permissions to create app clients for the Staff Users user pool in the needed AWS accounts
- Python 3.6+ installed with boto3 dependency (`pip install boto3`)

### 2. Update Registry
Add the new app client information to the external Google Sheet registry for tracking and disaster recovery purposes (ie a deployment error or AWS region outage causes app client data to be lost so it must be recreated).

#### **Scope Configuration**
   Scopes are the permissions that the app client will have. There are two tiers of scopes:

##### **Compact-Level Scopes:**
   These are the scopes that are scoped to a specific compact. Granting these scopes will allow the app client to perform actions across all jurisdictions within that compact.
   Generally, the only scope that should be granted at the compact level is the `{compact}/readGeneral` scope if needed.

   The following scopes are available at the compact level:
   ```
   {compact}/admin
   {compact}/readGeneral
   {compact}/readSSN
   {compact}/write
   ```

##### **Jurisdiction-Level Scopes:**
   These are the scopes that are scoped to a specific jurisdiction/compact combination. Granting these scopes will allow the app client to perform actions within a specific jurisdiction/compact combination. You should only grant these scopes if the consuming team has a specific need for a jurisdiction/compact combination.

   The following scopes are available at the jurisdiction level:
   ```
   {jurisdiction}/{compact}.admin
   {jurisdiction}/{compact}.write
   {jurisdiction}/{compact}.readPrivate
   {jurisdiction}/{compact}.readSSN
   ```

   Currently, the most common scope needed by app clients is the `{jurisdiction}/{compact}.write` scope. This scope allows the app client to upload license data for a jurisdiction/compact combination.

### 3. Create App Client Using Interactive Python Script
   **Use the provided Python script in the bin directory for streamlined app client creation:**

   ```bash
   python3 bin/create_app_client.py -e <environment> -u <user_pool_id>
   ```

   **Interactive Process:**
   The script will prompt you for:
   - App client name (e.g., "example-ky-app-client-v1")
   - Compact (aslp, octp, coun)
   - State postal abbreviation (e.g., "ky", "la")
   - Additional scopes (optional)

   **Automatic Scope Generation:**
   The script automatically creates these standard scopes:
   - `{compact}/readGeneral` - General read access for the compact
   - `{state}/{compact}.write` - Write access for the specific state/compact combination



### 4. **Send Credentials to Consuming Team**
   **When using the Python script (recommended):**
   The script will output comprehensive JSON with all necessary information for the consuming team:
   ```json
   {
     "clientId": "6g34example89j",
     "clientSecret": "1234example567890",
     "compact": "octp",
     "state": "la",
     "authUrl": "https://compact-connect-staff-beta.auth.us-east-1.amazoncognito.com/oauth2/token",
     "licenseUploadUrl": "https://api.beta.compactconnect.org/v1/compacts/octp/jurisdictions/la/licenses"
   }
   ```
   **Important:** These credentials should be securely transmitted to the consuming team via an encrypted channel (i.e., a one-time use link). The Python script output is ready to use directly with your one-time secret link generator. Once you have sent the credentials over to the IT staff, ensure you remove all remnants of the credentials from your device.


#### Email Instructions for consuming team
As part of the email message sent to the consuming team, be sure to include the onboarding instructions document from the `it_staff_onboarding_instructions/` directory.

## Rotating App Client Credentials
Unfortunately, AWS Cognito does not support rotating app client credentials for an existing app client. The only way to rotate credentials is to create a new app client with a new clientId and clientSecret and then delete the old one. The following process should be performed if credentials are accidentally exposed or in the event of a security breach where the old credentials are compromised.

### 1. Pre-rotation Tasks
- Contact consuming team to schedule rotation
- Follow "Creating a New App Client" steps above using either the Python script (recommended) or AWS CLI, you will increment clientName version suffix by 1 (e.g. "example-ky-app-client-v1" -> "example-ky-app-client-v2")
- Update the external Google Sheet registry with new client information

### 2. Migration
- Provide new client id and client secret to consuming team
- Consuming team will need to confirm that the new credentials are deployed in their systems, the old app client is not in use, and their systems are working as expected.

### 3. Cleanup
- Delete old app client from Cognito using the following cli command:
```
aws cognito-idp delete-user-pool-client --user-pool-id '<staff users's user pool id>' --client-id '<old client id>'
```
