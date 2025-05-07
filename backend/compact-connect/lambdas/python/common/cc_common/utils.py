import json
from collections import UserDict
from collections.abc import Callable
from datetime import date
from decimal import Decimal
from functools import wraps
from json import JSONEncoder
from re import match
from types import MethodType
from typing import Any
from uuid import UUID

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.exceptions import ClientError

from cc_common.config import config, logger, metrics
from cc_common.data_model.schema.common import CCPermissionsAction
from cc_common.data_model.schema.provider.api import ProviderGeneralResponseSchema
from cc_common.exceptions import (
    CCAccessDeniedException,
    CCInvalidRequestException,
    CCNotFoundException,
    CCRateLimitingException,
    CCUnauthorizedException,
    CCUnsupportedMediaTypeException,
)


class ResponseEncoder(JSONEncoder):
    """JSON Encoder to handle data types that come out of our schema"""

    def default(self, o):
        if isinstance(o, Decimal):
            ratio = o.as_integer_ratio()
            if ratio[1] == 1:
                return ratio[0]
            return float(o)

        if isinstance(o, UUID):
            return str(o)

        if isinstance(o, date):
            return o.isoformat()

        if isinstance(o, set):
            return list(o)

        # This is just a catch-all that shouldn't realistically ever be reached.
        return super().default(o)


class CaseInsensitiveDict(UserDict):
    """
    Dictionary that enforces case-insensitive keys

    To accommodate HTTP2 vs HTTP1.1 behavior RE header capitalization
    https://www.rfc-editor.org/rfc/rfc7540#section-8.1.2
    """

    def __init__(self, in_dict: dict[str, Any], /):
        if in_dict:
            # Force all keys to lowercase
            super().__init__({k.lower(): v for k, v in in_dict.items()})
        else:
            super().__init__({})

    def pop(self, key: str, default=None):
        return super().pop(key.lower(), default)

    def __setitem__(self, key: str, value):
        super().__setitem__(key.lower(), value)

    def __getitem__(self, key: str):
        return super().__getitem__(key.lower())

    def get(self, key: str, default=None):
        return super().get(key.lower(), default)


def api_handler(fn: Callable):
    """Decorator to wrap an api gateway event handler in standard logging, HTTPError handling.

    - Logs each access
    - JSON-encodes returned responses
    - Translates CCBaseException subclasses to their respective HTTP response codes
    """

    @wraps(fn)
    @metrics.log_metrics
    @logger.inject_lambda_context
    def caught_handler(event, context: LambdaContext):
        # We have to jump through extra hoops to handle the case where APIGW sets headers to null
        headers = CaseInsensitiveDict(event.get('headers')) or {}
        headers.pop('Authorization', None)
        (event.get('multiValueHeaders') or {}).pop('Authorization', None)

        # Determine the appropriate CORS origin header value
        origin = headers.get('Origin')
        if origin in config.allowed_origins:
            cors_origin = origin
        else:
            cors_origin = config.allowed_origins[0]

        content_type = headers.get('Content-Type')

        # Propagate these keys to all log messages in this with block
        with logger.append_context_keys(
            method=event['httpMethod'],
            origin=origin,
            path=event['requestContext']['resourcePath'],
            content_type=content_type,
            identity={'user': event['requestContext'].get('authorizer', {}).get('claims', {}).get('sub')},
            query_params=event['queryStringParameters'],
            username=event['requestContext'].get('authorizer', {}).get('claims', {}).get('cognito:username'),
        ):
            logger.info('Incoming request')

            try:
                # We'll enforce json-only content for the whole API, right here.
                if event.get('body') is not None and content_type != 'application/json':
                    raise CCUnsupportedMediaTypeException(f'Unsupported media type: {content_type}')

                return {
                    'headers': {'Access-Control-Allow-Origin': cors_origin, 'Vary': 'Origin'},
                    'statusCode': 200,
                    'body': json.dumps(fn(event, context), cls=ResponseEncoder),
                }
            except CCUnauthorizedException as e:
                logger.info('Unauthorized request', exc_info=e)
                return {
                    'headers': {'Access-Control-Allow-Origin': cors_origin, 'Vary': 'Origin'},
                    'statusCode': 401,
                    'body': json.dumps({'message': 'Unauthorized'}),
                }
            except CCAccessDeniedException as e:
                logger.info('Forbidden request', exc_info=e)
                return {
                    'headers': {'Access-Control-Allow-Origin': cors_origin, 'Vary': 'Origin'},
                    'statusCode': 403,
                    'body': json.dumps({'message': 'Access denied'}),
                }
            except CCNotFoundException as e:
                logger.info('Resource not found', exc_info=e)
                return {
                    'headers': {'Access-Control-Allow-Origin': cors_origin, 'Vary': 'Origin'},
                    'statusCode': 404,
                    'body': json.dumps({'message': f'{e.message}'}),
                }
            except CCUnsupportedMediaTypeException as e:
                logger.info('Unsupported media type', exc_info=e)
                return {
                    'headers': {'Access-Control-Allow-Origin': cors_origin, 'Vary': 'Origin'},
                    'statusCode': 415,
                    'body': json.dumps({'message': 'Unsupported media type'}),
                }
            except CCRateLimitingException as e:
                logger.info('Rate limiting request', exc_info=e)
                return {
                    'headers': {'Access-Control-Allow-Origin': cors_origin, 'Vary': 'Origin'},
                    'statusCode': 429,
                    'body': json.dumps({'message': e.message}),
                }
            except CCInvalidRequestException as e:
                logger.info('Invalid request', exc_info=e)
                return {
                    'headers': {'Access-Control-Allow-Origin': cors_origin, 'Vary': 'Origin'},
                    'statusCode': 400,
                    'body': json.dumps({'message': e.message}),
                }
            except json.JSONDecodeError as e:
                logger.warning('Invalid JSON in request body', exc_info=e)
                return {
                    'headers': {'Access-Control-Allow-Origin': cors_origin, 'Vary': 'Origin'},
                    'statusCode': 400,
                    'body': json.dumps({'message': 'Invalid request: Malformed JSON'}),
                }
            except ClientError as e:
                # Any boto3 ClientErrors we haven't already caught and transformed are probably on us
                logger.error('boto3 ClientError', response=e.response, exc_info=e)
                raise
            except Exception as e:
                logger.warning(
                    'Error processing request',
                    exc_info=e,
                )
                raise

    return caught_handler


class logger_inject_kwargs:  # noqa: N801 invalid-name
    """Decorator to inject kwargs into the logger context"""

    def __init__(self, logger: Logger, *arg_names: tuple[str, ...]):
        if not isinstance(logger, Logger):
            raise ValueError('logger must be an instance of Logger')
        self.logger = logger
        self.arg_names = arg_names

    def __get__(self, instance, owner):
        return MethodType(self, instance)

    def __call__(self, fn: Callable):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            if not self.arg_names:
                raise ValueError('No argument names provided to logger_inject_kwargs')
            with self.logger.append_context_keys(**{k: kwargs.get(k) for k in self.arg_names}):
                return fn(*args, **kwargs)

        return wrapped


class authorize_compact_level_only_action:  # noqa: N801 invalid-name
    """Authorize endpoint by matching path parameter compact to the expected scope limited to compact level
    (i.e. aslp/admin).

    This wrapper should be used when we want to explicitly restrict access to callers with permission scopes
     at the compact level.
    """

    def __init__(self, action: str):
        super().__init__()
        self.action = action

    def __call__(self, fn: Callable):
        @wraps(fn)
        @logger.inject_lambda_context
        def authorized(event: dict, context: LambdaContext):
            try:
                resource_value = event['pathParameters']['compact']
            except KeyError as e:
                logger.error('Access attempt with missing path parameter!')
                raise CCInvalidRequestException('Missing path parameter!') from e

            logger.debug('Checking authorizer context', request_context=event['requestContext'])
            try:
                scopes = event['requestContext']['authorizer']['claims']['scope'].split(' ')
            except KeyError as e:
                logger.error('Unauthorized access attempt!', exc_info=e)
                raise CCUnauthorizedException('Unauthorized access attempt!') from e

            required_scope = f'{resource_value}/{self.action}'
            if required_scope not in scopes:
                logger.warning('Forbidden access attempt!')
                raise CCAccessDeniedException('Forbidden access attempt!')
            return fn(event, context)

        return authorized


class authorize_state_level_only_action:  # noqa: N801 invalid-name
    """Authorize endpoint by matching path parameter compact to the expected scope limited to state level
    (i.e. oh/{compact}.admin).

    This wrapper should be used when we want to explicitly restrict access to callers with permission scopes
    at the state level.
    """

    def __init__(self, action: str):
        super().__init__()
        self.action = action

    def __call__(self, fn: Callable):
        @wraps(fn)
        @logger.inject_lambda_context
        def authorized(event: dict, context: LambdaContext):
            try:
                compact = event['pathParameters']['compact']
                jurisdiction = event['pathParameters']['jurisdiction']
            except KeyError as e:
                logger.error('Access attempt with missing path parameter!')
                raise CCInvalidRequestException('Missing path parameter!') from e

            logger.debug('Checking authorizer context', request_context=event['requestContext'])
            try:
                scopes = event['requestContext']['authorizer']['claims']['scope'].split(' ')
            except KeyError as e:
                logger.error('Unauthorized access attempt!', exc_info=e)
                raise CCUnauthorizedException('Unauthorized access attempt!') from e

            required_scope = f'{jurisdiction}/{compact}.{self.action}'
            if required_scope not in scopes:
                logger.warning('Forbidden access attempt!')
                raise CCAccessDeniedException('Forbidden access attempt!')

            return fn(event, context)

        return authorized


class authorize_compact:  # noqa: N801 invalid-name
    """Authorize endpoint by matching path parameter compact to the expected scope

    This wrapper checks if the caller has the permission at either the compact or jurisdiction level for the compact
    (i.e. aslp/write or oh/aslp.write).
    """

    def __init__(self, action: str):
        super().__init__()
        self.action = action

    def __call__(self, fn: Callable):
        @wraps(fn)
        @logger.inject_lambda_context
        def authorized(event: dict, context: LambdaContext):
            try:
                compact = event['pathParameters']['compact']
            except KeyError as e:
                logger.error('Access attempt with missing path parameter!')
                raise CCInvalidRequestException('Missing path parameter!') from e

            logger.debug('Checking authorizer context', request_context=event['requestContext'])
            try:
                scopes: list[str] = event['requestContext']['authorizer']['claims']['scope'].split(' ')
            except KeyError as e:
                logger.error('Unauthorized access attempt!', exc_info=e)
                raise CCUnauthorizedException('Unauthorized access attempt!') from e

            compact_level_required_scope = f'{compact}/{self.action}'
            jurisdiction_level_required_scope = f'/{compact}.{self.action}'
            for scope in scopes:
                if compact_level_required_scope == scope or scope.endswith(jurisdiction_level_required_scope):
                    return fn(event, context)
            logger.warning('Forbidden access attempt!')
            raise CCAccessDeniedException('Forbidden access attempt!')

        return authorized


def _authorize_compact_with_scope(event: dict, resource_parameter: str, scope_parameter: str, action: str) -> None:
    """
    Check the authorization of the user attempting to access the endpoint.

    There are three types of action level permissions which can be granted to a user:

    1. read: Allows the user to read data from the compact.
    2. write: Allows the user to write data to the compact.
    3. admin: Allows the user to perform administrative actions on the compact.

    For each of these actions, specific rules apply to the scope required to perform the action, which are
    as follows:

    ReadGeneral - granted at compact level, allows read access to all generally available (not private) jurisdiction
    data within the compact.
    i.e. aslp/readGeneral would allow read access to all generally available jurisdiction data within the aslp compact.

    Write - granted at jurisdiction level, allows write access to a specific jurisdiction within the compact.
    i.e. oh/aslp.write would allow write access to the ohio jurisdiction within the aslp compact.

    Admin - granted at compact level and jurisdiction level, allows administrative access to either a specific
    compact or a specific jurisdiction within the compact.
    i.e. 'aslp/admin' would allow administrative access to the aslp compact. 'oh/aslp.admin' would allow
    administrative access to the ohio jurisdiction within the aslp compact.

    :param dict event: The event object passed to the lambda function.
    :param str resource_parameter: The value of the resource parameter in the path.
    :param str scope_parameter: The value of the scope parameter in the path.
    :param str action: The action we want to ensure the user has permissions for.
    :raises CCUnauthorizedException: If the user is missing scope claims.
    :raises CCAccessDeniedException: If the user does not have the necessary access.
    """
    try:
        resource_value = event['pathParameters'][resource_parameter]
        if scope_parameter != resource_parameter:
            scope_value = event['pathParameters'][scope_parameter]
        else:
            # if the scope parameter is the same as the resource parameter,
            # we use the resource value as the scope value
            scope_value = resource_value
    except KeyError as e:
        logger.error('Access attempt with missing path parameters!')
        raise CCInvalidRequestException('Missing path parameter!') from e

    try:
        scopes = event['requestContext']['authorizer']['claims']['scope'].split(' ')
    except KeyError as e:
        logger.error('Unauthorized access attempt!', exc_info=e)
        raise CCUnauthorizedException('Unauthorized access attempt!') from e

    required_scope = f'{resource_value}/{scope_value}.{action}'
    if required_scope not in scopes:
        logger.warning('Forbidden access attempt!')
        raise CCAccessDeniedException('Forbidden access attempt!')


class authorize_compact_jurisdiction:  # noqa: N801 invalid-name
    """
    Authorize endpoint by matching path parameters compact and jurisdiction to the expected scope.
    (i.e. oh/aslp.write)
    """

    def __init__(self, action: str):
        super().__init__()
        self.resource_parameter = 'jurisdiction'
        self.scope_parameter = 'compact'
        self.action = action

    def __call__(self, fn: Callable):
        @wraps(fn)
        @logger.inject_lambda_context
        def authorized(event: dict, context: LambdaContext):
            _authorize_compact_with_scope(event, self.resource_parameter, self.scope_parameter, self.action)
            return fn(event, context)

        return authorized


def sqs_handler(fn: Callable):
    """Process messages from the ingest queue.

    This handler uses batch item failure reporting:
    https://docs.aws.amazon.com/lambda/latest/dg/example_serverless_SQS_Lambda_batch_item_failures_section.html
    This allows the queue to continue to scale under load, even if a number of the messages are failing. It
    also improves efficiency, as we don't have to throw away the entire batch for a single failure.
    """

    @wraps(fn)
    @metrics.log_metrics
    @logger.inject_lambda_context
    def process_messages(event, context: LambdaContext):  # noqa: ARG001 unused-argument
        records = event['Records']
        logger.info('Starting batch', batch_count=len(records))
        batch_failures = []
        for record in records:
            try:
                message = json.loads(record['body'])
                logger.info(
                    'Processing message',
                    message_id=record['messageId'],
                    message_attributes=record.get('messageAttributes'),
                )
                # No exception here means success
                fn(message)
            # When we receive a batch of messages from SQS, letting an exception escape all the way back to AWS is
            # really undesirable. Instead, we're going to catch _almost_ any exception raised, note what message we
            # were processing, and report those item failures back to AWS.
            except Exception as e:  # noqa: BLE001 broad-exception-caught
                logger.error('Failed to process message', exc_info=e)
                batch_failures.append({'itemIdentifier': record['messageId']})
        logger.info('Completed batch', batch_failures=len(batch_failures))
        return {'batchItemFailures': batch_failures}

    return process_messages


def get_allowed_jurisdictions(*, compact: str, scopes: set[str]) -> list[str] | None:
    """Return a list of jurisdictions the user is allowed to access based on their scopes. If the scopes indicate
    the user is a compact admin, the function will return None, as they will do no jurisdiction-based filtering.
    :param str compact: The compact the user is trying to access.
    :param set scopes: The user's scopes from the request.
    :return: A list of jurisdictions the user is allowed to access, or None, if no filtering is needed.
    :rtype: list
    """
    if f'{compact}/admin' in scopes:
        # The user has compact-level admin, so no jurisdiction filtering
        return None

    compact_jurisdictions = []
    scope_pattern = f'([a-z]*)/{compact}.admin'
    for scope in scopes:
        if match_obj := match(scope_pattern, scope):
            compact_jurisdictions.append(match_obj.group(1))
    return compact_jurisdictions


def get_event_scopes(event: dict):
    """
    Get the scopes from the event object and return them as a list.

    :param dict event: The event object passed to the lambda function.
    :return: The scopes from the event object.
    """
    return set(event['requestContext']['authorizer']['claims']['scope'].split(' '))


def collect_and_authorize_changes(*, path_compact: str, scopes: set, compact_changes: dict) -> dict:
    """Transform PATCH user API changes to permissions into db operation changes. Operation changes are checked
    against the provided scopes to ensure the user is allowed to make the requested changes.
    :param str path_compact: The compact declared in the url path
    :param set scopes: The scopes associated with the user making the request
    :param dict compact_changes: Permissions changes in the request body
    Example:
    {
        'actions': {
            'admin': True,
            'read': False
        },
        'jurisdictions': {
            'oh': {
                'actions': {
                    'admin': True,
                    'write': False
                }
            }
        }
    }
    :return: Changes to the User's underlying record
    :rtype: dict
    """
    compact_action_additions = set()
    compact_action_removals = set()
    jurisdiction_action_additions = {}
    jurisdiction_action_removals = {}

    # Collect compact-wide permission changes
    for action, value in compact_changes.get('actions', {}).items():
        if action == CCPermissionsAction.ADMIN and f'{path_compact}/{CCPermissionsAction.ADMIN}' not in scopes:
            raise CCAccessDeniedException('Only compact admins can affect compact-level admin permissions')
        if action == CCPermissionsAction.READ_PRIVATE and f'{path_compact}/{CCPermissionsAction.ADMIN}' not in scopes:
            raise CCAccessDeniedException('Only compact admins can affect compact-level access to private information')

        # dropping the read action as this is now implicitly granted to all users
        if action == CCPermissionsAction.READ:
            logger.info('Dropping "read" action as this is implicitly granted to all users')
            continue
        # Any admin in the compact can affect read permissions, so no read-specific check is necessary here
        if value:
            compact_action_additions.add(action)
        else:
            compact_action_removals.add(action)

    # Collect jurisdiction-specific changes
    for jurisdiction, jurisdiction_changes in compact_changes.get('jurisdictions', {}).items():
        if not {
            f'{path_compact}/{CCPermissionsAction.ADMIN}',
            f'{jurisdiction}/{path_compact}.{CCPermissionsAction.ADMIN}',
        }.intersection(scopes):
            raise CCAccessDeniedException(
                f'Only {path_compact} or {jurisdiction}/{path_compact} admins can affect {jurisdiction}/{path_compact} '
                'permissions',
            )

        # verify that the jurisdiction is in the list of active jurisdictions for the compact
        active_jurisdictions = config.compact_configuration_client.get_compact_jurisdictions(compact=path_compact)
        active_jurisdictions_postal_abbreviations = [
            jurisdiction['postalAbbreviation'].lower() for jurisdiction in active_jurisdictions
        ]
        if jurisdiction.lower() not in active_jurisdictions_postal_abbreviations:
            raise CCInvalidRequestException(
                f"'{jurisdiction.upper()}' is not a valid jurisdiction for '{path_compact.upper()}' compact"
            )

        for action, value in jurisdiction_changes.get('actions', {}).items():
            # dropping the read action as this is now implicitly granted to all users
            if action == CCPermissionsAction.READ:
                logger.info('Dropping "read" action as this is implicitly granted to all users')
                continue

            if value:
                jurisdiction_action_additions.setdefault(jurisdiction, set()).add(action)
            else:
                jurisdiction_action_removals.setdefault(jurisdiction, set()).add(action)

    return {
        'compact_action_additions': compact_action_additions,
        'compact_action_removals': compact_action_removals,
        'jurisdiction_action_additions': jurisdiction_action_additions,
        'jurisdiction_action_removals': jurisdiction_action_removals,
    }


def get_sub_from_user_attributes(attributes: list):
    for attribute in attributes:
        if attribute['Name'] == 'sub':
            return attribute['Value']
    raise ValueError('Failed to find user sub!')


def _user_has_read_private_access_for_provider(compact: str, provider_information: dict, scopes: set[str]) -> bool:
    return _user_has_permission_for_action_on_user(
        action=CCPermissionsAction.READ_PRIVATE,
        compact=compact,
        provider_information=provider_information,
        scopes=scopes,
    )


def user_has_read_ssn_access_for_provider(compact: str, provider_information: dict, scopes: set[str]) -> bool:
    return _user_has_permission_for_action_on_user(
        action=CCPermissionsAction.READ_SSN, compact=compact, provider_information=provider_information, scopes=scopes
    )


def _user_has_permission_for_action_on_user(
    action: str, compact: str, provider_information: dict, scopes: set[str]
) -> bool:
    if f'{compact}/{action}' in scopes:
        logger.debug(
            f'User has {action} permission at compact level',
            compact=compact,
            provider_id=provider_information['providerId'],
        )
        return True

    # iterate through the users privileges and licenses and create a set out of all the jurisdictions
    relevant_provider_jurisdictions = set()
    for privilege in provider_information.get('privileges', []):
        relevant_provider_jurisdictions.add(privilege['jurisdiction'])
    for license_record in provider_information.get('licenses', []):
        relevant_provider_jurisdictions.add(license_record['jurisdiction'])

    for jurisdiction in relevant_provider_jurisdictions:
        if f'{jurisdiction}/{compact}.{action}' in scopes:
            logger.debug(
                f'User has {action} permission at jurisdiction level',
                compact=compact,
                provider_id=provider_information['providerId'],
                jurisdiction=jurisdiction,
            )
            return True

    logger.debug(
        f'Caller does not have {action} permission at compact or jurisdiction level',
        provider_id=provider_information['providerId'],
    )
    return False


def sanitize_provider_data_based_on_caller_scopes(compact: str, provider: dict, scopes: set[str]) -> dict:
    """
    Take a provider and a set of user scopes, then return a provider, with information sanitized based on what
    the user is authorized to view.

    :param str compact: The compact the user is trying to access.
    :param dict provider: The provider record to be sanitized.
    :param set scopes: The user's scopes from the request.
    :return: The provider record, sanitized based on the user's scopes.
    """
    if _user_has_read_private_access_for_provider(compact=compact, provider_information=provider, scopes=scopes):
        # return full object since caller has 'readPrivate' access for provider
        return provider

    logger.debug(
        'Caller does not have readPrivate at compact or jurisdiction level, removing private information',
        provider_id=provider['providerId'],
    )
    provider_read_general_schema = ProviderGeneralResponseSchema()
    # we filter the record to ensure that the schema is applied to the record to remove private fields
    return provider_read_general_schema.load(provider)


def send_licenses_to_preprocessing_queue(licenses_data: list[dict], event_time: str) -> list[str]:
    """
    Send license data to the preprocessing queue in batches.

    This function batches license data and sends it to the preprocessing queue using the SQS batch send_messages method.
    It handles chunking the data into batches of 10 (SQS batch limit) and tracks failures.

    :param list[dict] licenses_data: List of SERIALIZED license data to send (must be serialized using the
    dump method of the LicensePostRequestSchema)
    :param str event_time: ISO formatted event time string
    :return: list of license numbers that failed to be ingested (if any)
    """
    # Track failures
    failed_license_numbers = []

    # Process in batches of 10 (SQS batch limit)
    batch_size = 10
    for i in range(0, len(licenses_data), batch_size):
        batch = licenses_data[i : i + batch_size]

        # Prepare batch entries
        entries = []
        for idx, license_data in enumerate(batch):
            message_body = json.dumps(
                {
                    'eventTime': event_time,
                    **license_data,
                }
            )
            entries.append(
                {
                    'Id': f'msg-{idx}',  # Unique ID for each message in the batch
                    'MessageBody': message_body,
                }
            )

        try:
            # Send batch to preprocessing queue
            response = config.license_preprocessing_queue.send_messages(Entries=entries)

            # Check for failed messages
            for failed in response.get('Failed', []):
                failed_index = int(failed['Id'].split('-')[-1])
                failed_license_number = batch[failed_index].get('licenseNumber', 'unknown')
                failed_license_numbers.append(failed_license_number)
                logger.error(f'Failed to send message to preprocessing queue: {failed.get("Message", "Unknown error")}')
        except ClientError as e:
            # If the entire batch fails, count all messages as failed
            failed_license_numbers.extend(license_data.get('licenseNumber', 'unknown') for license_data in batch)
            logger.error(f'Error sending batch to preprocessing queue: {str(e)}')

    # Return success status and failure count
    return failed_license_numbers
