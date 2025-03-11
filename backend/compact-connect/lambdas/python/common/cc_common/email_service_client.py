import json
from datetime import datetime
from typing import Any, Optional

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
        self.lambda_client = lambda_client
        self.email_notification_service_lambda_name = email_notification_service_lambda_name
        self.logger = logger


    def _invoke_lambda(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Invoke the email notification service lambda with the given payload.

        :param payload: Payload to send to the lambda
        :return: Response from the lambda
        :raises CCInternalException: If the lambda invocation fails
        """
        if not self.email_notification_service_lambda_name:
            raise CCInternalException("Email notification service lambda name not set")

        try:
            response = self.lambda_client.invoke(
                FunctionName=self.email_notification_service_lambda_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload),
            )

            if response.get('FunctionError'):
                error_message = f"Failed to send email notification: {response.get('FunctionError')}"
                self.logger.error(error_message, payload=payload)
                raise CCInternalException(error_message)

            return response
        except Exception as e:
            error_message = f"Error invoking email notification service lambda: {str(e)}"
            self.logger.error(error_message, payload=payload, exception=str(e))
            raise CCInternalException(error_message) from e

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

    def send_custom_email(
        self,
        compact: str,
        template: str,
        recipient_type: str,
        template_variables: dict[str, Any],
        jurisdiction: Optional[str] = None,
        specific_emails: Optional[list[str]] = None,
    ) -> dict[str, str]:
        """
        Send a custom email using the email notification service.

        :param compact: Compact name
        :param template: Email template name
        :param recipient_type: Type of recipient (e.g., 'COMPACT_OPERATIONS_TEAM', 'SPECIFIC')
        :param template_variables: Variables to be used in the email template
        :param jurisdiction: Optional jurisdiction name
        :param specific_emails: Optional list of specific email addresses (required if recipient_type is 'SPECIFIC')
        :return: Response from the email notification service
        """
        payload = {
            'compact': compact,
            'template': template,
            'recipientType': recipient_type,
            'templateVariables': template_variables,
        }

        if jurisdiction:
            payload['jurisdiction'] = jurisdiction

        if specific_emails:
            payload['specificEmails'] = specific_emails

        return self._invoke_lambda(payload)
