import { GetObjectCommand, S3Client } from '@aws-sdk/client-s3';
import { BaseEmailService } from './base-email-service';
import { EnvironmentVariablesService } from '../environment-variables-service';
import { RecipientType } from '../models/email-notification-service-event';
import { invoiceBody, invoiceSubject } from './invoice-email-service';
import { InvoiceReport } from '../models/invoice';

const environmentVariableService = new EnvironmentVariablesService();

/**
 * Email service for handling email notifications
 */
export class EmailNotificationService extends BaseEmailService {
    public readonly s3Client: S3Client;

    public constructor(props: ConstructorParameters<typeof BaseEmailService>[0] & { s3Client?: S3Client }) {
        super(props);
        this.s3Client = props.s3Client ?? new S3Client({});
    }

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

        if (!recipients || recipients.length === 0) {
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
     * Attach the invoice zip that the Python reporter stored. This service does not build the CSVs.
     */
    public async sendCompactInvoiceEmail(
        compact: string,
        reportS3Path: string,
        licenseType: string,
        billingMonth: string,
        totalBillable: number,
        totalOwed: number,
        recipientType: RecipientType,
        specificEmails?: string[]
    ): Promise<void> {
        this.logger.info('Sending compact invoice email', {
            compact,
            licenseType,
            billingMonth,
            reportS3Path,
        });

        const recipients = await this.invoiceRecipients(compact, recipientType, specificEmails);
        const reportZipResponse = await this.s3Client.send(new GetObjectCommand({
            Bucket: environmentVariableService.getInvoiceReportsBucketName(),
            Key: reportS3Path,
        }));

        if (!reportZipResponse.Body) {
            throw new Error(`Failed to retrieve invoice report from S3: ${reportS3Path}`);
        }

        const reportZipBuffer = Buffer.from(await reportZipResponse.Body.transformToByteArray());
        const compactConfig = await this.compactConfigurationClient.getCompactConfiguration(compact);
        const report: InvoiceReport = {
            compactName: compactConfig.compactName,
            licenseType,
            billingMonth,
            stateSections: [],
            totalUploaded: 0,
            totalBillable,
            totalOwed,
        };
        const subject = invoiceSubject(report);
        const template = this.getNewEmailTemplate();

        this.insertHeader(template, subject);
        this.insertBody(template, invoiceBody(report), 'left');
        this.insertFooter(template);

        await this.sendEmailWithAttachments({
            htmlContent: this.renderTemplate(template),
            subject,
            recipients,
            errorMessage: 'Unable to send compact invoice email',
            attachments: [
                {
                    filename: `${licenseType}-${billingMonth}-invoice.zip`,
                    content: reportZipBuffer,
                    contentType: 'application/zip',
                },
            ],
        });
    }

    private async invoiceRecipients(
        compact: string,
        recipientType: RecipientType,
        specificEmails?: string[]
    ): Promise<string[]> {
        if (recipientType === 'SPECIFIC') {
            if (specificEmails && specificEmails.length > 0) {
                return specificEmails;
            }
            throw new Error('SPECIFIC recipientType requested but no specific email addresses provided');
        }
        if (recipientType !== 'COMPACT_OPERATIONS_TEAM') {
            throw new Error(`Unsupported recipient type for compact invoice: ${recipientType}`);
        }

        const compactConfig = await this.compactConfigurationClient.getCompactConfiguration(compact);

        if (!compactConfig.compactOperationsTeamEmails.length) {
            throw new Error(`No operations recipients found for compact ${compact}`);
        }

        return compactConfig.compactOperationsTeamEmails;
    }
}
