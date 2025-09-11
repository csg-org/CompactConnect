#!/usr/bin/env python3
# Quick script to generate some mock data in CSV or JSON format for test environments
# The CSV file can be uploaded into the system using the bulk upload process.
# The JSON file can be used for API testing or other purposes.
#
# Run from 'backend/compact-connect' like:
# bin/generate_mock_license_csv_upload_file.py --count 100 --compact octp --jurisdiction ne --format csv
# bin/generate_mock_license_csv_upload_file.py --count 100 --compact octp --jurisdiction ne --format json
import json
import os
import sys
from csv import DictWriter
from datetime import UTC, datetime, timedelta
from random import choice, randint

from faker import Faker

# We have to do some set-up before we can import everything we need
# Add the provider data lambda runtime to our pythonpath
provider_data_path = os.path.join('lambdas', 'python', 'common')
sys.path.append(provider_data_path)

with open('cdk.json') as context_file:
    _context = json.load(context_file)['context']
JURISDICTIONS = _context['jurisdictions']
COMPACTS = _context['compacts']
LICENSE_TYPES = {compact: [t['name'] for t in types] for compact, types in _context['license_types'].items()}


os.environ['COMPACTS'] = json.dumps(COMPACTS)
os.environ['JURISDICTIONS'] = json.dumps(JURISDICTIONS)
# The environment name has no bearing on the staff user creation process, but we need a value to be set
# for the data model to work.
os.environ['ENVIRONMENT_NAME'] = 'test'

from cc_common.data_model.schema.common import ActiveInactiveStatus, CompactEligibilityStatus  # noqa: E402
from cc_common.data_model.schema.license.api import LicensePostRequestSchema  # noqa: E402

# This will be overridden based on command line arguments
name_faker = None
faker = Faker(['en_US'])

schema = LicensePostRequestSchema()

FIELDS = (
    'ssn',
    'npi',
    'licenseNumber',
    'licenseType',
    'licenseStatus',
    'licenseStatusName',
    'compactEligibility',
    'givenName',
    'middleName',
    'familyName',
    'suffix',
    'dateOfIssuance',
    'dateOfRenewal',
    'dateOfExpiration',
    'dateOfBirth',
    'homeAddressStreet1',
    'homeAddressStreet2',
    'homeAddressCity',
    'homeAddressState',
    'homeAddressPostalCode',
    'emailAddress',
    'phoneNumber',
)


def generate_mock_data_file(
    count, *, compact: str, jurisdiction: str = None, file_format: str = 'csv', ssn_prefix: str, all_active: bool
):
    """Generate mock license data and write it to a file in the specified format."""
    if file_format == 'csv':
        generate_mock_csv_file(
            count, compact=compact, jurisdiction=jurisdiction, ssn_prefix=ssn_prefix, all_active=all_active
        )
    elif file_format == 'json':
        generate_mock_json_file(
            count, compact=compact, jurisdiction=jurisdiction, ssn_prefix=ssn_prefix, all_active=all_active
        )
    else:
        raise ValueError(f'Unsupported format: {file_format}')


def generate_mock_csv_file(count, *, compact: str, jurisdiction: str = None, ssn_prefix: str, all_active: bool):
    """Generate mock license data in CSV format."""
    filename = f'{compact}-{jurisdiction}-mock-data.csv'
    with open(filename, 'w', encoding='utf-8') as data_file:
        writer = DictWriter(data_file, fieldnames=FIELDS)
        writer.writeheader()
        for row in generate_license_records(
            count, compact=compact, jurisdiction=jurisdiction, ssn_prefix=ssn_prefix, all_active=all_active
        ):
            writer.writerow(row)


def generate_mock_json_file(count, *, compact: str, jurisdiction: str = None, ssn_prefix: str, all_active: bool):
    """Generate mock license data in JSON format."""
    licenses = list(
        generate_license_records(
            count, compact=compact, jurisdiction=jurisdiction, ssn_prefix=ssn_prefix, all_active=all_active
        )
    )
    # Remove any fields that are None or empty strings, since API doesn't accept them
    licenses = [{k: v for k, v in license_record.items() if v is not None and v != ''} for license_record in licenses]

    filename = f'{compact}-{jurisdiction}-mock-data.json'
    with open(filename, 'w', encoding='utf-8') as data_file:
        json.dump(licenses, data_file, indent=2, ensure_ascii=False, default=str)

    sys.stdout.write(f'Generated {len(licenses)} license records in {filename}')


def generate_license_records(count, *, compact: str, jurisdiction: str = None, ssn_prefix: str, all_active: bool):
    """Generate a specified number of mock license records."""
    i = 0
    while i < count:
        yield get_mock_license(
            i, compact=compact, jurisdiction=jurisdiction, ssn_prefix=ssn_prefix, all_active=all_active
        )
        i += 1
        if i % 1000 == 0:
            sys.stdout.write(f'Generated {i} records\n')
    sys.stdout.write(f'Final record count: {i}\n')


def get_mock_license(i: int, *, compact: str, jurisdiction: str = None, ssn_prefix: str, all_active: bool) -> dict:
    if jurisdiction is None:
        jurisdiction = faker.state_abbr().lower()
    license_data = {
        #                                              |Zero padded 4 digit int|
        'ssn': f'{ssn_prefix}-{(i // 10_000) % 100:02}-{(i % 10_000):04}',
        # Some have NPI, some don't
        'npi': str(randint(1_000_000_000, 9_999_999_999)) if choice([True, False]) else None,
        # Some have License number, some don't
        'licenseNumber': generate_mock_license_number() if choice([True, False]) else None,
        'licenseType': choice(LICENSE_TYPES[compact]),
        'givenName': name_faker.first_name(),
        'middleName': name_faker.first_name(),
        'familyName': name_faker.last_name(),
        # A few will have a suffix
        'suffix': name_faker.suffix() if randint(0, 10) == 10 else None,
        'homeAddressStreet1': faker.street_address(),
        # Flip a coin, add secondary address line?
        'homeAddressStreet2': faker.secondary_address() if choice([True, False]) else None,
        'homeAddressCity': faker.city(),
        # Some have email addresses, some don't
        'emailAddress': faker.email() if choice([True, False]) else None,
        'phoneNumber': f'+1{randint(1_000_000_000, 9_999_999_999)}',
    }
    license_data = _set_address_state(license_data, jurisdiction)
    license_data = _set_dates_and_statuses(license_data, all_active=all_active)
    return schema.dump(license_data)


def generate_mock_license_number() -> str:
    license_str = ''
    size = randint(5, 20)

    for _ in range(size):
        if choice([True, False]):
            if randint(0, 9) > 2:
                license_str += chr(randint(ord('A'), ord('Z')))
            else:
                license_str += '-'
        else:
            license_str += str(randint(0, 9))
    return license_str


def _set_address_state(license_data: dict, jurisdiction: str) -> dict:
    license_data.update(
        {
            'homeAddressState': jurisdiction,
            'homeAddressPostalCode': faker.zipcode_in_state(state_abbr=jurisdiction.upper()),
        },
    )
    return license_data


def _set_dates_and_statuses(license_data: dict, all_active: bool = False) -> dict:
    date_of_birth = faker.date_of_birth()
    # Issuance between when they were ~22 and ~40 years old, but still in the past
    now = datetime.now(tz=UTC).date()
    date_of_issuance = min(date_of_birth + timedelta(days=randint(22 * 365, 40 * 365)), now - timedelta(days=1))
    # For simplicity, we'll assume that under-70-year-olds are active, over are inactive.
    # Unless all_active is True, then all licenses are active and eligible
    if all_active or date_of_birth + 70 * timedelta(days=365) > now:
        is_active = True
        # We'll have renewal be within the last year, but on or after issuance.
        date_of_renewal = max(now - timedelta(days=randint(1, 365)), date_of_issuance)
        # Expiry, one year from renewal
        date_of_expiry = date_of_renewal + timedelta(days=365)
        compact_eligibility = CompactEligibilityStatus.ELIGIBLE
    elif date_of_birth + 70 * timedelta(days=365) > now:
        is_active = True
        # We'll have renewal be within the last year, but on or after issuance.
        date_of_renewal = max(now - timedelta(days=randint(1, 365)), date_of_issuance)
        # Expiry, one year from renewal
        date_of_expiry = date_of_renewal + timedelta(days=365)
        # Licensees can only be eligible if they are also active
        compact_eligibility = (
            CompactEligibilityStatus.ELIGIBLE if choice([True, False]) else CompactEligibilityStatus.INELIGIBLE
        )
    else:
        is_active = False
        # They renewed at some point in the last 20 years, but on or after their issuance date.
        date_of_renewal = max(date_of_issuance, now - randint(1, 20) * timedelta(days=365))
        # Their license expired a year after renewal, but no later than yesterday.
        date_of_expiry = min(date_of_renewal + timedelta(days=365), now - timedelta(days=1))
        compact_eligibility = CompactEligibilityStatus.INELIGIBLE
    license_data.update(
        {
            'licenseStatus': ActiveInactiveStatus.ACTIVE if is_active else ActiveInactiveStatus.INACTIVE,
            'compactEligibility': compact_eligibility,
            'dateOfBirth': date_of_birth,
            'dateOfIssuance': date_of_issuance,
            'dateOfRenewal': date_of_renewal,
            'dateOfExpiration': date_of_expiry,
        },
    )

    # Flip a coin, include a license status name?
    active_status_names = ['ACTIVE', 'ACTIVE_IN_RENEWAL']
    inactive_status_names = ['INACTIVE', 'SUSPENDED', 'EXPIRED', 'REVOKED', 'ON_PROBATION']
    if choice([True, False]):
        license_data['licenseStatusName'] = choice(active_status_names if is_active else inactive_status_names)
    return license_data


def _initialize_name_faker(us_names_only: bool = False):
    """Initialize the name_faker based on localization preference."""
    global name_faker
    if us_names_only:
        # Only use US English names
        name_faker = Faker(['en_US'])
    else:
        # We'll grab three different localizations to provide a variety of names/characters
        name_faker = Faker(['en_US', 'ja_JP', 'es_MX'])


if __name__ == '__main__':
    import logging
    from argparse import ArgumentParser

    logging.basicConfig()

    parser = ArgumentParser(description='Generate mock license data in CSV or JSON format')
    parser.add_argument('--count', help='The count of licenses to generate', required=True, type=int)
    parser.add_argument('--compact', help='The compact these licenses will be for', required=True, choices=COMPACTS)
    parser.add_argument(
        '-j',
        '--jurisdiction',
        help='The jurisdiction these licenses will be for',
        required=False,
        choices=JURISDICTIONS,
    )
    parser.add_argument(
        '--format',
        help='Output format for the generated data',
        choices=['csv', 'json'],
        default='csv',
        required=False,
    )
    parser.add_argument(
        '--us-names-only',
        help='Use only US English names instead of mixed localizations',
        action='store_true',
        required=False,
    )
    parser.add_argument(
        '--ssn-prefix',
        help='Three-digit prefix for SSN generation (default: 000)',
        default='000',
        required=False,
    )
    parser.add_argument(
        '--all-active',
        help='all all licenses to be active and eligible',
        action='store_true',
        required=False,
    )

    args = parser.parse_args()
    _initialize_name_faker(args.us_names_only)

    generate_mock_data_file(
        args.count,
        compact=args.compact,
        jurisdiction=args.jurisdiction,
        file_format=args.format,
        ssn_prefix=args.ssn_prefix,
        all_active=args.all_active,
    )
