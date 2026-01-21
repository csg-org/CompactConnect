import json
from base64 import b64decode, b64encode
from collections.abc import Callable
from types import MethodType

from botocore.exceptions import ClientError

from cc_common.config import config, logger
from cc_common.exceptions import CCInvalidRequestException
from cc_common.utils import load_records_into_schemas


# It's conventional to name a decorator in snake_case, even if it is implemented as a class
class paginated_query:  # noqa: N801 invalid-name
    """Decorator to handle converting API interface pagination to DynamoDB pagination.

    This will process incoming pagination fields for passing to DynamoDB, then take the raw DynamoDB response and
    transform it into a dict that includes an encoded lastKey field.

    {
        'items': response['Items'],
        'pagination': {
            'pageSize': <page size>,
            'prevLastKey': <encoded pagination key if available>,
            'lastKey': <encoded pagination key if available>
        }
    }

    IMPORTANT: When a FilterExpression is used over a large partition space, DynamoDB can return fewer items than is
    specified as the pageSize. To ensure that we always return the full pageSize, this decorator will repeat queries as
    needed until it has a full page of items to return. In order to reduce the number of queries made when using filter
    expressions, you should set the set_query_limit_to_match_page_size flag to False. This will not set the Limit
    parameter on the query, so DynamoDB will evaluate as many items as it can within a single query, returning all
    evaluated items that match the filter expression. The decorator will handle truncating the items to fit within the
    pageSize, and will also handle calculating the lastKey for the next page of results.
    """

    def __init__(self, set_query_limit_to_match_page_size: bool = True):
        super().__init__()
        self.set_query_limit_to_match_page_size = set_query_limit_to_match_page_size

    def __call__(self, fn: Callable):
        return _PaginatedQueryDecorator(fn, self.set_query_limit_to_match_page_size)


class _PaginatedQueryDecorator:
    """Internal decorator class that handles the actual pagination logic."""

    def __init__(self, fn: Callable, set_query_limit_to_match_page_size: bool):
        self.fn = fn
        self.set_query_limit_to_match_page_size = set_query_limit_to_match_page_size

    def __get__(self, instance, owner):
        return MethodType(self, instance)

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
        last_known_evaluated_key = None
        for raw_resp in self._generate_pages(
            last_key=last_key,
            page_size=page_size,
            client_filter=client_filter,
            args=args,
            kwargs=kwargs,
        ):
            items.extend(raw_resp.get('Items', []))
            # track the last key for the page, in the event more items are returned on the last page than the page size
            last_known_evaluated_key = raw_resp.get('LastEvaluatedKey', last_known_evaluated_key)

        # items can be longer than page_size, so we trim it to the page size:
        if len(items) > page_size:
            items = items[:page_size]
            last_item = items[-1]
            # Since we truncated our items, we need to recalculate the last key
            # We will use the last known evaluated key to determine the needed fields
            # for the last key if we have one
            if last_known_evaluated_key is not None:
                last_key = {k: last_item[k] for k in last_known_evaluated_key.keys()}
            # Else the first query was the last query, but there were more items to be returned than the specified page
            # size. In this case, we need to determine the last key for getting the next page. The keys needed by the
            # last key are not static (for example, if you are querying by a GSI you must include the GSI fields as
            # part of the last key) so to have a generic solution for this scenario, we make a query with a limit of 1
            # so we can get the LastEvaluatedKey from the response, and then map the keys from that to the values of
            # the last item that will be returned in the response to create our own last key.
            else:
                last_key_resp = self._caught_query(client_filter, *args, dynamo_pagination={'Limit': 1}, **kwargs)
                last_known_evaluated_key = last_key_resp.get('LastEvaluatedKey')
                last_key = {k: last_item[k] for k in last_known_evaluated_key.keys()}
        # else if the page size matched the query, and there are more records to return, set the last key to match
        elif raw_resp.get('LastEvaluatedKey'):
            last_key = raw_resp.get('LastEvaluatedKey')
        # else there are not more records to fetch, set last key to none
        else:
            last_key = None

        resp = {
            # Deserializing everything that comes out of the database
            'items': load_records_into_schemas(items),
            'pagination': {'pageSize': page_size, 'prevLastKey': pagination.get('lastKey')},
        }

        # Last key, if present, will be a dict like {'pk': 'some-pk', 'sk': 'cosm/PROVIDER'}
        if last_key is not None:
            last_key = b64encode(json.dumps(last_key).encode('utf-8')).decode('utf-8')
        resp['pagination']['lastKey'] = last_key
        return resp

    def _generate_pages(
        self,
        *,
        last_key: str | None,
        page_size: int,
        client_filter: Callable[[dict], bool] | None,
        args,
        kwargs,
    ):
        """Repeat the wrapped query until we get everything or the full page_size of items"""
        dynamo_pagination = {**({'ExclusiveStartKey': last_key} if last_key is not None else {})}
        if self.set_query_limit_to_match_page_size:
            dynamo_pagination['Limit'] = page_size

        raw_resp = self._caught_query(client_filter, *args, dynamo_pagination=dynamo_pagination, **kwargs)
        count = raw_resp['Count']
        last_key = raw_resp.get('LastEvaluatedKey')

        yield raw_resp
        while last_key is not None and count < page_size:
            dynamo_pagination = {**({'ExclusiveStartKey': last_key} if last_key is not None else {})}
            if self.set_query_limit_to_match_page_size:
                dynamo_pagination['Limit'] = page_size

            raw_resp = self._caught_query(client_filter, *args, dynamo_pagination=dynamo_pagination, **kwargs)
            count += raw_resp['Count']
            last_key = raw_resp.get('LastEvaluatedKey')
            yield raw_resp

    def _caught_query(self, client_filter: Callable[[dict], bool] | None, *args, **kwargs):
        """Uniformly convert our DynamoDB query validation errors to invalid request exceptions"""
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
            raw_resp['Items'] = [item for item in raw_resp['Items'] if client_filter(item)]
            count = len(raw_resp['Items'])
            raw_resp['Count'] = count

        return raw_resp
