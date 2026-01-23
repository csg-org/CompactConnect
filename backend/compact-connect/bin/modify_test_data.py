#!/usr/bin/env python3
"""
Modify existing license CSV data for beta testing.

This script applies consistent, easily identifiable markers to license records
so that state IT staff can verify that license updates are being processed correctly.

Modifications applied:
- Phone numbers: Last 4 digits changed to "9999"
- Email addresses: ".UPDATED" added before the @ symbol
- Street addresses: " (UPDATED)" appended to the address
- Records where SSN mod 100 = 0: licenseStatus set to "inactive" and compactEligibility set to "ineligible"
  (e.g., SSNs ending in -00-0000, -00-0100, -00-0200, etc.)
- Records where SSN ends in 5: Email address removed (to test missing email handling)
- Records where SSN ends in 7: Phone number removed (to test missing phone handling)

Usage:
    bin/modify_test_data.py input-file.csv
    # Creates: modified-input-file.csv

Example:
    bin/modify_test_data.py aslp-al-mock-data.csv
    # Creates: modified-aslp-al-mock-data.csv
"""

import sys
from csv import DictReader, DictWriter
from pathlib import Path


def modify_record(record: dict) -> dict:
    """
    Apply test modifications to a single license record.

    Args:
        record: Dictionary containing license data fields

    Returns:
        Modified record with test markers applied
    """
    # Phone: Keep format but change last 4 digits to 9999 for easy identification
    if record.get('phoneNumber'):
        phone = record['phoneNumber']
        if len(phone) >= 4:
            record['phoneNumber'] = phone[:-4] + '9999'

    # Email: Add .UPDATED marker before the @ symbol
    if record.get('emailAddress') and record['emailAddress'].strip():
        email = record['emailAddress']
        if '@' in email:
            name, domain = email.split('@', 1)
            record['emailAddress'] = f'{name}.UPDATED@{domain}'

    # Address: Append (UPDATED) to street address
    if record.get('homeAddressStreet1') and record['homeAddressStreet1'].strip():
        record['homeAddressStreet1'] = f'{record["homeAddressStreet1"]} (UPDATED)'

    # SSN-based modifications for testing various scenarios
    if record.get('ssn'):
        ssn = record['ssn']
        # Extract the numeric portion of the SSN (remove hyphens)
        ssn_numeric = ssn.replace('-', '')
        if ssn_numeric.isdigit():
            ssn_int = int(ssn_numeric)
            last_digit = ssn_int % 10

            # Records where SSN mod 100 = 0: Set to inactive and ineligible
            if ssn_int % 100 == 0:
                record['licenseStatus'] = 'inactive'
                record['compactEligibility'] = 'ineligible'

            # Records where SSN ends in 5: Remove email (test missing email handling)
            if last_digit == 5:
                record['emailAddress'] = ''

            # Records where SSN ends in 7: Remove phone (test missing phone handling)
            if last_digit == 7:
                record['phoneNumber'] = ''

    return record


def modify_csv_file(input_filepath: Path) -> Path:
    """
    Read a CSV file, modify its records, and write to a new file.

    Args:
        input_filepath: Path to the input CSV file

    Returns:
        Path to the created output file

    Raises:
        FileNotFoundError: If input file doesn't exist
        ValueError: If CSV is empty or has no header
    """
    if not input_filepath.exists():
        raise FileNotFoundError(f'Input file not found: {input_filepath}')

    # Create output filename with 'modified-' prefix
    output_filepath = input_filepath.parent / f'modified-{input_filepath.name}'

    records_processed = 0

    with open(input_filepath, 'r', encoding='utf-8') as infile:
        reader = DictReader(infile)

        # Verify we have a header
        if not reader.fieldnames:
            raise ValueError(f'CSV file has no header row: {input_filepath}')

        with open(output_filepath, 'w', encoding='utf-8', newline='') as outfile:
            writer = DictWriter(outfile, fieldnames=reader.fieldnames)
            writer.writeheader()

            for record in reader:
                records_processed += 1
                modified_record = modify_record(record)
                writer.writerow(modified_record)

                # Progress indicator for large files
                if records_processed % 1000 == 0:
                    sys.stdout.write(f'Processed {records_processed} records...\n')

    return output_filepath, records_processed


if __name__ == '__main__':
    import logging
    from argparse import ArgumentParser

    logging.basicConfig(level=logging.INFO, format='%(message)s')
    logger = logging.getLogger(__name__)

    parser = ArgumentParser(
        description='Modify license CSV data with test markers for beta testing',
        epilog='Output file will be created with "modified-" prefix in the same directory as input file.',
    )
    parser.add_argument(
        'input_file',
        help='Path to the CSV file to modify',
        type=str,
    )

    args = parser.parse_args()

    try:
        input_path = Path(args.input_file)
        logger.info(f'Reading from: {input_path}')

        output_path, count = modify_csv_file(input_path)

        logger.info(f'Successfully processed {count} records')
        logger.info(f'Output written to: {output_path}')

    except FileNotFoundError as e:
        logger.error(f'Error: {e}')
        sys.exit(1)
    except ValueError as e:
        logger.error(f'Error: {e}')
        sys.exit(1)
    except Exception as e:
        logger.error(f'Unexpected error: {e}')
        sys.exit(1)
