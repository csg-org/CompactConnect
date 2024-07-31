# Backend design

Look here for continued documentation of the back-end design, as it progresses.

## License Ingest
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
