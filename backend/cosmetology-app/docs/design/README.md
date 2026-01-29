# Backend design

Look here for continued documentation of the back-end design, as it progresses.

## Table of Contents
- **[Compacts and Jurisdictions](#compacts-and-jurisdictions)**
- **[License Ingest](#license-ingest)**
- **[User Architecture](#user-architecture)**
- **[Data Model](#data-model)**
- **[Privileges](#privileges)**
- **[Advanced Data Search](#advanced-data-search)**
- **[CI/CD Pipelines](#cicd-pipelines)**
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
ky/cosm.admin
ky/cosm.write
ky/cosm.readPrivate
ky/cosm.readSSN
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
cosm/admin
cosm/readGeneral
cosm/readPrivate
cosm/readSSN
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

### Record Types in Detail

The data model comprises five distinct record types, each with a specific purpose:

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

A single query for a provider's partition with a sort key starting with `{compact}#PROVIDER` retrieves all records
needed to construct a complete view of the provider, including licenses, privileges, and their entire history in the
system.

### Historical Tracking

CompactConnect maintains a comprehensive historical record of each provider from their first addition to the system.
Any change to a provider's status, dates, or demographic information creates a supporting record that tracks the change.

For license changes, records use sort keys like `cosm#PROVIDER#license/oh#UPDATE#1735232821/1a812bc8f`. This key
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

This comprehensive data model enables efficient queries while maintaining complete historical data, supporting both
operational needs and audit requirements for healthcare provider licensing across jurisdictions.

## Privileges
[Back to top](#backend-design)

Privileges are authorizations that allow licensed providers to practice their profession in jurisdictions other than their home state. The CompactConnect system manages the privilege lifecycle, including renewals and encumbrance handling. This section provides a comprehensive walkthrough of how privileges work within the system.

### Overview of Privilege System

The privilege system is built around several core concepts:

1. **Home Jurisdiction**: The state where a provider holds their primary license
2. **Privilege Jurisdictions**: Other compact member states where the provider wants to practice
3. **License-Based Eligibility**: Privileges are tied to specific license types and depend on having a valid, unencumbered license in the home jurisdiction

#### Adverse Actions and Encumbrance
The system supports encumbering privileges due to adverse actions:
- **Privilege-Specific Encumbrance**: Targets individual privileges
- **License-Based Encumbrance**: If the encumbered license is in the home state, all privileges tied to that license are also encumbered


### Privilege History Timeline
The system presents a timeline of events and updates that happen to a privilege. This will allow users to see the events that impacted the privilege in a chronological order to help make sense of the changes over time.

#### We store the following privilege events / changes in our database:
- `deactivation`
- `renewal`
- `encumbrance`
- `liftingEncumbrance`
- `licenseDeactivation`

#### We dynamically calculate the following events for display despite them not explicitly being in the database:
- `issuance`
- `expiration`


In the timeline, the events are ordered chronologically by their effective datetime. We opted to use a datetime so that events occurring on the same day can be correctly ordered.  For most events their effective datetime is simply when it occurs in the system. However, for the following events there is more complexity:
- **Encumbrances**
  - Encumbrances are ordered and shown as having occurred at the effective date uploaded to the system by staff users
  - The staff users do not upload a time explicitly, but we assign the time to be noon UTC-4:00 so that users across the US will see that same date uploaded by the staff user regardless of timezone
- **Encumbrances Lifted**
  - Lifted encumbrances follow the same pattern as encumbrances mentioned above
- **Expirations**
  - Expirations are assigned the time of 23:59 UTC-4:00 because a privilege does not expire until the first second of the day after the listed date of expiration
  - All actions that occurred on that privilege during that day would therefor be correctly placed chronologically before the expiration while retaining the expiration's display date to be the privilege's date of expiration


## Advanced Data Search
[Back to top](#backend-design)

To support advanced search capabilities for provider and privilege records, this project leverages
[AWS OpenSearch Service](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/what-is.html).
Provider data from the provider DynamoDB table is indexed into an OpenSearch Domain (Cluster), enabling staff users to perform complex searches through the Search API (search.compactconnect.org). 

The OpenSearch resources are deployed within a Virtual Private Cloud (VPC) to provide network-level security and restrict outside access. Unlike DynamoDB, which is a fully managed and serverless AWS service that does not require (and does not support) VPC deployment, OpenSearch domains have data nodes that must be managed. Placing the OpenSearch domain in a VPC allows us to tightly control which resources and users can access it, reducing exposure to external threats.

### Architecture Overview
![Advanced Search Diagram](./advanced-provider-search.pdf)

The search infrastructure consists of several key components:

1. **OpenSearch Domain**: A managed OpenSearch cluster deployed within a VPC
2. **Index Manager**: A CloudFormation custom resource that creates and manages domain indices
3. **Search API**: API Gateway endpoints backed by Lambda functions for querying the domain
4. **Populate Handler**: A Lambda function for bulk indexing all provider data from DynamoDB
5. **Provider Update Ingest Handler**: A Lambda function for updating documents in OpenSearch whenever provider records are updated in DynamoDB.

### Index Structure

Provider documents are stored in compact-specific indices with the naming convention: `compact_{compact}_providers_{version}`
(e.g., `compact_aslp_providers_v1`). We use index aliases to provide a stable reference to the current version of each index, allowing read and write operations to be transparently redirected during planned index migrations or upgrades. This enables seamless index schema changes without requiring app code changes, as applications and APIs can continue to reference the alias rather than a specific index name. See [OpenSearch index alias documentation](https://docs.opensearch.org/latest/im-plugin/index-alias/) for more information.

#### Index Management

The `IndexManagerCustomResource` is a CloudFormation custom resource that creates compact-specific indices when the
domain is first created. It ensures the indices/aliases exist with the correct mapping before any indexing operations begin.

#### Index Mapping

Each provider document contains all information you would see from the provider detail api endpoint with `readGeneral` permission. See the [application code](../../lambdas/python/search/handlers/manage_opensearch_indices.py) for the current mapping definition.

The index uses a custom ASCII-folding analyzer for name fields, which allows searching for names with international
characters using their ASCII equivalents (e.g., searching "Jose" matches "José").

### Search API Endpoints

The Search API provides two endpoints for querying the OpenSearch domain:

#### Provider Search
```
POST /v1/compacts/{compact}/providers/search
```

Returns provider records matching the query. Response includes the full provider document with licenses and privileges.

#### Privilege CSV Export
```
POST /v1/compacts/{compact}/privileges/export
```

Returns flattened privilege records. This endpoint queries the same provider index but extracts and flattens
privileges, combining privilege data with license data to provide a denormalized list of objects which are then exported to a CSV file for downloading.

### Document Indexing

#### Initial Population / Re-indexing

The `populate_provider_documents` Lambda function handles bulk indexing of provider data from DynamoDB into
OpenSearch. This function is invoked manually through the AWS Console for:
- Initial data population when the search infrastructure is first deployed
- Full re-indexing if data becomes out of sync

The function:
1. Scans the provider table using the `providerDateOfUpdate` GSI
2. Retrieves complete provider records for each provider
3. Sanitizes data using `ProviderGeneralResponseSchema`
4. Bulk indexes documents

**Resumable Processing**: If the function approaches the 15-minute Lambda timeout, it returns pagination information in the 
`resumeFrom` field that can be passed as lambda input to continue processing:

```json
{
  "startingCompact": "cosm",
  "startingLastKey": {"pk": "...", "sk": "..."}
}
```

**Race Condition Consideration**: A potential race condition can occur when running this function while provider data is being actively updated:

1. The `populate_provider_documents` Lambda function queries the current data from DynamoDB for a provider
2. A change is made in DynamoDB for that same provider
3. The DynamoDB stream handler queries the data and indexes the change into OpenSearch after the ~30 second delay of sitting in SQS
4. The `populate_provider_documents` Lambda function finally indexes the stale data into OpenSearch, overwriting the change indexed by the DynamoDB stream handler

For this reason, it is recommended that this process be run during a period of low traffic. Given that it is a one-time process to initially populate the table, the risk is low and if needed, the Lambda function can be run again to synchronize all the provider documents.

#### Updates via DynamoDB Streams

To keep the OpenSearch index synchronized with changes in the provider DynamoDB table, the system uses DynamoDB Streams to capture all modifications made to provide records (see [AWS documentation](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Streams.html)). This ensures that provider documents in OpenSearch are updated automatically whenever records are created, modified, or deleted in the provider table.

**Architecture Flow:**

1. **DynamoDB Stream**: The provider table has a DynamoDB stream enabled with `NEW_AND_OLD_IMAGES` view type, which captures both the before and after state of any record modification.

2. **EventBridge Pipe**: An EventBridge Pipe reads events from the DynamoDB stream and forwards them to an SQS queue.

3. **Provider Update Ingest Lambda**: The Lambda function processes SQS message batches, determines the providers that were modified, and upserts their latest information into the appropriate OpenSearch index.

### Monitoring and Alarms

The search infrastructure includes CloudWatch alarms for capacity monitoring. If these alarms get triggered, review
usage metrics to determine if the Domain needs to be scaled up:

- **CPU Utilization**: Alerts when CPU exceeds threshold
- **Memory Pressure**: Monitors JVM memory pressure
- **Storage Space**: Alerts on low disk space
- **Cluster Health**: Monitors yellow/red cluster status

## CI/CD Pipelines

This project leverages AWS CodePipeline to deploy the backend and frontend infrastructure. See the
[pipeline architecture docs](./pipeline-architecture.md) for detailed discussion.

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
