import { BaseEmailService } from './base-email-service';
import { EnvironmentVariablesService } from '../environment-variables-service';
import { RecipientType } from '../models/email-notification-service-event';

const environmentVariableService = new EnvironmentVariablesService();

/**
 * Email service for handling email notifications
 */
export class EmailNotificationService extends BaseEmailService {

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
        case 'JURISDICTION_OPERATIONS_TEAM':
            return jurisdictionConfig.jurisdictionOperationsTeamEmails;
        default:
            throw new Error(`Unsupported recipient type for compact configuration: ${recipientType}`);
        }
    }

    /**
     * Sends a notification email to a jurisdiction operations team when a practitioner's home state license changes
     * @param compact - The compact name
     * @param jurisdiction - The jurisdiction to notify
     * @param providerFirstName - The provider's first name
     * @param providerLastName - The provider's last name
     * @param providerId - The provider's ID
     * @param previousJurisdiction - The previous home jurisdiction
     * @param newJurisdiction - The new home jurisdiction
     */
    public async sendHomeJurisdictionChangeStateNotificationEmail(
        compact: string,
        jurisdiction: string,
        providerFirstName: string,
        providerLastName: string,
        providerId: string,
        previousJurisdiction: string,
        newJurisdiction: string
    ): Promise<void> {
        this.logger.info('Sending home jurisdiction change state notification email', {
            compact: compact,
            jurisdiction: jurisdiction
        });

        const recipients = await this.getJurisdictionRecipients(
            compact,
            jurisdiction,
            'JURISDICTION_OPERATIONS_TEAM'
        );

        if (recipients.length === 0) {
            throw new Error(`No recipients found for jurisdiction ${jurisdiction} in compact ${compact}`);
        }

        const formattedPreviousJurisdiction = previousJurisdiction.toUpperCase();
        const formattedNewJurisdiction = newJurisdiction.toUpperCase();

        const compactConfig = await this.compactConfigurationClient.getCompactConfiguration(compact);
        const report = this.getNewEmailTemplate();
        const subject = `Practitioner Home State Change - ${compactConfig.compactName}`;
        const bodyText = `This is to notify you that ${providerFirstName} ${providerLastName} has changed their home state from ${formattedPreviousJurisdiction} to ${formattedNewJurisdiction}.\n\n` +
            `Provider Details: ${environmentVariableService.getUiBasePathUrl()}/${compact}/Licensing/${providerId}\n\n` +
            'If the above link does not work, you can copy and paste the url into a browser tab, where you are already logged in.';

        this.insertHeader(report, subject);
        this.insertBody(report, bodyText, 'center', true);
        this.insertFooter(report);

        const htmlContent = this.renderTemplate(report);

        await this.sendEmail({ htmlContent, subject, recipients, errorMessage: 'Unable to send home jurisdiction change state notification email' });
    }
}
