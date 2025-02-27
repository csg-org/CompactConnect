import { GetObjectCommand } from '@aws-sdk/client-s3';
import { renderToStaticMarkup } from '@usewaypoint/email-builder';
import { BaseEmailService } from './base-email-service';
import { EnvironmentVariablesService } from '../environment-variables-service';
import { RecipientType } from '../models/email-notification-service-event';

const environmentVariableService = new EnvironmentVariablesService();

/**
 * Email service for handling email notifications
 */
export class EmailNotificationService extends BaseEmailService {
    private async getRecipients(compact: string,
        recipientType: RecipientType,
        specificEmails?: string[]
    ): Promise<string[]> {
        if (recipientType === 'SPECIFIC') {
            if (specificEmails) return specificEmails;

            throw new Error(`SPECIFIC recipientType requested but no specific email addresses provided`);
        }

        const compactConfig = await this.compactConfigurationClient.getCompactConfiguration(compact);

        switch (recipientType) {
        case 'COMPACT_OPERATIONS_TEAM':
            return compactConfig.compactOperationsTeamEmails;
        case 'COMPACT_SUMMARY_REPORT':
            return compactConfig.compactSummaryReportNotificationEmails;
        default:
            throw new Error(`Unsupported recipient type for compact configuration: ${recipientType}`);
        }
    }

    public async sendTransactionBatchSettlementFailureEmail(compact: string,
        recipientType: RecipientType,
        specificEmails?: string[]
    ): Promise<void> {
        this.logger.info('Sending transaction batch settlement failure email', { compact: compact });
        const recipients = await this.getRecipients(compact, recipientType, specificEmails);

        if (recipients.length === 0) {
            throw new Error(`No recipients found for compact ${compact} with recipient type ${recipientType}`);
        }

        const report = JSON.parse(JSON.stringify(this.emailTemplate));
        const subject = `Transactions Failed to Settle for ${compact.toUpperCase()} Payment Processor`;
        const bodyText = 'A transaction settlement error was detected within the payment processing account for the compact. ' +
            'Please reach out to your payment processing representative to determine the cause. ' +
            'Transactions made in the account will not be able to be settled until the issue is addressed.';

        this.insertHeader(report, subject);
        this.insertBody(report, bodyText);
        this.insertFooter(report);

        const htmlContent = renderToStaticMarkup(report, { rootBlockId: 'root' });

        await this.sendEmail({ htmlContent, subject, recipients, errorMessage: 'Unable to send transaction batch settlement failure email' });
    }

    public async sendCompactTransactionReportEmail(
        compact: string,
        reportS3Path: string,
        reportingCycle: string,
        startDate: string,
        endDate: string
    ): Promise<void> {
        this.logger.info('Sending compact transaction report email', { compact: compact });
        const recipients = await this.getRecipients(compact, 'COMPACT_SUMMARY_REPORT');

        if (recipients.length === 0) {
            throw new Error(`No recipients found for compact ${compact} with recipient type COMPACT_SUMMARY_REPORT`);
        }

        // Get the report zip file from S3
        const reportZipResponse = await this.s3Client.send(new GetObjectCommand({
            Bucket: environmentVariableService.getTransactionReportsBucketName(),
            Key: reportS3Path
        }));

        if (!reportZipResponse.Body) {
            throw new Error(`Failed to retrieve report from S3: ${reportS3Path}`);
        }

        const reportZipBuffer = Buffer.from(await reportZipResponse.Body.transformToByteArray());

        const report = JSON.parse(JSON.stringify(this.emailTemplate));
        const subject = `${reportingCycle === 'weekly' ? 'Weekly' : 'Monthly'} Report for Compact ${compact.toUpperCase()}`;
        const bodyText = `Please find attached the ${reportingCycle} settled transaction reports for the compact for the period ${startDate} to ${endDate}:\n\n` +
            '- Financial Summary Report - A summary of all settled transactions and fees\n' +
            '- Transaction Detail Report - A detailed list of all settled transactions';

        this.insertHeader(report, subject);
        this.insertMarkdownBody(report, bodyText);
        this.insertFooter(report);

        const htmlContent = renderToStaticMarkup(report, { rootBlockId: 'root' });

        await this.sendEmailWithAttachments({
            htmlContent,
            subject,
            recipients,
            errorMessage: 'Unable to send compact transaction report email',
            attachments: [
                {
                    filename: `${compact}-settled-transaction-report-${startDate}--${endDate}.zip`,
                    content: reportZipBuffer,
                    contentType: 'application/zip'
                }
            ]
        });
    }

    public async sendJurisdictionTransactionReportEmail(
        compact: string,
        jurisdiction: string,
        reportS3Path: string,
        reportingCycle: string,
        startDate: string,
        endDate: string
    ): Promise<void> {
        this.logger.info('Sending jurisdiction transaction report email', {
            compact: compact,
            jurisdiction: jurisdiction
        });

        const jurisdictionConfig = await this.jurisdictionClient.getJurisdictionConfiguration(compact, jurisdiction);
        const recipients = jurisdictionConfig.jurisdictionSummaryReportNotificationEmails;

        if (recipients.length === 0) {
            throw new Error(`No recipients found for jurisdiction ${jurisdiction} in compact ${compact}`);
        }

        // Get the report zip file from S3
        const reportZipResponse = await this.s3Client.send(new GetObjectCommand({
            Bucket: environmentVariableService.getTransactionReportsBucketName(),
            Key: reportS3Path
        }));

        if (!reportZipResponse.Body) {
            throw new Error(`Failed to retrieve report from S3: ${reportS3Path}`);
        }

        const reportZipBuffer = Buffer.from(await reportZipResponse.Body.transformToByteArray());

        const report = JSON.parse(JSON.stringify(this.emailTemplate));
        const subject = `${jurisdictionConfig.jurisdictionName} ${reportingCycle === 'weekly' ? 'Weekly' : 'Monthly'} Report for Compact ${compact.toUpperCase()}`;
        const bodyText = `Please find attached the ${reportingCycle} settled transaction report for your jurisdiction for the period ${startDate} to ${endDate}.`;

        this.insertHeader(report, subject);
        this.insertBody(report, bodyText);
        this.insertFooter(report);

        const htmlContent = renderToStaticMarkup(report, { rootBlockId: 'root' });

        await this.sendEmailWithAttachments({
            htmlContent,
            subject,
            recipients,
            errorMessage: 'Unable to send jurisdiction transaction report email',
            attachments: [
                {
                    filename: `${jurisdiction}-settled-transaction-report-${startDate}--${endDate}.zip`,
                    content: reportZipBuffer,
                    contentType: 'application/zip'
                }
            ]
        });
    }
}
