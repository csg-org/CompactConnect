# Compact Connect - technical user guide

This documentation is intended for technical IT staff that plan to integrate with this data system. It will likely grow as the features of this system grow.

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

The data system API supports uploading of a large CSV file for asynchronous data ingest. The feature involves using two endpoints, which are described in the [Open API Specification](#open-api-specification) above. To upload a file for asynchronous data ingest perform the following steps:
1) Export your license data to a CSV file, formatted as follows:
   1) The file must be a utf-8 encoded text format
   2) The first line must be a header with column names exactly matching the field names listed in the `POST /v0/boards/:jurisdiction/licenses` request body schema.
   3) At least all required fields must be present as a column. Any optional fields may also be included. Order of columns does not matter.
   4) All subsequent lines must be individual licenses.
   5) If optional fields are included, their values may be omitted in some rows by leaving the position empty.
2) Call the `GET /v0/boards/:jurisdiction/licenses-noauth/bulk-upload` endpoint to receive an upload URL and upload fields to use when uploading your file.
3) `POST` to the provided url, with `Content-Type: multipart/form-data`, providing all the fields returned from the `GET` endpoint as form-data fields in addition to your file.

For your convenience, use of this feature is included in the [Postman Collection](./postman/postman-collection.json). Note that, as we build features, we will transition away from the `/licenses-noauth` path to the `/licenses` path and begin requiring authentication before implementing any real data ingest processes.

### Example CSV
```csv
date_of_issuance,npi,date_of_birth,license_type,family_name,home_state_city,middle_name,license_status,ssn,home_state_street_1,home_state_street_2,date_of_expiration,home_state_postal_code,given_name,date_of_renewal
2024-06-30,0608337260,2024-06-30,speech language,Guðmundsdóttir,Birmingham,Gunnar,active,529-31-5408,123 A St.,Apt 321,2024-06-30,35004,Björk,2024-06-30
2024-06-30,0608337260,2024-06-30,audiology,Scott,Huntsville,Patricia,active,529-31-5409,321 B St.,,2024-06-30,35005,Elizabeth,2024-06-30
2024-06-30,0608337260,2024-06-30,speech language,毛,Hoover,泽,active,529-31-5410,10101 Binary Ave.,,2024-06-30,35006,覃,2024-06-30
2024-06-30,0608337260,2024-06-30,speech language,Adams,Tuscaloosa,Michael,inactive,529-31-5411,1AB3 Hex Blvd.,,2024-06-30,35007,John,2024-06-30
2024-06-30,0608337260,2024-06-30,speech language,Carreño Quiñones,Montgomery,José,active,529-31-5412,10 Main St.,,2024-06-30,35008,María,2024-06-30
```

## Open API Specification
[Back to top](#compact-connect---technical-user-guide)

We will maintain the latest api specification here, in [latest-oas30.json](api-specification/latest-oas30.json). You can open a Swagger UI view of it by opening up the accompanying [swagger.html](api-specification/swagger.html) in your browser.

### Change summary:
- 2024-06-03: Early draft specification
