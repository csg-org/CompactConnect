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
        provider_first_name: str,
        privilege_id: str,
        jurisdiction: str,
        license_type: str,
        total_cost: str,
        cost_line_items: list[dict]
    ) -> dict[str, str]:
        """
        Send a jurisdiction transaction report email.

        :param provider_first_name: Provider's first name
        :param privilege_id: Privilege Id of the purchased privilege
        :param jurisdiction: Jurisdiction name
        :param license_type: Reporting cycle (e.g., 'weekly', 'monthly')
        :param start_date: Start date of the reporting period
        :param end_date: End date of the reporting period
        :return: Response from the email notification service
        """

        payload = {
            'template': 'privilegePurchaseProviderNotification',
            'templateVariables': {
                'providerFirstName': provider_first_name,
                'privilegeId': privilege_id,
                'jurisdiction': jurisdiction,
                'licenseType': license_type,
                'totalCost': total_cost,
                'costLineItems': cost_line_items
            },
        }

        return self._invoke_lambda(payload)
