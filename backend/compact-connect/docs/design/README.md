# Backend design

Look here for continued documentation of the back-end design, as it progresses.

## Table of Contents
- **[Compacts and Jurisdictions](#compacts-and-jurisdictions)**
- **[License Ingest](#license-ingest)**
- **[User Architecture](#user-architecture)**
- **[Data Model](#data-model)**
- **[Privileges](#privileges)**
- **[Attestations](#attestations)**
- **[Transaction History Reporting](#transaction-history-reporting)**
- **[Audit Logging](#audit-logging)**

## Compacts and Jurisdictions

The CompactConnect system supports multiple licensure compacts and, within each compact, multiple jurisdictions. The
jurisdictions it supports within each compact is all 50 states, Washington D.C., Puerto Rico, and the Virgin Islands.

### Adding a compact to CompactConnect

When a new compact joins CompactConnect, some configuration has to be done to add them to the system. First, a new
entry has to be added to the list of supported compacts, found in [cdk.json](../../cdk.json). Each compact is
represented there with an abbreviation, which determines how the compact will be represented in the API as well as
in its corresponding Oauth2 access scopes. Because of the way that the scopes are represented, the compact abbreviation
must not overlap with any jurisdiction abbreviations (which correspond to the jurisdictions' USPS postal abbreviations).
**Since postal abbreviations are all two letters, make a point to choose a compact abbreviation that is at least four
letters for clarity and to avoid naming conflicts.** Note that the compact abbreviations in this system do no
necessarily need to match the ones used publicly by those compacts. It only affects how the compact is represented
in the REST API and its access token scopes.

Once the supported compacts have been updated and the configuration change deployed, a CompactConnect admin can create
a user for the compact's executive director, who then will be allowed to start creating users for the boards of each
jurisdiction within the compact.

## License Ingest
[Back to top](#backend-design)

To facilitate sharing of license data across states, compact member jurisdictions will periodically upload data for
eligible licensees to CompactConnect. See [license-ingest-digram.pdf](./license-ingest-diagram.pdf) for an illustration
of the ingest chain architecture. Board admins and/or information systems have two primary methods of upload:
- A direct HTTP POST method, where they can synchronously validate up to 100 licenses per call.
- A bulk-upload mechanism that allows submitting of a CSV file with a much larger number of licenses for asynchronous
  validation and ingest.

### SSN Access Controls
The system implements strict controls for SSN access:

1. **Dedicated SSN Table**: All SSN data is stored in a dedicated DynamoDB table with strict access controls and
   customer-managed KMS encryption.
2. **Limited API Access**: Only specific API endpoints can query SSN data for staff users with the proper `readSSN`
   scope.
3. **Comprehensive Audit Logging**:
   - All SSN data access through the application is logged with user identity, timestamp, and access context
   - Direct database access is independently tracked through our secure audit logging system (see
     [Audit Logging](#audit-logging))
4. **Restricted Operations**: The SSN table policy explicitly denies batch operations to prevent mass data extraction.

#### SSN Role-Based Access
Three specialized IAM roles control access to SSN data:
   - `license_upload_role`: Used by upload handlers to encrypt SSN data for the preprocessing queue.
   - `ingest_role`: Used by the license preprocessor to create and update SSN records in the SSN table.
   - `api_query_role`: Used by the Get SSN API endpoint to allow staff users to read the SSN for an individual provider
     per request (staff user must have the readSSN permission).

### Ingest Flow

The ingest process begins when license data enters the system through one of the following two methods:

#### HTTP POST
   Clients can directly post an array of up to 100 licenses to the license data API. If they do this, the API will
validate each license synchronously and return any validation errors to the client. If the licenses are valid,
the API will send the validated licenses to the preprocessing queue.

#### Bulk Upload
   To upload a bulk license file, clients use an authenticated GET endpoint to receive a
[presigned url](https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-presigned-url.html) that will allow the
client to directly upload their file to s3. Once the file is uploaded to s3, an s3 event triggers a lambda to read and
validate each license in the data file, then fire either a success or failure event to the license data event bus.

Both of these upload methods will place license records containing full SSNs in an SQS queue which is encrypted with the
same KMS key as the SSN table to invoke the license preprocessor Lambda function.

#### **License Preprocessing**:
   - A Lambda function processes messages from the encrypted queue
   - For each license, it:
     - Extracts the full SSN from the license data and creates/updates a record in the SSN table, which becomes
       associated with a provider ID. This provider id is unique to the CompactConnect system and is used to generate
       provider records within the system.
     - After creating the SSN record, the lambda Publishes an event to the data event bus with the license data
       (minus the full SSN)

   The event bus then triggers the license data processing Lambda function.

#### **License Data Processing**:
   - The data event bus receives the sanitized license events
   - Downstream processors create provider and license records in the provider table, using only the last four digits
     of the SSN

This architecture ensures that SSN data is protected throughout the ingest process while still allowing the system to
associate licenses with the correct providers across jurisdictions.

### Asynchronous validation feedback
Asynchronous validation feedback for boards to review is not yet implemented.

## User Architecture
[Back to top](#backend-design)

Authentication with the CompactConnect backend will be controlled through Oauth2 via
[AWS Cognito User Pools](https://github.com/csg-org/CompactConnect). Clients will be divided into two groups, each
represented by an independent User Pool: [Staff Users](#staff-users) and [Licensee Users](#licensee-users). See
the accompanying [architecture diagram](./users-arch-diagram.pdf) for an illustration.

### Staff Users

Staff users will be granted a variety of different permissions, depending on their role. Read permissions are granted
to a user for an entire compact or not at all. Data writing and user administration permissions can each be granted to
a user per compact/jurisdiction combination. All of a compact user's permissions are stored in a DynamoDB record that is
associated with their own Cognito user id. That record will be used to generate scopes in the Oauth2 token issued to
them on login. See [Implementation of scopes](#implementation-of-scopes) for a detailed explanation of the design for
exactly how permissions will be represented by scopes in an access token. See
[Implementation of permissions](#implementation-of-permissions) for a detailed explanation of the design for exactly
how permissions are stored and translated into scopes.

#### Common Staff User Types
The system permissions are designed around several common types of staff users. It is important to note that these user
types are an abstraction which do not correlate directly to specific roles or access within the system. All access is
controlled by the specific permissions associated with a user. Still, these abstractions are useful for understanding
the system's design.

##### Compact Executive Directors and Staff

Compact ED level staff will typically be granted the following permissions at the compact level:

- `admin` - grants access to administrative functions for the compact, such as creating and managing users and their
  permissions.
- `readPrivate` - grants access to view all data for any licensee within the compact.

With the `admin` permission, they can grant other users the ability to write data for a particular
jurisdiction and to create more users associated with a particular jurisdiction. They can also delete any user within
their compact, so long as that user does not have permissions associated with a different compact, in which case the
permissions from the other compact would have to be removed first.

Users granted any of these permissions will also be implicitly granted the `readGeneral` scope for the associated
compact, which allows them to read any licensee data within that compact that is not considered private.

##### Board Executive Directors and Staff

Board ED level staff may be granted the following permissions at a jurisdiction level:

- `admin` - grants access to administrative functions for the jurisdiction, such as creating and managing users and
their permissions.
- `write` - grants access to write data for their particular jurisdiction (ie uploading license information).
- `readPrivate` - grants access to view all information for any licensee that has either a license or privilege within
  their jurisdiction (except the full SSN, see `readSSN` permission below. This permission allows viewing the last 4
  digits of the SSN).
- `readSSN` - grants access to view the full SSN for any licensee that has either a license or privilege within their
  jurisdiction.

#### Implementation of Scopes

AWS Cognito integrates with API Gateway to provide
[authorizers](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-integrate-with-cognito.html)
on an API that can verify the tokens issued by a given User Pool and to protect access based on scopes belonging to
[Resource Servers](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-define-resource-servers.html)
associated with that User Pool.

The Staff Users pool implements authorization using resource servers configured for each jurisdiction and compact. This
design allows for efficient management of permissions while staying within AWS Cognito's limits (100 scopes per
resource server, 300 resource servers per user pool).

Each jurisdiction has its own resource server with scopes that control access to that jurisdiction's data across
different compacts. For example, the Kentucky (KY) resource server would have scopes like:

```
ky/aslp.admin
ky/aslp.write
ky/aslp.readPrivate
ky/aslp.readSSN
ky/octp.admin
ky/octp.write
ky/octp.readPrivate
ky/octp.readSSN
```

If a user has the `ky/aslp.admin` scope, for example, they will be able to perform any admin action within the Kentucky
jurisdiction within the ASLP compact.

Each compact also has its own resource server with compact-wide scopes, which are used to control access to data across
all jurisdictions within a compact:

```
aslp/admin
aslp/readGeneral
aslp/readPrivate
aslp/readSSN
```

If a user has the `aslp/admin` scope, for example, they will be able to perform any admin action for any jurisdiction
within the compact.

Staff users in a compact will also be implicitly granted the `readGeneral` scope for the associated compact,
which allows them to read any licensee data that is not considered private.

In addition to the `readGeneral` scope, there is a `readPrivate` scope, which can be granted at both compact and
jurisdiction levels. This permission indicates the user can read all of a compact's provider data (licenses and
privileges), so long as the provider has at least one license or privilege within their jurisdiction or the user has
compact-wide permissions.

#### Implementation of Permissions

Staff user permissions are stored in a dedicated DynamoDB table, which has a single record for each user
and includes a data structure that details that user's particular permissions. Cognito allows for a lambda to be
[invoked just before it issues a token](https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-lambda-pre-token-generation.html).
We use that feature to retrieve the database record for each user, parse the permissions data and translate those
into scopes, which will be added to the Cognito token. The lambda generates scopes based on both compact-level and
jurisdiction-level permissions, ensuring consistent access control at token issuance.

#### Machine-to-machine app clients

See README under the [app_clients](../../app_clients/README.md) directory for more information about how
machine-to-machine app clients are configured and used in the system.

### Licensee Users

Licensee users permissions are much simpler as compared to Compact Users. Their access is entirely based on identity.
Once their identity has been verified and associated with a licensee in the license data system, they will only have
permission to view system data that is specific to them. They will be able to apply for and renew privileges to practice
across jurisdictions, subject to their eligibility.

## Data Model
[Back to top](#backend-design)

CompactConnect uses a single noSQL (DynamoDB) table design for storing provider (practitioner) data, following the
[single table design](https://aws.amazon.com/blogs/database/single-table-vs-multi-table-design-in-amazon-dynamodb/)
pattern. This approach optimizes for:

1) **Compact-Level Partitioning**: Data is always partitioned by compact, ensuring that queries never return records
   from multiple compacts. This enforces a deliberate separation of data across all layers - UI, API, and database -
   where users must explicitly specify which compact's data they're accessing.

2) **Query Efficiency**: Access patterns are optimized so most data needs can be satisfied in a single query, leveraging
   DynamoDB's single-digit-millisecond latency at any scale.

### Key Structure and Record Types

Each provider is assigned a unique partition key in the format: `{compact}#PROVIDER#{providerId}` (example:
`"pk": "aslp#PROVIDER#89a6377e-c3a5-40e5-bca5-317ec854c570"`). Within this partition, multiple record types are stored
with different sort keys:

```
- Provider:           {compact}#PROVIDER
- License:            {compact}#PROVIDER#license/{jurisdiction}/{licenseTypeAbbr}#
- Privilege:          {compact}#PROVIDER#privilege/{jurisdiction}/{licenseTypeAbbr}#
- License Update:     {compact}#PROVIDER#license/{jurisdiction}/{licenseTypeAbbr}#UPDATE#{timestamp}/{changeHash}
- Privilege Update:   {compact}#PROVIDER#privilege/{jurisdiction}/{licenseTypeAbbr}#UPDATE#{timestamp}/{changeHash}
- Home Jurisdiction:  {compact}#PROVIDER#home-jurisdiction#
- Military Affiliation: {compact}#PROVIDER#military-affiliation#{timestamp}
```

This design allows for retrieving specific record types by using sort key prefixes. For example, querying with a sort
key beginning with `{compact}#PROVIDER#license/` would return all license records for that provider.

### Record Types in Detail

The data model comprises seven distinct record types, each with a specific purpose:

1. **Provider Record** (`provider`): The core record containing a provider's foundational information:
   - Personal details (name, DOB, contact information)
   - Home address
   - License jurisdiction of record
   - SSN last four digits (full SSN is stored separately for security)
   - National Provider Identifier (NPI)
   - Set of privilege jurisdictions
   - Status (calculated based on expiration date and jurisdiction status)

2. **License Record** (`license`): Represents professional licenses held by the provider:
   - License number and type
   - Issuing jurisdiction
   - Issuance, renewal, and expiration dates
   - License status (active/inactive, calculated at load time, based on current time, expiry, and other factors)
   - Provider's name and contact details at time of issuance

3. **Privilege Record** (`privilege`): Represents authorizations to practice in other jurisdictions:
   - Jurisdiction where privilege is granted
   - Dates of issuance, renewal, and expiration
   - Status (active/inactive, calculated at load time, based on current time, expiry, and other factors)
   - Reference to the transaction ID from purchase
   - Attestations accepted when purchasing the privilege
   - Unique privilege identifier
   - License jurisdiction and type on which the privilege is based

4. **License Update Record** (`licenseUpdate`): Tracks historical changes to licenses:
   - Update type (renewal, deactivation, or other)
   - Previous values before the update
   - Updated values that changed
   - List of values that were removed
   - Timestamp of the update
   - Change hash for uniqueness

5. **Privilege Update Record** (`privilegeUpdate`): Similar to license updates, tracks changes to privileges:
   - Previous privilege state
   - Updated values
   - Timestamp of the update
   - Change hash for uniqueness

6. **Home Jurisdiction Selection Record** (`homeJurisdictionSelection`): Records the provider's selected home
   jurisdiction:
   - Selected jurisdiction
   - Date of selection

7. **Military Affiliation Record** (`militaryAffiliation`): Tracks a provider's military status:
   - Affiliation type
   - Status (active/inactive/initializing)
   - Documentation references
   - Upload date

A single query for a provider's partition with a sort key starting with `{compact}#PROVIDER` retrieves all records
needed to construct a complete view of the provider, including licenses, privileges, and their entire history in the
system.

### Historical Tracking

CompactConnect maintains a comprehensive historical record of each provider from their first addition to the system.
Any change to a provider's status, dates, or demographic information creates a supporting record that tracks the change.

For license changes, records use sort keys like `aslp#PROVIDER#license/oh#UPDATE#1735232821/1a812bc8f`. This key
contains:
- The jurisdiction (e.g., "oh")
- "UPDATE" indicator
- POSIX timestamp of the change
- A hash of the previous and updated values for uniqueness

Similarly, privilege changes use sort keys like `aslp#PROVIDER#privilege/ne#UPDATE#1735232821/1a812bc8f`.

This historical tracking allows authorized users to determine a provider's practice eligibility status in any member
state for any point in time since they entered the system.

### Global Secondary Indexes (GSIs)

The provider table includes several GSIs to support different access patterns:

1. **Provider Name Index** (`providerFamGivMid`):
   - Enables searching providers by name
   - Uses a composite sort key of quoted and lowercase family name, given name, and middle name

2. **Provider Update Time Index** (`providerDateOfUpdate`):
   - Allows retrieving providers by the date they were last updated
   - Useful for getting recently modified provider records

3. **License GSI** (`licenseGSI`):
   - Facilitates finding licenses by jurisdiction and provider name
   - Supports compact and jurisdiction-specific queries

4. **Compact Transaction ID GSI** (`compactTransactionIdGSI`):
   - Links privileges to their purchase transactions
   - Important for financial reporting and reconciliation

### Security and Status Calculation

The model incorporates several security and operational features:

1. **SSN Protection**: Only the last four digits of SSNs are stored in the provider table. Full SSNs are stored in a
   separate, highly secured table with strict access controls.

2. **Status Calculation**: Rather than storing a simple status flag, the system calculates status at read time based on:
   - The jurisdiction's reported status (active/inactive)
   - The current date compared to the expiration date
   - This ensures accurate representation of a provider's current status without requiring updates

3. **Historical Tracking**: All changes are preserved as separate records, allowing point-in-time deduction of a
   provider's status for any historical date.

4. **Attestation Tracking**: When providers purchase privileges, the system records which attestation versions they
   accepted, creating an audit trail of consent.

This comprehensive data model enables efficient queries while maintaining complete historical data, supporting both
operational needs and audit requirements for healthcare provider licensing across jurisdictions.

## Privileges
[Back to top](#backend-design)

Privileges are authorizations that allow licensed providers to practice their profession in jurisdictions other than their home state. The CompactConnect system manages the entire privilege lifecycle, from initial purchase through home jurisdiction changes and renewals. This section provides a comprehensive walkthrough of how privileges work within the system.

### Overview of Privilege System

The privilege system is built around several core concepts:

1. **Home Jurisdiction**: The state where a provider holds their primary license and has selected as their home base
2. **Privilege Jurisdictions**: Other compact member states where the provider wants to practice
3. **License-Based Eligibility**: Privileges are tied to specific license types and depend on having a valid, unencumbered license in the home jurisdiction

### Privilege Purchase Flow

When a provider wants to purchase privileges to practice in additional jurisdictions, they follow this process:

#### 1. Eligibility Check
The system first verifies the provider's eligibility:
- Provider must have a valid, active license in their home jurisdiction
- License must not be expired or encumbered
- Provider must have completed registration in CompactConnect
- Provider must accept current attestations for privilege purchase

#### 2. Jurisdiction Selection
Providers can select multiple jurisdictions for privilege purchase in a single transaction. The system:
- Validates each selected jurisdiction is a compact member
- Checks for existing privileges to avoid duplicates
- Calculates fees based on jurisdiction-specific pricing

#### 3. Payment Processing
The purchase process integrates with payment processors (currently Authorize.net):
- Creates line items for each jurisdiction privilege
- Includes compact administrative fees
- Processes payment with privilege details
- Links payment transaction id to privilege records for audit trails

#### 4. Privilege Record Creation
Upon successful payment, the system creates privilege records. Each privilege record includes:
- Unique privilege identifier (example: `slp-ky-1234`)
- Issuance and expiration dates (tied to home license expiration)
- Reference to the purchase transaction id
- Attestations accepted during purchase
- Status tracking fields

### Home Jurisdiction Changes
[Flow chart diagram](./practitioner-home-state-update-flow-chart.pdf)

One of the most complex aspects of the privilege system is handling when a provider changes their home jurisdiction. This process follows a detailed business logic flow chart to ensure privileges are properly transferred, deactivated, or updated based on various conditions.

#### Rules for Home Jurisdiction Changes

The system applies the following rules when a provider updates their home jurisdiction:

##### Rule 1: No License in Selected Jurisdiction
If the provider has no known license in the newly selected jurisdiction:
- All existing privileges are marked with `homeJurisdictionChangeStatus: 'inactive'`
- Provider record is updated with the new home jurisdiction
- Privileges remain in the system but cannot be used for practice

##### Rule 2: Expired License in Current Home State
If the license in the current home state has expired:
- Privileges are not transferred to the new jurisdiction
- Existing privileges remain expired
- Provider can renew privileges later if they obtain a valid license

##### Rule 3: Encumbered License in Current Home State
If the current home state license is encumbered (due to adverse actions):
- Privileges are not moved to the new jurisdiction
- Encumbered status is maintained
- Provider must resolve encumbrance issues before privileges can be renewed

##### Rule 4: Ineligible License in New Jurisdiction
If the license in the new jurisdiction has `compactEligibility: 'ineligible'`:
- Existing privileges are deactivated (`homeJurisdictionChangeStatus: 'inactive'`)
- Provider cannot practice under compact privileges until eligibility is restored

##### Rule 5: Encumbered License in New Jurisdiction
If the new jurisdiction license is encumbered but unexpired:
- Privileges are transferred to the new jurisdiction
- Privileges that aren't already encumbered get `encumberedStatus: 'licenseEncumbered'`
- Expiration dates are updated to match the new license

##### Rule 6: Valid License Transfer
If the provider has a  valid, unencumbered, compact-eligible license in the new jurisdiction:
- Privileges are transferred to the new jurisdiction
- Expiration dates are updated to match the new license expiration
- Any privilege for the same jurisdiction as the new license is deactivated (to avoid conflicts)
- License jurisdiction on privilege records is updated

### Privilege Lifecycle Management


#### Privilege Renewals
When providers renew privileges:
- System checks for existing privilege records
- Preserves original issuance date and privilege ID
- Updates expiration date and renewal date
- Creates privilege update history records
- Reactivates privileges that were previously deactivated due to administrator action

#### Adverse Actions and Encumbrance
The system supports encumbering privileges due to adverse actions:
- **Privilege-Specific Encumbrance**: Targets individual privileges
- **License-Based Encumbrance**: If the encumbered license is in the home state, all privileges tied to that license are also encumbered

## Attestations
[Back to top](#backend-design)

Attestations are statements that providers must agree to when performing certain actions within the system, such as
purchasing privileges. The attestation system is designed to support versioned, localized attestation text that
providers must explicitly accept.

### Storage and Versioning

Attestations are stored in the compact configuration table with a composite key structure that enables efficient
querying of the latest version for a given attestation type and locale:

```
PK: {compact}#CONFIGURATION
SK: {compact}#ATTESTATION#{attestationId}#LOCALE#{locale}#VERSION#{version}
```

This structure allows us to:
1. Group all attestations for a compact together (via PK)
2. Sort attestations by type, locale, and version (via SK)
3. Query for the latest version of a specific attestation in a given locale using a begins_with condition on the SK

### Retrieval and Validation

The system provides a `GET /v1/compacts/{compact}/attestations/{attestationId}` endpoint that returns the latest version
of an attestation. This endpoint:
1. Accepts an optional `locale` query parameter (defaults to 'en').
2. Returns a 404 if no attestation is found for the given type/locale.
3. Always returns the latest version of the attestation.

When providers perform actions that require attestations (like purchasing privileges), they must:
1. Fetch the latest version of each required attestation
2. Include the attestation IDs and versions in their request
3. The system validates that:
   - All required attestations are present
   - The provided versions match the latest versions
   - No invalid attestation types are included

### Usage in Privilege Purchases

When purchasing privileges, providers must accept all required attestations. The purchase endpoint:
1. Validates the attestations array in the request body
2. Verifies each attestation is the latest version
3. Stores the accepted attestations with the privilege record
4. Returns a 400 error if any attestation is invalid or outdated

This ensures that providers always see and accept the most current version of required attestations, and we maintain an
audit trail of which attestation versions were accepted for each privilege purchase.

## Transaction History Reporting
[Back to top](#backend-design)

![Transaction History Reporting Diagram](./transaction-history-reporting-diagram.pdf)

When a provider purchases privileges in a compact, the purchase is recorded in the compact's payment processor
(currently we only support Authorize.net). There is at least a 24 hour delay before the transaction is settled. The
transaction history reporting system is designed to track and report on all settled transactions in the system.

### Transaction Processing Overview

The system processes transactions through multiple stages:

1. **Initial Purchase**
   - Provider initiates a purchase for one or more privileges
   - System creates an `authCaptureTransaction` in Authorize.net with line items for:
     - Each jurisdiction privilege
     - Compact administrative fees
     - Transaction fees (if configured)
   - Transaction details include provider ID in the order description for tracking

2. **Settlement Process**
   - By default, Authorize.net batches settlements daily at 4:00 PM Pacific Time (this can be changed by the
     Authorize.net account owners)
   - Each batch contains transactions since the last batch was settled
   - Batches can be in one of several states:
     - Settled: Successfully processed
     - Settlement Error: Failed to settle (triggers email notification to compact support contacts) see
       [Batch Settlement Failure Handling](#batch-settlement-failure-handling)

3. **Transaction Collection**
   - A Step Function workflow runs daily at 5:00 PM Pacific Time (1:00 AM UTC)
   - The workflow:
     - Queries Authorize.net for all batches in the last 24 hours
     - Processes transactions in groups of up to 500 (to avoid lambda timeouts)
     - Retrieves the associated privilege id from CompactConnect's provider data DynamoDB Table for the privilege that
       was purchased for each transaction and injects it into the data that is stored in the Transaction History
       DynamoDB Table.
     - Handles pagination across multiple batches
     - Sends email alerts if settlement errors are detected

4. **Reporting**

   The System generates two types of reports:
     - **Compact Reports**:
       - Financial summary showing total amount of fees collected
       - Detailed transaction listing
     - **Jurisdiction Reports**:
       - Transaction details for privileges purchased in their jurisdiction


All of these reports are sent out weekly (Fridays at 10:00 PM UTC) and monthly (1st day of each month at 8:00 AM UTC).

### Data Storage
#### Transaction History
Transactions are stored in DynamoDB with the following key structure:
```
PK: COMPACT#{compact}#TRANSACTIONS#MONTH#{YYYY-MM}
SK: COMPACT#{compact}#TIME#{batch settled time epoch_timestamp}#BATCH#{batch_id}#TX#{transaction_id}
```

This structure enables:
- Efficient querying of transactions by compact and time period
- Monthly partitioning for performance

#### Report Files
Reports are stored in the Transaction Reports S3 bucket as compressed ZIP files under the following path:
```
compact/{compact}/reports/{compact-transactions|jurisdiction-transactions}/reporting-cycle/{monthly|weekly}/{YYYY}/{MM}/{DD}/{file-name}.zip
```
The date in the path corresponds to the date that the report was generated.


### Monitoring and Alerts

The system includes several monitoring mechanisms:
- CloudWatch alarms for workflow failures
- Alerts for batch settlement errors
- Duration monitoring for long-running processes
- Error tracking for transaction processing issues

This design ensures reliable transaction processing and reporting while maintaining a complete audit trail of all
successfully settled financial transactions within the system.

### Batch Settlement Failure Handling
If a batch fails to settle for whatever reason, Authorize.net will return the batch with a status of `Settlement Error`.
From their [documentation about possible transaction statuses](https://support.authorize.net/knowledgebase/Knowledgearticle/?code=000001360),
a settlement error can result from one of the following:
 > - Entire Batch with Settlement Error: If all transactions in the batch show a "Settlement Error" status, it may
 >   indicate that the batch initially failed. If the batch was not reset or made viewable within 30 days of the
 >   failure, further action cannot be taken. If funding is missing for this batch, please contact your Merchant Service
 >   Provider (MSP) to explore possible solutions or reprocess the transactions from that batch.
 > - Partial Batch with Settlement Error: If one or more (but not all) transactions in the batch show a "Settlement
 >   Error" status, there might be a configuration issue (likely related to accepted card types) where the processor
 >   authorized the transactions but rejected them at settlement. In this case, please ask your MSP to investigate the
 >   issue with the processor.

When a batch fails to settle, we send an email to the compact's support contacts alerting them to reach out to their MSP
to investigate the issue. After the issue is resolved, Authorize.net can be instructed to reprocess the batch. Per
Authorize.net [support documentation](https://community.developer.cybersource.com/t5/Integration-and-Testing/What-happens-to-a-batch-having-a-settlementState-of/td-p/58993):

> A failed batch needs to be reset and this means that the merchant will need to contact Authorize.Net to request for a
> batch reset. It is important to note that batches over 30 days old cannot be reset. When resetting a batch, merchant
> needs to confirm first with their MSP (Merchant Service Provider) that the batch was not funded, and the error that
> failed the batch has been fixed, before submitting a ticket for the batch to be reset.

> Resetting a batch doesn't really modify the batch, what it does, is it takes the transactions from the batch and puts
> them back into unsetttled so they settle with the next batch. Those transactions that were in the failed batch will
> still have the original submit date.

For this reason, we use the batch settlement time as the timestamp for the transaction records we store in the
transaction history table. This ensures that any transactions that are in a batch which fails to settle will eventually
be processed and stored in the transaction history table.

## Audit Logging
[Back to top](#backend-design)

### Overview

CompactConnect implements a comprehensive audit logging system using AWS CloudTrail to track access to sensitive data,
particularly DynamoDB tables containing SSNs. This system provides accountability, supports audit requirements, and
enables incident investigation when needed.

### Multi-Account Architecture

The audit logging infrastructure is deployed across two AWS accounts for enhanced security:

1. **Logs Account**: Contains secured S3 buckets for storing:
   - CloudTrail logs from sensitive table operations
   - Access logs from all buckets for comprehensive tracking

2. **Management Account**: Hosts the CloudTrail organization trail and the KMS encryption key

This separation follows security best practices and ensures that those who can access sensitive data can't modify the
logs of their actions, and vice versa.

### Understanding CloudTrail Organization Trail

AWS CloudTrail is a service that records API calls made within an AWS account. Our implementation uses an organization
trail, which provides several important capabilities:

- **Cross-Account Visibility**: A single trail that captures activities across all AWS accounts in our organization
- **Centralized Logging**: All logs are automatically sent to a central, secured location in the logs account
- **Data Event Focus**: The trail is configured to capture specific "data events" - detailed records of when someone
  reads data from sensitive tables
- **Consistent Policy**: The same logging standards are automatically applied to all accounts in the organization

This approach ensures that all interactions with sensitive data are captured, regardless of which account the user is
operating from.

### Logging Strategy

The system balances comprehensive coverage with cost efficiency:

- **Selective Logging**: We focus on tables containing the most sensitive data, particularly SSNs
- **Read Operations**: We track primarily read operations as these represent potential data exposure
- **Opt-In Design**: Tables are explicitly marked for logging with a special suffix (-DataEventsLog)

### Key Security Features

Several important controls protect the integrity of the audit logs:

- **Immutable Storage**: S3 buckets with versioning and support for object locks, to prevent log deletion or
  modification
- **Encryption**: KMS encryption with restricted access protects log content
- **Break-Glass Access**: A security model where even administrators need special authorization to access logs
- **Organization-wide Visibility**: The CloudTrail is configured as an organization trail, capturing events across all
  accounts

### Business Benefits

This audit logging architecture delivers several advantages:

- **Security Governance**: Supports audit requirements and security best practices
- **Forensic Capability**: Enables detailed investigation of any potential data misuse
- **Accountability**: Creates clear audit trails of who accessed what data and when
- **Cost Optimization**: Intelligent storage tiering and selective logging minimize expenses

The system operates automatically in the background, requiring minimal day-to-day management while providing essential
security and governance capabilities.
