import json
from base64 import b64decode, b64encode
from types import MethodType
from typing import Callable, List

from botocore.exceptions import ClientError
from marshmallow import ValidationError

from config import config, logger
from data_model.schema.user import UserRecordSchema
from exceptions import CCInvalidRequestException, CCInternalException


_user_record_schema = UserRecordSchema()


# It's conventional to name a decorator in snake_case, even if it is implemented as a class
class paginated_query:  # pylint: disable=invalid-name
    """
    Decorator to handle converting API interface pagination to DynamoDB pagination.

    This will process incoming pagination fields for passing to DynamoDB, then take the raw DynamoDB response and
    transform it into a dict that includes an encoded lastKey field.

    {
        'items': response['Items'],
        'lastKey': <encoded pagination key>
    }

    When a FilterExpression is used, DynamoDB can return fewer items than is specified as the pageSize. To ensure
    that we always return the full pageSize, when there are enough results, this decorator will also potentially repeat
    queries multiple times internally, until it has pageSize items to return.
    """
    def __init__(self, fn: Callable):
        super().__init__()
        self.fn = fn

    def __get__(self, instance, owner):
        ret = MethodType(self, instance)
        return ret

    def __call__(self, *args, pagination: dict = None, client_filter: Callable[[dict], bool] = None, **kwargs):
        if pagination is None:
            pagination = {}
        # We b64 encode/decode the lastKey just for convenience passing to/from the client over HTTP
        last_key = pagination.get('lastKey')
        if last_key is not None:
            try:
                last_key = json.loads(b64decode(last_key).decode('utf-8'))
            except Exception as e:
                raise CCInvalidRequestException(message='Invalid lastKey') from e
        page_size = pagination.get('pageSize', config.default_page_size)

        items = []
        raw_resp = {}
        for raw_resp in self._generate_pages(
                last_key=last_key,
                page_size=page_size,
                client_filter=client_filter,
                args=args,
                kwargs=kwargs
        ):
            items.extend(raw_resp.get('Items', []))

        # items can be longer than page_size, so trim it:
        items = items[:page_size]
        raw_last_key = raw_resp.get('LastEvaluatedKey')

        resp = {
            # Deserializing everything that comes out of the database
            'items': self._load_records(items),
            'pagination': {
                'pageSize': page_size,
                'prevLastKey': pagination.get('lastKey')
            }
        }

        # Since we truncated our items, we need to recalculate the last key
        last_key = None
        if raw_last_key is not None:
            last_item = items[-1]
            last_key = {
                k: last_item[k]
                for k in raw_last_key.keys()
            }

        # Last key, if present, will be a dict like {'pk': 'some-pk', 'sk': 'aslp/PROVIDER'}
        if last_key is not None:
            last_key = b64encode(json.dumps(last_key).encode('utf-8')).decode('utf-8')
        resp['pagination']['lastKey'] = last_key
        return resp

    def _generate_pages(
            self, *,
            last_key: str | None,
            page_size: int,
            client_filter: Callable[[dict], bool] | None,
            args,
            kwargs
    ):
        """
        Repeat the wrapped query until we get everything or the full page_size of items
        """
        dynamo_pagination = {
            'Limit': page_size,
            **({'ExclusiveStartKey': last_key} if last_key is not None else {})
        }

        raw_resp = self._caught_query(client_filter, *args, dynamo_pagination=dynamo_pagination, **kwargs)
        count = raw_resp['Count']
        last_key = raw_resp.get('LastEvaluatedKey')

        yield raw_resp
        while last_key is not None and count < page_size:
            dynamo_pagination = {
                'Limit': page_size,
                **({'ExclusiveStartKey': last_key} if last_key is not None else {})
            }

            raw_resp = self._caught_query(client_filter, *args, dynamo_pagination=dynamo_pagination, **kwargs)
            count += raw_resp['Count']
            last_key = raw_resp.get('LastEvaluatedKey')
            yield raw_resp

    def _caught_query(self, client_filter: Callable[[dict], bool] | None, *args, **kwargs):
        """
        Uniformly convert our DynamoDB query validation errors to invalid request exceptions
        """
        try:
            raw_resp = self.fn(*args, **kwargs)
        except ClientError as e:
            # If the client sends in an invalid lastKey that is good enough to get sent to DynamoDB,
            # DynamoDB will return us a ValidationException, so we'll handle that here
            if e.response['Error']['Code'] == 'ValidationException':
                logger.warning('Invalid request caused a ValidationException', response=e.response, exc_info=e)
                raise CCInvalidRequestException('Invalid request') from e
            raise

        # Apply client filter if provided
        if client_filter is not None:
            raw_resp['Items'] = [
                item
                for item in raw_resp['Items']
                if client_filter(item)
            ]
            count = len(raw_resp['Items'])
            raw_resp['Count'] = count

        return raw_resp

    @staticmethod
    def _load_records(records: List[dict]):
        """
        Every record coming through this paginator should be de-serializable through our *RecordSchema
        """
        print(records)
        try:
            return [
                _user_record_schema.load(item)
                for item in records
            ]
        except (KeyError, ValidationError) as e:
            raise CCInternalException('Data validation failure!') from e
