from cc_common.config import config, logger
from cc_common.data_model.schema.data_event.api import HomeJurisdictionChangeEventDetailSchema
from cc_common.email_service_client import HomeJurisdictionChangeNotificationTemplateVariables
from cc_common.utils import sqs_handler


@sqs_handler
def home_state_change_notification_listener(message: dict):
    """
    Handle home state change events by sending notifications.

    For theSocial Workcompact, the home state for a practitioner is determined by
    which license was issued or renewed most recently. If another home state uploads
    or renews a license record for that same practitioner with a more recent date,
    that state becomes the new home state for that practitioner, and this notification
    listener is triggered.
    """
    detail_schema = HomeJurisdictionChangeEventDetailSchema()
    detail = detail_schema.load(message['detail'])

    compact = detail['compact']
    provider_id = detail['providerId']
    jurisdiction = detail['jurisdiction']
    former_home_jurisdiction = detail['formerHomeJurisdiction']
    license_type = detail['licenseType']
    event_time = detail['eventTime']

    with logger.append_context_keys(
        compact=compact,
        provider_id=provider_id,
        jurisdiction=jurisdiction,
        license_type=license_type,
        event_time=event_time,
    ):
        logger.info('Processing provider home state change event')

        # Get top level provider record to gather provider information
        provider_record = config.data_client.get_provider_top_level_record(compact=compact, provider_id=provider_id)

        # Send notification to former state
        config.email_service_client.send_provider_home_state_change_email(
            compact=compact,
            # in the case of social work, we only send the email notification to the former state.
            jurisdiction=former_home_jurisdiction,
            template_variables=HomeJurisdictionChangeNotificationTemplateVariables(
                provider_first_name=provider_record.givenName,
                provider_last_name=provider_record.familyName,
                former_jurisdiction=former_home_jurisdiction,
                current_jurisdiction=jurisdiction,
                license_type=license_type,
                provider_id=provider_id,
            ),
        )

        logger.info('Successfully processed home state change event')
