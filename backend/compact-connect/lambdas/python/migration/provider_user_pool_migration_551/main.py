import os
from botocore.exceptions import ClientError
from cc_common.config import config, logger
from custom_resource_handler import CustomResourceHandler, CustomResourceResponse


class ProviderUserPoolMigration(CustomResourceHandler):
    """Migration for deleting the cognito domain from the deprecated user pool."""

    def on_create(self, properties: dict) -> None:
        do_migration(properties)

    def on_update(self, properties: dict) -> None:
        do_migration(properties)

    def on_delete(self, _properties: dict) -> CustomResourceResponse | None:
        """
        No roll-back on delete.
        """


on_event = ProviderUserPoolMigration('provider-user-pool-migration-551')


def do_migration(_properties: dict) -> None:
    """
    This migration deletes the user pool domain from the deprecated user pool
    to allow the new user pool to use the same domain prefix.
    """
    logger.info('Starting provider user pool migration - deleting user pool domain from deprecated user pool')
    
    # Validate required environment variables
    user_pool_id = os.environ.get('PROVIDER_USER_POOL_ID')
    user_pool_domain = os.environ.get('PROVIDER_USER_POOL_DOMAIN')
    
    if not user_pool_id:
        raise ValueError('PROVIDER_USER_POOL_ID environment variable is required')
    if not user_pool_domain:
        raise ValueError('PROVIDER_USER_POOL_DOMAIN environment variable is required')
    
    logger.info(f'Attempting to delete domain "{user_pool_domain}" from user pool "{user_pool_id}"')
    
    try:
        config.cognito_client.delete_user_pool_domain(
            UserPoolId=user_pool_id,
            Domain=user_pool_domain
        )
        logger.info(f'Successfully deleted domain "{user_pool_domain}" from user pool "{user_pool_id}"')
    except ClientError as e:
        error_code = e.response['Error']['Code']
        
        if error_code == 'ResourceNotFoundException':
            # Domain doesn't exist - this is OK, migration is idempotent
            logger.info(f'Domain "{user_pool_domain}" not found for user pool "{user_pool_id}" - '
                       'assuming already deleted (idempotent operation)')
        elif error_code == 'InvalidParameterException':
            # This could mean the domain doesn't exist or the user pool doesn't exist
            logger.info(f'Invalid parameter when deleting domain "{user_pool_domain}" from user pool "{user_pool_id}" - '
                       'assuming already deleted (idempotent operation)')
        else:
            # Unexpected error - re-raise
            logger.error(f'Unexpected error deleting domain "{user_pool_domain}" from user pool "{user_pool_id}": {e}')
            raise
    except Exception as e:
        logger.error(f'Unexpected error deleting domain "{user_pool_domain}" from user pool "{user_pool_id}": {e}')
        raise
    
    logger.info('Provider user pool domain cleanup completed successfully')



