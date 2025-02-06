# ruff: noqa: T201  we use print statements for migration scripts
#!/usr/bin/env python3
import argparse

import boto3

# This migration script updates privilege records that don't have an attestations field
# by adding an empty attestations list to them.


def update_privileges_missing_attestations(table_name: str, dry_run: bool = False) -> None:
    """
    Scans the provider table for privilege records missing the attestations field
    and adds an empty attestations list to them.

    Args:
        table_name: The name of the DynamoDB table to update
        dry_run: If True, only print what would be updated without making changes
    """
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)

    # Get all privilege records
    scan_kwargs = {
        'FilterExpression': 'contains(#type_attr, :type_value)',
        'ExpressionAttributeNames': {'#type_attr': 'type'},
        'ExpressionAttributeValues': {':type_value': 'privilege'},
    }

    updated_count = 0
    try:
        done = False
        start_key = None
        while not done:
            if start_key:
                scan_kwargs['ExclusiveStartKey'] = start_key
            response = table.scan(**scan_kwargs)
            items = response.get('Items', [])

            for item in items:
                # Check if attestations field is missing
                if 'attestations' not in item:
                    print(f"{'Would update' if dry_run else 'Updating'} record with pk={item['pk']}, sk={item['sk']}")

                    if not dry_run:
                        # Update the item with an empty attestations list
                        table.update_item(
                            Key={'pk': item['pk'], 'sk': item['sk']},
                            UpdateExpression='SET attestations = :empty_list',
                            ExpressionAttributeValues={':empty_list': []},
                        )
                    updated_count += 1

            start_key = response.get('LastEvaluatedKey')
            done = start_key is None

        print(f"{'Would have updated' if dry_run else 'Successfully updated'} {updated_count} privilege records")

    except Exception as e:
        print(f'Error updating privileges: {str(e)}')
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Update privilege records to include empty attestations list if missing'
    )
    parser.add_argument('table_name', help='The name of the DynamoDB table to update')
    parser.add_argument('-d', '--dry-run', action='store_true', help='Perform a dry run without making any changes')

    args = parser.parse_args()

    print(f"Starting migration on table: {args.table_name} {'(DRY RUN)' if args.dry_run else ''}")
    update_privileges_missing_attestations(args.table_name, args.dry_run)
