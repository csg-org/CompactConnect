# Backend design

Look here for continued documentation of the back-end design, as it progresses.

## Table of Contents
- **[Compacts and Jurisdictions](#compacts-and-jurisdictions)**
- **[License Ingest](#license-ingest)**
- **[User Architecture](#user-architecture)**
- **[Data Model](#data-model)**
- **[Attestations](#attestations)**

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

Internally, the ingest chain is an event-driven architecture, with a single ingest process that receives events from a
single EventBridge event bus. Both the HTTP POST and the bulk-upload file publish events for each individual license
to be validated.

### Bulk-Upload
To upload a bulk license file, clients use an authenticated GET endpoint to receive a
[presigned url](https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-presigned-url.html) that will allow the
client to directly upload their file to s3. Once the file is uploaded to s3, an s3 event triggers a lambda to read and
validate each license in the data file, then fire either a success or failure event to the license data event bus.

### HTTP POST
Clients can directly post an array of up to 100 licenses to the license data API. If they do this, the API will
validate each license synchronously and return any validation errors to the client. If the licenses are valid,
the API will publish an ingest event for each license.

### Ingest processing
Ingest events published to the event bus will be passed to an SQS queue, where ingest jobs will be batched for
efficient processing. A lambda receives messages from the SQS queue. Each message corresponds to one license to be
ingested. The lambda receives the data and creates or updates a corresponding license record in the DynamoDB license
data table.

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
associated with their own Cognito user id. That record will be used to generate scopes in the Oauth2 token issued to them
on login. See [Implementation of scopes](#implementation-of-scopes) for a detailed explanation of the design for exactly
how permissions will be represented by scopes in an access token. See 
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

Users granted any of these permissions will also be implicitly granted the `readGeneral` scope for the associated compact,
which allows them to read any licensee data within that compact that is not considered private.

##### Board Executive Directors and Staff

Board ED level staff may be granted the following permissions at a jurisdiction level:

- `admin` - grants access to administrative functions for the jurisdiction, such as creating and managing users and 
their permissions.
- `write` - grants access to write data for their particular jurisdiction (ie uploading license information).
- `readPrivate` - grants access to view all information for any licensee that has either a license or privilege
within their jurisdiction. 

Users granted any of these permissions will also be implicitly granted the `readGeneral` scope for the associated compact,
which allows them to read any licensee data that is not considered private.

#### Implementation of Scopes

AWS Cognito integrates with API Gateway to provide
[authorizers](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-integrate-with-cognito.html) on an
API that can verify the tokens issued by a given User Pool and to protect access based on scopes belonging to
[Resource Servers](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-define-resource-servers.html)
associated with that User Pool. In the Staff Users user pool, we represent each compact as its own Resource Server, with
associated scopes. Unfortunately, because resource servers support only up to 100 scopes each, and we would like to
control permission to write to or administrate each of more than 50 jurisdictions independently, the combinations would
require more than 100 scopes per resource server.

To design around the 100 scope limit, we will have to split authorization into two layers: coarse- and fine-grained.
We can rely on the Cognito authorizers to protect our API endpoints based on fewer coarse-grained scopes, then
protect the more fine-grained access within the API endpoint logic. The Staff User pool resource servers are
configured with `readGeneral`, `write`, and `admin` scopes. The `readGeneral` scope is implicitly granted to all users in
the system, and is used to indicate that the user is allowed to read any compact's licensee data that is not considered
private. The `write` and `admin` scopes, however, indicate only that the user is allowed to write or administrate 
_something_ in the compact respectively, thus giving them access to the write or administrative API endpoints. We will 
then rely on the API endpoint logic to refine their access based on the more fine-grained access scopes.

In addition to the `readGeneral` scope, there is a `readPrivate` scope, which can be granted at both compact and 
jurisdiction levels. This permission indicates the user can read all of a compact's provider data (licenses and privileges),
so long as the provider has at least one license or privilege within their jurisdiction or the user has compact-wide 
permissions.

To compliment each of the `write` and `admin` scopes, there will be at least one, more specific, scope, 
to indicate _what_ within the compact they are allowed to write or administrate, respectively. In the case of `write` 
scopes, a jurisdiction-specific scope will control what jurisdiction they are able to write data for (i.e. `al.write` 
grants permission to write data for the Alabama jurisdiction). Similarly, `admin` scopes can have a jurisdiction-specific
scope like `al.admin` and can also have a compact-wide scope like `aslp.admin`, which grants permission for a compact
executive director to perform the administrative functions for the Audiology and Speech Language Pathology compact.

#### Implementation of Permissions

Staff user permissions will be stored in a dedicated DynamoDB table, which will have a single record for each user
and include a data structure that details that user's particular permissions. Cognito allows for a lambda to be [invoked
just before it issues a token](https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-lambda-pre-token-generation.html).
We will use that feature to retrieve the database record for each user, parse the permissions data and translate those
into scopes, which will be added to the Cognito token. The lambda will generate both the coarse- and fine-grained
scopes to be added to the token, thus being the single control point for access control on the token-issuing side.

### Licensee Users

Licensee users permissions are much simpler as compared to Compact Users. Their access is entirely based on identity.
Once their identity has been verified and associated with a licensee in the license data system, they will only have
permission to view system data that is specific to them. They will be able to apply for and renew privileges to practice
across jurisdictions, subject to their eligibility.

## Data Model
[Back to top](#backend-design)

Data for the licensed practitioners is housed primarily in a single noSQL (DynamoDB) table, using a
[single table design](https://aws.amazon.com/blogs/database/single-table-vs-multi-table-design-in-amazon-dynamodb/).
The design of the data model is built around expected access patterns for practitioner data, with two main priorities
in mind:
1) Compact data should always be partitioned. This means that, whenever querying the database, it should not be possible
   to query for data that may contain records for more than one compact in the response. The intent here is that
   CompactConnect should have a deliberately partitioned experience in its data, from the UI, to the API, and all the
   way down to the database layer, where a user must always be explicit about which compact's data they are interacting
   with.
2) As much as is practical, an access pattern for retrieving practitioner data should be satisfied in a single query.
   DynamoDB is designed to have single-millisecond latency for queries, at any scale. If we want a fast, performant
   API, we should leverage that performance by deliberately crafting our records so that any set of records we expect
   our users to want should be retrieved in a single query.

### Provider records

Provider (practitioner) records are stored in the database with each provider having their own partition key, for
example: `"pk": "aslp#PROVIDER#89a6377e-c3a5-40e5-bca5-317ec854c570"`. This allows for the partition to be retrieved
if a user is armed with only a compact and the identifier for the provider. From there, the provider's data is split
into records of multiple types that are distinguished by their sort key:

Primary information about a provider, as deduced mostly from license data provided by states, is stored in their
`provider` type record and includes things like their name, home address, and date of birth. The provider record uses
a sort key like `"sk": "aslp#PROVIDER"`.

Each license associated with a provider has the data submitted by a state saved in a record with a sort key like
`"sk": "aslp#PROVIDER#license/oh#"`. This example record would be for a license in Ohio. Each license a state uploads
that is associated with this provider can then be returned by a query for that provider's partition, with a query
key condition that specifies a sort key starting with `aslp#PROVIDER#license/`.

Similarly, privileges to practice granted to the provider for a state are stored in a record with a sort key like
`"sk": "aslp#PROVIDER#privilege/ne#"`. This example record represents a privilege granted to practice in Nebraska.
The sort key pattern for privileges allows all privilege records to be queried by a sort key starting with
`aslp#PROVIDER#privilege/`.

In addition to recording the current state of the provider, their licenses and privileges, CompactConnect also stores
historical data for providers, starting the day they are first added to the system. This historical data allows
interested parties to determine the status of a provider's ability to practice in any given member state on any given
day in the past. Any time a provider's status, date of expiration, renewal, or other values like name are changed,
a supporting record is created to track the change. For changes to a license, the record is stored with a sort key like
`aslp#PROVIDER#license/oh#UPDATE#1735232821/1a812bc8f`. This sort key will uniquely represent one particular change,
the time it was effective in the system, and the contents of that change. Similarly, a change to a privilege will be
represented with a record stored with a sort key like `aslp#PROVIDER#privilege/ne#UPDATE#1735232821/1a812bc8f`.

A query for a provider's partition and a sort key starting with `aslp#PROVIDER` would retrieve enough records to
represent all of the provider's licenses, privileges and their complete history from when they were created in
the system.

## Attestations
[Back to top](#backend-design)

Attestations are statements that providers must agree to when performing certain actions within the system, such as purchasing privileges. The attestation system is designed to support versioned, localized attestation text that providers must explicitly accept.

### Storage and Versioning

Attestations are stored in the compact configuration table with a composite key structure that enables efficient querying of the latest version for a given attestation type and locale:

```
PK: {compact}#CONFIGURATION
SK: {compact}#ATTESTATION#{attestationId}#LOCALE#{locale}#VERSION#{version}
```

This structure allows us to:
1. Group all attestations for a compact together (via PK)
2. Sort attestations by type, locale, and version (via SK)
3. Query for the latest version of a specific attestation in a given locale using a begins_with condition on the SK

### Retrieval and Validation

The system provides a `GET /v1/compacts/{compact}/attestations/{attestationId}` endpoint that returns the latest version of an attestation. This endpoint:
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

This ensures that providers always see and accept the most current version of required attestations, and we maintain an audit trail of which attestation versions were accepted for each privilege purchase.
