import { BaseEmailService } from './base-email-service';
import { RecipientType } from '../models/email-notification-service-event';
/**
 * Email service for handling email notifications
 */
export class EmailNotificationService extends BaseEmailService {
    private async getCompactRecipients(
        compact: string,
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

    private async getJurisdictionRecipients(
        compact: string,
        jurisdiction: string,
        recipientType: RecipientType,
        specificEmails?: string[]
    ): Promise<string[]> {
        if (recipientType === 'SPECIFIC') {
            if (specificEmails) return specificEmails;

            throw new Error(`SPECIFIC recipientType requested but no specific email addresses provided`);
        }

        const jurisdictionConfig = await this.jurisdictionClient.getJurisdictionConfiguration(compact, jurisdiction);

        switch (recipientType) {
        case 'JURISDICTION_SUMMARY_REPORT':
            return jurisdictionConfig.jurisdictionSummaryReportNotificationEmails;
        default:
            throw new Error(`Unsupported recipient type for compact configuration: ${recipientType}`);
        }
    }

    public async sendTransactionBatchSettlementFailureEmail(
        compact: string,
        recipientType: RecipientType,
        specificEmails?: string[],
        batchFailureErrorMessage?: string
    ): Promise<void> {
        this.logger.info('Sending transaction batch settlement failure email', { compact: compact });
        const recipients = await this.getCompactRecipients(compact, recipientType, specificEmails);

        if (recipients.length === 0) {
            throw new Error(`No recipients found for compact ${compact} with recipient type ${recipientType}`);
        }

        const compactConfig = await this.compactConfigurationClient.getCompactConfiguration(compact);
        const report = this.getNewEmailTemplate();
        const subject = `Transactions Failed to Settle for ${compactConfig.compactName} Payment Processor`;
        
        let bodyText = 'A transaction settlement error was detected within the payment processing account for the compact. ' +
            'Please reach out to your payment processing representative if needed to determine the cause. ';

        // Include detailed error message if provided
        if (batchFailureErrorMessage) {
            try {
                const errorDetails = JSON.parse(batchFailureErrorMessage);

                bodyText += '\n\nDetailed Error Information:\n';
                
                if (errorDetails.message) {
                    bodyText += `Error Message: ${errorDetails.message}\n`;
                }
                
                if (errorDetails.failedTransactionIds && errorDetails.failedTransactionIds.length > 0) {
                    bodyText += `Failed Transaction IDs: ${errorDetails.failedTransactionIds.join(', ')}\n`;
                }
                
                if (errorDetails.unsettledTransactionIds && errorDetails.unsettledTransactionIds.length > 0) {
                    bodyText += `Unsettled Transaction IDs (older than 48 hours): ${errorDetails.unsettledTransactionIds.join(', ')}\n`;
                }
            } catch {
                // If JSON parsing fails, include the raw message
                bodyText += `\n\nError Details: ${batchFailureErrorMessage}`;
            }
        }

        this.insertHeader(report, subject);
        this.insertBody(report, bodyText, 'center', true);
        this.insertFooter(report);

        const htmlContent = this.renderTemplate(report);

        await this.sendEmail({ htmlContent, subject, recipients, errorMessage: 'Unable to send transaction batch settlement failure email' });
    }

    /**
     * Sends an email notification to the jurisdiction report notification emails when a privilege is deactivated
     * @param compact - The compact name for which the privilege was deactivated
     * @param jurisdiction - The jurisdiction for which the privilege was deactivated
     * @param privilegeId - The privilege ID of the privilege that was deactivated
     * @param providerFirstName - The first name of the provider whose privilege was deactivated
     * @param providerLastName - The last name of the provider whose privilege was deactivated
     */
    public async sendPrivilegeDeactivationJurisdictionNotificationEmail(
        compact: string,
        jurisdiction: string,
        recipientType: RecipientType,
        privilegeId: string,
        providerFirstName: string,
        providerLastName: string
    ): Promise<void> {

        this.logger.info('Sending privilege deactivation jurisdiction notification email', { compact: compact, jurisdiction: jurisdiction });

        const recipients = await this.getJurisdictionRecipients(
            compact,
            jurisdiction,
            recipientType
        );

        if (recipients?.length === 0) {
            throw new Error(`No recipients found for jurisdiction ${jurisdiction} in compact ${compact}`);
        }

        const compactConfig = await this.compactConfigurationClient.getCompactConfiguration(compact);
        const report = this.getNewEmailTemplate();
        const subject = `A Privilege was Deactivated in the ${compactConfig.compactName} Compact`;
        const bodyText = `This message is to notify you that privilege ${privilegeId} held by ${providerFirstName} ${providerLastName} was deactivated and can no longer be used to practice.`;

        this.insertHeader(report, subject);
        this.insertBody(report, bodyText);
        this.insertFooter(report);

        const htmlContent = this.renderTemplate(report);

        await this.sendEmail({ htmlContent, subject, recipients, errorMessage: 'Unable to send privilege deactivation state notification email' });
    }
}
