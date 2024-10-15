import json
from base64 import b64decode, b64encode
from functools import wraps
from urllib.parse import quote

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from config import _Config, config, logger
from exceptions import CCInternalException, CCInvalidRequestException, CCNotFoundException
from marshmallow import ValidationError

from data_model.schema.base_record import BaseRecordSchema
from data_model.schema.license import SSNIndexRecordSchema


def paginated(fn):
    """
    Process incoming pagination fields for passing to DynamoDB, then take the raw DynamoDB response and transform it
    into a dict that includes an encoded lastKey field.

    {
        'items': response['Items'],
        'lastKey': <encoded pagination key>
    }
    """

    @wraps(fn)
    def process_pagination_parameters(*args, pagination: dict = None, **kwargs):
        if pagination is None:
            pagination = {}
        # We b64 encode/decode the lastKey just for convenience passing to/from the client over HTTP
        last_key = pagination.get('lastKey')
        if last_key is not None:
            try:
                last_key = json.loads(b64decode(last_key).decode('ascii'))
            except Exception as e:
                raise CCInvalidRequestException(message='Invalid lastKey') from e
        page_size = pagination.get('pageSize', config.default_page_size)

        dynamo_pagination = {'Limit': page_size, **({'ExclusiveStartKey': last_key} if last_key is not None else {})}
        try:
            raw_resp = fn(*args, dynamo_pagination=dynamo_pagination, **kwargs)
        except ClientError as e:
            # If the client sends in an invalid lastKey that is good enough to get sent to DynamoDB,
            # DynamoDB will return us a ValidationException, so we'll handle that here
            if e.response['Error']['Code'] == 'ValidationException':
                logger.warning('Invalid request caused a ValidationException', response=e.response, exc_info=e)
                raise CCInvalidRequestException('Invalid request') from e
            raise

        resp = {
            'items': raw_resp.get('Items', []),
            'pagination': {'pageSize': page_size, 'prevLastKey': pagination.get('lastKey')},
        }

        # Last key, if present, will be a dict like {'pk': '123-12-1234', 'sk': 'aslp/co/license-home'}
        last_key = raw_resp.get('LastEvaluatedKey')
        if last_key is not None:
            last_key = b64encode(json.dumps(last_key).encode('utf-8')).decode('ascii')
        resp['pagination']['lastKey'] = last_key
        return resp

    return process_pagination_parameters


class DataClient:
    """
    Client interface for license data dynamodb queries
    """

    def __init__(self, config: _Config):  # pylint: disable=redefined-outer-name
        self.config = config
        self.ssn_index_record_schema = SSNIndexRecordSchema()

    def get_provider_id(self, *, ssn: str) -> str:
        """
        Get all records associated with a given SSN.
        """
        logger.info('Getting provider id by ssn')
        resp = self.config.license_table.query(
            IndexName=config.ssn_index_name,
            Select='ALL_PROJECTED_ATTRIBUTES',
            KeyConditionExpression=Key('ssn').eq(quote(ssn)),
        )
        # Create a set of provider ids (which will ensure no duplicate values) from all license-home records
        items = {self.ssn_index_record_schema.load(item)['licenseHomeProviderId'] for item in resp['Items']}
        item_count = len(items)
        # If there is more than one value in the set, we have multiple provider ids associated with
        # the requested SSN, which is a problem.
        if item_count > 1:
            raise CCInternalException('Data consistency error!')

        if item_count < 1:
            raise CCNotFoundException('No licensee found by that identifier')

        return str(list(items)[0])

    @paginated
    def get_provider(self, *, provider_id: str, dynamo_pagination: dict):
        logger.info('Getting provider', provider_id=provider_id)
        resp = self.config.license_table.query(
            Select='ALL_ATTRIBUTES', KeyConditionExpression=Key('pk').eq(provider_id), **dynamo_pagination
        )
        resp['Items'] = self._load_records(resp.get('Items', []))
        return resp

    @paginated
    def get_licenses_sorted_by_family_name(
        self, *, compact: str, jurisdiction: str, dynamo_pagination: dict, scan_forward: bool = True
    ):  # pylint: disable-redefined-outer-name
        logger.info('Getting licenses by family name')
        resp = self.config.license_table.query(
            IndexName=config.cj_name_index_name,
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('compactJur').eq(f'{quote(compact)}/{quote(jurisdiction)}'),
            ScanIndexForward=scan_forward,
            **dynamo_pagination,
        )
        resp['Items'] = self._load_records(resp.get('Items', []))
        return resp

    @paginated
    def get_licenses_sorted_by_date_updated(
        self, *, compact: str, jurisdiction: str, dynamo_pagination: dict, scan_forward: bool = True
    ):  # pylint: disable-redefined-outer-name
        compact = quote(compact, safe='')
        jurisdiction = quote(jurisdiction, safe='')

        logger.info('Getting licenses by date updated')
        resp = self.config.license_table.query(
            IndexName=config.cj_updated_index_name,
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('compactJur').eq(f'{compact}/{jurisdiction}'),
            ScanIndexForward=scan_forward,
            **dynamo_pagination,
        )
        resp['Items'] = self._load_records(resp.get('Items', []))
        return resp

    @staticmethod
    def _load_records(records: list[dict]):
        try:
            return [BaseRecordSchema.get_schema_by_type(item['type']).load(item) for item in records]
        except (KeyError, ValidationError) as e:
            raise CCInternalException('Data validation failure!') from e
