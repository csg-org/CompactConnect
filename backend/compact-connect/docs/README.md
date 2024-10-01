# Compact Connect - technical user guide

This documentation is intended for technical IT staff that plan to integrate with this data system. It will likely grow
as the features of this system grow. For technical documentation of the internal design of the CompactConnect backend,
look [here](./design/README.md).

## Introduction

The Audiology and Speech Language Pathology, Counseling, and Occupational Therapy compact commissions are collectively building a system to share professional licensure data between their state licensing boards to facilitate participation in their respective occupational licensure compacts. To date, this system is solely composed of a mock API.

## Table of Contents
- **[Mock API](#mock-api)**
- **[How to use the API bulk-upload feature](#how-to-use-the-api-bulk-upload-feature)**
- **[Open API Specification](#open-api-specification)**

## Mock API
[Back to top](#compact-connect---technical-user-guide)

This system includes a mock license data API that has two functions: A synchronous license data validation endpoint that can allow users to test their data against the expected data schema and an asynchronous bulk upload function that can allow for uploading a large file to be asynchronously processed. Currently, neither endpoint has any back-end processing and data is immediately discarded. If you wish to test out these endpoints, **please make a point to only send artificial data**.

## How to use the API bulk-upload feature
[Back to top](#compact-connect---technical-user-guide)

### Generating a CSV export of your license data

Export your license data to a CSV file, formatted as follows:
   1) The file must be a utf-8 encoded text format
   2) The first line must be a header with column names exactly matching the field names listed in the `POST /v1/compacts/{compact}/jurisdictions/{jurisdiction}/licenses` request body schema.
   3) At least all required fields must be present as a column. Any optional fields may also be included. Order of columns does not matter.
   4) All subsequent lines must be individual licenses.
   5) If optional fields are included, their values may be omitted in some rows by leaving the position empty.

#### Example CSV
```csv
dateOfIssuance,npi,dateOfBirth,licenseType,familyName,homeAddressCity,middleName,status,ssn,homeAddressStreet1,homeAddressStreet2,dateOfExpiration,homeAddressState,homeAddressPostalCode,givenName,dateOfRenewal
2024-06-30,0608337260,2024-06-30,speech-language pathologist,Guðmundsdóttir,Birmingham,Gunnar,active,529-31-5408,123 A St.,Apt 321,2024-06-30,oh,35004,Björk,2024-06-30
2024-06-30,0608337260,2024-06-30,audiologist,Scott,Huntsville,Patricia,active,529-31-5409,321 B St.,,2024-06-30,oh,35005,Elizabeth,2024-06-30
2024-06-30,0608337260,2024-06-30,speech-language pathologist,毛,Hoover,泽,active,529-31-5410,10101 Binary Ave.,,2024-06-30,oh,35006,覃,2024-06-30
2024-06-30,0608337260,2024-06-30,speech-language pathologist,Adams,Tuscaloosa,Michael,inactive,529-31-5411,1AB3 Hex Blvd.,,2024-06-30,oh,35007,John,2024-06-30
2024-06-30,0608337260,2024-06-30,speech-language pathologist,Carreño Quiñones,Montgomery,José,active,529-31-5412,10 Main St.,,2024-06-30,oh,35008,María,2024-06-30
```

### Manual Uploads

1) Request a staff user with permissions you need.
2) Log into CompactConnect with your new user.
3) Navigate to the bulk-upload page to upload your exported CSV. It may take about five minutes for uploaded licenses to be fully ingested and appear in the system.

### Machine-to-machine automated uploads

The data system API supports uploading of a large CSV file for asynchronous data ingest. The feature involves using two endpoints, which are described in the [Open API Specification](#open-api-specification) above. To upload a file for asynchronous data ingest perform the following steps:
1) Request a dedicated client for your automated integration. Note that there may be some lead time for that request.
2) Authenticate your client using the **OAuth2.0 client-credentials-grant** to obtain an access token for the API.
3) Call the `GET /v1/compacts/{compact}/jurisdictions/{jurisdiction}/licenses/bulk-upload` endpoint to receive an upload URL and upload fields to use when uploading your file.
4) `POST` to the provided url, with `Content-Type: multipart/form-data`, providing all the fields returned from the `GET` endpoint as form-data fields in addition to your file.

For your convenience, use of this feature is included in the [Postman Collection](./postman/postman-collection.json).

## Open API Specification
[Back to top](#compact-connect---technical-user-guide)

We will maintain the latest api specification here, in [latest-oas30.json](api-specification/latest-oas30.json). You can
use [Swagger.io](https://editor.swagger.io/) to render the json directly or, if you happen to use an IDE that supports
the feature, you can open a Swagger UI view of it by opening up the accompanying [swagger.html](api-specification/swagger.html) in your browser.

### Change summary:
- 2024-08-21: First API version release
- 2024-09-03: Proposed addition of staff-user API
