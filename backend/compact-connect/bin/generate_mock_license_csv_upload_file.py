#!/usr/bin/env python3
# Quick script to generate some mock data in a csv file for test environments
# The csv file must then be uploaded into the system using the bulk upload process.
#
# Run from 'backend/compact-connect' like:
# bin/generate_mock_license_csv_upload_file.py --count 100 --compact octp --jurisdiction ne
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

from cc_common.data_model.schema.license.api import LicensePostRequestSchema  # noqa: E402

# We'll grab three different localizations to provide a variety of names/characters
name_faker = Faker(['en_US', 'ja_JP', 'es_MX'])
faker = Faker(['en_US'])

schema = LicensePostRequestSchema()

FIELDS = (
    'ssn',
    'npi',
    'licenseNumber',
    'licenseType',
    'status',
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


def generate_mock_csv_file(count, *, compact: str, jurisdiction: str = None):
    with open(f'{compact}-{jurisdiction}-mock-data.csv', 'w', encoding='utf-8') as data_file:
        writer = DictWriter(data_file, fieldnames=FIELDS)
        writer.writeheader()
        for row in generate_csv_rows(count, compact=compact, jurisdiction=jurisdiction):
            writer.writerow(row)


def generate_csv_rows(count, *, compact: str, jurisdiction: str = None) -> dict:
    i = 0
    while i < count:
        yield get_mock_license(i, compact=compact, jurisdiction=jurisdiction)
        i += 1
        if i % 1000 == 0:
            sys.stdout.write(f'Generated {i} records')
    sys.stdout.write(f'Final record count: {i}\n')


def get_mock_license(i: int, *, compact: str, jurisdiction: str = None) -> dict:
    if jurisdiction is None:
        jurisdiction = faker.state_abbr().lower()
    license_data = {
        #                                                          |Zero padded 4 digit int|
        'ssn': f'{(i // 1_000_000) % 1000:03}-{(i // 10_000) % 100:02}-{(i % 10_000):04}',
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
    license_data = _set_dates(license_data)
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


def _set_dates(license_data: dict) -> dict:
    date_of_birth = faker.date_of_birth()
    # Issuance between when they were ~22 and ~40 years old, but still in the past
    now = datetime.now(tz=UTC).date()
    date_of_issuance = min(date_of_birth + timedelta(days=randint(22 * 365, 40 * 365)), now - timedelta(days=1))
    # For simplicity, we'll assume that under-70-year-olds are active, over are inactive.
    if date_of_birth + 70 * timedelta(days=365) > now:
        active = True
        # We'll have renewal be within the last year, but on or after issuance.
        date_of_renewal = max(now - timedelta(days=randint(1, 365)), date_of_issuance)
        # Expiry, one year from renewal
        date_of_expiry = date_of_renewal + timedelta(days=365)
    else:
        active = False
        # They renewed at some point in the last 20 years, but on or after their issuance date.
        date_of_renewal = max(date_of_issuance, now - randint(1, 20) * timedelta(days=365))
        # Their license expired a year after renewal, but no later than yesterday.
        date_of_expiry = min(date_of_renewal + timedelta(days=365), now - timedelta(days=1))
    license_data.update(
        {
            'status': 'active' if active else 'inactive',
            'dateOfBirth': date_of_birth,
            'dateOfIssuance': date_of_issuance,
            'dateOfRenewal': date_of_renewal,
            'dateOfExpiration': date_of_expiry,
        },
    )
    return license_data


if __name__ == '__main__':
    import logging
    from argparse import ArgumentParser

    logging.basicConfig()

    parser = ArgumentParser(description='Generate mock license data for upload')
    parser.add_argument('--count', help='The count of licenses to generate', required=True, type=int)
    parser.add_argument('--compact', help='The compact these licenses will be for', required=True, choices=COMPACTS)
    parser.add_argument(
        '-j',
        '--jurisdiction',
        help='The jurisdiction these licenses will be for',
        required=False,
        choices=JURISDICTIONS,
    )

    args = parser.parse_args()
    generate_mock_csv_file(args.count, compact=args.compact, jurisdiction=args.jurisdiction)
