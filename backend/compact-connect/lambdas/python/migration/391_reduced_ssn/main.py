from aws_lambda_powertools.utilities.typing import LambdaContext
from boto3.dynamodb.conditions import Attr
from cc_common.config import config, logger


def on_event(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """CloudFormation event handler using the CDK provider framework.
    See: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.custom_resources/README.html

    This lambda migrates the provider data table to remove ssn fields from the schema.

    :param event: The lambda event with the compact configuration in a JSON formatted string.
    :param context:
    :return: None - no infrastructure resources are created
    """
    logger.info('Entering SSNIndexRecordSchema migration')
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
        scan_params = {'TableName': config.provider_table.table_name}
        if last_evaluated_key:
            scan_params['ExclusiveStartKey'] = last_evaluated_key

        # Perform the scan
        logger.info('Scanning Provider Data table')
        response = config.provider_table.scan(
            **scan_params,
            FilterExpression=Attr('type').eq('provider')
            | Attr('type').eq('license')
            | Attr('type').eq('licenseUpdate'),
        )

        # Process the current batch of records
        for record in response.get('Items', []):
            logger.debug('Migrating record', pk=record['pk'], sk=record['sk'])

            # Remove the ssn field from the record
            if record['type'] in ['provider', 'license']:
                if 'ssn' in record:
                    ssn = record.pop('ssn')
                    record['ssnLastFour'] = ssn[-4:]
                else:
                    logger.debug('No ssn field found for record', pk=record['pk'], sk=record['sk'])
            elif record['type'] == 'licenseUpdate':
                if 'ssn' in record['previous']:
                    ssn = record['previous'].pop('ssn')
                    record['previous']['ssnLastFour'] = ssn[-4:]
                else:
                    logger.debug('No ssn field found for record', pk=record['pk'], sk=record['sk'])

            config.provider_table.put_item(Item=record)
            processed_count += 1
        # Check if there are more items to process
        last_evaluated_key = response.get('LastEvaluatedKey')
        if not last_evaluated_key:
            break
    logger.info('Migration complete', processed_count=processed_count)
