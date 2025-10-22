# Compact Connect - technical user guide

This documentation is intended for technical IT staff that plan to integrate with this data system. It will likely grow
as the features of this system grow. For technical documentation of the internal design of the CompactConnect backend,
look [here](./design/README.md).

## Introduction

The Audiology and Speech Language Pathology, Counseling, and Occupational Therapy compact commissions are collectively
building a system to share professional licensure data between their state licensing boards to facilitate participation
in their respective occupational licensure compacts. To date, this system is solely composed of a mock API.

## Table of Contents
- **[How to use the API bulk-upload feature](#how-to-use-the-api-bulk-upload-feature)**
- **[Frequently Asked Questions](#frequently-asked-questions)**
- **[Open API Specification](#open-api-specification)**

## How to use the API bulk-upload feature
[Back to top](#compact-connect---technical-user-guide)

### Generating a CSV export of your license data

Export your license data to a CSV file, formatted as follows:
   - The file must be a utf-8 encoded text format
   - The first line must be a header with column names exactly matching the field names listed in
     [the table below](#field-descriptions).
   - All subsequent lines must be individual licenses.
   - At least all required fields must be present as a column and required fields cannot be empty in any row.
   - Any optional fields may also be included. Optional fields can be left empty in some rows.
   - Order of columns does not matter.
   - String lengths are enforced - exceeding them will cause validation errors
   - Some fields have a set list of allowed values. For those fields, make sure to enter the value exactly, including
     spacing and capitalization

#### Field Descriptions

The following table describes all available fields for the license CSV file. Required fields are marked with an asterisk
(*). Note that our API does not accept `NULL` values - if some of your licenses have no value for an optional field,
leave the field entirely empty. If some of your licenses are missing a required field, those licenses will be rejected.

| Field Name | Description | Format | Example |
|------------|-------------|---------|---------|
| dateOfBirth* | Provider's date of birth | YYYY-MM-DD | 1980-01-31 |
| dateOfExpiration* | License expiration date | YYYY-MM-DD | 2025-12-31 |
| dateOfIssuance* | Date when license was originally issued | YYYY-MM-DD | 2020-01-01 |
| dateOfRenewal | Most recent license renewal date | YYYY-MM-DD | 2023-01-01 |
| familyName* | Provider's family/last name | String (max 100 chars) | Smith |
| givenName* | Provider's given/first name | String (max 100 chars) | John |
| homeAddressCity* | City of provider's home address | String (max 100 chars) | Springfield |
| homeAddressPostalCode* | Postal/ZIP code of provider's home address | String (5-7 chars) | 12345 |
| homeAddressState* | State/province of provider's home address | String (max 100 chars) | IL |
| homeAddressStreet1* | First line of provider's street address | String (max 100 chars) | 123 Main St |
| licenseType* | Type of professional license. Types you provide must be associated with the compact you are uploading for. | One of: `audiologist`, `speech-language pathologist`, `occupational therapist`, `occupational therapy assistant`, `licensed professional counselor` | occupational therapist |
| ssn* | Social Security Number | Format: XXX-XX-XXXX | 123-45-6789 |
| licenseStatus* | Current status of the license. "active" means they are allowed to practice their profession. *Note: licenses will automatically be displayed as `inactive` after their date of expiration, even if the last upload still showed them as `active`.* | One of: `active`, `inactive` | active |
| licenseStatusName | An optional more descriptive name of the license status. | String (max 100 chars) | SUSPENDED |
| compactEligibility* | Whether this license makes the licensee eligible to participate in the compact based on the compact's requirements. Cannot be `eligible` if licenseStatus is `inactive`. *Note: licenses will automatically be displayed as `ineligible` after their date of expiration, even if the last upload still showed them as `eligible`.* | One of: `eligible`, `ineligible` | eligible |
| emailAddress | Provider's email address (optional) | Email (max 100 chars) | john.smith@example.com |
| homeAddressStreet2 | Second line of provider's street address (optional) | String (max 100 chars) | Suite 100 |
| licenseNumber | License number (optional) | String (max 100 chars) | OT12345 |
| middleName | Provider's middle name (optional) | String (max 100 chars) | Robert |
| npi | National Provider Identifier (optional) | 10-digit number | 1234567890 |
| phoneNumber | Provider's phone number (optional) | [ITU-T E.164 format](https://www.itu.int/rec/T-REC-E.164-201011-I/en) (must include country code, no spaces or dashes) | +12025550123 |
| suffix | Provider's name suffix (optional) | String (max 100 chars) | Jr. |

#### Example CSV
```csv
dateOfIssuance,npi,licenseNumber,dateOfBirth,licenseType,familyName,homeAddressCity,middleName,licenseStatus,licenseStatusName,compactEligibility,ssn,homeAddressStreet1,homeAddressStreet2,dateOfExpiration,homeAddressState,homeAddressPostalCode,givenName,dateOfRenewal
2024-06-30,0608337260,A0608337260,2024-06-30,speech-language pathologist,Guðmundsdóttir,Birmingham,Gunnar,active,ACTIVE,eligible,529-31-5408,123 A St.,Apt 321,2024-06-30,oh,35004,Björk,2024-06-30
2024-06-30,0608337260,B0608337260,2024-06-30,audiologist,Scott,Huntsville,Patricia,active,ACTIVE,eligible,529-31-5409,321 B St.,,2024-06-30,oh,35005,Elizabeth,2024-06-30
2024-06-30,0608337260,C0608337260,2024-06-30,speech-language pathologist,毛,Hoover,泽,active,ACTIVE,eligible,529-31-5410,10101 Binary Ave.,,2024-06-30,oh,35006,覃,2024-06-30
2024-06-30,0608337260,D0608337260,2024-06-30,speech-language pathologist,Adams,Tuscaloosa,Michael,inactive,EXPIRED,ineligible,529-31-5411,1AB3 Hex Blvd.,,2024-06-30,oh,35007,John,2024-06-30
2024-06-30,0608337260,E0608337260,2024-06-30,speech-language pathologist,Carreño Quiñones,Montgomery,José,active,ACTIVE_IN_RENEWAL,eligible,529-31-5412,10 Main St.,,2024-06-30,oh,35008,María,2024-06-30
```

### Manual Uploads

1) Request a staff user with permissions you need.
2) Log into CompactConnect with your new user.
3) Navigate to the bulk-upload page to upload your exported CSV. It may take about five minutes for uploaded licenses to
   be fully ingested and appear in the system.

### Machine-to-machine automated uploads

The data system API supports uploading of a large CSV file for asynchronous data ingest, as well as JSON license records
for synchronous data ingest. See the [CompactConnect Automated License Data Upload Instructions](./it_staff_onboarding_instructions.md) for more information.

## Frequently Asked Questions
[Back to top](#compact-connect---technical-user-guide)

### What if we don't have data for an optional field?

If data is not available for an optional field, it must be left empty in the case of CSV data, and in the case of JSON the key must be excluded from the object. Please do not include NULL or similar N/A type values for missing data.

**CSV Example with missing optional fields:**
```csv
dateOfIssuance,npi,licenseNumber,dateOfBirth,licenseType,familyName,homeAddressCity,middleName,licenseStatus,licenseStatusName,compactEligibility,ssn,homeAddressStreet1,homeAddressStreet2,dateOfExpiration,homeAddressState,homeAddressPostalCode,givenName,dateOfRenewal
2024-06-30,,,2024-06-30,speech-language pathologist,Guðmundsdóttir,Birmingham,,active,,eligible,529-31-5408,123 A St.,,2024-06-30,oh,35004,Björk,
```

### What if we don't have data for a required field?

If data is not available for a required field, that particular license record cannot be uploaded into CompactConnect. Required fields must be included or the record will not be accepted. Please do not include NULL or empty values for required fields.

### Can we upload the same licenses multiple times? What if their information changes?

Yes. CompactConnect is designed to automatically detect and track changes to license records over time. When you upload a license record, CompactConnect will determine if this is the first time the license has been uploaded, and create the record. If the license record already exists, CompactConnect will check the differences between the existing record in the system and changes uploaded by the state, and apply the changes accordingly.

### Which of these License values is going to be publicly visible?

The following license fields are publicly visible through CompactConnect's public lookup endpoints:

- Licensee name (given, middle, family, suffix).
- The jurisdiction and compact their license is associated with.
- License status and compact eligibility.
- National Provider Identifier (NPI).

**Fields that are NOT publicly visible include:**
- Social Security Numbers
- Full addresses (street, city, state, postal code)
- Email addresses
- Phone numbers
- Date of birth

### What if I want to receive CompactConnect data back to my state IT system?

CompactConnect has additional security requirements for automatic API retrieval of data from the system. Please see the [Client Signature Authentication documentation](./client_signature_auth.md) for detailed information about implementing request signing for secure data retrieval.

## Open API Specification
[Back to top](#compact-connect---technical-user-guide)

We will maintain the latest api specification here, in [latest-oas30.json](api-specification/latest-oas30.json). You can
use [Swagger.io](https://editor.swagger.io/) to render the json directly or, if you happen to use an IDE that supports
the feature, you can open a Swagger UI view of it by opening up the accompanying
[swagger.html](api-specification/swagger.html) in your browser.

Note that HTTP request headers such as `Content-Type` and `User-Agent` are important to the API and should be
transmitted with HTTP requests. Most of the API only accepts a `Content-Type` of `application/json`.
