# App Client Management for Staff Users

## Overview
This document is a guide for technical staff for managing Cognito app clients for machine-to-machine authentication in the Staff Users pool. All app clients must be documented in yaml files in the `/app_clients` directory for disaster recovery purposes (ie a deployment error or AWS region outage causes app client data to be lost so it must be recreated). See the example app client for the format.

## Creating a New App Client

### 1. Documentation Prerequisites
Before creating a new app client, ensure you have:
- Jurisdiction requirements documented
- Contact information for the consuming team
- Approval to grant the app client with the requested scopes
- AWS CLI permissions to create app clients for the Staff Users user pool in the needed AWS accounts

### 2. Update Registry
Add a new app client yaml file to `/app_clients` following the schema of the example app client.

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

### 3. Create App Client in AWS Using CLI
   To create an app client with the needed OAuth scopes configured, you will use the AWS CLI. After logging into the correct AWS account for the us-east-1 region, run the following cli command (for the OAuth scopes, you will put whatever scopes are documented in the yaml file, the following is an example of the format used to define the scopes):
   ```
   aws cognito-idp create-user-pool-client --user-pool-id '<staff users's user pool id>' \
   --client-name '<name of client you set in the yaml file, it should include a version suffix for rotation, e.g. "example-ky-app-client-v1">'\
   --prevent-user-existence-errors ENABLED \
   --generate-secret \
   --token-validity-units AccessToken='minutes'\
   --access-token-validity 15 \
   --allowed-o-auth-flows-user-pool-client \
   --allowed-o-auth-flows 'client_credentials' \
   --allowed-o-auth-scopes '<compact>/readGeneral' '<jurisdiction>/<compact>.write'
   ```

   This command creates an app client with the ability to generate access tokens that expire after 15 minutes. This expiration time can be adjusted according to the needs of the consuming team up to 1 day (see [AccessTokenValidity](https://docs.aws.amazon.com/cognito-user-identity-pools/latest/APIReference/API_CreateUserPoolClient.html#CognitoUserPools-CreateUserPoolClient-request-AccessTokenValidity)), though it is strongly recommended to keep this value as short as possible to limit the amount of time an access token is valid for if it is compromised. The consuming team will need to implement logic to generate new access tokens before previous tokens expire.

   If the consuming team plans to use both the beta and production environments, you will need to create two separate app clients- one in each respective AWS account.

   The cognito token URL for the beta environment is `https://compact-connect-staff-beta.auth.us-east-1.amazoncognito.com/oauth2/token` 
   The cognito token URL for the prod environment is `https://compact-connect-staff.auth.us-east-1.amazoncognito.com/oauth2/token`


### 4. **Send Credentials to Consuming Team**
   - The client_id and client_secret will be needed by the consuming team to authenticate with the API. This information is returned in the response of the cli command.
   ```
   {
   "UserPoolClient": {
        "ClientId": "6g34example89j",
        "ClientSecret": "1234example567890",
        ...
        }
   }
   ```

These credentials should be securely transmitted to the consuming team via an encrypted channel (i.e., a one-time use link) in the following format:
   ```json
   {
   "clientId": "<client id>",
   "clientSecret": "<client secret>"
   }
   ```


#### Email Instructions for consuming team
As part of the email message sent to the consuming team, be sure to attach the onboarding instructions document ("Compact Connect Automated License Upload Instructions.txt").

## Rotating App Client Credentials
Unfortunately, AWS Cognito does not support rotating app client credentials for an existing app client. The only way to rotate credentials is to create a new app client with a new clientId and clientSecret and then delete the old one. The following process should be performed if credentials are accidentally exposed or in the event of a security breach where the old credentials are compromised.

### 1. Pre-rotation Tasks
- Contact consuming team to schedule rotation
- Follow "Creating a New App Client" steps above, you will increment clientName version suffix by 1 (e.g. "example-ky-app-client-v1" -> "example-ky-app-client-v2")
- Update yaml file with new clientId, clientName, and createdDate

### 2. Migration
- Provide new client id and client secret to consuming team
- Consuming team will need to confirm that the new credentials are deployed in their systems, the old app client is not in use, and their systems are working as expected.

### 3. Cleanup
- Delete old app client from Cognito using the following cli command:
```
aws cognito-idp delete-user-pool-client --user-pool-id '<staff users's user pool id>' --client-id '<old client id>'
```
