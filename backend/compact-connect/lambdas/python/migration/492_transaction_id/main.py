from aws_lambda_powertools.utilities.typing import LambdaContext
from boto3.dynamodb.conditions import Attr
from cc_common.config import config, logger
from cc_common.data_model.schema.privilege.record import PrivilegeRecordSchema, PrivilegeUpdateRecordSchema

COMPACT_TRANSACTION_ID_GSI_PK_FIELD = 'compactTransactionIdGSIPK'
ATTESTATIONS_FIELD = 'attestations'


def on_event(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """CloudFormation event handler using the CDK provider framework.
    See: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.custom_resources/README.html

    This lambda migrates the provider data table to add the compactTransactionIdGSIPk field to privilege records
    as well as privilege update records.

    :param event: The lambda event with the compact configuration in a JSON formatted string.
    :param context:
    :return: None - no infrastructure resources are created
    """
    logger.info('Entering CompactTransactionIdGSI migration')
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
            FilterExpression=Attr('type').eq('privilege') | Attr('type').eq('privilegeUpdate'),
        )

        # Process the current batch of records
        for record in response.get('Items', []):
            logger.info('Migrating record', pk=record['pk'], sk=record['sk'])

            # Remove the ssn field from the record
            if record['type'] == 'privilege':
                schema = PrivilegeRecordSchema()
                # compactTransactionIdGSIPK is required in the schema in order to load the record
                # so we add a dummy compactTransactionIdGSIPK field
                record[COMPACT_TRANSACTION_ID_GSI_PK_FIELD] = 'dummy'
                # we recently started requiring the attestations field for all privileges,
                # this adds that field if it is not already present
                if ATTESTATIONS_FIELD not in record:
                    record[ATTESTATIONS_FIELD] = []
                privilege_record = schema.load(record)
                # dumping the record will generate the needed GSI PK
                serialized_record = schema.dump(privilege_record)
            elif record['type'] == 'privilegeUpdate':
                schema = PrivilegeUpdateRecordSchema()
                # compactTransactionIdGSIPK is required in the schema in order to load the record
                # so we add a dummy compactTransactionIdGSIPK field
                record[COMPACT_TRANSACTION_ID_GSI_PK_FIELD] = 'dummy'
                # we recently started requiring the attestations field for all privilege updates,
                # this adds that field if it is not already present
                if ATTESTATIONS_FIELD not in record['previous']:
                    record['previous'][ATTESTATIONS_FIELD] = []
                privilege_update_record = schema.load(record)
                # dumping the record will generate the needed GSI PK
                serialized_record = schema.dump(privilege_update_record)

            config.provider_table.put_item(Item=serialized_record)
            processed_count += 1
        # Check if there are more items to process
        last_evaluated_key = response.get('LastEvaluatedKey')
        if not last_evaluated_key:
            break
    logger.info('Migration complete', processed_count=processed_count)
