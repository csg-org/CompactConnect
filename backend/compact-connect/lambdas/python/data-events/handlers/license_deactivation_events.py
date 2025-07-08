from cc_common.config import config, logger
from cc_common.data_model.schema.data_event.api import LicenseDeactivationDetailSchema
from cc_common.utils import sqs_handler


@sqs_handler
def license_deactivation_listener(message: dict):
    """
    Handle license deactivation events by deactivating associated privileges.

    This handler processes 'license.deactivation' events and automatically deactivates
    all privileges associated with the deactivated license.
    """
    # Validate the event detail using the schema
    license_deactivation_schema = LicenseDeactivationDetailSchema()
    validated_detail = license_deactivation_schema.dump(license_deactivation_schema.load(message['detail']))

    compact = validated_detail['compact']
    provider_id = validated_detail['providerId']
    jurisdiction = validated_detail['jurisdiction']
    license_type = validated_detail['licenseType']

    with logger.append_context_keys(
        compact=compact, provider_id=provider_id, jurisdiction=jurisdiction, license_type=license_type
    ):
        logger.info('Processing license deactivation event')

        # Deactivate the privileges using the data client method
        config.data_client.deactivate_license_privileges(
            compact=compact,
            provider_id=provider_id,
            jurisdiction=jurisdiction,
            license_type=license_type,
        )

        logger.info('Successfully processed license deactivation event')
