import json

from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger
from cc_common.exceptions import CCInternalException, CCInvalidRequestException
from cc_common.utils import api_handler
from feature_flag_client import FeatureFlagRequest, FeatureFlagValidationException, create_feature_flag_client

# Initialize feature flag client outside of handler for caching
feature_flag_client = create_feature_flag_client(environment=config.environment_name)


@api_handler
def check_feature_flag(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """
    Public endpoint for checking feature flags.

    This endpoint is designed to be called by other parts of the system for feature flag evaluation.
    It abstracts away the underlying feature flag provider and provides a consistent interface for
    checking feature flags.
    """
    try:
        # Extract flagId from path parameters
        path_parameters = event.get('pathParameters') or {}
        flag_id = path_parameters.get('flagId')

        if not flag_id:
            raise CCInvalidRequestException('flagId is required in the URL path')

        # Parse and validate request body using client's validation
        try:
            body = json.loads(event['body'])
            validated_body = feature_flag_client.validate_request(body)
        except FeatureFlagValidationException as e:
            logger.warning('Feature flag validation failed', error=str(e))
            raise CCInvalidRequestException(str(e)) from e

        # Create request object for flag evaluation with flagId from path
        flag_request = FeatureFlagRequest(flagName=flag_id, context=validated_body.get('context', {}))

        # Check the feature flag
        result = feature_flag_client.check_flag(flag_request)

        logger.debug('Feature flag checked', flag_name=flag_id, enabled=result.enabled)

        # Return simple response with just the enabled status
        return {'enabled': result.enabled}

    except CCInvalidRequestException:
        # Re-raise CC exceptions as-is
        raise
    except Exception as e:
        logger.error(f'Unexpected error checking feature flag: {e}')
        raise CCInternalException('Feature flag check failed') from e
