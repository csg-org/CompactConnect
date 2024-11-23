#!/usr/bin/env python3
# Quick script to generate some mock data for test environments
#
# Run from 'backend/compact-connect/lambdas/license-data' with:
# python -m tests.bin.generate_mock_data
# Required environment variables:
# export LICENSE_TABLE_NAME='Sandbox-PersistentStack-MockLicenseTable12345-ETC'
# export COMPACTS='["aslp", "octp", "coun"]'
# export JURISDICTIONS='["al", "co"]'
# export LICENSE_TYPES='{"aslp": ["audiologist", "speech-language pathologist", "speech and language pathologist"]}'

import os
from random import randint
from uuid import uuid4

from config import config, logger
from data_model.schema.license import LicenseRecordSchema
from license_csv_reader import LicenseCSVReader


def generate_csv_rows(count):
    i = 0
    while i < count:
        with open(os.path.join('tests', 'resources', 'licenses.csv')) as f:
            reader = LicenseCSVReader()
            for license_row in reader.licenses(f):
                validated_license = reader.schema.load({'compact': 'aslp', 'jurisdiction': 'co', **license_row})
                logger.debug('Read validated license', license_data=reader.schema.dump(validated_license))
                yield i, validated_license
                i += 1


def put_licenses(jurisdiction: str, count: int = 100):
    schema = LicenseRecordSchema()
    for i, license_data in generate_csv_rows(count):
        ssn = f'{randint(100, 999)}-{randint(10, 99)}-{9999-i}'
        provider_id = uuid4()
        license_data.update({'providerId': provider_id, 'ssn': ssn, 'compact': 'aslp', 'jurisdiction': jurisdiction})
        logger.info('Put license', license_data=license_data)
        config.license_table.put_item(Item=schema.dump(license_data))


if __name__ == '__main__':
    import logging

    logging.basicConfig()

    put_licenses('co', 100)
    put_licenses('al', 100)
