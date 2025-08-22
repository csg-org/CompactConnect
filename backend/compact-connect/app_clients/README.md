# App Client Management for Staff Users

## Overview

This document is a guide for technical staff for managing Cognito app clients for machine-to-machine authentication in
the State API. All app clients must be documented in the external 'Compact Connect App Client Registry' Google Sheet
(If you do not have access to said registry, contact a maintainer of the project and request access).

## Creating a New App Client

### 1. Prerequisites

Before creating a new app client, ensure you have:
- Jurisdiction requirements documented (compact and state)
- Contact information for the consuming team
- Approval to grant the app client with the requested scopes
- AWS credentials configured with permissions to create app clients for the State Auth user pool in the needed AWS
  accounts
- Python 3.10+ installed with boto3 dependency (`pip install boto3`)

### 2. Update Registry

Add the new app client information to the external Google Sheet registry for tracking and disaster recovery purposes
(ie a deployment error or AWS region outage causes app client data to be lost so it must be recreated).

#### **Scope Configuration**

Scopes are the permissions that the app client will have. There are two tiers of scopes:

##### **Compact-Level Scopes:**

These are the scopes that are scoped to a specific compact. Granting these scopes will allow the app client to perform
actions across all jurisdictions within that compact.  Generally, the only scope that should be granted at the compact
level is the `{compact}/readGeneral` scope if needed.

The following scopes are available at the compact level:
```
{compact}/admin
{compact}/readGeneral
{compact}/readSSN
{compact}/write
```

##### **Jurisdiction-Level Scopes:**

These are the scopes that are scoped to a specific jurisdiction/compact combination. Granting these scopes will allow
the app client to perform actions within a specific jurisdiction/compact combination. You should only grant these
scopes if the consuming team has a specific need for a jurisdiction/compact combination.

The following scopes are available at the jurisdiction level:
```
{jurisdiction}/{compact}.admin
{jurisdiction}/{compact}.write
{jurisdiction}/{compact}.readPrivate
{jurisdiction}/{compact}.readSSN
```

Currently, the most common scope needed by app clients is the `{jurisdiction}/{compact}.write` scope. This scope
allows the app client to upload license data for a jurisdiction/compact combination.

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
The script will output two separate sections:

**A. Credentials JSON (for one-time link service):**
```json
{
   "clientId": "6g34example89j",
   "clientSecret": "1234example567890"
}
```
**Important:** These credentials should be securely transmitted to the consuming team via an encrypted channel
(i.e., a one-time use link). Copy this JSON and use it with your one-time secret link generator. Once you have sent
the credentials over to the IT staff, ensure you remove all remnants of the credentials from your device.

**B. Email Template:**
The script will also generate an email template with contextual information (compact name, state, auth URL, license
upload URL) that you can copy/paste into your email client. This template includes a placeholder for the one-time
link that you'll generate separately.


#### Email Instructions for consuming team

As part of the email message sent to the consuming team, be sure to include the onboarding instructions document from
the `it_staff_onboarding_instructions/` directory.

## Managing HMAC Public Keys

### Overview

HMAC authentication provides an additional layer of security for API access to sensitive licensure data. Each
compact/state combination can have multiple HMAC public keys configured to support key rotation and zero-downtime
deployments.

### Authorization Requirements

**⚠️ CRITICAL SECURITY NOTICE:** Due to the sensitivity of the data protected by HMAC authentication (including
partial Social Security Numbers, personal addresses, and professional license details), configuration of new HMAC
public keys in production environments **MUST** include explicit authorization from the state board executive director.

### Creating HMAC Public Keys

Once a state configures a public key, they will be able to access the HMAC-required API endpoints. API endpoints with
_optional_ HMAC support will also begin to enforce HMAC signatures for that combination of compact and state. **This
means that, once a compact/state has a public key configured, they will be denied access to HMAC-Optional endpoints,
such as the `POST license` endpoint, unless they have also implemented HMAC signatures there as well.** Be sure that
the representative is advised that they should begin signing those requests _before_ CompactConnect has a configured
public key.

#### 1. Prerequisites

Before creating a new HMAC public key, ensure you have:
- **Production Authorization**: Explicit approval from the state board executive director for production environments
- Validated the identity of the individual providing the public key to you
- Jurisdiction and compact information confirmed
- Contact information for the state IT representative
- The public key file (`.pub` format) from the state IT representative
- AWS credentials configured with permissions to write to the compact configuration table
- Python 3.10+ installed with boto3 dependency (`pip install boto3`)

#### 2. Key ID Naming Convention

The state IT department should provide you with an identifier, however you can recommend a descriptive key IDs that
includes:
- Environment indicator (if applicable)
- Version or date suffix

Examples:
- `prod-key-001`
- `beta-key-2024-01`

#### 3. Create HMAC Public Key Using Interactive Python Script

**Use the provided Python script in the bin directory for streamlined HMAC key management:**

```bash
python3 bin/manage_hmac_keys.py create -t <table_name>
```

**Interactive Process:**
The script will prompt you for:
- Compact (aslp, octp, coun)
- State postal abbreviation (e.g., "ky", "la")
- Key ID (e.g., "client-org-prod-key-001")

**File Reading:**
The script will:
- Notify you that it will read the public key from `<key-id>.pub`
- Validate the PEM format of the public key
- Check for existing keys with the same ID
- Write the key to the compact configuration database

#### 4. Database Schema

HMAC keys are stored in the compact configuration table with the following schema:
- **Primary Key (pk)**: `{compact}#HMAC_KEYS`
- **Sort Key (sk)**: `{compact}#JURISDICTION#{jurisdiction}#{key_id}`
- **Additional Fields**:
  - `publicKey`: PEM-encoded public key content
  - `compact`: Compact abbreviation
  - `jurisdiction`: Jurisdiction abbreviation
  - `keyId`: Key identifier
  - `createdAt`: Creation timestamp

### Deleting HMAC Public Keys

#### 1. Prerequisites

Before deleting an HMAC public key, ensure you have:
- Confirmation that the key is no longer in use by the state IT department
- Confirmation of the key id to be deleted
- Understanding of the impact on API access for the compact/state combination

#### 2. Delete HMAC Public Key Using Interactive Python Script

```bash
python3 bin/manage_hmac_keys.py delete -t <table_name>
```

**Interactive Process:**
The script will:
- Prompt for compact and state
- List all existing keys for the compact/state combination
- Allow you to select the specific key ID to delete
- Require typing "DELETE" to confirm the deletion
- Remove the key from the compact configuration database

### Key Rotation Best Practices

#### 1. Planning

- Coordinate with the State IT representative well in advance
- Plan for zero-downtime deployment

#### 2. Implementation

- Create new keys before removing old ones
- Allow both keys to be active during the transition period
- Monitor API access and authentication success rates
- Remove old keys only after confirming new keys are working correctly

#### 3. Documentation

- Document key rotation dates and reasons
- Maintain audit trail of all key management activities

### Security Considerations

#### 1. Key Storage

- Public keys are stored in DynamoDB with appropriate access controls
- Private keys should never be stored in CompactConnect systems
- State IT departments are responsible for secure private key management

#### 2. Access Control

- Only authorized technical staff should have access to key management resources
- All key management activities should be logged and audited
- Production key creation requires executive director approval

## Rotating App Client Credentials

Unfortunately, AWS Cognito does not support rotating app client credentials for an existing app client. The only way
to rotate credentials is to create a new app client with a new clientId and clientSecret and then delete the old one.
The following process should be performed if credentials are accidentally exposed or in the event of a security breach
where the old credentials are compromised.

### 1. Pre-rotation Tasks

- Contact consuming team to schedule rotation
- Follow "Creating a New App Client" steps above using either the Python script (recommended) or AWS CLI, you will
increment clientName version suffix by 1 (e.g. "example-ky-app-client-v1" -> "example-ky-app-client-v2")
- Update the external Google Sheet registry with new client information

### 2. Migration

- Provide new client id and client secret to consuming team
- Consuming team will need to confirm that the new credentials are deployed in their systems, the old app client is
not in use, and their systems are working as expected.

### 3. Cleanup

- Delete old app client from Cognito using the following cli command:
```
aws cognito-idp delete-user-pool-client --user-pool-id '<state auth user pool id>' --client-id '<old client id>'
```
