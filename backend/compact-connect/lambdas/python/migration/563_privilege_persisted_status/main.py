from aws_lambda_powertools.utilities.typing import LambdaContext
from boto3.dynamodb.conditions import Attr
from cc_common.config import config, logger


def on_event(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """CloudFormation event handler using the CDK provider framework.
    See: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.custom_resources/README.html

    This lambda migrates privilege records in the provider table to add persistedStatus field.

    :param event: The lambda event from the custom resource provider framework.
    :param context: The lambda context.
    :return: None - no infrastructure resources are created
    """
    logger.info('Entering privilege persisted status migration')
    request_type = event['RequestType']
    match request_type:
        case 'Create' | 'Update':
            try:
                return migrate()
            except Exception as e:
                logger.error('Error migrating privilege records', error=e)
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
        scan_params = {'TableName': config.provider_table.table_name}
        if last_evaluated_key:
            scan_params['ExclusiveStartKey'] = last_evaluated_key

        # Perform the scan
        logger.info('Scanning Provider Data table')
        response = config.provider_table.scan(
            **scan_params,
            FilterExpression=Attr('type').eq('privilege') & Attr('persistedStatus').not_exists(),
        )

        # Process the current batch of records
        for record in response.get('Items', []):
            logger.debug('Migrating record', pk=record['pk'], sk=record['sk'])
            record['persistedStatus'] = 'active'
            config.provider_table.put_item(Item=record)
            processed_count += 1

        # Check if there are more items to process
        last_evaluated_key = response.get('LastEvaluatedKey')
        if not last_evaluated_key:
            break
    logger.info('Migration complete', processed_count=processed_count)
