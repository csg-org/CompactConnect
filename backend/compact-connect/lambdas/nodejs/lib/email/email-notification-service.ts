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
        specificEmails?: string[]
    ): Promise<void> {
        this.logger.info('Sending transaction batch settlement failure email', { compact: compact });
        const recipients = await this.getCompactRecipients(compact, recipientType, specificEmails);

        if (recipients.length === 0) {
            throw new Error(`No recipients found for compact ${compact} with recipient type ${recipientType}`);
        }

        const report = this.getNewEmailTemplate();
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

        const report = this.getNewEmailTemplate();
        const subject = `A Privilege was Deactivated in the ${compact.toUpperCase()} Compact`;
        const bodyText = `This message is to notify you that privilege ${privilegeId} held by ${providerFirstName} ${providerLastName} was deactivated and can no longer be used to practice.`;

        this.insertHeader(report, subject);
        this.insertBody(report, bodyText);
        this.insertFooter(report);

        const htmlContent = renderToStaticMarkup(report, { rootBlockId: 'root' });

        await this.sendEmail({ htmlContent, subject, recipients, errorMessage: 'Unable to send privilege deactivation state notification email' });
    }

    /**
     * Sends an email notification to a provider when one of their privileges is deactivated
     * @param compact - The compact name for which the privilege was deactivated
     * @param jurisdiction - The jurisdiction for which the privilege was deactivated
     * @param privilegeId - The privilege ID
     */
    public async sendPrivilegeDeactivationProviderNotificationEmail(
        compact: string,
        specificEmails: string[] | undefined,
        privilegeId: string
    ): Promise<void> {
        this.logger.info('Sending provider privilege deactivation notification email', { compact: compact });

        const recipients = specificEmails || [];

        if (recipients.length === 0) {
            throw new Error(`No recipients specified for provider privilege deactivation notification email`);
        }

        const report = this.getNewEmailTemplate();
        const subject = `Your Privilege ${privilegeId} is Deactivated`;
        const bodyText = `This message is to notify you that your privilege ${privilegeId} is deactivated and can no longer be used to practice.`;

        this.insertHeader(report, subject);
        this.insertBody(report, bodyText);
        this.insertFooter(report);

        const htmlContent = renderToStaticMarkup(report, { rootBlockId: 'root' });

        await this.sendEmail({ htmlContent, subject, recipients, errorMessage: 'Unable to send provider privilege deactivation notification email' });
    }

    public async sendCompactTransactionReportEmail(
        compact: string,
        reportS3Path: string,
        reportingCycle: string,
        startDate: string,
        endDate: string
    ): Promise<void> {
        this.logger.info('Sending compact transaction report email', { compact: compact });
        const recipients = await this.getCompactRecipients(compact, 'COMPACT_SUMMARY_REPORT');

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

        const report = this.getNewEmailTemplate();
        const subject = `${reportingCycle === 'weekly' ? 'Weekly' : 'Monthly'} Report for Compact ${compact.toUpperCase()}`;
        const bodyText = `Please find attached the ${reportingCycle} settled transaction reports for the compact for the period ${startDate} to ${endDate}:\n\n` +
            '- Financial Summary Report - A summary of all settled transactions and fees\n' +
            '- Transaction Detail Report - A detailed list of all settled transactions';

        this.insertHeader(report, subject);
        this.insertBody(report, bodyText, 'left', true);
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

        const report = this.getNewEmailTemplate();
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

    /**
     * Sends an email notification to a provider when they purchase privilege(s)
     * @param specificEmails - The email adresses(s) to send the email to, in this case always the provider's email
     * @param transactionDate - The date the transaction occured
     * @param privileges - The relevant privilege data necessary to generate teh email
     * @param totalCost - The total cost of the transaction
     * @param costLineItems - The line items involved in the purchase transaction
     */
    public async sendPrivilegePurchaseProviderNotificationEmail(
        transactionDate: string,
        privileges: {
            jurisdiction: string,
            licenseTypeAbbrev: string,
            privilegeId: string
        }[], 
        totalCost: string,
        costLineItems: {
                name: string,
                quantity: string,
                unitPrice: string
        }[],
        specificEmails: string[] = []
    ): Promise<void> {
        this.logger.info('Sending provider privilege purchase notification email', { providerEmail: specificEmails[0] });

        const recipients = specificEmails;

        if (recipients.length === 0) {
            throw new Error(`No recipients found`);
        }

        const emailContent = this.getNewEmailTemplate();
        const headerText = `Privilege Purchase Confirmation`;
        const subject = `Compact Connect Privilege Purchase Confirmation`;
        const bodyText = `This email is to confirm you successfully purchased the following privileges on ${transactionDate}`;

        this.insertHeader(emailContent, headerText);
        this.insertBody(emailContent, bodyText, 'center');

        privileges.forEach((privilege) => {
            const titleText = `${privilege.licenseTypeAbbrev.toUpperCase()} - ${privilege.jurisdiction.toUpperCase()}`;
            const privilegeIdText = `Privilege Id: ${privilege.privilegeId}`;
    
            this.insertTuple(emailContent, titleText, privilegeIdText);
        });

        const rows = costLineItems.map((lineItem) => {
            const quantityNum = parseInt(lineItem.quantity, 10);
            const unitPriceNum = Number(lineItem.unitPrice);


            const quantityText = quantityNum > 1 ? `x ${quantityNum}` : '';
            const left = `${lineItem.name} ${quantityText}`;
            const right = `$${(unitPriceNum * quantityNum).toFixed(2)}`;

            return { left, right };
        });

        const totalCostDisplay = `$${Number(totalCost).toFixed(2)}`;

        this.insertTwoColumnTable(emailContent, 'Cost breakdown', rows);

        this.insertTwoColumnRow(emailContent, 'Total', totalCostDisplay, true, 24);

        this.insertFooter(emailContent);

        const htmlContent = renderToStaticMarkup(emailContent, { rootBlockId: 'root' });

        await this.sendEmail({ htmlContent, subject, recipients, errorMessage: 'Unable to send provider privilege purchase notification email' });
    }

    /**
     * Sends an email notification to a provider when someone attempts to register with their email address
     * @param compact - The compact name
     * @param specificEmails - The email address to send the notification to
     */
    public async sendMultipleRegistrationAttemptNotificationEmail(
        compact: string,
        specificEmails: string[] = []
    ): Promise<void> {
        this.logger.info('Sending multiple registration attempt notification email', { compact: compact, recipients: specificEmails });

        const recipients = specificEmails;

        if (recipients.length === 0) {
            throw new Error(`No recipients found for multiple registration attempt notification email`);
        }

        const report = this.getNewEmailTemplate();
        const subject = `Registration Attempt Notification - Compact Connect`;
        const loginUrl = `${environmentVariableService.getUiBasePathUrl()}/Dashboard`;
        const bodyText = `A registration attempt was made in the Compact Connect system for an account associated with this email address. This email address is already registered in our system.\n\nIf you originally registered within the past 24 hours, make sure to login with your temporary password sent to this same email address. You may log in to your existing account using the link below:\n\n${loginUrl}\n\nFor your security, we recommend that you log in to your account to verify your account information and ensure your account remains secure.`;

        this.insertHeader(report, 'Registration Attempt');
        this.insertBody(report, bodyText, 'center', true);
        this.insertFooter(report);

        const htmlContent = renderToStaticMarkup(report, { rootBlockId: 'root' });

        await this.sendEmail({ htmlContent, subject, recipients, errorMessage: 'Unable to send multiple registration attempt notification email' });
    }
}
