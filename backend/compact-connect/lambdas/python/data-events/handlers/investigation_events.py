from uuid import UUID

from cc_common.config import config, logger
from cc_common.data_model.provider_record_util import ProviderUserRecords
from cc_common.data_model.schema.data_event.api import InvestigationEventDetailSchema
from cc_common.data_model.schema.provider import ProviderData
from cc_common.email_service_client import InvestigationNotificationTemplateVariables, ProviderNotificationMethod
from cc_common.license_util import LicenseUtility
from cc_common.utils import sqs_handler


def _get_license_type_name(compact: str, license_type_abbreviation: str) -> str:
    """
    Get the license type name from abbreviation.

    :param compact: The compact identifier
    :param license_type_abbreviation: The license type abbreviation
    :return: The license type name
    """
    return LicenseUtility.get_license_type_by_abbreviation(compact, license_type_abbreviation).name


def _get_provider_records(compact: str, provider_id: str) -> tuple[ProviderUserRecords, ProviderData]:
    """
    Retrieve and validate provider records for notification processing.

    :param compact: The compact identifier
    :param provider_id: The provider ID
    :return: Tuple of (provider_records, provider_record)
    :raises Exception: If provider records cannot be retrieved
    """
    try:
        provider_records = config.data_client.get_provider_user_records(
            compact=compact,
            provider_id=provider_id,
        )
        provider_record = provider_records.get_provider_record()
        return provider_records, provider_record
    except Exception as e:
        logger.error('Failed to retrieve provider records for notification', exception=str(e))
        raise


def _send_provider_notification(
    notification_method: ProviderNotificationMethod,
    notification_type: str,
    *,
    provider_record: ProviderData,
    compact: str,
    **notification_kwargs,
) -> None:
    """
    Send notification to provider if they are registered.

    :param provider_record: The provider record
    :param notification_method: The email service method to call
    :param notification_type: Type of notification for logging
    :param compact: The compact identifier
    :param notification_kwargs: Additional arguments for the notification method
    """
    provider_email = provider_record.compactConnectRegisteredEmailAddress
    if provider_email:
        logger.info(f'Sending {notification_type} notification to provider', provider_email=provider_email)
        try:
            notification_method(
                compact=compact,
                provider_email=provider_email,
                template_variables=InvestigationNotificationTemplateVariables(
                    provider_first_name=provider_record.givenName,
                    provider_last_name=provider_record.familyName,
                    **notification_kwargs,
                ),
            )
        except Exception as e:
            logger.error('Failed to send provider notification', exception=str(e))
            raise
    else:
        logger.info('Provider not registered in system, skipping provider notification')


def _send_primary_state_notification(
    notification_method: ProviderNotificationMethod,
    notification_type: str,
    *,
    provider_record: ProviderData,
    jurisdiction: str,
    compact: str,
    **notification_kwargs,
) -> None:
    """
    Send notification to the primary affected state.

    :param notification_method: The email service method to call
    :param notification_type: Type of notification for logging
    :param provider_record: The provider record
    :param jurisdiction: The jurisdiction to notify
    :param compact: The compact identifier
    :param notification_kwargs: Additional arguments for the notification method
    """
    logger.info(f'Sending {notification_type} notification to affected state', affected_jurisdiction=jurisdiction)
    try:
        notification_method(
            compact=compact,
            jurisdiction=jurisdiction,
            template_variables=InvestigationNotificationTemplateVariables(
                provider_first_name=provider_record.givenName,
                provider_last_name=provider_record.familyName,
                **notification_kwargs,
            ),
        )
    except Exception as e:
        logger.error('Failed to send state notification', jurisdiction=jurisdiction, exception=str(e))
        raise


def _send_additional_state_notifications(
    notification_method: ProviderNotificationMethod,
    notification_type: str,
    *,
    provider_records: ProviderUserRecords,
    provider_record: ProviderData,
    provider_id: UUID,
    excluded_jurisdiction: str,
    compact: str,
    **notification_kwargs,
) -> None:
    """
    Send notifications to all other states where the provider has licenses or privileges.

    :param provider_records: The provider records collection
    :param notification_method: The email service method to call
    :param notification_type: Type of notification for logging
    :param provider_record: The provider record
    :param provider_id: The provider ID
    :param excluded_jurisdiction: Jurisdiction to exclude from notifications
    :param compact: The compact identifier
    :param notification_kwargs: Additional arguments for the notification method
    """
    # Query provider's records to find all states where they hold or have held licenses or privileges
    all_licenses = provider_records.get_license_records()
    all_privileges = provider_records.get_privilege_records()

    # Get unique jurisdictions (excluding the one already notified)
    notification_jurisdictions = set()
    for license_record in all_licenses:
        if license_record.jurisdiction != excluded_jurisdiction:
            notification_jurisdictions.add(license_record.jurisdiction)
    for privilege_record in all_privileges:
        if privilege_record.jurisdiction != excluded_jurisdiction:
            notification_jurisdictions.add(privilege_record.jurisdiction)

    # Send notifications to all other states with provider licenses or privileges
    template_variables = InvestigationNotificationTemplateVariables(
        provider_first_name=provider_record.givenName,
        provider_last_name=provider_record.familyName,
        provider_id=provider_id,
        **notification_kwargs,
    )
    for notification_jurisdiction in notification_jurisdictions:
        logger.info(
            f'Sending {notification_type} notification to other state',
            notification_jurisdiction=notification_jurisdiction,
        )
        try:
            notification_method(
                compact=compact,
                jurisdiction=notification_jurisdiction,
                template_variables=template_variables,
            )
        except Exception as e:
            logger.error(
                'Failed to send notification to other state',
                notification_jurisdiction=notification_jurisdiction,
                exception=str(e),
            )
            raise


@sqs_handler
def license_investigation_notification_listener(message: dict):
    """
    Handle license investigation events by sending notifications.

    This handler processes 'license.investigation' events and sends notifications
    to the affected provider and relevant states.
    """
    detail_schema = InvestigationEventDetailSchema()
    detail = detail_schema.load(message['detail'])

    compact = detail['compact']
    provider_id = detail['providerId']
    jurisdiction = detail['jurisdiction']
    license_type_abbreviation = detail['licenseTypeAbbreviation']
    event_time = detail['eventTime']

    with logger.append_context_keys(
        compact=compact,
        provider_id=provider_id,
        jurisdiction=jurisdiction,
        license_type_abbreviation=license_type_abbreviation,
        event_time=event_time,
    ):
        logger.info('Processing license investigation event')

        # Get license type name from abbreviation (lookup once at the top)
        license_type_name = _get_license_type_name(compact, license_type_abbreviation)

        # Get provider records to gather notification targets and provider information
        provider_records, provider_record = _get_provider_records(compact, provider_id)

        # Provider Notification
        _send_provider_notification(
            config.email_service_client.send_license_investigation_provider_notification_email,
            'license investigation',
            provider_record=provider_record,
            compact=compact,
            investigation_jurisdiction=jurisdiction,
            license_type=license_type_name,
        )

        # State Notifications
        # Send notification to the state where the license is under investigation
        _send_primary_state_notification(
            config.email_service_client.send_license_investigation_state_notification_email,
            'license investigation',
            provider_record=provider_record,
            provider_id=provider_id,
            jurisdiction=jurisdiction,
            compact=compact,
            investigation_jurisdiction=jurisdiction,
            license_type=license_type_name,
        )

        # Send notifications to all other states with provider licenses or privileges
        _send_additional_state_notifications(
            config.email_service_client.send_license_investigation_state_notification_email,
            'license investigation',
            provider_records=provider_records,
            provider_record=provider_record,
            provider_id=provider_id,
            excluded_jurisdiction=jurisdiction,
            compact=compact,
            investigation_jurisdiction=jurisdiction,
            license_type=license_type_name,
        )

        logger.info('Successfully processed license investigation event')


@sqs_handler
def license_investigation_closed_notification_listener(message: dict):
    """
    Handle license investigation closed events by sending notifications.

    This handler processes 'license.investigationClosed' events and sends notifications
    to the affected provider and relevant states.
    """
    detail_schema = InvestigationEventDetailSchema()
    detail = detail_schema.load(message['detail'])

    compact = detail['compact']
    provider_id = detail['providerId']
    jurisdiction = detail['jurisdiction']
    license_type_abbreviation = detail['licenseTypeAbbreviation']
    event_time = detail['eventTime']

    with logger.append_context_keys(
        compact=compact,
        provider_id=provider_id,
        jurisdiction=jurisdiction,
        license_type_abbreviation=license_type_abbreviation,
        event_time=event_time,
    ):
        logger.info('Processing license investigation closed event')

        # Get license type name from abbreviation (lookup once at the top)
        license_type_name = _get_license_type_name(compact, license_type_abbreviation)

        # Get provider records to gather notification targets and provider information
        provider_records, provider_record = _get_provider_records(compact, provider_id)

        # Provider Notification
        _send_provider_notification(
            config.email_service_client.send_license_investigation_closed_provider_notification_email,
            'license investigation closed',
            provider_record=provider_record,
            compact=compact,
            investigation_jurisdiction=jurisdiction,
            license_type=license_type_name,
        )

        # State Notifications
        # Send notification to the state where the license investigation was closed
        _send_primary_state_notification(
            config.email_service_client.send_license_investigation_closed_state_notification_email,
            'license investigation closed',
            provider_record=provider_record,
            provider_id=provider_id,
            jurisdiction=jurisdiction,
            compact=compact,
            investigation_jurisdiction=jurisdiction,
            license_type=license_type_name,
        )

        # Send notifications to all other states with provider licenses or privileges
        _send_additional_state_notifications(
            config.email_service_client.send_license_investigation_closed_state_notification_email,
            'license investigation closed',
            provider_records=provider_records,
            provider_record=provider_record,
            provider_id=provider_id,
            excluded_jurisdiction=jurisdiction,
            compact=compact,
            investigation_jurisdiction=jurisdiction,
            license_type=license_type_name,
        )

        logger.info('Successfully processed license investigation closed event')


@sqs_handler
def privilege_investigation_notification_listener(message: dict):
    """
    Handle privilege investigation events by sending notifications.

    This handler processes 'privilege.investigation' events and sends notifications
    to the affected provider and relevant states.
    """
    detail_schema = InvestigationEventDetailSchema()
    detail = detail_schema.load(message['detail'])

    compact = detail['compact']
    provider_id = detail['providerId']
    jurisdiction = detail['jurisdiction']
    license_type_abbreviation = detail['licenseTypeAbbreviation']
    event_time = detail['eventTime']

    with logger.append_context_keys(
        compact=compact,
        provider_id=provider_id,
        jurisdiction=jurisdiction,
        license_type_abbreviation=license_type_abbreviation,
        event_time=event_time,
    ):
        logger.info('Processing privilege investigation event')

        # Get license type name from abbreviation (lookup once at the top)
        license_type_name = _get_license_type_name(compact, license_type_abbreviation)

        # Get provider records to gather notification targets and provider information
        provider_records, provider_record = _get_provider_records(compact, provider_id)

        # Provider Notification
        _send_provider_notification(
            config.email_service_client.send_privilege_investigation_provider_notification_email,
            'privilege investigation',
            provider_record=provider_record,
            compact=compact,
            investigation_jurisdiction=jurisdiction,
            license_type=license_type_name,
        )

        # State Notifications
        # Send notification to the state where the privilege is under investigation
        _send_primary_state_notification(
            config.email_service_client.send_privilege_investigation_state_notification_email,
            'privilege investigation',
            provider_record=provider_record,
            provider_id=provider_id,
            jurisdiction=jurisdiction,
            compact=compact,
            investigation_jurisdiction=jurisdiction,
            license_type=license_type_name,
        )

        # Send notifications to all other states with provider licenses or privileges
        _send_additional_state_notifications(
            config.email_service_client.send_privilege_investigation_state_notification_email,
            'privilege investigation',
            provider_records=provider_records,
            provider_record=provider_record,
            provider_id=provider_id,
            excluded_jurisdiction=jurisdiction,
            compact=compact,
            investigation_jurisdiction=jurisdiction,
            license_type=license_type_name,
        )

        logger.info('Successfully processed privilege investigation event')


@sqs_handler
def privilege_investigation_closed_notification_listener(message: dict):
    """
    Handle privilege investigation closed events by sending notifications.

    This handler processes 'privilege.investigationClosed' events and sends notifications
    to the affected provider and relevant states.
    """
    detail_schema = InvestigationEventDetailSchema()
    detail = detail_schema.load(message['detail'])

    compact = detail['compact']
    provider_id = detail['providerId']
    jurisdiction = detail['jurisdiction']
    license_type_abbreviation = detail['licenseTypeAbbreviation']
    event_time = detail['eventTime']

    with logger.append_context_keys(
        compact=compact,
        provider_id=provider_id,
        jurisdiction=jurisdiction,
        license_type_abbreviation=license_type_abbreviation,
        event_time=event_time,
    ):
        logger.info('Processing privilege investigation closed event')

        # Get license type name from abbreviation (lookup once at the top)
        license_type_name = _get_license_type_name(compact, license_type_abbreviation)

        # Get provider records to gather notification targets and provider information
        provider_records, provider_record = _get_provider_records(compact, provider_id)

        # Provider Notification
        _send_provider_notification(
            config.email_service_client.send_privilege_investigation_closed_provider_notification_email,
            'privilege investigation closed',
            provider_record=provider_record,
            compact=compact,
            investigation_jurisdiction=jurisdiction,
            license_type=license_type_name,
        )

        # State Notifications
        # Send notification to the state where the privilege investigation was closed
        _send_primary_state_notification(
            config.email_service_client.send_privilege_investigation_closed_state_notification_email,
            'privilege investigation closed',
            provider_record=provider_record,
            provider_id=provider_id,
            jurisdiction=jurisdiction,
            compact=compact,
            investigation_jurisdiction=jurisdiction,
            license_type=license_type_name,
        )

        # Send notifications to all other states with provider licenses or privileges
        _send_additional_state_notifications(
            config.email_service_client.send_privilege_investigation_closed_state_notification_email,
            'privilege investigation closed',
            provider_records=provider_records,
            provider_record=provider_record,
            provider_id=provider_id,
            excluded_jurisdiction=jurisdiction,
            compact=compact,
            investigation_jurisdiction=jurisdiction,
            license_type=license_type_name,
        )

        logger.info('Successfully processed privilege investigation closed event')
