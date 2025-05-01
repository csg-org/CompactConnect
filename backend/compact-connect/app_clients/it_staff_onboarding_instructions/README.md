# CompactConnect Automated License Data Upload Instructions (Beta Release)

## Overview

CompactConnect is a centralized platform that facilitates interstate license recognition for healthcare professionals
through occupational licensing compacts. These compacts allow practitioners with licenses in good standing to work 
across state lines without obtaining additional licenses.

As a state IT department responsible for managing professional license data, your role is crucial in this process. 
This document provides instructions for integrating your existing licensing systems with CompactConnect through its API.

By automating license data uploads, your state will:

- **Ensure Timely Data Synchronization**: Keep the compact database up-to-date with your state's latest license information
- **Reduce Manual Work**: Eliminate the need for manual license data entry by staff
- **Improve Accuracy**: Minimize human error in license data transmission
- **Support Interstate Mobility**: Enable qualified professionals to practice in participating states
- **Meet Compact Obligations**: Fulfill your state's requirements as a compact member

This document outlines the technical process for setting up machine-to-machine authentication and automated license data
uploads to CompactConnect's API. Following these instructions will help you establish a secure, reliable connection 
between your licensing systems and the CompactConnect platform.

## Credential Security

You have received a one-time use link to access your API credentials. After retrieving the credentials, please:

1. Store the credentials securely in a password manager or secrets management system
2. Do not share these credentials with unauthorized personnel
3. Do not hardcode these credentials in source code repositories

> **Important**: If the link provided has already been used when you attempt to access the credentials, please contact the individual who sent the link to you as the credentials will need to be regenerated and sent using another link.

> Likewise, if these credentials are ever accidentally shared or compromised, please inform the CompactConnect team as soon as possible, so the credentials can be deactivated and regenerated to prevent abuse of the system.

The credentials will be sent to you in this format:

```json
{
  "clientId": "<client id>",
  "clientSecret": "<client secret>"
}
```

## Authentication Process for Uploading License Data

Follow these steps to obtain an access token and make requests to the CompactConnect License API:

### Step 1: Generate an Access Token

You must first obtain an access token to authenticate your API requests. The access token will be used in the 
Authorization header of subsequent API calls. While the following curl command demonstrates how to generate a token for
the **beta** environment, you should implement this authentication flow in your application's programming language using
appropriate OAuth/HTTP libraries:

> **Note**: When copying commands, be careful of line breaks. You may need to remove any extra spaces or 
> line breaks that occur when pasting.

```bash
curl --location --request POST 'https://compact-connect-staff-beta.auth.us-east-1.amazoncognito.com/oauth2/token' \
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
- `<jurisdiction>` with your lower-cased two-letter state code (e.g., `ky` for Kentucky)
- `<compact>` with the lower-cased compact abbreviation (`octp` for the 'Occupational Therapy' Compact,
`aslp` for 'Audiology and Speech Language Pathology' Compact, or `coun` for the 'Counseling' Compact)

Example response:
```json
{
  "access_token": "eyJraWQiOiJleGFtcGxlS2V5SWQiLCJhbGciOiJSUzI1NiJ9...",
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

### Step 2: Upload License Data to the Beta Environment

The CompactConnect License API can be called through a POST REST endpoint which takes in a list of license record objects.
The following curl command example demonstrates how to upload license data into the **beta** environment, but you should
implement this API call in your application's programming language using appropriate HTTP libraries. You will need to 
replace the example payload with valid license data that includes the correct license types for your 
specific compact (you can send up to 100 license records per request):

```bash
curl --location --request POST 'https://api.beta.compactconnect.org/v1/compacts/<compact>/jurisdictions/<jurisdiction>/licenses' \
--header 'Authorization: Bearer <access_token>' \
--header 'Content-Type: application/json' \
--data '[{"ssn":"123-45-6789","licenseNumber":"LIC123456","licenseStatusName":"Active","licenseStatus":"active","compactEligibility":"eligible","licenseType":"audiologist","givenName":"Jane","middleName":"Marie","familyName":"Smith","dateOfIssuance":"2023-01-15","dateOfRenewal":"2023-01-15","dateOfExpiration":"2025-01-14","dateOfBirth":"1980-05-20","homeAddressStreet1":"123 Main Street","homeAddressStreet2":"Apt 4B","homeAddressCity":"Louisville","homeAddressState":"KY","homeAddressPostalCode":"40202","emailAddress":"jane.smith@example.com","phoneNumber":"+15555551234","npi":"1234567890"}]'
```

Replace:
- `<access_token>` with the access token from Step 1
- `<compact>` with the lower-cased compact abbreviation (e.g., `aslp`, `octp`, or `coun`)
- `<jurisdiction>` with your lower-cased two-letter state code (e.g., `ky`)
- The example payload shown here with your test license data

### Step 2 Alternative: Upload License Data via CSV File

In addition to calling the POST endpoint, there is also an option to upload license data in a CSV file format.
This method may be preferable for larger datasets or for systems that already generate CSV exports.

For detailed documentation on CSV file uploads, including required fields, formatting requirements, and the upload process, please refer to:
https://github.com/csg-org/CompactConnect/tree/main/backend/compact-connect/docs#machine-to-machine-automated-uploads

## License Data Schema Requirements

For the latest information about the license data field requirements, along with descriptions of each field, please see:
https://github.com/csg-org/CompactConnect/tree/main/backend/compact-connect/docs#field-descriptions

**Important Notes**:
- If `licenseStatus` is "inactive", `compactEligibility` cannot be "eligible"
- `licenseType` must match exactly with one of the valid types for the specified compact
- All date fields must use the `YYYY-MM-DD` format

## Verification that License Records are Uploaded

After submitting license data to the API, you can verify that your records were successfully uploaded by checking the API response:

### 1. Successful Upload
If the API responds with a 200 status code, your request was successful and the license data is being processed
by the CompactConnect System. The response will return the following body:

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
- **502**: Internal Server Error - There was a problem processing your request

### 3. Validation Errors
If your license data fails validation, the API will return a 400 status code with details about the 
validation errors in the response body.

> **Note**: Successful API responses (200 status code) indicate that the license data has been accepted for processing, but 
> actual processing happens asynchronously. The data will be validated and processed by the CompactConnect System after acceptance.

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
- Verify that `licenseType` matches exactly one of the valid types for the compact

## Implementation Recommendations

1. Implement token refresh logic to get a new token before the current one expires
2. Implement error handling for API responses
3. Configure your application to securely store and access the client credentials, do not store the credentials in your 
application code.

## Support and Feedback

If you encounter any issues, have questions, or would like to provide feedback based on your experience working with 
the CompactConnect API, please contact the individual which sent you the credentials.
