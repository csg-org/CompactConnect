#!/usr/bin/env python3
"""One-off rollback of Cosmetology data-live for states marked via the state-admin workaround.

For each postal abbreviation:

- Sets that jurisdiction's licenseeRegistrationEnabled to false.
- Removes it from the compact configuredStates list only when isLive is not true.

Writes DynamoDB directly so it can bypass the API irreversibility checks.
Do not run until the state list is provided. This is not part of ongoing operations.

Usage:
    COMPACT_CONFIGURATION_TABLE_NAME=... \\
        python rollback_data_live.py ky oh
"""

import argparse
import logging
import os
from datetime import UTC, datetime

import boto3

logger = logging.getLogger(__name__)


def _configuration_key(compact: str) -> dict:
    return {'pk': f'{compact}#CONFIGURATION', 'sk': f'{compact}#CONFIGURATION'}


def _jurisdiction_key(compact: str, postal_abbreviation: str) -> dict:
    return {
        'pk': f'{compact}#CONFIGURATION',
        'sk': f'{compact}#JURISDICTION#{postal_abbreviation.lower()}',
    }


def rollback_data_live(table, compact: str, postal_abbreviations: list[str]) -> None:
    now = datetime.now(UTC).isoformat()
    compact_key = _configuration_key(compact)
    compact_item = table.get_item(Key=compact_key).get('Item')
    if compact_item:
        configured_states = list(compact_item.get('configuredStates', []))
    else:
        configured_states = []
        logger.info('No compact configuration found for %s; skipping configuredStates cleanup', compact)
    states_to_remove = set()

    for postal_abbreviation in postal_abbreviations:
        postal_abbreviation = postal_abbreviation.lower()
        jurisdiction_key = _jurisdiction_key(compact, postal_abbreviation)
        jurisdiction_item = table.get_item(Key=jurisdiction_key).get('Item')
        if jurisdiction_item:
            table.update_item(
                Key=jurisdiction_key,
                UpdateExpression='SET licenseeRegistrationEnabled = :enabled, dateOfUpdate = :updated',
                ExpressionAttributeValues={':enabled': False, ':updated': now},
            )
            logger.info('%s: set licenseeRegistrationEnabled to false', postal_abbreviation)
        else:
            logger.info('%s: no jurisdiction configuration record', postal_abbreviation)

        matching_states = [
            state
            for state in configured_states
            if state.get('postalAbbreviation', '').lower() == postal_abbreviation
        ]
        if not matching_states:
            logger.info('%s: not present in configuredStates', postal_abbreviation)
            continue
        if any(state.get('isLive') for state in matching_states):
            logger.info('%s: privilege-live, left in configuredStates', postal_abbreviation)
            continue
        states_to_remove.add(postal_abbreviation)
        logger.info('%s: will remove from configuredStates', postal_abbreviation)

    if not states_to_remove:
        return

    updated_states = [
        state
        for state in configured_states
        if state.get('postalAbbreviation', '').lower() not in states_to_remove
    ]
    table.update_item(
        Key=compact_key,
        UpdateExpression='SET configuredStates = :states, dateOfUpdate = :updated',
        ExpressionAttributeValues={':states': updated_states, ':updated': now},
    )
    logger.info('Removed %s from configuredStates', ', '.join(sorted(states_to_remove)))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('postal_abbreviations', nargs='+', help='Jurisdiction postal abbreviations to roll back')
    parser.add_argument('--compact', default='cosm')
    args = parser.parse_args()

    table_name = os.environ.get('COMPACT_CONFIGURATION_TABLE_NAME')
    if not table_name:
        raise SystemExit('COMPACT_CONFIGURATION_TABLE_NAME is required')

    table = boto3.resource('dynamodb').Table(table_name)
    rollback_data_live(table, args.compact, args.postal_abbreviations)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
