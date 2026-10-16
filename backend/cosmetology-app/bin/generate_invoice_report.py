#!/usr/bin/env python3
# ruff: noqa: T201 we use print statements for local scripts
"""Invoke the invoice reporter for one billing month.

The monthly schedule bills the previous month. Use this to send a specific month,
including the retroactive September and October runs:

    cd backend/cosmetology-app
    python bin/generate_invoice_report.py --month 2024-09
    python bin/generate_invoice_report.py --month 2024-10
"""

import argparse
import json
import re
import sys

import boto3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Generate a Cosmetology Compact invoice for one billing month')
    parser.add_argument('--month', required=True, help='Billing month as YYYY-MM')
    parser.add_argument(
        '--function-name',
        help='Invoice reporter Lambda name. Defaults to the only function containing InvoiceReporter.',
    )
    return parser.parse_args()


def validate_month(month: str) -> str:
    if not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', month):
        raise ValueError(f'--month must be YYYY-MM, got {month!r}')
    return month


def find_function_name(lambda_client, explicit_name: str | None) -> str:
    if explicit_name:
        return explicit_name

    matches = []
    paginator = lambda_client.get_paginator('list_functions')
    for page in paginator.paginate():
        for function in page['Functions']:
            if 'InvoiceReporter' in function['FunctionName']:
                matches.append(function['FunctionName'])

    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise RuntimeError('No Lambda function name contains InvoiceReporter. Pass --function-name.')

    joined = '\n'.join(sorted(matches))
    raise RuntimeError(f'Multiple invoice reporter functions found. Pass --function-name.\n{joined}')


def invoke_invoice(function_name: str, billing_month: str) -> None:
    lambda_client = boto3.client('lambda')
    resolved_name = find_function_name(lambda_client, function_name)
    payload = {'eventType': 'manual', 'billingMonth': billing_month}

    print(f'Invoking {resolved_name} for {billing_month}')
    response = lambda_client.invoke(
        FunctionName=resolved_name,
        InvocationType='RequestResponse',
        Payload=json.dumps(payload).encode(),
    )
    body = response['Payload'].read().decode()
    print(body)

    if response.get('FunctionError'):
        raise RuntimeError(f'{resolved_name} failed: {response["FunctionError"]}')


def main() -> None:
    args = parse_args()
    try:
        invoke_invoice(args.function_name, validate_month(args.month))
    except Exception as error:  # noqa: BLE001 surface the CLI failure and exit
        print(f'Error: {error}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
