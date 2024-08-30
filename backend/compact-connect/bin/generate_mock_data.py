#!/usr/bin/env python3
# Quick script to generate some mock data for test environments
#
# Run from 'backend/compact-connect' like:
# bin/generate_mock_data.py --count 100 --compact octp --jurisdiction ne
import os
import sys

import json
from csv import DictWriter
from datetime import timedelta, UTC, datetime
from random import randint, choice

from faker import Faker

# We have to do some set-up before we can import everything we need
# Add the provider data lambda runtime to our pythonpath
provider_data_path = os.path.join('lambdas', 'provider-data-v1')
sys.path.append(provider_data_path)

with open('cdk.json', 'r') as context_file:
    _context = json.load(context_file)['context']
JURISDICTIONS = _context['jurisdictions']
COMPACTS = _context['compacts']
LICENSE_TYPES = _context['license_types']

os.environ['COMPACTS'] = json.dumps(COMPACTS)
os.environ['JURISDICTIONS'] = json.dumps(JURISDICTIONS)

from data_model.schema.license import LicensePostSchema  # pylint: disable=wrong-import-position


# We'll grab three different localizations to provide a variety of names/characters
name_faker = Faker(['en_US', 'ja_JP', 'es_MX'])
faker = Faker(['en_US'])

schema = LicensePostSchema()

FIELDS = (
    'ssn',
    'npi',
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
    'militaryWaiver',
    'emailAddress',
    'phoneNumber'
)


def generate_mock_csv_file(count, *, compact: str, jurisdiction: str = None):
    with open('mock-data.csv', 'w', encoding='utf-8') as data_file:
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
            print(f'Generated {i} records')
    print(f'Final record count: {i}')


def get_mock_license(i: int, *, compact: str, jurisdiction: str = None) -> dict:
    if jurisdiction is None:
        jurisdiction = faker.state_abbr().lower()
    license_data = {
        #                                                          |Zero padded 4 digit int|
        'ssn': f'{(i//1_000_000) % 1000:03}-{(i//10_000) % 100:02}-{(i % 10_000):04}',
        # Some have NPI, some don't
        'npi': str(randint(1_000_000_000, 9_999_999_999)) if choice([True, False]) else None,
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
        'phoneNumber': f'+1{randint(1_000_000_000, 9_999_999_999)}'
    }
    license_data = _set_address_state(license_data, jurisdiction)
    license_data = _set_dates(license_data)
    return schema.dump(license_data)


def _set_address_state(license_data: dict, jurisdiction: str) -> dict:
    # 1/5 will have a military waiver
    military = choice([False, False, False, False, True])
    if military:
        home_state = faker.state_abbr().lower()
        license_data.update({
            'homeAddressState': home_state,
            'homeAddressPostalCode': faker.zipcode_in_state(state_abbr=home_state.upper()),
            'militaryWaiver': military
        })
    else:
        license_data.update({
            'homeAddressState': jurisdiction,
            'homeAddressPostalCode': faker.zipcode_in_state(state_abbr=jurisdiction.upper()),
            # Explicitly set False for some, omit for others
            'militaryWaiver': military if choice([True, False]) else None
        })
    return license_data


def _set_dates(license_data: dict) -> dict:
    date_of_birth = faker.date_of_birth()
    # Issuance between when they were ~22 and ~40 years old, but still in the past
    now = datetime.now(tz=UTC).date()
    date_of_issuance = min(
        date_of_birth + timedelta(days=randint(22 * 365, 40 * 365)),
        now - timedelta(days=1)
    )
    # For simplicity, we'll assume that under-70-year-olds are active, over are inactive.
    if date_of_birth + 70*timedelta(days=365) > now:
        active = True
        # We'll have renewal be within the last year, but on or after issuance.
        date_of_renewal = max(
            now - timedelta(days=randint(1, 365)),
            date_of_issuance
        )
        # Expiry, one year from renewal
        date_of_expiry = date_of_renewal + timedelta(days=365)
    else:
        active = False
        # They renewed at some point in the last 20 years, but on or after their issuance date.
        date_of_renewal = max(
            date_of_issuance,
            now - randint(1, 20)*timedelta(days=365)
        )
        # Their license expired a year after renewal, but no later than yesterday.
        date_of_expiry = min(
            date_of_renewal + timedelta(days=365),
            now - timedelta(days=1)
        )
    license_data.update({
        'status': 'active' if active else 'inactive',
        'dateOfBirth': date_of_birth,
        'dateOfIssuance': date_of_issuance,
        'dateOfRenewal': date_of_renewal,
        'dateOfExpiration': date_of_expiry
    })
    return license_data


if __name__ == '__main__':
    import logging
    from argparse import ArgumentParser

    logging.basicConfig()

    parser = ArgumentParser(
        description='Generate mock license data for upload'
    )
    parser.add_argument(
        '--count',
        help="The count of licenses to generate",
        required=True,
        type=int
    )
    parser.add_argument(
        '--compact',
        help="The compact these licenses will be for",
        required=True,
        choices=COMPACTS
    )
    parser.add_argument(
        '-j', '--jurisdiction',
        help="The jurisdiction these licenses will be for",
        required=False,
        choices=JURISDICTIONS
    )

    args = parser.parse_args()
    generate_mock_csv_file(args.count, compact=args.compact, jurisdiction=args.jurisdiction)
