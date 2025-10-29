import { BaseEmailService } from './base-email-service';
import { IJurisdiction } from 'lib/models/jurisdiction';


/**
 * Service for handling investigation-related email notifications
 */
export class InvestigationNotificationService extends BaseEmailService {
    private async getJurisdictionAdverseActionRecipients(
        jurisdictionConfig: IJurisdiction
    ): Promise<string[]> {
        const recipients = jurisdictionConfig.jurisdictionAdverseActionsNotificationEmails;

        if (recipients.length === 0) {
            // If the state hasn't provided a contact for adverse actions, we note it and move on, preferring to
            // continue with other notifications, rather than failing the entire notification process.
            this.logger.warn('No adverse action notification recipients found for jurisdiction', {
                compact: jurisdictionConfig.compact,
                jurisdiction: jurisdictionConfig.postalAbbreviation
            });
            return [];
        }

        return recipients;
    }

    /**
     * Gets jurisdiction configurations and adverse action recipients for state notifications,
     * handling errors gracefully by logging warnings and continuing
     * @param compact - The compact name
     * @param notifyingJurisdiction - The jurisdiction that should be notified
     * @param affectedJurisdiction - The jurisdiction where the investigation occurred
     * @param context - Context for logging (e.g., 'license investigation', 'privilege investigation closed')
     * @returns Object containing recipients and affected jurisdiction config, or empty if error occurred
     */
    private async getStateNotificationData(
        compact: string,
        notifyingJurisdiction: string,
        affectedJurisdiction: string,
        context: string
    ): Promise<{
        recipients: string[];
        affectedJurisdictionConfig: IJurisdiction | undefined;
    }> {
        let affectedJurisdictionConfig: IJurisdiction | undefined;
        let recipients: string[] = [];

        try {
            const notifyingJurisdictionConfig = await this.jurisdictionClient.getJurisdictionConfiguration(
                compact, notifyingJurisdiction
            );

            if (notifyingJurisdictionConfig.postalAbbreviation !== affectedJurisdiction) {
                affectedJurisdictionConfig = await this.jurisdictionClient.getJurisdictionConfiguration(
                    compact, affectedJurisdiction
                );
            } else {
                affectedJurisdictionConfig = notifyingJurisdictionConfig;
            }

            recipients = await this.getJurisdictionAdverseActionRecipients(notifyingJurisdictionConfig);
        } catch (error) {
            // If we have missing jurisdiction configuration, we note it and move on, preferring to
            // continue, rather than failing the entire notification process.
            this.logger.warn(`Error getting jurisdiction configuration for state ${context} notification email`, {
                compact: compact,
                notifyingJurisdiction: notifyingJurisdiction,
                affectedJurisdiction: affectedJurisdiction,
                error: error
            });
        }

        return { recipients, affectedJurisdictionConfig };
    }

    /**
     * Sends a license investigation notification email to state authorities
     * @param compact - The compact name
     * @param jurisdiction - The jurisdiction to notify
     * @param providerFirstName - The provider's first name
     * @param providerLastName - The provider's last name
     * @param providerId - The provider's ID
     * @param investigationJurisdiction - The jurisdiction where the license is under investigation
     * @param licenseType - The license type that is under investigation
     */
    public async sendLicenseInvestigationStateNotificationEmail(
        compact: string,
        jurisdiction: string,
        providerFirstName: string,
        providerLastName: string,
        providerId: string,
        investigationJurisdiction: string,
        licenseType: string
    ): Promise<void> {
        this.logger.info('Sending license investigation state notification email', {
            compact: compact,
            jurisdiction: jurisdiction
        });

        const { recipients, affectedJurisdictionConfig } = await this.getStateNotificationData(
            compact, jurisdiction, investigationJurisdiction, 'license investigation'
        );

        if (recipients.length === 0) {
            this.logger.warn('No recipients found for license investigation state notification', {
                compact: compact,
                jurisdiction: jurisdiction
            });
            return;
        }

        const compactConfig = await this.compactConfigurationClient.getCompactConfiguration(compact);
        const report = this.getNewEmailTemplate();
        const subject = `${providerFirstName} ${providerLastName} holding ${licenseType} license in ${affectedJurisdictionConfig?.jurisdictionName} is under investigation`;
        const bodyText = `This message is to notify you that ${providerFirstName} ${providerLastName} (Provider ID: ${providerId}) ` +
            `holding a *${licenseType}* license in ${affectedJurisdictionConfig?.jurisdictionName} is under investigation ` +
            `in the ${compactConfig.compactName} compact.\n\n` +
            `Please contact the licensing board in ${affectedJurisdictionConfig?.jurisdictionName} for more information about this investigation.`;

        this.insertHeader(report, subject);
        this.insertBody(report, bodyText, 'center', true);
        this.insertFooter(report);

        const htmlContent = this.renderTemplate(report);

        await this.sendEmail({ htmlContent, subject, recipients, errorMessage: 'Unable to send license investigation state notification email' });
    }

    /**
     * Sends a license investigation closed notification email to state authorities
     * @param compact - The compact name
     * @param jurisdiction - The jurisdiction to notify
     * @param providerFirstName - The provider's first name
     * @param providerLastName - The provider's last name
     * @param providerId - The provider's ID
     * @param investigationJurisdiction - The jurisdiction where the license investigation was closed
     * @param licenseType - The license type that was under investigation
     */
    public async sendLicenseInvestigationClosedStateNotificationEmail(
        compact: string,
        jurisdiction: string,
        providerFirstName: string,
        providerLastName: string,
        providerId: string,
        investigationJurisdiction: string,
        licenseType: string
    ): Promise<void> {
        this.logger.info('Sending license investigation closed state notification email', {
            compact: compact,
            jurisdiction: jurisdiction
        });

        const { recipients, affectedJurisdictionConfig } = await this.getStateNotificationData(
            compact, jurisdiction, investigationJurisdiction, 'license investigation closed'
        );

        if (recipients.length === 0) {
            this.logger.warn('No recipients found for license investigation closed state notification', {
                compact: compact,
                jurisdiction: jurisdiction
            });
            return;
        }

        const compactConfig = await this.compactConfigurationClient.getCompactConfiguration(compact);
        const report = this.getNewEmailTemplate();
        const subject = `Investigation on ${providerFirstName} ${providerLastName}'s ${licenseType} license in ${affectedJurisdictionConfig?.jurisdictionName} has been closed`;
        const bodyText = `This message is to notify you that the investigation on ${providerFirstName} ${providerLastName} (Provider ID: ${providerId}) ` +
            `holding a *${licenseType}* license in ${affectedJurisdictionConfig?.jurisdictionName} has been closed ` +
            `in the ${compactConfig.compactName} compact.\n\n` +
            `Please contact the licensing board in ${affectedJurisdictionConfig?.jurisdictionName} for more information about this investigation closure.`;

        this.insertHeader(report, subject);
        this.insertBody(report, bodyText, 'center', true);
        this.insertFooter(report);

        const htmlContent = this.renderTemplate(report);

        await this.sendEmail({ htmlContent, subject, recipients, errorMessage: 'Unable to send license investigation closed state notification email' });
    }

    /**
     * Sends a privilege investigation notification email to state authorities
     * @param compact - The compact name
     * @param jurisdiction - The jurisdiction to notify
     * @param providerFirstName - The provider's first name
     * @param providerLastName - The provider's last name
     * @param providerId - The provider's ID
     * @param investigationJurisdiction - The jurisdiction where the privilege is under investigation
     * @param licenseType - The license type that is under investigation
     */
    public async sendPrivilegeInvestigationStateNotificationEmail(
        compact: string,
        jurisdiction: string,
        providerFirstName: string,
        providerLastName: string,
        providerId: string,
        investigationJurisdiction: string,
        licenseType: string
    ): Promise<void> {
        this.logger.info('Sending privilege investigation state notification email', {
            compact: compact,
            jurisdiction: jurisdiction
        });

        const { recipients, affectedJurisdictionConfig } = await this.getStateNotificationData(
            compact, jurisdiction, investigationJurisdiction, 'privilege investigation'
        );

        if (recipients.length === 0) {
            this.logger.warn('No recipients found for privilege investigation state notification', {
                compact: compact,
                jurisdiction: jurisdiction
            });
            return;
        }

        const compactConfig = await this.compactConfigurationClient.getCompactConfiguration(compact);
        const report = this.getNewEmailTemplate();
        const subject = `${providerFirstName} ${providerLastName} holding ${licenseType} privilege in ${affectedJurisdictionConfig?.jurisdictionName} is under investigation`;
        const bodyText = `This message is to notify you that ${providerFirstName} ${providerLastName} (Provider ID: ${providerId}) ` +
            `holding a *${licenseType}* privilege in ${affectedJurisdictionConfig?.jurisdictionName} is under investigation ` +
            `in the ${compactConfig.compactName} compact.\n\n` +
            `Please contact the licensing board in ${affectedJurisdictionConfig?.jurisdictionName} for more information about this investigation.`;

        this.insertHeader(report, subject);
        this.insertBody(report, bodyText, 'center', true);
        this.insertFooter(report);

        const htmlContent = this.renderTemplate(report);

        await this.sendEmail({ htmlContent, subject, recipients, errorMessage: 'Unable to send privilege investigation state notification email' });
    }

    /**
     * Sends a privilege investigation closed notification email to state authorities
     * @param compact - The compact name
     * @param jurisdiction - The jurisdiction to notify
     * @param providerFirstName - The provider's first name
     * @param providerLastName - The provider's last name
     * @param providerId - The provider's ID
     * @param investigationJurisdiction - The jurisdiction where the privilege investigation was closed
     * @param licenseType - The license type that was under investigation
     */
    public async sendPrivilegeInvestigationClosedStateNotificationEmail(
        compact: string,
        jurisdiction: string,
        providerFirstName: string,
        providerLastName: string,
        providerId: string,
        investigationJurisdiction: string,
        licenseType: string
    ): Promise<void> {
        this.logger.info('Sending privilege investigation closed state notification email', {
            compact: compact,
            jurisdiction: jurisdiction
        });

        const { recipients, affectedJurisdictionConfig } = await this.getStateNotificationData(
            compact, jurisdiction, investigationJurisdiction, 'privilege investigation closed'
        );

        if (recipients.length === 0) {
            this.logger.warn('No recipients found for privilege investigation closed state notification', {
                compact: compact,
                jurisdiction: jurisdiction
            });
            return;
        }

        const compactConfig = await this.compactConfigurationClient.getCompactConfiguration(compact);
        const report = this.getNewEmailTemplate();
        const subject = `Investigation on ${providerFirstName} ${providerLastName}'s ${licenseType} privilege in ${affectedJurisdictionConfig?.jurisdictionName} has been closed`;
        const bodyText = `This message is to notify you that the investigation on ${providerFirstName} ${providerLastName} (Provider ID: ${providerId}) ` +
            `holding a *${licenseType}* privilege in ${affectedJurisdictionConfig?.jurisdictionName} has been closed ` +
            `in the ${compactConfig.compactName} compact.\n\n` +
            `Please contact the licensing board in ${affectedJurisdictionConfig?.jurisdictionName} for more information about this investigation closure.`;

        this.insertHeader(report, subject);
        this.insertBody(report, bodyText, 'center', true);
        this.insertFooter(report);

        const htmlContent = this.renderTemplate(report);

        await this.sendEmail({ htmlContent, subject, recipients, errorMessage: 'Unable to send privilege investigation closed state notification email' });
    }
}
