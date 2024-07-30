# Backend design

Look here for continued documentation of the back-end design, as it progresses.

## Table of Contents
- **[License Ingest](#license-ingest)**
- **[User Architecture](#user-architecture)**

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
of ability to read and write data, and to administrate users:
[Compact EDs and Staff](#compact-executive-directors-and-staff) and
[Board EDs and Staff](#board-executive-directors-and-staff). Read permissions are granted to a user for an entire
compact or not at all. Data writing and user administration permissions can each be granted to a user per
compact/jurisdiction combination. All of a compact user's permissions are stored in a DynamoDB record that is associated
with their own Cognito user id. That record will be used to generate scopes in the Oauth2 token issued to them on login.

#### Compact Executive Directors and Staff

Compact ED level staff can have permission to read all compact data as well as to create and manage users and their
permissions. They can grant other users the ability to write data for a particular jurisdiction and to create more
users associated with a particular jurisdiction. They can also delete any user within their compact, so long as that
user does not have permissions associated with a different compact.

#### Board Executive Directors and Staff

Board ED level staff can have permission to read all compact data, write data to for their own jurisdiction, and to
create more users that have permissions within their own jurisdiction. They can also delete any user within their
jurisdiction, so long as that user does not have permissions associated with a different compact or jurisdiction.

### Licensee Users

Licensee users permissions are much simpler as compared to Compact Users. Their access is entirely based on identity.
Once their identity has been verified and associated with a licensee in the license data system, they will only have
permission to view system data that is specific to them. They will be able to apply for and renew privileges to practice
across jurisdictions, subject to their eligibility.
