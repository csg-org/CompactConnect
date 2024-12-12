# Backend design

Look here for continued documentation of the back-end design, as it progresses.

## Table of Contents
- **[Compacts and Jurisdictions](#compacts-and-jurisdictions)**
- **[License Ingest](#license-ingest)**
- **[User Architecture](#user-architecture)**

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

Staff users come with a variety of different permissions, depending on their role. There are Compact Executive
Directors, Compact ED Staff, Board Executive Directors, Board ED Staff, and CSG Admins, each with different levels
of ability to read and write data, and to administrate users. Read permissions are granted to a user for an entire
compact or not at all. Data writing and user administration permissions can each be granted to a user per
compact/jurisdiction combination. All of a compact user's permissions are stored in a DynamoDB record that is associated
with their own Cognito user id. That record will be used to generate scopes in the Oauth2 token issued to them on login.
See [Implementation of scopes](#implementation-of-scopes) for a detailed explanation of the design for exactly how
permissions will be represented by scopes in an access token. See
[Implementation of permissions](#implementation-of-permissions) for a detailed explanation of the design for exactly
how permissions are stored and translated into scopes.

#### Compact Executive Directors and Staff

Compact ED level staff can have permission to read all generally available data for any compact, and if they have the 
`readPrivate` permission they will be able to view all data for any licensee within the compact. They will also be able
to create and manage users and their permissions. They can grant other users the ability to write data for a particular
jurisdiction and to create more users associated with a particular jurisdiction. They can also delete any user within 
their compact, so long as that user does not have permissions associated with a different compact.

#### Board Executive Directors and Staff

Board ED level staff can have permission to read all generally available jurisdiction data, and if they have the 
`readPrivate` permission they will be able to view all information for any licensee that has either a license or privilege
within their jurisdiction. They can also write data to for their own jurisdiction, and to create more users that have 
permissions within their own jurisdiction. They can also delete any user within their jurisdiction, so long as that user
does not have permissions associated with a different compact or jurisdiction.

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

In addition to the `readGeneral` scope, there is a `readPrivate` scope that is used to indicate that the user is allowed
to read all of a compact's licensee data, so long as that licensee is within their compact or jurisdiction for which
they have that permission.

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
