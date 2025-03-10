import json
import uuid
from datetime import timedelta

from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.exceptions import ClientError
from cc_common.config import config, logger, metrics
from cc_common.data_model.schema.common import CCPermissionsAction
from cc_common.data_model.schema.provider.api import ProviderGeneralResponseSchema
from cc_common.exceptions import (
    CCAccessDeniedException,
    CCAwsServiceException,
    CCInvalidRequestException,
    CCRateLimitingException,
)
from cc_common.utils import (
    api_handler,
    authorize_compact,
    get_event_scopes,
    sanitize_provider_data_based_on_caller_scopes,
    user_has_read_ssn_access_for_provider,
)

from . import get_provider_information


@api_handler
@authorize_compact(action=CCPermissionsAction.READ_GENERAL)
def query_providers(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """Query providers data
    :param event: Standard API Gateway event, API schema documented in the CDK ApiStack
    :param LambdaContext context:
    """
    compact = event['pathParameters']['compact']

    body = json.loads(event['body'])
    query = body.get('query', {})
    if 'providerId' in query.keys():
        provider_id = query['providerId']
        query = {'providerId': provider_id}
        resp = config.data_client.get_provider(
            compact=compact,
            provider_id=provider_id,
            pagination=body.get('pagination'),
            detail=False,
        )
        resp['query'] = query

    else:
        if 'givenName' in query.keys() and 'familyName' not in query.keys():
            raise CCInvalidRequestException('familyName is required if givenName is provided')
        provider_name = None
        if 'familyName' in query.keys():
            provider_name = (query.get('familyName'), query.get('givenName'))

        jurisdiction = query.get('jurisdiction')

        sorting = body.get('sorting', {})
        sorting_key = sorting.get('key')

        sort_direction = sorting.get('direction', 'ascending')
        scan_forward = sort_direction == 'ascending'

        match sorting_key:
            case None | 'familyName':
                resp = {
                    'query': query,
                    'sorting': {'key': 'familyName', 'direction': sort_direction},
                    **config.data_client.get_providers_sorted_by_family_name(
                        compact=compact,
                        jurisdiction=jurisdiction,
                        provider_name=provider_name,
                        scan_forward=scan_forward,
                        pagination=body.get('pagination'),
                    ),
                }
            case 'dateOfUpdate':
                if provider_name is not None:
                    raise CCInvalidRequestException(
                        'givenName and familyName are not supported for sorting by dateOfUpdate',
                    )
                resp = {
                    'query': query,
                    'sorting': {'key': 'dateOfUpdate', 'direction': sort_direction},
                    **config.data_client.get_providers_sorted_by_updated(
                        compact=compact,
                        jurisdiction=jurisdiction,
                        scan_forward=scan_forward,
                        pagination=body.get('pagination'),
                    ),
                }
            case _:
                # This shouldn't happen unless our api validation gets misconfigured
                raise CCInvalidRequestException(f"Invalid sort key: '{sorting_key}'")
    # Convert generic field to more specific one for this API and sanitize data
    unsanitized_providers = resp.pop('items', [])
    # for the query endpoint, we only return generally available data, regardless of the caller's scopes
    general_schema = ProviderGeneralResponseSchema()
    sanitized_providers = [general_schema.load(provider) for provider in unsanitized_providers]

    resp['providers'] = sanitized_providers

    return resp


@api_handler
@authorize_compact(action=CCPermissionsAction.READ_GENERAL)
def get_provider(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """Return one provider's data
    :param event: Standard API Gateway event, API schema documented in the CDK ApiStack
    :param LambdaContext context:
    """
    try:
        compact = event['pathParameters']['compact']
        provider_id = event['pathParameters']['providerId']
    except (KeyError, TypeError) as e:
        # This shouldn't happen without miss-configuring the API, but we'll handle it, anyway
        logger.error(f'Missing parameter: {e}')
        raise CCInvalidRequestException('Missing required field') from e

    with logger.append_context_keys(compact=compact, provider_id=provider_id):
        provider_information = get_provider_information(compact=compact, provider_id=provider_id)

        return sanitize_provider_data_based_on_caller_scopes(
            compact=compact, provider=provider_information, scopes=get_event_scopes(event)
        )


@api_handler
@authorize_compact(action=CCPermissionsAction.READ_SSN)
def get_provider_ssn(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """
    Return one provider's SSN
    :param event: Standard API Gateway event, API schema documented in the CDK ApiStack
    :param LambdaContext context:
    """
    compact = event['pathParameters']['compact']
    provider_id = event['pathParameters']['providerId']
    user_id = event['requestContext']['authorizer']['claims']['sub']

    with logger.append_context_keys(compact=compact, provider_id=provider_id, user_id=user_id):
        logger.info('Processing provider SSN request')

        # Check if the user has exceeded the rate limit
        if _ssn_rate_limit_exceeded(user_id=user_id, provider_id=provider_id, compact=compact):
            metrics.add_metric(name='rate-limited-ssn-access', value=1, unit='Count')
            logger.warning('Rate limited SSN access attempt')
            raise CCRateLimitingException(
                'Rate limit exceeded. You have reached the maximum number of SSN requests allowed in a 24-hour period.'
            )

        provider_information = get_provider_information(compact=compact, provider_id=provider_id)

        # Inspect the caller's scopes to determine if they have readSSN permission for this provider
        if not user_has_read_ssn_access_for_provider(
            compact=compact,
            provider_information=provider_information,
            scopes=get_event_scopes(event),
        ):
            metrics.add_metric(name='unauthorized-ssn-access', value=1, unit='Count')
            logger.warning('Unauthorized SSN access attempt')
            raise CCAccessDeniedException(
                f'User does not have {CCPermissionsAction.READ_SSN} permission for this provider'
            )

        # Query the provider's SSN from the database
        ssn = config.data_client.get_ssn_by_provider_id(compact=compact, provider_id=provider_id)

        metrics.add_metric(name='read-ssn', value=1, unit='Count')
        # Return the SSN to the caller
        return {
            'ssn': ssn,
        }


def _ssn_rate_limit_exceeded(user_id: str, provider_id: str, compact: str) -> bool:
    """Check if the user has exceeded the SSN rate limit.

    :param user_id: The Cognito user ID of the staff user
    :param provider_id: The provider ID being accessed
    :param compact: The compact being accessed
    :return: True if rate limit is exceeded, False otherwise
    """
    now = config.current_standard_datetime
    window_start = now - timedelta(hours=24)
    window_start_timestamp = window_start.timestamp()
    now_timestamp = now.timestamp()

    # Generate a unique ID for this request
    # This ensures every request is recorded, even for requests within the same second
    request_sk = f'TIME#{now_timestamp}#UUID#{uuid.uuid4()}'

    try:
        # First, record this request in the rate limiting table
        config.rate_limiting_table.put_item(
            Item={
                'pk': 'READ_SSN_REQUESTS',
                'sk': request_sk,
                'compact': compact,
                'provider_id': provider_id,
                'staffUserId': user_id,
                'ttl': int(now_timestamp) + 86400,  # 24 hours in seconds
            }
        )

        # Check if the global rate limit has been exceeded (more than 15 requests in 24 hours)
        all_requests = config.rate_limiting_table.query(
            KeyConditionExpression='pk = :pk AND sk BETWEEN :start_sk AND :end_sk',
            ExpressionAttributeValues={
                ':pk': 'READ_SSN_REQUESTS',
                ':start_sk': f'TIME#{window_start_timestamp}',
                # Add 1 second to ensure we include all records at the current timestamp
                ':end_sk': f'TIME#{now_timestamp + 1}',
            },
            ConsistentRead=True,
        )

        global_request_count = len(all_requests['Items'])
        logger.info(f'Global SSN request count in last 24 hours: {global_request_count}')

        # If there are more than 15 requests globally in the last 24 hours, throttle the entire endpoint
        if global_request_count > 15:
            logger.critical(
                'Global SSN rate limit exceeded, throttling endpoint',
                global_request_count=global_request_count,
                current_request_user_id=user_id,
                current_request_compact=compact,
            )

            # Set the lambda's reserved concurrency to 0 to throttle the endpoint
            try:
                config.lambda_client.put_function_concurrency(
                    FunctionName=config.current_lambda_name, ReservedConcurrentExecutions=0
                )
                logger.critical('Lambda concurrency set to 0 due to excessive SSN requests')
                metrics.add_metric(name='ssn-endpoint-throttled', value=1, unit='Count')
            except ClientError as e:
                logger.error('Failed to set lambda concurrency', error=str(e))

            return True

        # Count how many requests were made by this user
        user_request_count = 0
        for item in all_requests.get('Items', []):
            if item.get('staffUserId') == user_id:
                user_request_count += 1

        logger.info(f'User SSN request count: {user_request_count}', user_id=user_id)

        # If there are more than 7 requests by this user in the window, deactivate the user's account
        if user_request_count >= 7:
            logger.warning(
                'User exceeded SSN rate limit multiple times, deactivating account',
                user_id=user_id,
                request_count=user_request_count,
            )

            # Deactivate the user's account
            try:
                config.cognito_client.admin_disable_user(UserPoolId=config.user_pool_id, Username=user_id)
                logger.warning('User account deactivated due to excessive SSN requests', user_id=user_id)
            except ClientError as e:
                logger.error('Failed to deactivate user account', error=str(e), user_id=user_id)

            return True

        # If there are 5 or more requests by this user in the window, rate limit is exceeded
        if user_request_count >= 6:
            logger.warning('SSN rate limit exceeded for user', user_id=user_id, request_count=user_request_count)
            return True

        logger.info(
            'Rate limit has not been exceeded, proceeding with request',
            user_request_count=user_request_count,
            staff_user_id=user_id,
            provider_id=provider_id,
        )
        return False
    except ClientError as e:
        logger.error('Failed to check SSN rate limit', error=str(e))
        raise CCAwsServiceException('Failed to check SSN rate limit') from e
