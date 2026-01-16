import json
from dataclasses import dataclass
from datetime import date
from typing import Any, Protocol
from uuid import UUID

import boto3
from aws_lambda_powertools.logging import Logger

from cc_common.exceptions import CCInternalException


@dataclass
class EncumbranceNotificationTemplateVariables:
    """
    Template variables for encumbrance notification emails.
    """

    provider_first_name: str
    provider_last_name: str
    encumbered_jurisdiction: str
    license_type: str
    effective_date: date
    provider_id: UUID | None = None


@dataclass
class InvestigationNotificationTemplateVariables:
    """
    Template variables for investigation notification emails.
    """

    provider_first_name: str
    provider_last_name: str
    investigation_jurisdiction: str
    license_type: str
    provider_id: UUID


class JurisdictionNotificationMethod(Protocol):
    """Protocol for Jurisdiction encumbrance notification methods."""

    def __call__(
        self, *, compact: str, jurisdiction: str, template_variables: EncumbranceNotificationTemplateVariables
    ) -> dict[str, Any]: ...


class EmailServiceClient:
    """
    Client for sending email notifications through the email notification service lambda.
    This class abstracts the lambda client and provides a clean interface for sending emails.
    """

    def __init__(self, lambda_client: boto3.client, email_notification_service_lambda_name: str, logger: Logger):
        """
        Initialize the EmailServiceClient.

        :param lambda_client: boto3 lambda client.
        :param email_notification_service_lambda_name: Name of the email notification service lambda.
        """
        self._lambda_client = lambda_client
        self._email_notification_service_lambda_name = email_notification_service_lambda_name
        self._logger = logger

    def _invoke_lambda(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Invoke the email notification service lambda with the given payload.

        :param payload: Payload to send to the lambda
        :return: Response from the lambda
        :raises CCInternalException: If the lambda invocation fails
        """
        if not self._email_notification_service_lambda_name:
            raise CCInternalException('Email notification service lambda name not set')

        try:
            response = self._lambda_client.invoke(
                FunctionName=self._email_notification_service_lambda_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload),
            )

            if response.get('FunctionError'):
                error_message = f'Failed to send email notification: {response.get("FunctionError")}'
                self._logger.error(error_message, payload=payload)
                raise CCInternalException(error_message)

            return response
        except Exception as e:
            error_message = f'Error invoking email notification service lambda: {str(e)}'
            self._logger.error(error_message, payload=payload, exception=str(e))
            raise CCInternalException(error_message) from e

    def send_jurisdiction_privilege_deactivation_email(
        self,
        compact: str,
        jurisdiction: str,
        privilege_id: str,
        provider_first_name: str,
        provider_last_name: str,
    ) -> dict[str, str]:
        """
        Send a privilege deactivation notification email to jurisdiction.

        :param compact: Compact name
        :param jurisdiction: Jurisdiction name
        :param privilege_id: ID of the privilege being deactivated
        :param provider_first_name: First name of the provider whose privilege was deactivated
        :param provider_last_name: Last name of the provider whose privilege was deactivated
        :return: Response from the email notification service
        """
        payload = {
            'compact': compact,
            'jurisdiction': jurisdiction,
            'template': 'privilegeDeactivationJurisdictionNotification',
            # for now, we send this notification to the same contacts as the summary report recipients
            'recipientType': 'JURISDICTION_SUMMARY_REPORT',
            'templateVariables': {
                'privilegeId': privilege_id,
                'providerFirstName': provider_first_name,
                'providerLastName': provider_last_name,
            },
        }

        return self._invoke_lambda(payload)

    def send_license_encumbrance_provider_notification_email(
        self,
        *,
        compact: str,
        provider_email: str,
        template_variables: EncumbranceNotificationTemplateVariables,
    ) -> dict[str, str]:
        """
        Send a license encumbrance notification email to a provider.

        :param compact: Compact name
        :param provider_email: Email address of the provider
        :param template_variables: Template variables for the email
        :return: Response from the email notification service
        """
        payload = {
            'compact': compact,
            'template': 'licenseEncumbranceProviderNotification',
            'recipientType': 'SPECIFIC',
            'specificEmails': [provider_email],
            'templateVariables': {
                'providerFirstName': template_variables.provider_first_name,
                'providerLastName': template_variables.provider_last_name,
                'encumberedJurisdiction': template_variables.encumbered_jurisdiction,
                'licenseType': template_variables.license_type,
                'effectiveStartDate': template_variables.effective_date.strftime('%B %d, %Y'),
            },
        }
        return self._invoke_lambda(payload)

    def send_license_encumbrance_state_notification_email(
        self,
        *,
        compact: str,
        jurisdiction: str,
        template_variables: EncumbranceNotificationTemplateVariables,
    ) -> dict[str, str]:
        """
        Send a license encumbrance notification email to a state.

        :param compact: Compact name
        :param jurisdiction: Jurisdiction to notify
        :param template_variables: Template variables for the email
        :return: Response from the email notification service
        """
        if template_variables.provider_id is None:
            raise ValueError('Provider ID is required for state notification emails')

        payload = {
            'compact': compact,
            'jurisdiction': jurisdiction,
            'template': 'licenseEncumbranceStateNotification',
            'recipientType': 'JURISDICTION_ADVERSE_ACTIONS',
            'templateVariables': {
                'providerFirstName': template_variables.provider_first_name,
                'providerLastName': template_variables.provider_last_name,
                'providerId': str(template_variables.provider_id),
                'encumberedJurisdiction': template_variables.encumbered_jurisdiction,
                'licenseType': template_variables.license_type,
                'effectiveStartDate': template_variables.effective_date.strftime('%B %d, %Y'),
            },
        }
        return self._invoke_lambda(payload)

    def send_license_encumbrance_lifting_provider_notification_email(
        self,
        *,
        compact: str,
        provider_email: str,
        template_variables: EncumbranceNotificationTemplateVariables,
    ) -> dict[str, str]:
        """
        Send a license encumbrance lifting notification email to a provider.

        :param compact: Compact name
        :param provider_email: Email address of the provider
        :param template_variables: Template variables for the email
        :return: Response from the email notification service
        """
        payload = {
            'compact': compact,
            'template': 'licenseEncumbranceLiftingProviderNotification',
            'recipientType': 'SPECIFIC',
            'specificEmails': [provider_email],
            'templateVariables': {
                'providerFirstName': template_variables.provider_first_name,
                'providerLastName': template_variables.provider_last_name,
                'liftedJurisdiction': template_variables.encumbered_jurisdiction,
                'licenseType': template_variables.license_type,
                'effectiveLiftDate': template_variables.effective_date.strftime('%B %d, %Y'),
            },
        }
        return self._invoke_lambda(payload)

    def send_license_encumbrance_lifting_state_notification_email(
        self,
        *,
        compact: str,
        jurisdiction: str,
        template_variables: EncumbranceNotificationTemplateVariables,
    ) -> dict[str, str]:
        """
        Send a license encumbrance lifting notification email to a state.

        :param compact: Compact name
        :param jurisdiction: Jurisdiction to notify
        :param template_variables: Template variables for the email
        :return: Response from the email notification service
        """
        if template_variables.provider_id is None:
            raise ValueError('Provider ID is required for state notification emails')

        payload = {
            'compact': compact,
            'jurisdiction': jurisdiction,
            'template': 'licenseEncumbranceLiftingStateNotification',
            'recipientType': 'JURISDICTION_ADVERSE_ACTIONS',
            'templateVariables': {
                'providerFirstName': template_variables.provider_first_name,
                'providerLastName': template_variables.provider_last_name,
                'providerId': str(template_variables.provider_id),
                'liftedJurisdiction': template_variables.encumbered_jurisdiction,
                'licenseType': template_variables.license_type,
                'effectiveLiftDate': template_variables.effective_date.strftime('%B %d, %Y'),
            },
        }
        return self._invoke_lambda(payload)

    def send_privilege_encumbrance_provider_notification_email(
        self,
        *,
        compact: str,
        provider_email: str,
        template_variables: EncumbranceNotificationTemplateVariables,
    ) -> dict[str, str]:
        """
        Send a privilege encumbrance notification email to a provider.

        :param compact: Compact name
        :param provider_email: Email address of the provider
        :param template_variables: Template variables for the email
        :return: Response from the email notification service
        """
        payload = {
            'compact': compact,
            'template': 'privilegeEncumbranceProviderNotification',
            'recipientType': 'SPECIFIC',
            'specificEmails': [provider_email],
            'templateVariables': {
                'providerFirstName': template_variables.provider_first_name,
                'providerLastName': template_variables.provider_last_name,
                'encumberedJurisdiction': template_variables.encumbered_jurisdiction,
                'licenseType': template_variables.license_type,
                'effectiveStartDate': template_variables.effective_date.strftime('%B %d, %Y'),
            },
        }
        return self._invoke_lambda(payload)

    def send_privilege_encumbrance_state_notification_email(
        self,
        *,
        compact: str,
        jurisdiction: str,
        template_variables: EncumbranceNotificationTemplateVariables,
    ) -> dict[str, str]:
        """
        Send a privilege encumbrance notification email to a state.

        :param compact: Compact name
        :param jurisdiction: Jurisdiction to notify
        :param template_variables: Template variables for the email
        :return: Response from the email notification service
        """
        if template_variables.provider_id is None:
            raise ValueError('Provider ID is required for state notification emails.')

        payload = {
            'compact': compact,
            'jurisdiction': jurisdiction,
            'template': 'privilegeEncumbranceStateNotification',
            'recipientType': 'JURISDICTION_ADVERSE_ACTIONS',
            'templateVariables': {
                'providerFirstName': template_variables.provider_first_name,
                'providerLastName': template_variables.provider_last_name,
                'providerId': str(template_variables.provider_id),
                'encumberedJurisdiction': template_variables.encumbered_jurisdiction,
                'licenseType': template_variables.license_type,
                'effectiveStartDate': template_variables.effective_date.strftime('%B %d, %Y'),
            },
        }
        return self._invoke_lambda(payload)

    def send_privilege_encumbrance_lifting_provider_notification_email(
        self,
        *,
        compact: str,
        provider_email: str,
        template_variables: EncumbranceNotificationTemplateVariables,
    ) -> dict[str, str]:
        """
        Send a privilege encumbrance lifting notification email to a provider.

        :param compact: Compact name
        :param provider_email: Email address of the provider
        :param template_variables: Template variables for the email
        :return: Response from the email notification service
        """
        payload = {
            'compact': compact,
            'template': 'privilegeEncumbranceLiftingProviderNotification',
            'recipientType': 'SPECIFIC',
            'specificEmails': [provider_email],
            'templateVariables': {
                'providerFirstName': template_variables.provider_first_name,
                'providerLastName': template_variables.provider_last_name,
                'liftedJurisdiction': template_variables.encumbered_jurisdiction,
                'licenseType': template_variables.license_type,
                'effectiveLiftDate': template_variables.effective_date.strftime('%B %d, %Y'),
            },
        }
        return self._invoke_lambda(payload)

    def send_privilege_encumbrance_lifting_state_notification_email(
        self,
        *,
        compact: str,
        jurisdiction: str,
        template_variables: EncumbranceNotificationTemplateVariables,
    ) -> dict[str, str]:
        """
        Send a privilege encumbrance lifting notification email to a state.

        :param compact: Compact name
        :param jurisdiction: Jurisdiction to notify
        :param template_variables: Template variables for the email
        :return: Response from the email notification service
        """
        if template_variables.provider_id is None:
            raise ValueError('Provider ID is required for state notification emails.')

        payload = {
            'compact': compact,
            'jurisdiction': jurisdiction,
            'template': 'privilegeEncumbranceLiftingStateNotification',
            'recipientType': 'JURISDICTION_ADVERSE_ACTIONS',
            'templateVariables': {
                'providerFirstName': template_variables.provider_first_name,
                'providerLastName': template_variables.provider_last_name,
                'providerId': str(template_variables.provider_id),
                'liftedJurisdiction': template_variables.encumbered_jurisdiction,
                'licenseType': template_variables.license_type,
                'effectiveLiftDate': template_variables.effective_date.strftime('%B %d, %Y'),
            },
        }
        return self._invoke_lambda(payload)

    def send_license_investigation_state_notification_email(
        self,
        *,
        compact: str,
        jurisdiction: str,
        template_variables: InvestigationNotificationTemplateVariables,
    ) -> dict[str, str]:
        """
        Send a license investigation notification email to a state.

        :param compact: Compact name
        :param jurisdiction: Jurisdiction to notify
        :param template_variables: Template variables for the email
        :return: Response from the email notification service
        """
        if template_variables.provider_id is None:
            raise ValueError('provider_id must be provided for state notifications')

        payload = {
            'compact': compact,
            'jurisdiction': jurisdiction,
            'template': 'licenseInvestigationStateNotification',
            'recipientType': 'JURISDICTION_ADVERSE_ACTIONS',
            'templateVariables': {
                'providerFirstName': template_variables.provider_first_name,
                'providerLastName': template_variables.provider_last_name,
                'providerId': str(template_variables.provider_id),
                'investigationJurisdiction': template_variables.investigation_jurisdiction,
                'licenseType': template_variables.license_type,
            },
        }
        return self._invoke_lambda(payload)

    def send_license_investigation_closed_state_notification_email(
        self,
        *,
        compact: str,
        jurisdiction: str,
        template_variables: InvestigationNotificationTemplateVariables,
    ) -> dict[str, str]:
        """
        Send a license investigation closed notification email to a state.

        :param compact: Compact name
        :param jurisdiction: Jurisdiction to notify
        :param template_variables: Template variables for the email
        :return: Response from the email notification service
        """
        if template_variables.provider_id is None:
            raise ValueError('provider_id must be provided for state notifications')

        payload = {
            'compact': compact,
            'jurisdiction': jurisdiction,
            'template': 'licenseInvestigationClosedStateNotification',
            'recipientType': 'JURISDICTION_ADVERSE_ACTIONS',
            'templateVariables': {
                'providerFirstName': template_variables.provider_first_name,
                'providerLastName': template_variables.provider_last_name,
                'providerId': str(template_variables.provider_id),
                'investigationJurisdiction': template_variables.investigation_jurisdiction,
                'licenseType': template_variables.license_type,
            },
        }
        return self._invoke_lambda(payload)

    def send_privilege_investigation_state_notification_email(
        self,
        *,
        compact: str,
        jurisdiction: str,
        template_variables: InvestigationNotificationTemplateVariables,
    ) -> dict[str, str]:
        """
        Send a privilege investigation notification email to a state.

        :param compact: Compact name
        :param jurisdiction: Jurisdiction to notify
        :param template_variables: Template variables for the email
        :return: Response from the email notification service
        """
        if template_variables.provider_id is None:
            raise ValueError('provider_id must be provided for state notifications')

        payload = {
            'compact': compact,
            'jurisdiction': jurisdiction,
            'template': 'privilegeInvestigationStateNotification',
            'recipientType': 'JURISDICTION_ADVERSE_ACTIONS',
            'templateVariables': {
                'providerFirstName': template_variables.provider_first_name,
                'providerLastName': template_variables.provider_last_name,
                'providerId': str(template_variables.provider_id),
                'investigationJurisdiction': template_variables.investigation_jurisdiction,
                'licenseType': template_variables.license_type,
            },
        }
        return self._invoke_lambda(payload)

    def send_privilege_investigation_closed_state_notification_email(
        self,
        *,
        compact: str,
        jurisdiction: str,
        template_variables: InvestigationNotificationTemplateVariables,
    ) -> dict[str, str]:
        """
        Send a privilege investigation closed notification email to a state.

        :param compact: Compact name
        :param jurisdiction: Jurisdiction to notify
        :param template_variables: Template variables for the email
        :return: Response from the email notification service
        """
        if template_variables.provider_id is None:
            raise ValueError('provider_id must be provided for state notifications')

        payload = {
            'compact': compact,
            'jurisdiction': jurisdiction,
            'template': 'privilegeInvestigationClosedStateNotification',
            'recipientType': 'JURISDICTION_ADVERSE_ACTIONS',
            'templateVariables': {
                'providerFirstName': template_variables.provider_first_name,
                'providerLastName': template_variables.provider_last_name,
                'providerId': str(template_variables.provider_id),
                'investigationJurisdiction': template_variables.investigation_jurisdiction,
                'licenseType': template_variables.license_type,
            },
        }
        return self._invoke_lambda(payload)
