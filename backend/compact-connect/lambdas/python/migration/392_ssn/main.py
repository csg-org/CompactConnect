from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger
from cc_common.data_model.schema.base_record import SSNIndexRecordSchema


def on_event(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """CloudFormation event handler using the CDK provider framework.
    See: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.custom_resources/README.html

    This lambda migrates the SSNIndexRecordSchema with the new providerIdGSIpk field.

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
                logger.error('Error migrating SSN records', error=e)
                raise
        case 'Delete':
            # In the case of delete we do not remove any data from the table
            # data deletion will be managed by the DB's removal policy.
            return None
        case _:
            raise ValueError(f'Unexpected request type: {request_type}')


def migrate():
    # Scan all SSN records in the ssn table, load via the SSNRecordSchema, then put it back into the ssn table
    schema = SSNIndexRecordSchema()

    # Initialize pagination parameters
    last_evaluated_key = None

    logger.info('Starting migration')
    processed_count = 0
    while True:
        # Prepare scan parameters
        scan_params = {'TableName': config.ssn_table_name}
        if last_evaluated_key:
            scan_params['ExclusiveStartKey'] = last_evaluated_key

        # Perform the scan
        logger.info('Scanning SSN table')
        response = config.ssn_table.scan(**scan_params)

        # Process the current batch of records
        for ssn_record in response.get('Items', []):
            ssn_record = schema.load(ssn_record)
            logger.debug('Migrating record', provider_id=ssn_record['providerId'])
            # The GSI pk is generated on dump(), so this will migrate the record schema.
            config.ssn_table.put_item(Item=schema.dump(ssn_record))
            processed_count += 1
        # Check if there are more items to process
        last_evaluated_key = response.get('LastEvaluatedKey')
        if not last_evaluated_key:
            break
    logger.info('Migration complete', processed_count=processed_count)
