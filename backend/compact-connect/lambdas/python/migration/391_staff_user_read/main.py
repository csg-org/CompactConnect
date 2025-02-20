from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger


def on_event(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """CloudFormation event handler using the CDK provider framework.
    See: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.custom_resources/README.html

    This lambda migrates the staff user data table to remove the read action from the compact permissions.

    :param event: The lambda event from the custom resource provider framework.
    :param context: The lambda context.
    :return: None - no infrastructure resources are created
    """
    logger.info('Entering StaffUser Table migration')
    # If a future script needs input properties, they can be passed in here
    # properties = event['ResourceProperties']
    request_type = event['RequestType']
    match request_type:
        case 'Create' | 'Update':
            try:
                return migrate()
            except Exception as e:
                logger.error('Error migrating provider data records', error=e)
                raise
        case 'Delete':
            # In the case of delete we do not roll back the migration, so that we can safely
            # remove this migration, once complete.
            return None
        case _:
            raise ValueError(f'Unexpected request type: {request_type}')


def migrate():
    # Initialize pagination parameters
    last_evaluated_key = None

    logger.info('Starting migration')
    processed_count = 0
    while True:
        # Prepare scan parameters
        scan_params = {'TableName': config.users_table.table_name}
        if last_evaluated_key:
            scan_params['ExclusiveStartKey'] = last_evaluated_key

        # Perform the scan
        logger.info('Scanning Staff User table')
        response = config.users_table.scan(
            **scan_params,
        )

        # Process the current batch of records
        for record in response.get('Items', []):
            logger.debug('Migrating record', pk=record['pk'], sk=record['sk'])

            # Remove the 'read' action from compact permissions, if present
            if 'permissions' in record and 'actions' in record['permissions']:
                compact_actions: set = record['permissions']['actions']
                compact_actions -= {'read'}
                if not compact_actions:
                    # We cannot save an empty string set, so we will remove the whole actions field
                    logger.debug('Removing actions field from permissions')
                    del record['permissions']['actions']
                else:
                    logger.debug('Removing read action from permissions')
                    record['permissions']['actions'] = compact_actions
            config.users_table.put_item(Item=record)
            processed_count += 1
        # Check if there are more items to process
        last_evaluated_key = response.get('LastEvaluatedKey')
        if not last_evaluated_key:
            break
    logger.info('Migration complete', processed_count=processed_count)
