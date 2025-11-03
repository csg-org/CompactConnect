# CompactConnect Automated License Data Upload Instructions (Beta Release)

## Overview

CompactConnect is a centralized platform that facilitates interstate license recognition for healthcare professionals
through occupational licensing compacts. These compacts allow practitioners with licenses in good standing to work
across state lines without obtaining additional licenses.

As a state IT department responsible for managing professional license data, your role is crucial in this process.
This document provides instructions for integrating your existing licensing systems with CompactConnect through its API.

By automating license data uploads, your state will:

- **Ensure Timely Data Synchronization**: Keep the compact database up-to-date with your state's latest license
  information
- **Reduce Manual Work**: Eliminate the need for manual license data entry by staff
- **Improve Accuracy**: Minimize human error in license data transmission
- **Support Interstate Mobility**: Enable qualified professionals to practice in participating states
- **Meet Compact Obligations**: Fulfill your state's requirements as a compact member

This document outlines the technical process for setting up machine-to-machine authentication and automated license data
uploads to CompactConnect's API, as well as common strategies for uploading data into the system. 
Following these instructions will help you establish a secure, reliable connection
between your licensing systems and the CompactConnect platform.

## Credential Security

This article assumes you have received a one-time use link to access your API credentials, along with an email containing contextual
information about your integration. After retrieving the credentials, please:

1. Store the credentials securely in a password manager or secrets management system
2. Do not share these credentials with unauthorized personnel
3. Do not hardcode these credentials in source code repositories
4. Keep the contextual information (compact, state, URLs) for reference during integration

> **Important**: If the link provided has already been used when you attempt to access the credentials, please contact
> the individual who sent the link to you as the credentials will need to be regenerated and sent using another link.
>
> Likewise, if these credentials are ever accidentally shared or compromised, please inform the CompactConnect team as
> soon as possible, so the credentials can be deactivated and regenerated to prevent abuse of the system.

The credentials will be sent to you in this format:

```json
{
  "clientId": "<client id>",
  "clientSecret": "<client secret>"
}
```

You will also receive an email with the following contextual information:
- **Compact**: The full name of the compact (e.g., "Occupational Therapy", "Audiology and Speech Language Pathology")
- **State**: Your state's postal abbreviation (e.g., "KY", "LA")
- **Auth URL**: The authentication endpoint URL
- **License Upload URL**: The API endpoint for uploading license data

## Authentication Process for Uploading License Data

Follow these steps to obtain an access token and make requests to the CompactConnect License API:

### Step 1: Generate an Access Token

You must first obtain an access token to authenticate your API requests. The access token will be used in the
Authorization header of subsequent API calls. While the following curl command demonstrates how to generate a token for
the **beta** environment, you should implement this authentication flow in your application's programming language using
appropriate HTTPS request libraries:

> **Note**: When copying commands, be careful of line breaks. You may need to remove any extra spaces or
> line breaks that occur when pasting.

```bash
curl --location --request POST '<authUrl>' \
--header 'Content-Type: application/x-www-form-urlencoded' \
--header 'Accept: application/json' \
--data-urlencode 'grant_type=client_credentials' \
--data-urlencode 'client_id=<clientId>' \
--data-urlencode 'client_secret=<clientSecret>' \
--data-urlencode 'scope=<jurisdiction>/<compact>.write'
```

Replace:
- `<clientId>` with your client ID
- `<clientSecret>` with your client secret
- `<jurisdiction>` with your lower-cased two-letter state code (e.g., `ky` for Kentucky) - this information was provided
  in the email
- `<compact>` with the lower-cased compact abbreviation (`octp` for the 'Occupational Therapy' Compact,
  `aslp` for 'Audiology and Speech Language Pathology' Compact, or `coun` for the 'Counseling' Compact) - this
  information was provided in the email

Example response:
```json
{
  "access_token": "<your-access-token>",
  "expires_in": 900,
  "token_type": "Bearer"
}
```

For more information about this authentication process, please see the following
AWS documentation: https://docs.aws.amazon.com/cognito/latest/developerguide/token-endpoint.html

**Important Notes**:
- For security reasons, the access token is valid for 15 minutes from the time it is generated (900 seconds)
- Your application should request a new token before the current one expires
- Store the `access_token` value for use in API requests

### Step 2: Upload License Data to the Beta Environment (JSON POST Endpoint)

The CompactConnect License API can be called through a POST REST endpoint which takes in a list of license record
objects. The following curl command example demonstrates how to upload license data into the **beta** environment, but
you should implement this API call in your application's programming language using appropriate HTTPS request libraries.
You will need to replace the example payload with valid license data that includes the correct license types for your
specific compact. See the
[Technical User Guide](./README.md) for more details about API use:

```bash
curl --location --request POST 'https://state-api.beta.compactconnect.org/v1/compacts/<compact>/jurisdictions/<jurisdiction>/licenses' \
--header 'Authorization: Bearer <access_token>' \
--header 'Content-Type: application/json' \
--header 'User-Agent: <your-app-name>/<version> (<contact-email-or-url>)' \
--data '[
  {
    "ssn":"123-45-6789",
    "licenseNumber":"LIC123456",
    "licenseStatusName":"Active",
    "licenseStatus":"active",
    "compactEligibility":"eligible",
    "licenseType":"audiologist",
    "givenName":"Jane",
    "middleName":"Marie",
    "familyName":"Smith",
    "dateOfIssuance":"2023-01-15",
    "dateOfRenewal":"2023-01-15",
    "dateOfExpiration":"2025-01-14",
    "dateOfBirth":"1980-05-20",
    "homeAddressStreet1":"123 Main Street",
    "homeAddressStreet2":"Apt 4B",
    "homeAddressCity":"Louisville",
    "homeAddressState":"KY",
    "homeAddressPostalCode":"40202",
    "emailAddress":"jane.smith@example.com",
    "phoneNumber":"+15555551234",
    "npi":"1234567890"
  }
]'
```

Replace:
- `<access_token>` with the access token from Step 1
- `<compact>` with the lower-cased compact abbreviation (e.g., `aslp`, `octp`, or `coun`) - this information was
  provided in the email.
- `<jurisdiction>` with your lower-cased two-letter state code (e.g., `ky`) - this information was provided in the email
- The `User-Agent` header value with your own application name, version, and contact information
- The example payload shown here with your test license data

Note: The URL was provided during onboarding and is already configured for your jurisdiction and compact.

> **Note**: While the JSON API accepts arrays of up to 100 records, some states have found it's easier to send one license record per request. See the [Common Upload Strategies](#common-upload-strategies-json-vs-csv) section below for detailed guidance.

### Step 2 Alternative: Upload License Data via CSV File

In addition to calling the POST endpoint, there is also an option to upload license data in a CSV file format.
This method may be preferable for the initial data upload or for systems that already generate CSV exports.

#### CSV Upload Process

The CSV upload process involves two steps:

**Step 2a: Get Upload Configuration**

First, obtain the upload URL and required form fields:

```bash
curl --location --request GET 'https://state-api.beta.compactconnect.org/v1/compacts/<compact>/jurisdictions/<jurisdiction>/licenses/bulk-upload' \
--header 'Authorization: Bearer <access_token>' \
--header 'Accept: application/json' \
--header 'User-Agent: <your-app-name>/<version> (<contact-email-or-url>)'
```

Replace:
- `<access_token>` with the access token from Step 1
- `<compact>` with the lower-cased compact abbreviation (e.g., `aslp`, `octp`, or `coun`) - this information was
  provided in the email.
- `<jurisdiction>` with your lower-cased two-letter state code (e.g., `ky`) - this information was provided in the email
- The `User-Agent` header value with your own application name, version, and contact information

This will return a response like:
```json
{
  "upload": {
    "url": "<url>",
    "fields": {
      "key": "<object key>",
      "x-amz-algorithm": "AWS4-HMAC-SHA256",
      "x-amz-credential": "<credentials>",
      "x-amz-date": "20240101T000000Z",
      "x-amz-security-token": "<token>",
      "policy": "<policy>",
      "x-amz-signature": "<signature>",
    }
  }
}
```

**Step 2b: Upload Your CSV File**

Using the URL and fields from Step 2a, upload your CSV file. **Important**: You must include all the fields from the response, plus a `content-type` field set to `text/csv`, and your file:

```bash
curl --location --request POST '<upload_url_from_step_2a>' \
--form 'key="<key_from_response>"' \
--form 'x-amz-algorithm="<algorithm_from_response>"' \
--form 'x-amz-credential="<credential_from_response>"' \
--form 'x-amz-date="<date_from_response>"' \
--form 'x-amz-signature="<signature_from_response>"' \
--form 'x-amz-security-token="<token_from_response>"' \
--form 'policy="<policy_from_response>"' \
--form 'content-type="text/csv"' \
--form 'file=@"/path/to/your/licenses.csv"'
```

**IMPORTANT**: The order of form fields matters for S3 uploads. Ensure the `file` field comes last, and all AWS signature fields are included as shown.

Note that, when using the bulk-upload feature, processing of licenses is asynchronous, and so feedback on invalid
licenses is slow. The operational reports contact email will be sent a nightly report with a sample of validation
errors, if there were any, from the day's uploads. For faster feedback, we highly recommend that states with the 
capability integrate with the JSON endpoint described above in step 2 instead, for more efficient communication and feedback. 

## License Data Schema Requirements

For the latest information about the license data field requirements, along with descriptions of each field, please see the field description
section of [the technical user guide](./README.md#field-descriptions).

See the API specification at [Open API Specification](./README.md#open-api-specification) for more API schema details.

For your convenience, use of this feature is included in the [Postman Collection](./postman/postman-collection.json).

**Important Notes**:
- If `licenseStatus` is "inactive", `compactEligibility` cannot be "eligible"
- `licenseType` must match exactly with one of the valid types for the specified compact
- All date fields must use the `YYYY-MM-DD` format
- The API does not accept `null` values. For optional fields with no value, omit the field or leave it empty in CSV.
- For CSV uploads, SSNs must be unique within a single file. Do not include multiple rows with the same `ssn` in one upload. If duplicate SSNs are sent within the same file, the first row will be processed, but all other duplicate rows will be rejected.
- For JSON uploads, SSNs must be unique within a single request payload (array). Do not include duplicate `ssn` values in the same batch. Attempting to do so will cause the entire request to be rejected.

## Common Upload Strategies: JSON vs CSV

Based on feedback from state IT departments that have successfully integrated with CompactConnect, the following approaches have been used for different use cases:

### Bulk Uploads: CSV Methods

For states that need to upload a large number of existing license records (typically during initial onboarding), or systems that are set up to primarily export data in CSV formats, CSV upload has been the preferred approach. 

Note that CSV uploads are an asynchronous process, meaning that **there may still be validation errors in the data even if the file is uploaded successfully.** CompactConnect will process all the valid records in the CSV file, and will report on any licenses in the file that could not be processed due to validation error. In order to receive data validation error notifications from CompactConnect, your state administrator must configure your email address as a point of contact for operation support. See [System Configuration section of the Staff User Documentation](../../../staff-user-documentation/README.md#system-configuration)

#### Manual CSV uploads
If a state IT department intends to use the CSV upload process only once for the initial upload, or their system is not able to process automated uploads, consider using the **web-based CSV upload interface**. Your compact state administrator will need to create a staff user account for you with **Write permissions**, which you will use to access the application and upload the data, see [Data Upload section of the Staff User Documentation](../../../staff-user-documentation/README.md#data-upload)

#### API CSV uploads
If a state IT department intends to use the CSV upload process continuously for every upload of new and updated data into the system, consider integrating your system with the CSV Bulk Upload API as described above.

### Ongoing Updates: JSON Method

For ongoing license updates after the initial bulk upload, consider using the **JSON API**. The JSON API supports processing up to 100 license records per request, but if any records within the batch are invalid, **the entire batch will be rejected**. Some states have found that sending one license record per JSON request (rather than batching multiple records) makes it easier to track issues within their data.

The JSON API is not recommended for performing initial massive bulk uploads, as there are rate limits in place that will throttle high volumes of requests from the same IT department.


## Verification that License Records are Uploaded

After submitting license data to the JSON API, you can verify that your records were successfully uploaded by checking the API response. See [Troubleshooting Common Issues](it_staff_onboarding_instructions.md#troubleshooting-common-issues)

For CSV uploads, if your email address is configured to receive the upload error reports, you will receive an email in the event that the license data had any errors. See [System Configuration section of the Staff User Documentation](../../../staff-user-documentation/README.md#system-configuration) for setting up contacts to receive these error notifications.

### 1. Successful Upload
If the API responds with a 200 status code, your request was accepted and basic validation passed (e.g., schema and
field-level checks). The data is then queued for asynchronous ingest and business processing. The response will be:

```json
{
  "message": "OK"
}
```

### 2. Error Responses
If you receive an error response, check the status code and message:
- **400**: Bad Request - Your request data is invalid (check the response body for validation errors)
- **401**: Unauthorized - Your access token is invalid or expired
- **403**: Forbidden - Your app client doesn't have permission to upload to the specified jurisdiction/compact
           Also note that some firewall rules require a valid `User-Agent` header; omitting it will result in 403.
- **415**: Unsupported Media Type - Ensure `Content-Type: application/json` is set for this endpoint.
- **502**: Internal Server Error - There was a problem processing your request

### 3. Validation Errors
If your license data fails validation, the API will return a 400 status code with details about the
validation errors in the response body.

> **Note**: 200 status code means your request passed synchronous validation and was accepted for processing. Ingest and
> downstream processing are asynchronous and may take several minutes.

## Retrieving Data from CompactConnect

In addition to uploading license data, state IT departments can retrieve privilege data from CompactConnect to integrate with their own systems. The State API provides two primary endpoints for data retrieval: a query endpoint for bulk retrieval of updated records, and a get endpoint for retrieving details about specific providers.

> **Important**: Data retrieval endpoints require additional security through request signature authentication. Please see the [Client Signature Authentication documentation](./client_signature_auth.md) for detailed information about implementing request signing before attempting to use these endpoints.

### Required OAuth Scope for Data Retrieval

To retrieve data from the CompactConnect API, you must request the `<compact>/readGeneral` OAuth scope when generating your access token. This scope grants read access to provider and privilege data for your jurisdiction.

If your integration needs both to upload license data AND retrieve privilege data within the same access token, you can request multiple OAuth scopes at the same time by separating them with a space in the scope parameter:

```bash
curl --location --request POST '<authUrl>' \
--header 'Content-Type: application/x-www-form-urlencoded' \
--header 'Accept: application/json' \
--data-urlencode 'grant_type=client_credentials' \
--data-urlencode 'client_id=<clientId>' \
--data-urlencode 'client_secret=<clientSecret>' \
--data-urlencode 'scope=<jurisdiction>/<compact>.write <compact>/readGeneral'
```

Replace:
- `<clientId>` with your client ID
- `<clientSecret>` with your client secret
- `<jurisdiction>` with your lower-cased two-letter state code (e.g., `ky`)
- `<compact>` with the lower-cased compact abbreviation (`aslp`, `octp`, or `coun`)

**OAuth Scope Reference**:
- `<jurisdiction>/<compact>.write` - Required for uploading license data
- `<compact>/readGeneral` - Required for retrieving provider and privilege data

The access token you receive will be authorized for both operations. If this request fails, your credentials may have not been granted the ability to grant the read scope for the specific compact when they were created. Reach out to your CompactConnect representative to request this permission if needed.

### Query Providers Endpoint

The query endpoint allows you to retrieve a list of providers who have privileges in your jurisdiction, filtered by when their records were last updated. This is useful for identifying which providers have had changes that need to be synchronized to your systems.

**Endpoint**: `POST /v1/compacts/<compact>/jurisdictions/<jurisdiction>/licenses/query`

**Request Body**:
```json
{
  "query": {
    "startDateTime": "2024-10-01T00:00:00Z",
    "endDateTime": "2024-10-07T23:59:59Z"
  }
}
```

**Example Response**:
```json
{
  "query": {
    "startDateTime": "2024-10-01T00:00:00Z",
    "endDateTime": "2024-10-07T23:59:59Z"
  },
  "sorting": {
    "direction": "ascending"
  },
  "providers": [
    {
      "providerId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "type": "provider",
      "compact": "aslp",
      "dateOfUpdate": "2024-10-05T14:32:10.123Z",
      "licenseJurisdiction": "ky",
      "licenseStatus": "active",
      "compactEligibility": "eligible",
      "givenName": "Jane",
      "middleName": "Marie",
      "familyName": "Smith",
      "birthMonthDay": "05-20",
      "dateOfExpiration": "2025-01-14",
      "jurisdictionUploadedLicenseStatus": "active",
      "jurisdictionUploadedCompactEligibility": "eligible",
      "privilegeJurisdictions": ["oh", "tn", "va"]
    }
  ],
  "pagination": {
    "lastKey": "eyJwayI6InByb3ZpZGVyI..."
  }
}
```

**Response Fields**:
- `providerId`: Unique identifier for the provider in CompactConnect
- `dateOfUpdate`: When the provider record was last updated
- `privilegeJurisdictions`: Array of jurisdictions where the provider currently has active privileges
- `pagination.lastKey`: Token to use for retrieving the next page of results (include in next request's `pagination.lastKey` field)

#### Pagination

When querying for providers, results are paginated. To retrieve additional pages:

1. Check the response for the `pagination.lastKey` field
2. If present, include it in your next request's `pagination.lastKey` to get the next page
3. Continue until `pagination.lastKey` is not present in the response

**Example of retrieving next page**:
```json
{
  "query": {
    "startDateTime": "2024-10-01T00:00:00Z",
    "endDateTime": "2024-10-07T23:59:59Z"
  },
  "pagination": {
    "lastKey": "eyJwayI6InByb3ZpZGVyI..."
  }
}
```

### Get Provider Details Endpoint

The get provider endpoint returns detailed information about a specific provider's privileges in your jurisdiction.

**Endpoint**: `GET /v1/compacts/<compact>/jurisdictions/<jurisdiction>/licenses/{providerId}`

**Example Response**:
```json
{
  "privileges": [
    {
      "type": "statePrivilege",
      "providerId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "privilegeId": "priv_xyz123",
      "compact": "aslp",
      "jurisdiction": "oh",
      "licenseType": "audiologist",
      "status": "active",
      "compactEligibility": "eligible",
      "dateOfIssuance": "2023-01-15",
      "dateOfRenewal": "2023-01-15",
      "dateOfExpiration": "2025-01-14",
      "dateOfUpdate": "2024-10-05T14:32:10.123Z",
      "licenseJurisdiction": "ky",
      "licenseStatus": "active",
      "givenName": "Jane",
      "middleName": "Marie",
      "familyName": "Smith",
      "npi": "1234567890",
      "licenseNumber": "LIC123456",
      "licenseStatusName": "Active"
    }
  ],
  "providerUIUrl": "https://app.beta.compactconnect.org/aslp/Licensing/a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**Response Fields**:
- `privileges`: Array of privilege records for this provider in your jurisdiction (typically one per license type)
- `providerUIUrl`: Direct link to view this provider's details in the CompactConnect web interface
- Each privilege record combines data from both the privilege and the underlying license record

**Note**: A provider may have multiple privileges in your jurisdiction if they hold multiple license types (e.g., both audiologist and speech-language pathologist licenses).

## Troubleshooting Common Issues

### 1. "Unknown error parsing request body"
- Ensure your JSON data is properly formatted with no trailing commas
- Check that all quoted strings use double quotes, not single quotes
- Verify that your payload is a valid JSON array, even for a single license record

### 2. Authentication errors (401)
- Your access token might have expired - generate a new one
- Make sure you're including the "Bearer" prefix before the token in the Authorization header

### 3. Validation errors (400)
- Check the error response for specific validation issues
- Ensure all required fields are present and formatted correctly

```json
{
  "message": "Invalid license records in request. See errors for more detail.",
  "errors": {
    "0": {
      "licenseType": ["Missing data for required field."],
    },
    "1": {
      "dateOfBirth": ["Not a valid date."],
      "compactEligibility": ["Must be one of: eligible, ineligible."]
    }
  }
}
```

## Implementation Recommendations

1. Implement token refresh logic to get a new token before the current one expires
2. Implement error handling for API responses
3. Configure your application to securely store and access the client credentials, **do not store the credentials in your
application code.**

## Support and Feedback

If you encounter any issues, have questions, or would like to provide feedback based on your experience working with
the CompactConnect API, please contact the individual which sent you the credentials.
