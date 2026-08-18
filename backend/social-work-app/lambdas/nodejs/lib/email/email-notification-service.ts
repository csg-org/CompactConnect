import { BaseEmailService } from './base-email-service';
import { EnvironmentVariablesService } from '../environment-variables-service';
import { RecipientType } from '../models/email-notification-service-event';

const environmentVariableService = new EnvironmentVariablesService();

/** Format an ISO 8601 date string (YYYY-MM-DD) for display as MM/DD/YYYY (e.g. "09/14/2026"). Timezone-neutral. */
function formatIsoDateAsSlashFormat(isoDate: string): string {
    const [year, month, day] = isoDate.split('-').map(Number);
    const paddedMonth = String(month).padStart(2, '0');
    const paddedDay = String(day).padStart(2, '0');

    return `${paddedMonth}/${paddedDay}/${year}`;
}

/**
 * Email service for handling email notifications
 */
export class EmailNotificationService extends BaseEmailService {

    private async getJurisdictionRecipients(
        compact: string,
        jurisdiction: string,
        recipientType: RecipientType
    ): Promise<string[]> {

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

    /**
     * Sends a notification that a staff user's account is scheduled for inactivity deactivation.
     *
     * The body is written in the third person so the same email serves the staff user and their
     * administrators, and states an absolute date rather than a countdown so it stays true whenever it is read.
     *
     * @param compact - The compact name
     * @param specificEmails - The address(es) to send this notification to
     * @param staffUserFirstName - The affected staff user's first name
     * @param staffUserLastName - The affected staff user's last name
     * @param staffUserEmail - The affected staff user's email address
     * @param deactivationDate - ISO 8601 date string (YYYY-MM-DD) the account is deactivated on
     * @param inactivityPeriodDays - How many days of inactivity trigger deactivation
     */
    public async sendStaffUserInactivityNotificationEmail(
        compact: string,
        specificEmails: string[],
        staffUserFirstName: string,
        staffUserLastName: string,
        staffUserEmail: string,
        deactivationDate: string,
        inactivityPeriodDays: number
    ): Promise<void> {
        this.logger.info('Sending staff user inactivity notification email', { compact: compact });

        if (specificEmails.length === 0) {
            throw new Error('No recipients found for staff user inactivity notification email');
        }

        const compactConfig = await this.compactConfigurationClient.getCompactConfiguration(compact);
        const staffUserName = `${staffUserFirstName} ${staffUserLastName}`;
        const deactivationDateDisplay = formatIsoDateAsSlashFormat(deactivationDate);
        const subject = `CompactConnect account for ${staffUserName} will be deactivated on ${deactivationDateDisplay}`;

        const report = this.getNewEmailTemplate();
        const bodyText = `The ${compactConfig.compactName} CompactConnect account for ${staffUserName} (${staffUserEmail}) will be deactivated on **${deactivationDateDisplay}**. CompactConnect deactivates staff user accounts after ${inactivityPeriodDays} days with no sign-in activity.\n\n` +
            `To prevent deactivation, ${staffUserName} should sign in to CompactConnect before **${deactivationDateDisplay}**.\n\n` +
            `If the account has already been deactivated, an administrator will need to re-invite ${staffUserName} to CompactConnect to restore access.\n\n` +
            `Sign in: ${environmentVariableService.getUiBasePathUrl()}/Dashboard`;

        this.insertHeader(report, 'Account Deactivation Notice');
        this.insertBody(report, bodyText, 'center', true);
        this.insertFooter(report);

        const htmlContent = this.renderTemplate(report);

        await this.sendEmail({
            htmlContent,
            subject,
            recipients: specificEmails,
            errorMessage: 'Unable to send staff user inactivity notification email'
        });
    }

}
