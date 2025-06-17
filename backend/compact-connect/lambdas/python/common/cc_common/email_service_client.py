import json
from datetime import datetime
from typing import Any

import boto3
from aws_lambda_powertools.logging import Logger

from cc_common.exceptions import CCInternalException


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
        start_date: datetime,
        end_date: datetime,
    ) -> dict[str, str]:
        """
        Send a compact transaction report email.

        :param compact: Compact name
        :param report_s3_path: S3 path to the report zip file
        :param reporting_cycle: Reporting cycle (e.g., 'weekly', 'monthly')
        :param start_date: Start datetime of the reporting period
        :param end_date: End datetime of the reporting period
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
        start_date: datetime,
        end_date: datetime,
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

    def send_license_encumbrance_provider_notification_email(
        self,
        compact: str,
        provider_email: str,
        provider_first_name: str,
        provider_last_name: str,
        encumbered_jurisdiction: str,
        license_type: str,
        effective_start_date: str,
    ) -> dict[str, str]:
        """
        Send a license encumbrance notification email to a provider.

        :param compact: Compact name
        :param provider_email: Email address of the provider
        :param provider_first_name: First name of the provider
        :param provider_last_name: Last name of the provider
        :param encumbered_jurisdiction: Jurisdiction where the license was encumbered
        :param license_type: Type of license that was encumbered
        :param effective_start_date: Date when the encumbrance became effective
        :return: Response from the email notification service
        """
        payload = {
            'compact': compact,
            'template': 'licenseEncumbranceProviderNotification',
            'recipientType': 'SPECIFIC',
            'specificEmails': [provider_email],
            'templateVariables': {
                'providerFirstName': provider_first_name,
                'providerLastName': provider_last_name,
                'encumberedJurisdiction': encumbered_jurisdiction,
                'licenseType': license_type,
                'effectiveStartDate': effective_start_date,
            },
        }
        return self._invoke_lambda(payload)

    def send_license_encumbrance_state_notification_email(
        self,
        compact: str,
        jurisdiction: str,
        provider_first_name: str,
        provider_last_name: str,
        provider_id: str,
        encumbered_jurisdiction: str,
        license_type: str,
        effective_start_date: str,
    ) -> dict[str, str]:
        """
        Send a license encumbrance notification email to a state.

        :param compact: Compact name
        :param jurisdiction: Jurisdiction to notify
        :param provider_first_name: First name of the provider
        :param provider_last_name: Last name of the provider
        :param provider_id: Provider ID
        :param encumbered_jurisdiction: Jurisdiction where the license was encumbered
        :param license_type: Type of license that was encumbered
        :param effective_start_date: Date when the encumbrance became effective
        :return: Response from the email notification service
        """
        payload = {
            'compact': compact,
            'jurisdiction': jurisdiction,
            'template': 'licenseEncumbranceStateNotification',
            'recipientType': 'JURISDICTION_ADVERSE_ACTIONS',
            'templateVariables': {
                'providerFirstName': provider_first_name,
                'providerLastName': provider_last_name,
                'providerId': provider_id,
                'encumberedJurisdiction': encumbered_jurisdiction,
                'licenseType': license_type,
                'effectiveStartDate': effective_start_date,
            },
        }
        return self._invoke_lambda(payload)

    def send_license_encumbrance_lifting_provider_notification_email(
        self,
        compact: str,
        provider_email: str,
        provider_first_name: str,
        provider_last_name: str,
        lifted_jurisdiction: str,
        license_type: str,
        effective_lift_date: str,
    ) -> dict[str, str]:
        """
        Send a license encumbrance lifting notification email to a provider.

        :param compact: Compact name
        :param provider_email: Email address of the provider
        :param provider_first_name: First name of the provider
        :param provider_last_name: Last name of the provider
        :param lifted_jurisdiction: Jurisdiction where the license encumbrance was lifted
        :param license_type: Type of license that had encumbrance lifted
        :param effective_lift_date: Date when the encumbrance was lifted
        :return: Response from the email notification service
        """
        payload = {
            'compact': compact,
            'template': 'licenseEncumbranceLiftingProviderNotification',
            'recipientType': 'SPECIFIC',
            'specificEmails': [provider_email],
            'templateVariables': {
                'providerFirstName': provider_first_name,
                'providerLastName': provider_last_name,
                'liftedJurisdiction': lifted_jurisdiction,
                'licenseType': license_type,
                'effectiveLiftDate': effective_lift_date,
            },
        }
        return self._invoke_lambda(payload)

    def send_license_encumbrance_lifting_state_notification_email(
        self,
        compact: str,
        jurisdiction: str,
        provider_first_name: str,
        provider_last_name: str,
        provider_id: str,
        lifted_jurisdiction: str,
        license_type: str,
        effective_lift_date: str,
    ) -> dict[str, str]:
        """
        Send a license encumbrance lifting notification email to a state.

        :param compact: Compact name
        :param jurisdiction: Jurisdiction to notify
        :param provider_first_name: First name of the provider
        :param provider_last_name: Last name of the provider
        :param provider_id: Provider ID
        :param lifted_jurisdiction: Jurisdiction where the license encumbrance was lifted
        :param license_type: Type of license that had encumbrance lifted
        :param effective_lift_date: Date when the encumbrance was lifted
        :return: Response from the email notification service
        """
        payload = {
            'compact': compact,
            'jurisdiction': jurisdiction,
            'template': 'licenseEncumbranceLiftingStateNotification',
            'recipientType': 'JURISDICTION_ADVERSE_ACTIONS',
            'templateVariables': {
                'providerFirstName': provider_first_name,
                'providerLastName': provider_last_name,
                'providerId': provider_id,
                'liftedJurisdiction': lifted_jurisdiction,
                'licenseType': license_type,
                'effectiveLiftDate': effective_lift_date,
            },
        }
        return self._invoke_lambda(payload)

    def send_privilege_encumbrance_provider_notification_email(
        self,
        compact: str,
        provider_email: str,
        provider_first_name: str,
        provider_last_name: str,
        encumbered_jurisdiction: str,
        license_type: str,
        effective_start_date: str,
    ) -> dict[str, str]:
        """
        Send a privilege encumbrance notification email to a provider.

        :param compact: Compact name
        :param provider_email: Email address of the provider
        :param provider_first_name: First name of the provider
        :param provider_last_name: Last name of the provider
        :param encumbered_jurisdiction: Jurisdiction where the privilege was encumbered
        :param license_type: Type of license/privilege that was encumbered
        :param effective_start_date: Date when the encumbrance became effective
        :return: Response from the email notification service
        """
        payload = {
            'compact': compact,
            'template': 'privilegeEncumbranceProviderNotification',
            'recipientType': 'SPECIFIC',
            'specificEmails': [provider_email],
            'templateVariables': {
                'providerFirstName': provider_first_name,
                'providerLastName': provider_last_name,
                'encumberedJurisdiction': encumbered_jurisdiction,
                'licenseType': license_type,
                'effectiveStartDate': effective_start_date,
            },
        }
        return self._invoke_lambda(payload)

    def send_privilege_encumbrance_state_notification_email(
        self,
        compact: str,
        jurisdiction: str,
        provider_first_name: str,
        provider_last_name: str,
        provider_id: str,
        encumbered_jurisdiction: str,
        license_type: str,
        effective_start_date: str,
    ) -> dict[str, str]:
        """
        Send a privilege encumbrance notification email to a state.

        :param compact: Compact name
        :param jurisdiction: Jurisdiction to notify
        :param provider_first_name: First name of the provider
        :param provider_last_name: Last name of the provider
        :param provider_id: Provider ID
        :param encumbered_jurisdiction: Jurisdiction where the privilege was encumbered
        :param license_type: Type of license/privilege that was encumbered
        :param effective_start_date: Date when the encumbrance became effective
        :return: Response from the email notification service
        """
        payload = {
            'compact': compact,
            'jurisdiction': jurisdiction,
            'template': 'privilegeEncumbranceStateNotification',
            'recipientType': 'JURISDICTION_ADVERSE_ACTIONS',
            'templateVariables': {
                'providerFirstName': provider_first_name,
                'providerLastName': provider_last_name,
                'providerId': provider_id,
                'encumberedJurisdiction': encumbered_jurisdiction,
                'licenseType': license_type,
                'effectiveStartDate': effective_start_date,
            },
        }
        return self._invoke_lambda(payload)

    def send_privilege_encumbrance_lifting_provider_notification_email(
        self,
        compact: str,
        provider_email: str,
        provider_first_name: str,
        provider_last_name: str,
        lifted_jurisdiction: str,
        license_type: str,
        effective_lift_date: str,
    ) -> dict[str, str]:
        """
        Send a privilege encumbrance lifting notification email to a provider.

        :param compact: Compact name
        :param provider_email: Email address of the provider
        :param provider_first_name: First name of the provider
        :param provider_last_name: Last name of the provider
        :param lifted_jurisdiction: Jurisdiction where the privilege encumbrance was lifted
        :param license_type: Type of license/privilege that had encumbrance lifted
        :param effective_lift_date: Date when the encumbrance was lifted
        :return: Response from the email notification service
        """
        payload = {
            'compact': compact,
            'template': 'privilegeEncumbranceLiftingProviderNotification',
            'recipientType': 'SPECIFIC',
            'specificEmails': [provider_email],
            'templateVariables': {
                'providerFirstName': provider_first_name,
                'providerLastName': provider_last_name,
                'liftedJurisdiction': lifted_jurisdiction,
                'licenseType': license_type,
                'effectiveLiftDate': effective_lift_date,
            },
        }
        return self._invoke_lambda(payload)

    def send_privilege_encumbrance_lifting_state_notification_email(
        self,
        compact: str,
        jurisdiction: str,
        provider_first_name: str,
        provider_last_name: str,
        provider_id: str,
        lifted_jurisdiction: str,
        license_type: str,
        effective_lift_date: str,
    ) -> dict[str, str]:
        """
        Send a privilege encumbrance lifting notification email to a state.

        :param compact: Compact name
        :param jurisdiction: Jurisdiction to notify
        :param provider_first_name: First name of the provider
        :param provider_last_name: Last name of the provider
        :param provider_id: Provider ID
        :param lifted_jurisdiction: Jurisdiction where the privilege encumbrance was lifted
        :param license_type: Type of license/privilege that had encumbrance lifted
        :param effective_lift_date: Date when the encumbrance was lifted
        :return: Response from the email notification service
        """
        payload = {
            'compact': compact,
            'jurisdiction': jurisdiction,
            'template': 'privilegeEncumbranceLiftingStateNotification',
            'recipientType': 'JURISDICTION_ADVERSE_ACTIONS',
            'templateVariables': {
                'providerFirstName': provider_first_name,
                'providerLastName': provider_last_name,
                'providerId': provider_id,
                'liftedJurisdiction': lifted_jurisdiction,
                'licenseType': license_type,
                'effectiveLiftDate': effective_lift_date,
            },
        }
        return self._invoke_lambda(payload)
