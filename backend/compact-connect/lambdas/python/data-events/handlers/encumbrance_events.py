from cc_common.config import config, logger
from cc_common.data_model.schema.common import ActiveInactiveStatus
from cc_common.event_batch_writer import EventBatchWriter
from cc_common.event_bus_client import EventBusClient
from cc_common.license_util import LicenseUtility
from cc_common.utils import sqs_handler


@sqs_handler
def license_encumbrance_listener(message: dict):
    """
    Handle license encumbrance events by encumbering associated privileges.

    This handler processes 'license.encumbrance' events and automatically encumbers
    all privileges associated with the encumbered license, then publishes privilege
    encumbrance events for each affected privilege.
    """
    detail = message['detail']
    compact = detail['compact']
    provider_id = detail['providerId']
    jurisdiction = detail['jurisdiction']
    license_type_abbreviation = detail['licenseTypeAbbreviation']
    effective_start_date = detail['effectiveStartDate']

    with logger.append_context_keys(
        compact=compact,
        provider_id=provider_id,
        jurisdiction=jurisdiction,
        license_type_abbreviation=license_type_abbreviation,
    ):
        logger.info('Processing license encumbrance event')

        # Encumber the privileges using the data client method
        affected_privileges = config.data_client.encumber_home_jurisdiction_license_privileges(
            compact=compact,
            provider_id=provider_id,
            jurisdiction=jurisdiction,
            license_type_abbreviation=license_type_abbreviation,
        )

        # Publish privilege encumbrance events for each privilege that was encumbered
        if affected_privileges:
            event_bus_client = EventBusClient()
            with EventBatchWriter(config.events_client) as event_batch_writer:
                for privilege in affected_privileges:
                    logger.info(
                        'Publishing privilege encumbrance event for affected privilege',
                        privilege_jurisdiction=privilege.jurisdiction,
                    )
                    event_bus_client.publish_privilege_encumbrance_event(
                        source='data-events.license-encumbrance',
                        compact=compact,
                        provider_id=provider_id,
                        jurisdiction=privilege.jurisdiction,  # The privilege jurisdiction, not the license jurisdiction
                        license_type_abbreviation=license_type_abbreviation,
                        effective_start_date=effective_start_date,
                        event_batch_writer=event_batch_writer,
                    )

        logger.info('Successfully processed license encumbrance event', privileges_encumbered=len(affected_privileges))


@sqs_handler
def license_encumbrance_lifted_listener(message: dict):
    """
    Handle license encumbrance lifting events by unencumbering associated privileges.

    This handler processes 'license.encumbranceLifted' events and automatically unencumbers
    privileges that were encumbered due to the license encumbrance (but not those with
    their own separate encumbrances), then publishes privilege encumbrance lifting events
    for each affected privilege.
    """
    detail = message['detail']
    compact = detail['compact']
    provider_id = detail['providerId']
    jurisdiction = detail['jurisdiction']
    license_type_abbreviation = detail['licenseTypeAbbreviation']
    effective_lift_date = detail['effectiveLiftDate']

    with logger.append_context_keys(
        compact=compact,
        provider_id=provider_id,
        jurisdiction=jurisdiction,
        license_type_abbreviation=license_type_abbreviation,
    ):
        logger.info('Processing license encumbrance lifting event')

        # lift encumbrances from the privileges associated with this license using the data client method
        affected_privileges = config.data_client.lift_home_jurisdiction_license_privilege_encumbrances(
            compact=compact,
            provider_id=provider_id,
            jurisdiction=jurisdiction,
            license_type_abbreviation=license_type_abbreviation,
        )

        # Publish privilege encumbrance lifting events for each privilege that was unencumbered
        if affected_privileges:
            event_bus_client = EventBusClient()
            with EventBatchWriter(config.events_client) as event_batch_writer:
                for privilege in affected_privileges:
                    logger.info(
                        'Publishing privilege encumbrance lifting event for affected privilege',
                        privilege_jurisdiction=privilege.jurisdiction,
                    )
                    event_bus_client.publish_privilege_encumbrance_lifting_event(
                        source='data-events.license-encumbrance-lifting',
                        compact=compact,
                        provider_id=provider_id,
                        jurisdiction=privilege.jurisdiction,  # The privilege jurisdiction, not the license jurisdiction
                        license_type_abbreviation=license_type_abbreviation,
                        effective_lift_date=effective_lift_date,
                        event_batch_writer=event_batch_writer,
                    )

        logger.info(
            'Successfully processed license encumbrance lifting event', privileges_unencumbered=len(affected_privileges)
        )


@sqs_handler
def privilege_encumbrance_listener(message: dict):
    """
    Handle privilege encumbrance events by sending notifications.

    This handler processes 'privilege.encumbrance' events and sends notifications
    to the affected provider and relevant states.
    """
    detail = message['detail']
    compact = detail['compact']
    provider_id = detail['providerId']
    jurisdiction = detail['jurisdiction']
    license_type_abbreviation = detail['licenseTypeAbbreviation']
    effective_start_date = detail['effectiveStartDate']
    event_time = detail['eventTime']

    with logger.append_context_keys(
        compact=compact,
        provider_id=provider_id,
        jurisdiction=jurisdiction,
        license_type_abbreviation=license_type_abbreviation,
        event_time=event_time,
    ):
        logger.info('Processing privilege encumbrance event')

        # Get license type name from abbreviation (lookup once at the top)
        license_type_name = LicenseUtility.get_license_type_by_abbreviation(compact, license_type_abbreviation).name

        # Get provider records to gather notification targets and provider information
        try:
            provider_records = config.data_client.get_provider_user_records(
                compact=compact,
                provider_id=provider_id,
            )
        except Exception as e:
            logger.error('Failed to retrieve provider records for notification', exception=str(e))
            raise

        provider_record = provider_records.get_provider_record()

        # Provider Notification
        provider_email = provider_record.compactConnectRegisteredEmailAddress
        if provider_email:
            logger.info('Sending privilege encumbrance notification to provider', provider_email=provider_email)
            try:
                config.email_service_client.send_privilege_encumbrance_provider_notification_email(
                    compact=compact,
                    provider_email=provider_email,
                    provider_first_name=provider_record.givenName,
                    provider_last_name=provider_record.familyName,
                    encumbered_jurisdiction=jurisdiction,
                    license_type=license_type_name,
                    effective_start_date=effective_start_date,
                )
            except Exception as e:
                logger.error('Failed to send provider notification', exception=str(e))
                # Re-raise to ensure the event is retried
                raise
        else:
            logger.info('Provider not registered in system, skipping provider notification')

        # State Notifications
        # Send notification to the state where the privilege is encumbered
        logger.info('Sending privilege encumbrance notification to affected state', affected_jurisdiction=jurisdiction)
        try:
            config.email_service_client.send_privilege_encumbrance_state_notification_email(
                compact=compact,
                jurisdiction=jurisdiction,
                provider_first_name=provider_record.givenName,
                provider_last_name=provider_record.familyName,
                provider_id=provider_id,
                encumbered_jurisdiction=jurisdiction,
                license_type=license_type_name,
                effective_start_date=effective_start_date,
            )
        except Exception as e:
            logger.error('Failed to send state notification', jurisdiction=jurisdiction, exception=str(e))
            # Re-raise to ensure the event is retried
            raise

        # Query provider's records to find all states where they hold active licenses or privileges
        active_licenses = provider_records.get_license_records(
            filter_condition=lambda license_record: license_record.licenseStatus == ActiveInactiveStatus.ACTIVE
        )
        active_privileges = provider_records.get_privilege_records(
            filter_condition=lambda privilege_record: privilege_record.status == ActiveInactiveStatus.ACTIVE
        )

        # Get unique jurisdictions (excluding the one already notified)
        notification_jurisdictions = set()
        for license_record in active_licenses:
            if license_record.jurisdiction != jurisdiction:
                notification_jurisdictions.add(license_record.jurisdiction)
        for privilege_record in active_privileges:
            if privilege_record.jurisdiction != jurisdiction:
                notification_jurisdictions.add(privilege_record.jurisdiction)

        # Send notifications to all other states with provider licenses or privileges
        for notification_jurisdiction in notification_jurisdictions:
            logger.info(
                'Sending privilege encumbrance notification to other state',
                notification_jurisdiction=notification_jurisdiction,
            )
            try:
                config.email_service_client.send_privilege_encumbrance_state_notification_email(
                    compact=compact,
                    jurisdiction=notification_jurisdiction,
                    provider_first_name=provider_record.givenName,
                    provider_last_name=provider_record.familyName,
                    provider_id=provider_id,
                    encumbered_jurisdiction=jurisdiction,  # The jurisdiction where encumbrance occurred
                    license_type=license_type_name,
                    effective_start_date=effective_start_date,
                )
            except Exception as e:
                logger.error(
                    'Failed to send notification to other state',
                    notification_jurisdiction=notification_jurisdiction,
                    exception=str(e),
                )
                # Re-raise to ensure the event is retried
                raise

        logger.info('Successfully processed privilege encumbrance event')


@sqs_handler
def privilege_encumbrance_lifting_listener(message: dict):
    """
    Handle privilege encumbrance lifting events by sending notifications.

    This handler processes 'privilege.encumbranceLifted' events and sends notifications
    to the affected provider and relevant states.
    """
    detail = message['detail']
    compact = detail['compact']
    provider_id = detail['providerId']
    jurisdiction = detail['jurisdiction']
    license_type_abbreviation = detail['licenseTypeAbbreviation']
    effective_lift_date = detail['effectiveLiftDate']
    event_time = detail['eventTime']

    with logger.append_context_keys(
        compact=compact,
        provider_id=provider_id,
        jurisdiction=jurisdiction,
        license_type_abbreviation=license_type_abbreviation,
        event_time=event_time,
    ):
        logger.info('Processing privilege encumbrance lifting event')

        # Get license type name from abbreviation (lookup once at the top)
        license_type_name = LicenseUtility.get_license_type_by_abbreviation(compact, license_type_abbreviation).name

        # Get provider records to gather notification targets and provider information
        try:
            provider_records = config.data_client.get_provider_user_records(
                compact=compact,
                provider_id=provider_id,
            )
        except Exception as e:
            logger.error('Failed to retrieve provider records for notification', exception=str(e))
            raise

        provider_record = provider_records.get_provider_record()

        # Provider Notification
        provider_email = provider_record.compactConnectRegisteredEmailAddress
        if provider_email:
            logger.info('Sending privilege encumbrance lifting notification to provider', provider_email=provider_email)
            try:
                config.email_service_client.send_privilege_encumbrance_lifting_provider_notification_email(
                    compact=compact,
                    provider_email=provider_email,
                    provider_first_name=provider_record.givenName,
                    provider_last_name=provider_record.familyName,
                    lifted_jurisdiction=jurisdiction,
                    license_type=license_type_name,
                    effective_lift_date=effective_lift_date,
                )
            except Exception as e:
                logger.error('Failed to send provider notification', exception=str(e))
                # Re-raise to ensure the event is retried
                raise
        else:
            logger.info('Provider not registered in system, skipping provider notification')

        # State Notifications
        # Send notification to the state where the privilege encumbrance was lifted
        logger.info(
            'Sending privilege encumbrance lifting notification to affected state', affected_jurisdiction=jurisdiction
        )
        try:
            config.email_service_client.send_privilege_encumbrance_lifting_state_notification_email(
                compact=compact,
                jurisdiction=jurisdiction,
                provider_first_name=provider_record.givenName,
                provider_last_name=provider_record.familyName,
                provider_id=provider_id,
                lifted_jurisdiction=jurisdiction,
                license_type=license_type_name,
                effective_lift_date=effective_lift_date,
            )
        except Exception as e:
            logger.error('Failed to send state notification', jurisdiction=jurisdiction, exception=str(e))
            # Re-raise to ensure the event is retried
            raise

        # Query provider's records to find all states where they hold active licenses or privileges
        active_licenses = provider_records.get_license_records(
            filter_condition=lambda license_record: license_record.licenseStatus == ActiveInactiveStatus.ACTIVE
        )
        active_privileges = provider_records.get_privilege_records(
            filter_condition=lambda privilege_record: privilege_record.status == ActiveInactiveStatus.ACTIVE
        )

        # Get unique jurisdictions (excluding the one already notified)
        notification_jurisdictions = set()
        for license_record in active_licenses:
            if license_record.jurisdiction != jurisdiction:
                notification_jurisdictions.add(license_record.jurisdiction)
        for privilege_record in active_privileges:
            if privilege_record.jurisdiction != jurisdiction:
                notification_jurisdictions.add(privilege_record.jurisdiction)

        # Send notifications to all other states with provider licenses or privileges
        for notification_jurisdiction in notification_jurisdictions:
            logger.info(
                'Sending privilege encumbrance lifting notification to other state',
                notification_jurisdiction=notification_jurisdiction,
            )
            try:
                config.email_service_client.send_privilege_encumbrance_lifting_state_notification_email(
                    compact=compact,
                    jurisdiction=notification_jurisdiction,
                    provider_first_name=provider_record.givenName,
                    provider_last_name=provider_record.familyName,
                    provider_id=provider_id,
                    lifted_jurisdiction=jurisdiction,  # The jurisdiction where encumbrance was lifted
                    license_type=license_type_name,
                    effective_lift_date=effective_lift_date,
                )
            except Exception as e:
                logger.error(
                    'Failed to send notification to other state',
                    notification_jurisdiction=notification_jurisdiction,
                    exception=str(e),
                )
                # Re-raise to ensure the event is retried
                raise

        logger.info('Successfully processed privilege encumbrance lifting event')


@sqs_handler
def license_encumbrance_notification_listener(message: dict):
    """
    Handle license encumbrance events by sending notifications only.

    This handler processes 'license.encumbrance' events and sends notifications
    to the affected provider and relevant states. It does NOT perform any data operations.
    """
    detail = message['detail']
    compact = detail['compact']
    provider_id = detail['providerId']
    jurisdiction = detail['jurisdiction']
    license_type_abbreviation = detail['licenseTypeAbbreviation']
    effective_start_date = detail['effectiveStartDate']
    event_time = detail['eventTime']

    with logger.append_context_keys(
        compact=compact,
        provider_id=provider_id,
        jurisdiction=jurisdiction,
        license_type_abbreviation=license_type_abbreviation,
        event_time=event_time,
    ):
        logger.info('Processing license encumbrance notification event')

        # Get license type name from abbreviation (lookup once at the top)
        license_type_name = LicenseUtility.get_license_type_by_abbreviation(compact, license_type_abbreviation).name

        # Get provider records to gather notification targets and provider information
        try:
            provider_records = config.data_client.get_provider_user_records(
                compact=compact,
                provider_id=provider_id,
            )
        except Exception as e:
            logger.error('Failed to retrieve provider records for notification', exception=str(e))
            raise

        provider_record = provider_records.get_provider_record()

        # Provider Notification
        provider_email = provider_record.compactConnectRegisteredEmailAddress
        if provider_email:
            logger.info('Sending license encumbrance notification to provider', provider_email=provider_email)
            try:
                config.email_service_client.send_license_encumbrance_provider_notification_email(
                    compact=compact,
                    provider_email=provider_email,
                    provider_first_name=provider_record.givenName,
                    provider_last_name=provider_record.familyName,
                    encumbered_jurisdiction=jurisdiction,
                    license_type=license_type_name,
                    effective_start_date=effective_start_date,
                )
            except Exception as e:
                logger.error('Failed to send provider notification', exception=str(e))
                # Re-raise to ensure the event is retried
                raise
        else:
            logger.info('Provider not registered in system, skipping provider notification')

        # State Notifications
        # Send notification to the state where the license is encumbered
        logger.info('Sending license encumbrance notification to affected state', affected_jurisdiction=jurisdiction)
        try:
            config.email_service_client.send_license_encumbrance_state_notification_email(
                compact=compact,
                jurisdiction=jurisdiction,
                provider_first_name=provider_record.givenName,
                provider_last_name=provider_record.familyName,
                provider_id=provider_id,
                encumbered_jurisdiction=jurisdiction,
                license_type=license_type_name,
                effective_start_date=effective_start_date,
            )
        except Exception as e:
            logger.error('Failed to send state notification', jurisdiction=jurisdiction, exception=str(e))
            # Re-raise to ensure the event is retried
            raise

        # Query provider's records to find all states where they hold active licenses or privileges
        active_licenses = provider_records.get_license_records(
            filter_condition=lambda license_record: license_record.licenseStatus == ActiveInactiveStatus.ACTIVE
        )
        active_privileges = provider_records.get_privilege_records(
            filter_condition=lambda privilege_record: privilege_record.status == ActiveInactiveStatus.ACTIVE
        )

        # Get unique jurisdictions (excluding the one already notified)
        notification_jurisdictions = set()
        for license_record in active_licenses:
            if license_record.jurisdiction != jurisdiction:
                notification_jurisdictions.add(license_record.jurisdiction)
        for privilege_record in active_privileges:
            if privilege_record.jurisdiction != jurisdiction:
                notification_jurisdictions.add(privilege_record.jurisdiction)

        # Send notifications to all other states with provider licenses or privileges
        for notification_jurisdiction in notification_jurisdictions:
            logger.info(
                'Sending license encumbrance notification to other state',
                notification_jurisdiction=notification_jurisdiction,
            )
            try:
                config.email_service_client.send_license_encumbrance_state_notification_email(
                    compact=compact,
                    jurisdiction=notification_jurisdiction,
                    provider_first_name=provider_record.givenName,
                    provider_last_name=provider_record.familyName,
                    provider_id=provider_id,
                    encumbered_jurisdiction=jurisdiction,  # The jurisdiction where encumbrance occurred
                    license_type=license_type_name,
                    effective_start_date=effective_start_date,
                )
            except Exception as e:
                logger.error(
                    'Failed to send notification to other state',
                    notification_jurisdiction=notification_jurisdiction,
                    exception=str(e),
                )
                # Re-raise to ensure the event is retried
                raise

        logger.info('Successfully processed license encumbrance notification event')


@sqs_handler
def license_encumbrance_lifting_notification_listener(message: dict):
    """
    Handle license encumbrance lifting events by sending notifications only.

    This handler processes 'license.encumbranceLifted' events and sends notifications
    to the affected provider and relevant states. It does NOT perform any data operations.
    """
    detail = message['detail']
    compact = detail['compact']
    provider_id = detail['providerId']
    jurisdiction = detail['jurisdiction']
    license_type_abbreviation = detail['licenseTypeAbbreviation']
    effective_lift_date = detail['effectiveLiftDate']
    event_time = detail['eventTime']

    with logger.append_context_keys(
        compact=compact,
        provider_id=provider_id,
        jurisdiction=jurisdiction,
        license_type_abbreviation=license_type_abbreviation,
        event_time=event_time,
    ):
        logger.info('Processing license encumbrance lifting notification event')

        # Get license type name from abbreviation (lookup once at the top)
        license_type_name = LicenseUtility.get_license_type_by_abbreviation(compact, license_type_abbreviation).name

        # Get provider records to gather notification targets and provider information
        try:
            provider_records = config.data_client.get_provider_user_records(
                compact=compact,
                provider_id=provider_id,
            )
        except Exception as e:
            logger.error('Failed to retrieve provider records for notification', exception=str(e))
            raise

        provider_record = provider_records.get_provider_record()

        # Provider Notification
        provider_email = provider_record.compactConnectRegisteredEmailAddress
        if provider_email:
            logger.info('Sending license encumbrance lifting notification to provider', provider_email=provider_email)
            try:
                config.email_service_client.send_license_encumbrance_lifting_provider_notification_email(
                    compact=compact,
                    provider_email=provider_email,
                    provider_first_name=provider_record.givenName,
                    provider_last_name=provider_record.familyName,
                    lifted_jurisdiction=jurisdiction,
                    license_type=license_type_name,
                    effective_lift_date=effective_lift_date,
                )
            except Exception as e:
                logger.error('Failed to send provider notification', exception=str(e))
                # Re-raise to ensure the event is retried
                raise
        else:
            logger.info('Provider not registered in system, skipping provider notification')

        # State Notifications
        # Send notification to the state where the license encumbrance was lifted
        logger.info(
            'Sending license encumbrance lifting notification to affected state', affected_jurisdiction=jurisdiction
        )
        try:
            config.email_service_client.send_license_encumbrance_lifting_state_notification_email(
                compact=compact,
                jurisdiction=jurisdiction,
                provider_first_name=provider_record.givenName,
                provider_last_name=provider_record.familyName,
                provider_id=provider_id,
                lifted_jurisdiction=jurisdiction,
                license_type=license_type_name,
                effective_lift_date=effective_lift_date,
            )
        except Exception as e:
            logger.error('Failed to send state notification', jurisdiction=jurisdiction, exception=str(e))
            # Re-raise to ensure the event is retried
            raise

        # Query provider's records to find all states where they hold active licenses or privileges
        active_licenses = provider_records.get_license_records(
            filter_condition=lambda license_record: license_record.licenseStatus == ActiveInactiveStatus.ACTIVE
        )
        active_privileges = provider_records.get_privilege_records(
            filter_condition=lambda privilege_record: privilege_record.status == ActiveInactiveStatus.ACTIVE
        )

        # Get unique jurisdictions (excluding the one already notified)
        notification_jurisdictions = set()
        for license_record in active_licenses:
            if license_record.jurisdiction != jurisdiction:
                notification_jurisdictions.add(license_record.jurisdiction)
        for privilege_record in active_privileges:
            if privilege_record.jurisdiction != jurisdiction:
                notification_jurisdictions.add(privilege_record.jurisdiction)

        # Send notifications to all other states with provider licenses or privileges
        for notification_jurisdiction in notification_jurisdictions:
            logger.info(
                'Sending license encumbrance lifting notification to other state',
                notification_jurisdiction=notification_jurisdiction,
            )
            try:
                config.email_service_client.send_license_encumbrance_lifting_state_notification_email(
                    compact=compact,
                    jurisdiction=notification_jurisdiction,
                    provider_first_name=provider_record.givenName,
                    provider_last_name=provider_record.familyName,
                    provider_id=provider_id,
                    lifted_jurisdiction=jurisdiction,  # The jurisdiction where encumbrance was lifted
                    license_type=license_type_name,
                    effective_lift_date=effective_lift_date,
                )
            except Exception as e:
                logger.error(
                    'Failed to send notification to other state',
                    notification_jurisdiction=notification_jurisdiction,
                    exception=str(e),
                )
                # Re-raise to ensure the event is retried
                raise

        logger.info('Successfully processed license encumbrance lifting notification event')
