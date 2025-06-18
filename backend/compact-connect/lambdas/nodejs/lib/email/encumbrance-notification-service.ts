import { renderToStaticMarkup } from '@usewaypoint/email-builder';
import { BaseEmailService } from './base-email-service';
import { EnvironmentVariablesService } from '../environment-variables-service';
import { IJurisdiction } from 'lib/models/jurisdiction';

const environmentVariableService = new EnvironmentVariablesService();

/**
 * Service for handling encumbrance-related email notifications
 */
export class EncumbranceNotificationService extends BaseEmailService {
    private async getJurisdictionAdverseActionRecipients(
        jurisdictionConfig: IJurisdiction
    ): Promise<string[]> {
        const recipients = jurisdictionConfig.jurisdictionAdverseActionsNotificationEmails;

        if (recipients.length === 0) {
            this.logger.error('No adverse action notification recipients found for jurisdiction', {
                compact: jurisdictionConfig.compact,
                jurisdiction: jurisdictionConfig.postalAbbreviation
            });
            throw new Error(`No adverse action notification recipients found for jurisdiction ${jurisdictionConfig.postalAbbreviation} in compact ${jurisdictionConfig.compact}`);
        }

        return recipients;
    }

    /**
     * Sends a license encumbrance notification email to the provider
     * @param compact - The compact name
     * @param specificEmails - The provider's email address
     * @param providerFirstName - The provider's first name
     * @param providerLastName - The provider's last name
     * @param jurisdiction - The jurisdiction where the license was encumbered
     * @param licenseType - The license type that was encumbered
     * @param effectiveStartDate - The date the encumbrance became effective
     */
    public async sendLicenseEncumbranceProviderNotificationEmail(
        compact: string,
        specificEmails: string[],
        providerFirstName: string,
        providerLastName: string,
        encumberedJurisdiction: string,
        licenseType: string,
        effectiveStartDate: string
    ): Promise<void> {
        this.logger.info('Sending license encumbrance provider notification email', { compact: compact });

        if (specificEmails.length === 0) {
            throw new Error('No recipients specified for provider license encumbrance notification email');
        }

        const encumberedJurisdictionConfig = await this.jurisdictionClient.getJurisdictionConfiguration(
            compact, encumberedJurisdiction
        );
        const compactConfig = await this.compactConfigurationClient.getCompactConfiguration(compact);

        const report = this.getNewEmailTemplate();
        const subject = `Your ${licenseType} license in ${encumberedJurisdictionConfig.jurisdictionName} is encumbered`;
        const bodyText = `${providerFirstName} ${providerLastName},\n\n` +
            `This message is to notify you that your *${licenseType}* license in ${encumberedJurisdictionConfig.jurisdictionName} was encumbered, effective ${effectiveStartDate}. ` +
            `This encumbrance restricts your ability to practice under the ${compactConfig.compactName} compact.\n\n` +
            `Please contact the licensing board in ${encumberedJurisdictionConfig.jurisdictionName} for more information about this encumbrance.`;

        this.insertHeader(report, subject);
        this.insertBody(report, bodyText, 'center', true);
        this.insertFooter(report);

        const htmlContent = renderToStaticMarkup(report, { rootBlockId: 'root' });

        await this.sendEmail({ htmlContent, subject, recipients: specificEmails, errorMessage: 'Unable to send provider license encumbrance notification email' });
    }

    /**
     * Sends a license encumbrance notification email to state authorities
     * @param compact - The compact name
     * @param jurisdiction - The jurisdiction to notify
     * @param providerFirstName - The provider's first name
     * @param providerLastName - The provider's last name
     * @param providerId - The provider's ID
     * @param encumberedJurisdiction - The jurisdiction where the license was encumbered
     * @param licenseType - The license type that was encumbered
     * @param effectiveStartDate - The date the encumbrance became effective
     */
    public async sendLicenseEncumbranceStateNotificationEmail(
        compact: string,
        jurisdiction: string,
        providerFirstName: string,
        providerLastName: string,
        providerId: string,
        encumberedJurisdiction: string,
        licenseType: string,
        effectiveStartDate: string
    ): Promise<void> {
        this.logger.info('Sending license encumbrance state notification email', {
            compact: compact,
            jurisdiction: jurisdiction
        });

        let encumberedJurisdictionConfig: IJurisdiction;
        const jurisdictionConfig = await this.jurisdictionClient.getJurisdictionConfiguration(compact, jurisdiction);
        const compactConfig = await this.compactConfigurationClient.getCompactConfiguration(compact);

        if (jurisdictionConfig.postalAbbreviation != encumberedJurisdiction) {
            encumberedJurisdictionConfig = await this.jurisdictionClient.getJurisdictionConfiguration(
                compact, encumberedJurisdiction
            );
        } else {
            encumberedJurisdictionConfig = jurisdictionConfig;
        }
        const recipients = await this.getJurisdictionAdverseActionRecipients(jurisdictionConfig);

        const report = this.getNewEmailTemplate();
        const subject = `License Encumbrance Notification - ${providerFirstName} ${providerLastName}`;
        const bodyText = `This message is to notify you that the *${licenseType}* license held by ${providerFirstName} ${providerLastName} ` +
            `in ${encumberedJurisdictionConfig.jurisdictionName} was encumbered, effective ${effectiveStartDate}.\n\n` +
            `Provider Details: ${environmentVariableService.getUiBasePathUrl()}/${compact}/Licensing/${providerId}\n\n` +
            `This encumbrance restricts the provider's ability to practice under the ${compactConfig.compactName} compact.`;

        this.insertHeader(report, subject);
        this.insertBody(report, bodyText, 'center', true);
        this.insertFooter(report);

        const htmlContent = renderToStaticMarkup(report, { rootBlockId: 'root' });

        await this.sendEmail({ htmlContent, subject, recipients, errorMessage: 'Unable to send state license encumbrance notification email' });
    }

    /**
     * Sends a license encumbrance lifting notification email to the provider
     * @param compact - The compact name
     * @param specificEmails - The provider's email address
     * @param providerFirstName - The provider's first name
     * @param providerLastName - The provider's last name
     * @param jurisdiction - The jurisdiction where the license encumbrance was lifted
     * @param licenseType - The license type that had encumbrance lifted
     * @param effectiveLiftDate - The date the encumbrance was lifted
     */
    public async sendLicenseEncumbranceLiftingProviderNotificationEmail(
        compact: string,
        specificEmails: string[],
        providerFirstName: string,
        providerLastName: string,
        liftedJurisdiction: string,
        licenseType: string,
        effectiveLiftDate: string
    ): Promise<void> {
        this.logger.info('Sending license encumbrance lifting provider notification email', { compact: compact });

        if (specificEmails.length === 0) {
            throw new Error('No recipients specified for provider license encumbrance lifting notification email');
        }

        const liftedJurisdictionConfig = await this.jurisdictionClient.getJurisdictionConfiguration(
            compact, liftedJurisdiction
        );
        const compactConfig = await this.compactConfigurationClient.getCompactConfiguration(compact);

        const report = this.getNewEmailTemplate();
        const subject = `Your ${licenseType} license in ${liftedJurisdictionConfig.jurisdictionName} is no longer encumbered`;
        const bodyText = `${providerFirstName} ${providerLastName},\n\n` +
            `This message is to notify you that the encumbrance on your *${licenseType}* license in ${liftedJurisdictionConfig.jurisdictionName} was lifted, effective ${effectiveLiftDate}. ` +
            `This encumbrance no longer restricts your ability to practice under the ${compactConfig.compactName} compact.\n\n` +
            `Please contact the licensing board in ${liftedJurisdictionConfig.jurisdictionName} if you have any questions about this change.`;

        this.insertHeader(report, subject);
        this.insertBody(report, bodyText, 'center', true);
        this.insertFooter(report);

        const htmlContent = renderToStaticMarkup(report, { rootBlockId: 'root' });

        await this.sendEmail({ htmlContent, subject, recipients: specificEmails, errorMessage: 'Unable to send provider license encumbrance lifting notification email' });
    }

    /**
     * Sends a license encumbrance lifting notification email to state authorities
     * @param compact - The compact name
     * @param jurisdiction - The jurisdiction to notify
     * @param providerFirstName - The provider's first name
     * @param providerLastName - The provider's last name
     * @param providerId - The provider's ID
     * @param liftedJurisdiction - The jurisdiction where the license encumbrance was lifted
     * @param licenseType - The license type that had encumbrance lifted
     * @param effectiveLiftDate - The date the encumbrance was lifted
     */
    public async sendLicenseEncumbranceLiftingStateNotificationEmail(
        compact: string,
        jurisdiction: string,
        providerFirstName: string,
        providerLastName: string,
        providerId: string,
        liftedJurisdiction: string,
        licenseType: string,
        effectiveLiftDate: string
    ): Promise<void> {
        this.logger.info('Sending license encumbrance lifting state notification email', {
            compact: compact,
            jurisdiction: jurisdiction
        });

        let liftedJurisdictionConfig: IJurisdiction;
        const jurisdictionConfig = await this.jurisdictionClient.getJurisdictionConfiguration(compact, jurisdiction);
        const compactConfig = await this.compactConfigurationClient.getCompactConfiguration(compact);

        if (jurisdictionConfig.postalAbbreviation != liftedJurisdiction) {
            liftedJurisdictionConfig = await this.jurisdictionClient.getJurisdictionConfiguration(
                compact, liftedJurisdiction
            );
        } else {
            liftedJurisdictionConfig = jurisdictionConfig;
        }
        const recipients = await this.getJurisdictionAdverseActionRecipients(jurisdictionConfig);

        const report = this.getNewEmailTemplate();
        const subject = `License Encumbrance Lifted Notification - ${providerFirstName} ${providerLastName}`;
        const bodyText = `This message is to notify you that the encumbrance on the *${licenseType}* license held by ${providerFirstName} ${providerLastName} ` +
            `in ${liftedJurisdictionConfig.jurisdictionName} was lifted, effective ${effectiveLiftDate}.\n\n` +
            `Provider Details: ${environmentVariableService.getUiBasePathUrl()}/${compact}/Licensing/${providerId}\n\n` +
            `The encumbrance no longer restricts the provider's ability to practice under the ${compactConfig.compactName} compact.`;

        this.insertHeader(report, subject);
        this.insertBody(report, bodyText, 'center', true);
        this.insertFooter(report);

        const htmlContent = renderToStaticMarkup(report, { rootBlockId: 'root' });

        await this.sendEmail({ htmlContent, subject, recipients, errorMessage: 'Unable to send state license encumbrance lifting notification email' });
    }

    /**
     * Sends a privilege encumbrance notification email to the provider
     * @param compact - The compact name
     * @param specificEmails - The provider's email address
     * @param providerFirstName - The provider's first name
     * @param providerLastName - The provider's last name
     * @param jurisdiction - The jurisdiction where the privilege was encumbered
     * @param licenseType - The license type associated with the privilege
     * @param effectiveStartDate - The date the encumbrance became effective
     */
    public async sendPrivilegeEncumbranceProviderNotificationEmail(
        compact: string,
        specificEmails: string[],
        providerFirstName: string,
        providerLastName: string,
        encumberedJurisdiction: string,
        licenseType: string,
        effectiveStartDate: string
    ): Promise<void> {
        this.logger.info('Sending privilege encumbrance provider notification email', { compact: compact });

        if (specificEmails.length === 0) {
            throw new Error('No recipients specified for provider privilege encumbrance notification email');
        }

        const encumberedJurisdictionConfig = await this.jurisdictionClient.getJurisdictionConfiguration(
            compact, encumberedJurisdiction
        );
        const compactConfig = await this.compactConfigurationClient.getCompactConfiguration(compact);

        const report = this.getNewEmailTemplate();
        const subject = `Your ${licenseType} privilege in ${encumberedJurisdictionConfig.jurisdictionName} is encumbered`;
        const bodyText = `${providerFirstName} ${providerLastName},\n\n` +
            `This message is to notify you that your *${licenseType}* privilege in ${encumberedJurisdictionConfig.jurisdictionName} has been encumbered, effective ${effectiveStartDate}. ` +
            `This encumbrance restricts your ability to practice in ${encumberedJurisdictionConfig.jurisdictionName} under the ${compactConfig.compactName} compact.\n\n` +
            `Please contact the licensing board in ${encumberedJurisdictionConfig.jurisdictionName} for more information about this encumbrance.`;

        this.insertHeader(report, subject);
        this.insertBody(report, bodyText, 'center', true);
        this.insertFooter(report);

        const htmlContent = renderToStaticMarkup(report, { rootBlockId: 'root' });

        await this.sendEmail({ htmlContent, subject, recipients: specificEmails, errorMessage: 'Unable to send provider privilege encumbrance notification email' });
    }

    /**
     * Sends a privilege encumbrance notification email to state authorities
     * @param compact - The compact name
     * @param jurisdiction - The jurisdiction to notify
     * @param providerFirstName - The provider's first name
     * @param providerLastName - The provider's last name
     * @param providerId - The provider's ID
     * @param encumberedJurisdiction - The jurisdiction where the privilege was encumbered
     * @param licenseType - The license type associated with the privilege
     * @param effectiveStartDate - The date the encumbrance became effective
     */
    public async sendPrivilegeEncumbranceStateNotificationEmail(
        compact: string,
        jurisdiction: string,
        providerFirstName: string,
        providerLastName: string,
        providerId: string,
        encumberedJurisdiction: string,
        licenseType: string,
        effectiveStartDate: string
    ): Promise<void> {
        this.logger.info('Sending privilege encumbrance state notification email', {
            compact: compact,
            jurisdiction: jurisdiction
        });

        let encumberedJurisdictionConfig: IJurisdiction;
        const jurisdictionConfig = await this.jurisdictionClient.getJurisdictionConfiguration(compact, jurisdiction);
        const compactConfig = await this.compactConfigurationClient.getCompactConfiguration(compact);

        if (jurisdictionConfig.postalAbbreviation != encumberedJurisdiction) {
            encumberedJurisdictionConfig = await this.jurisdictionClient.getJurisdictionConfiguration(
                compact, encumberedJurisdiction
            );
        } else {
            encumberedJurisdictionConfig = jurisdictionConfig;
        }
        const recipients = await this.getJurisdictionAdverseActionRecipients(jurisdictionConfig);



        const report = this.getNewEmailTemplate();
        const subject = `Privilege Encumbrance Notification - ${providerFirstName} ${providerLastName}`;
        const bodyText = `This message is to notify you that the *${licenseType}* privilege held by ${providerFirstName} ${providerLastName} ` +
            `in ${encumberedJurisdictionConfig.jurisdictionName} was encumbered, effective ${effectiveStartDate}.\n\n` +
            `Provider Details: ${environmentVariableService.getUiBasePathUrl()}/${compact}/Licensing/${providerId}\n\n` +
            `This encumbrance restricts the provider's ability to practice in ${encumberedJurisdictionConfig.jurisdictionName} under the ${compactConfig.compactName} compact.`;

        this.insertHeader(report, subject);
        this.insertBody(report, bodyText, 'center', true);
        this.insertFooter(report);

        const htmlContent = renderToStaticMarkup(report, { rootBlockId: 'root' });

        await this.sendEmail({ htmlContent, subject, recipients, errorMessage: 'Unable to send state privilege encumbrance notification email' });
    }

    /**
     * Sends a privilege encumbrance lifting notification email to the provider
     * @param compact - The compact name
     * @param specificEmails - The provider's email address
     * @param providerFirstName - The provider's first name
     * @param providerLastName - The provider's last name
     * @param jurisdiction - The jurisdiction where the privilege encumbrance was lifted
     * @param licenseType - The license type associated with the privilege
     * @param effectiveLiftDate - The date the encumbrance was lifted
     */
    public async sendPrivilegeEncumbranceLiftingProviderNotificationEmail(
        compact: string,
        specificEmails: string[],
        providerFirstName: string,
        providerLastName: string,
        liftedJurisdiction: string,
        licenseType: string,
        effectiveLiftDate: string
    ): Promise<void> {
        this.logger.info('Sending privilege encumbrance lifting provider notification email', { compact: compact });

        if (specificEmails.length === 0) {
            throw new Error('No recipients specified for provider privilege encumbrance lifting notification email');
        }

        const liftedJurisdictionConfig = await this.jurisdictionClient.getJurisdictionConfiguration(
            compact, liftedJurisdiction
        );
        const compactConfig = await this.compactConfigurationClient.getCompactConfiguration(compact);

        const report = this.getNewEmailTemplate();
        const subject = `Your ${licenseType} privilege in ${liftedJurisdictionConfig.jurisdictionName} is no longer encumbered`;
        const bodyText = `${providerFirstName} ${providerLastName},\n\n` +
            `This message is to notify you that the encumbrance on your *${licenseType}* privilege in ${liftedJurisdictionConfig.jurisdictionName} was lifted, effective ${effectiveLiftDate}. ` +
            `The encumbrance no longer restricts your ability to practice in ${liftedJurisdictionConfig.jurisdictionName} under the ${compactConfig.compactName} compact.\n\n` +
            `Please contact the licensing board in ${liftedJurisdictionConfig.jurisdictionName} if you have any questions.`;

        this.insertHeader(report, subject);
        this.insertBody(report, bodyText, 'center', true);
        this.insertFooter(report);

        const htmlContent = renderToStaticMarkup(report, { rootBlockId: 'root' });

        await this.sendEmail({ htmlContent, subject, recipients: specificEmails, errorMessage: 'Unable to send provider privilege encumbrance lifting notification email' });
    }

    /**
     * Sends a privilege encumbrance lifting notification email to state authorities
     * @param compact - The compact name
     * @param jurisdiction - The jurisdiction to notify
     * @param providerFirstName - The provider's first name
     * @param providerLastName - The provider's last name
     * @param providerId - The provider's ID
     * @param liftedJurisdiction - The jurisdiction where the privilege encumbrance was lifted
     * @param licenseType - The license type associated with the privilege
     * @param effectiveLiftDate - The date the encumbrance was lifted
     */
    public async sendPrivilegeEncumbranceLiftingStateNotificationEmail(
        compact: string,
        jurisdiction: string,
        providerFirstName: string,
        providerLastName: string,
        providerId: string,
        liftedJurisdiction: string,
        licenseType: string,
        effectiveLiftDate: string
    ): Promise<void> {
        this.logger.info('Sending privilege encumbrance lifting state notification email', {
            compact: compact,
            jurisdiction: jurisdiction
        });

        let liftedJurisdictionConfig: IJurisdiction;
        const jurisdictionConfig = await this.jurisdictionClient.getJurisdictionConfiguration(compact, jurisdiction);
        const compactConfig = await this.compactConfigurationClient.getCompactConfiguration(compact);

        if (jurisdictionConfig.postalAbbreviation != liftedJurisdiction) {
            liftedJurisdictionConfig = await this.jurisdictionClient.getJurisdictionConfiguration(
                compact, liftedJurisdiction
            );
        } else {
            liftedJurisdictionConfig = jurisdictionConfig;
        }
        const recipients = await this.getJurisdictionAdverseActionRecipients(jurisdictionConfig);

        const report = this.getNewEmailTemplate();
        const subject = `Privilege Encumbrance Lifted Notification - ${providerFirstName} ${providerLastName}`;
        const bodyText = `This message is to notify you that the encumbrance on the *${licenseType}* privilege held by ${providerFirstName} ${providerLastName} ` +
            `in ${liftedJurisdictionConfig.jurisdictionName} was lifted, effective ${effectiveLiftDate}.\n\n` +
            `Provider Details: ${environmentVariableService.getUiBasePathUrl()}/${compact}/Licensing/${providerId}\n\n` +
            `The encumbrance no longer restricts the provider's ability to practice in ${liftedJurisdictionConfig.jurisdictionName} under the ${compactConfig.compactName} compact.`;

        this.insertHeader(report, subject);
        this.insertBody(report, bodyText, 'center', true);
        this.insertFooter(report);

        const htmlContent = renderToStaticMarkup(report, { rootBlockId: 'root' });

        await this.sendEmail({ htmlContent, subject, recipients, errorMessage: 'Unable to send state privilege encumbrance lifting notification email' });
    }
}
