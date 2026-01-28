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


@dataclass
class PrivilegeExpirationReminderTemplateVariables:
    """
    Template variables for privilege expiration reminder emails.
    """

    provider_first_name: str
    expiration_date: date
    privileges: list[dict]  # Each dict has: jurisdiction, licenseType, privilegeId


class ProviderNotificationMethod(Protocol):
    """Protocol for provider encumbrance notification methods."""

    def __call__(
        self, *, compact: str, provider_email: str, template_variables: EncumbranceNotificationTemplateVariables
    ) -> dict[str, Any]: ...


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
                error_message = 'Failed to send email notification'
                self._logger.error(error_message, payload=payload, response=response)
                raise CCInternalException(error_message)

            return response
        except Exception as e:
            error_message = f'Error invoking email notification service lambda: {str(e)}'
            self._logger.error(error_message, payload=payload, exception=str(e))
            raise CCInternalException(error_message) from e

    def send_provider_privilege_deactivation_email(
        self,
        compact: str,
        provider_email: str,
        privilege_id: str,
    ) -> dict[str, str]:
        """
        Send a privilege deactivation notification email to providers.

        :param compact: Compact name
        :param provider_email: Email address of the provider
        :param privilege_id: ID of the privilege being deactivated
        :return: Response from the email notification service
        """
        payload = {
            'compact': compact,
            'template': 'privilegeDeactivationProviderNotification',
            'recipientType': 'SPECIFIC',
            'specificEmails': [
                provider_email,
            ],
            'templateVariables': {
                'privilegeId': privilege_id,
            },
        }

        return self._invoke_lambda(payload)

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

    def send_compact_transaction_report_email(
        self,
        compact: str,
        report_s3_path: str,
        reporting_cycle: str,
        start_date: date,
        end_date: date,
    ) -> dict[str, Any]:
        """
        Send a compact transaction report email.

        :param compact: Compact name
        :param report_s3_path: S3 path to the report zip file
        :param reporting_cycle: Reporting cycle (e.g., 'weekly', 'monthly')
        :param start_date: Start date of the reporting period
        :param end_date: End date of the reporting period
        :return: Response from the email notification service
        """

        payload = {
            'compact': compact,
            'template': 'CompactTransactionReporting',
            'recipientType': 'COMPACT_SUMMARY_REPORT',
            'templateVariables': {
                'reportS3Path': report_s3_path,
                'reportingCycle': reporting_cycle,
                'startDate': start_date.strftime('%Y-%m-%d'),
                'endDate': end_date.strftime('%Y-%m-%d'),
            },
        }

        return self._invoke_lambda(payload)

    def send_jurisdiction_transaction_report_email(
        self,
        compact: str,
        jurisdiction: str,
        report_s3_path: str,
        reporting_cycle: str,
        start_date: date,
        end_date: date,
    ) -> dict[str, str]:
        """
        Send a jurisdiction transaction report email.

        :param compact: Compact name
        :param jurisdiction: Jurisdiction name
        :param report_s3_path: S3 path to the report zip file
        :param reporting_cycle: Reporting cycle (e.g., 'weekly', 'monthly')
        :param start_date: Start date of the reporting period
        :param end_date: End date of the reporting period
        :return: Response from the email notification service
        """

        payload = {
            'compact': compact,
            'jurisdiction': jurisdiction,
            'template': 'JurisdictionTransactionReporting',
            'recipientType': 'JURISDICTION_SUMMARY_REPORT',
            'templateVariables': {
                'reportS3Path': report_s3_path,
                'reportingCycle': reporting_cycle,
                'startDate': start_date.strftime('%Y-%m-%d'),
                'endDate': end_date.strftime('%Y-%m-%d'),
            },
        }

        return self._invoke_lambda(payload)

    def send_privilege_purchase_email(
        self,
        provider_email: str,
        transaction_date: str,
        privileges: list[dict],
        total_cost: str,
        cost_line_items: list[dict],
    ) -> dict[str, str]:
        """
        Send a privilege(s) purchase notification email.

        :param provider_email: email of the provider who purchased privileges
        :param transaction_date: date of the transaction
        :param privileges: privileges purchased
        :param total_cost: Total cost of the transaction
        :param cost_line_items: Line items (name, unitPrice, quantity) of transaction
        :return: Response from the email notification service
        """

        payload = {
            'template': 'privilegePurchaseProviderNotification',
            'specificEmails': [
                provider_email,
            ],
            'templateVariables': {
                'transactionDate': transaction_date,
                'privileges': privileges,
                'totalCost': total_cost,
                'costLineItems': cost_line_items,
            },
        }
        return self._invoke_lambda(payload)

    def send_provider_multiple_registration_attempt_email(
        self,
        compact: str,
        provider_email: str,
    ) -> dict[str, str]:
        """
        Send a notification email to a provider when someone attempts to register with their email address.

        :param compact: Compact name
        :param provider_email: Email address of the provider
        :return: Response from the email notification service
        """
        payload = {
            'compact': compact,
            'template': 'multipleRegistrationAttemptNotification',
            'recipientType': 'SPECIFIC',
            'specificEmails': [
                provider_email,
            ],
            'templateVariables': {},
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

    def send_provider_email_verification_code(
        self,
        compact: str,
        provider_email: str,
        verification_code: str,
    ) -> dict[str, str]:
        """
        Send an email verification code to a provider's new email address.

        :param compact: Compact name
        :param provider_email: Email address to send the verification code to
        :param verification_code: 4-digit verification code
        :return: Response from the email notification service
        """
        payload = {
            'compact': compact,
            'template': 'providerEmailVerificationCode',
            'recipientType': 'SPECIFIC',
            'specificEmails': [
                provider_email,
            ],
            'templateVariables': {
                'verificationCode': verification_code,
            },
        }

        return self._invoke_lambda(payload)

    def send_provider_email_change_notification(
        self,
        compact: str,
        old_email_address: str,
        new_email_address: str,
    ) -> dict[str, str]:
        """
        Send a notification to the old email address when a provider's email is changed.

        :param compact: Compact name
        :param old_email_address: The previous email address
        :param new_email_address: The new email address
        :return: Response from the email notification service
        """
        payload = {
            'compact': compact,
            'template': 'providerEmailChangeNotification',
            'recipientType': 'SPECIFIC',
            'specificEmails': [
                old_email_address,
            ],
            'templateVariables': {
                'newEmailAddress': new_email_address,
            },
        }

        return self._invoke_lambda(payload)

    def send_provider_account_recovery_confirmation_email(
        self,
        *,
        compact: str,
        provider_email: str,
        provider_id: str,
        recovery_token: str,
    ) -> dict[str, str]:
        """
        Send an account recovery confirmation email to a provider with a secure link.

        :param compact: The compact name
        :param provider_email: Email address of the provider
        :param provider_id: The id of the provider
        :param recovery_token: Recovery token
        :return: Response from the email notification service
        """

        payload = {
            'compact': compact,
            'template': 'providerAccountRecoveryConfirmation',
            'recipientType': 'SPECIFIC',
            'specificEmails': [provider_email],
            'templateVariables': {
                'providerId': str(provider_id),
                'recoveryToken': str(recovery_token),
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

    def send_military_audit_approved_notification(
        self,
        *,
        compact: str,
        provider_email: str,
    ) -> dict[str, str]:
        """
        Send a military audit approved notification email to a provider.

        :param compact: Compact name
        :param provider_email: Email address of the provider
        :return: Response from the email notification service
        """
        payload = {
            'compact': compact,
            'template': 'militaryAuditApprovedNotification',
            'recipientType': 'SPECIFIC',
            'specificEmails': [provider_email],
            'templateVariables': {},
        }
        return self._invoke_lambda(payload)

    def send_military_audit_declined_notification(
        self,
        *,
        compact: str,
        provider_email: str,
        audit_note: str,
    ) -> dict[str, str]:
        """
        Send a military audit declined notification email to a provider.

        :param compact: Compact name
        :param provider_email: Email address of the provider
        :param audit_note: Note from the admin explaining the decline
        :return: Response from the email notification service
        """
        payload = {
            'compact': compact,
            'template': 'militaryAuditDeclinedNotification',
            'recipientType': 'SPECIFIC',
            'specificEmails': [provider_email],
            'templateVariables': {
                'auditNote': audit_note,
            },
        }
        return self._invoke_lambda(payload)

    def send_privilege_expiration_reminder_email(
        self,
        *,
        compact: str,
        provider_email: str,
        template_variables: 'PrivilegeExpirationReminderTemplateVariables',
    ) -> dict[str, str]:
        """
        Send a privilege expiration reminder email to a provider.

        :param compact: Compact name
        :param provider_email: Email address of the provider
        :param template_variables: Template variables for the email (provider name, expiration date, privileges)
        :return: Response from the email notification service
        """
        payload = {
            'compact': compact,
            'template': 'privilegeExpirationReminder',
            'recipientType': 'SPECIFIC',
            'specificEmails': [provider_email],
            'templateVariables': {
                'providerFirstName': template_variables.provider_first_name,
                'expirationDate': template_variables.expiration_date.strftime('%B %d, %Y'),
                'privileges': template_variables.privileges,
            },
        }
        return self._invoke_lambda(payload)

    def send_home_jurisdiction_change_old_state_notification(
        self,
        *,
        compact: str,
        jurisdiction: str,
        provider_first_name: str,
        provider_last_name: str,
        provider_id: UUID,
        new_jurisdiction: str,
    ) -> dict[str, str]:
        """
        Notify the old home state that a practitioner has changed their home jurisdiction.

        :param compact: Compact name
        :param jurisdiction: Old jurisdiction to notify
        :param provider_first_name: Provider's first name
        :param provider_last_name: Provider's last name
        :param provider_id: Provider ID
        :param new_jurisdiction: New home jurisdiction
        :return: Response from the email notification service
        """
        payload = {
            'compact': compact,
            'jurisdiction': jurisdiction,
            'template': 'homeJurisdictionChangeOldStateNotification',
            'recipientType': 'JURISDICTION_OPERATIONS_TEAM',
            'templateVariables': {
                'providerFirstName': provider_first_name,
                'providerLastName': provider_last_name,
                'providerId': str(provider_id),
                'previousJurisdiction': jurisdiction,
                'newJurisdiction': new_jurisdiction,
            },
        }
        return self._invoke_lambda(payload)

    def send_home_jurisdiction_change_new_state_notification(
        self,
        *,
        compact: str,
        jurisdiction: str,
        provider_first_name: str,
        provider_last_name: str,
        provider_id: UUID,
        previous_jurisdiction: str,
    ) -> dict[str, str]:
        """
        Notify the new home state that a practitioner has selected them as their home jurisdiction.

        :param compact: Compact name
        :param jurisdiction: New jurisdiction to notify
        :param provider_first_name: Provider's first name
        :param provider_last_name: Provider's last name
        :param provider_id: Provider ID
        :param previous_jurisdiction: Previous home jurisdiction
        :return: Response from the email notification service
        """
        payload = {
            'compact': compact,
            'jurisdiction': jurisdiction,
            'template': 'homeJurisdictionChangeNewStateNotification',
            'recipientType': 'JURISDICTION_OPERATIONS_TEAM',
            'templateVariables': {
                'providerFirstName': provider_first_name,
                'providerLastName': provider_last_name,
                'providerId': str(provider_id),
                'previousJurisdiction': previous_jurisdiction,
                'newJurisdiction': jurisdiction,
            },
        }
        return self._invoke_lambda(payload)
