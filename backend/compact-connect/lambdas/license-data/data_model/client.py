import json
from base64 import b64decode, b64encode
from functools import wraps
from urllib.parse import quote

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from config import _Config, logger, config
from exceptions import CCInvalidRequestException


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
        # We b64 encode/decode the last_key just for convenience passing to/from the client over HTTP
        last_key = pagination.get('last_key')
        if last_key is not None:
            try:
                last_key = json.loads(b64decode(last_key).decode('ascii'))
            except Exception as e:
                raise CCInvalidRequestException(message='Invalid lastKey') from e
        page_size = pagination.get('page_size', config.default_page_size)

        dynamo_pagination = {
            'Limit': page_size,
            **({'ExclusiveStartKey': last_key} if last_key is not None else {})
        }
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
            'items': raw_resp.get('Items', [])
        }
        last_key = raw_resp.get('LastEvaluatedKey')
        # Last key, if present, will be a dict like {'pk': '123-12-1234', 'sk': 'aslp/co/license-home'}
        if last_key is not None:
            resp['lastKey'] = b64encode(json.dumps(last_key).encode('utf-8')).decode('ascii')
        return resp
    return process_pagination_parameters


class DataClient():
    """
    Client interface for license data dynamodb queries
    """
    def __init__(self, config: _Config):  # pylint: disable=redefined-outer-name
        self.config = config

    @paginated
    def get_ssn(self, *, ssn: str, dynamo_pagination: dict):
        """
        Get all records associated with a given SSN.
        """
        logger.info('Getting ssn')
        resp = self.config.license_table.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('pk').eq(quote(ssn)),
            **dynamo_pagination
        )
        return resp
