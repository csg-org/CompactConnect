import * as crypto from 'crypto';
import * as nodemailer from 'nodemailer';

import { Logger } from '@aws-lambda-powertools/logger';
import { SendEmailCommand, SendRawEmailCommand, SESClient } from '@aws-sdk/client-ses';
import { S3Client, GetObjectCommand } from '@aws-sdk/client-s3';
import { renderToStaticMarkup, TReaderDocument } from '@usewaypoint/email-builder';
import { CompactConfigurationClient } from './compact-configuration-client';
import { JurisdictionClient } from './jurisdiction-client';
import { EnvironmentVariablesService } from './environment-variables-service';
import { IIngestFailureEventRecord, IValidationErrorEventRecord } from './models';
import { RecipientType } from './models/email-notification-service-event';


const environmentVariableService = new EnvironmentVariablesService();

interface IIngestEvents {
    ingestFailures: IIngestFailureEventRecord[];
    validationErrors: IValidationErrorEventRecord[];
}

interface EmailServiceProperties {
    logger: Logger;
    sesClient: SESClient;
    s3Client: S3Client;
    compactConfigurationClient: CompactConfigurationClient;
    jurisdictionClient: JurisdictionClient;
}

const getEmailImageBaseUrl = () => {
    return `${environmentVariableService.getUiBasePathUrl()}/img/email`;
};


/*
 * Integrates with AWS SES to send emails and with EmailBuilderJS to render JS object templates into HTML
 * content that is expected to be consistently rendered across common email clients.
 */
export class EmailService {
    private readonly logger: Logger;
    private readonly sesClient: SESClient;
    private readonly s3Client: S3Client;
    private readonly compactConfigurationClient: CompactConfigurationClient;
    private readonly jurisdictionClient: JurisdictionClient;
    private readonly emailTemplate: TReaderDocument = {
        'root': {
            'type': 'EmailLayout',
            'data': {
                'backdropColor': '#E9EFF9',
                'canvasColor': '#FFFFFF',
                'textColor': '#242424',
                'fontFamily': 'MODERN_SANS',
                'childrenIds': []
            }
        }
    };

    public constructor(props: EmailServiceProperties) {
        this.logger = props.logger;
        this.sesClient = props.sesClient;
        this.s3Client = props.s3Client;
        this.compactConfigurationClient = props.compactConfigurationClient;
        this.jurisdictionClient = props.jurisdictionClient;
    }

    private async sendEmail({ htmlContent, subject, recipients, errorMessage }:
         {htmlContent: string, subject: string, recipients: string[], errorMessage: string}) {
        try {
            // Send the email
            const command = new SendEmailCommand({
                Destination: {
                    ToAddresses: recipients,
                },
                Message: {
                    Body: {
                        Html: {
                            Charset: 'UTF-8',
                            Data: htmlContent
                        }
                    },
                    Subject: {
                        Charset: 'UTF-8',
                        Data: subject
                    }
                },
                // We're required by the IAM policy to use this display name
                Source: `Compact Connect <${environmentVariableService.getFromAddress()}>`,
            });

            return (await this.sesClient.send(command)).MessageId;
        } catch (error) {
            this.logger.error(errorMessage, { error: error });
            throw error;
        }
    }

    private async sendEmailWithAttachments({
        htmlContent,
        subject,
        recipients,
        errorMessage,
        attachments
    }: {
        htmlContent: string;
        subject: string;
        recipients: string[];
        errorMessage: string;
        attachments: { filename: string; content: string | Buffer; contentType: string; }[];
    }) {
        try {
            // Create a nodemailer transport that generates raw MIME messages
            const transport = nodemailer.createTransport({
                SES: { ses: this.sesClient, aws: { SendRawEmailCommand }}
            });

            // Create the email message
            const message = {
                from: `Compact Connect <${environmentVariableService.getFromAddress()}>`,
                to: recipients,
                subject: subject,
                html: htmlContent,
                attachments: attachments.map((attachment) => ({
                    filename: attachment.filename,
                    content: attachment.content,
                    contentType: attachment.contentType
                }))
            };

            // Send the email
            const result = await transport.sendMail(message);

            return result.messageId;
        } catch (error) {
            this.logger.error(errorMessage, { error: error });
            throw error;
        }
    }

    public async sendReportEmail(events: IIngestEvents, compact: string, jurisdiction: string, recipients: string[]) {
        this.logger.info('Sending report email', { recipients: recipients });

        // Generate the HTML report
        const htmlContent = this.generateReport(events, compact, jurisdiction);

        return this.sendEmail({
            htmlContent,
            subject: `License Data Error Summary: ${compact} / ${jurisdiction}`,
            recipients,
            errorMessage: 'Error sending report email'
        });
    }

    public async sendAllsWellEmail(compact: string, jurisdiction: string, recipients: string[]) {
        this.logger.info('Sending alls well email', { recipients: recipients });

        // Generate the HTML report
        const report = JSON.parse(JSON.stringify(this.emailTemplate));

        this.insertHeaderWithJurisdiction(report, compact, jurisdiction, 'License Data Summary');
        this.insertNoErrorImage(report);
        this.insertSubHeading(report, 'There have been no license data errors this week!');
        this.insertFooter(report);

        const htmlContent = renderToStaticMarkup(report, { rootBlockId: 'root' });

        return this.sendEmail({
            htmlContent,
            subject: `License Data Summary: ${compact} / ${jurisdiction}`,
            recipients,
            errorMessage: 'Error sending alls well email'
        });
    }

    public async sendNoLicenseUpdatesEmail(compact: string, jurisdiction: string, recipients: string[]) {
        this.logger.info('Sending no license updates email', { recipients: recipients });

        // Generate the HTML report
        const report = JSON.parse(JSON.stringify(this.emailTemplate));

        this.insertHeaderWithJurisdiction(report, compact, jurisdiction, 'License Data Summary');
        this.insertClockImage(report);
        this.insertSubHeading(report, 'There have been no licenses uploaded in the last 7 days.');
        this.insertFooter(report);

        const htmlContent = renderToStaticMarkup(report, { rootBlockId: 'root' });

        return this.sendEmail({
            htmlContent,
            subject: `No License Updates for Last 7 Days: ${compact} / ${jurisdiction}`,
            recipients,
            errorMessage: 'Error sending no license updates email'
        });
    }

    public generateReport(events: IIngestEvents, compact: string, jurisdiction: string): string {
        const report = JSON.parse(JSON.stringify(this.emailTemplate));

        this.insertHeaderWithJurisdiction(
            report,
            compact,
            jurisdiction,
            'License Data Error Summary'
        );
        this.insertSubHeading(
            report,
            'There have been some license data errors that prevented ingest. '
            + 'They are listed below:'
        );
        for (const ingestFailure of events.ingestFailures) {
            this.insertDiv(report);
            this.insertIngestFailure(report, ingestFailure);
        }

        // Sort the validation errors by record number then by event time
        const validationErrors = this.sortValidationErrors(events.validationErrors);

        for (const validationError of validationErrors) {
            this.insertDiv(report);
            this.insertValidationError(report, validationError);
        }

        this.insertFooter(report);

        return renderToStaticMarkup(report, { rootBlockId: 'root' });
    }

    protected sortValidationErrors(validationErrors: IValidationErrorEventRecord[]) {
        validationErrors.sort((a, b) => {
            if ( a.recordNumber != b.recordNumber ) {
                return a.recordNumber - b.recordNumber;
            } else {
                return new Date(a.eventTime).getTime() - new Date(b.eventTime).getTime();
            }
        });
        return validationErrors;
    }

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

    private insertIngestFailure(report: TReaderDocument, ingestFailure: IIngestFailureEventRecord) {
        const blockAId = `block-${crypto.randomUUID()}`;

        report[blockAId] = {
            'type': 'Heading',
            'data': {
                'props': {
                    'text': 'Ingest error',
                    'level': 'h3'
                },
                'style': {
                    'color': '#DA2525',
                    'padding': {
                        'top': 0,
                        'bottom': 0,
                        'right': 24,
                        'left': 24
                    }
                }
            }
        };

        const blockBId: string = `block-${crypto.randomUUID()}`;

        report[blockBId] = {
            'type': 'Text',
            'data': {
                'style': {
                    'fontWeight': 'normal',
                    'padding': {
                        'top': 0,
                        'bottom': 0,
                        'right': 24,
                        'left': 24
                    }
                },
                'props': {
                    'text': ''
                }
            }
        };

        const blockCId = `block-${crypto.randomUUID()}`;

        report[blockCId] = {
            'type': 'Text',
            'data': {
                'style': {
                    'fontWeight': 'normal',
                    'padding': {
                        'top': 0,
                        'bottom': 0,
                        'right': 24,
                        'left': 24
                    }
                },
                'props': {
                    'text': ''
                }
            }
        };

        const blockDId = `block-${crypto.randomUUID()}`;
        const ingestErrorMessage = ingestFailure.errors.join('\n');

        report[blockDId] = {
            'type': 'Text',
            'data': {
                'style': {
                    'fontWeight': 'normal',
                    'padding': {
                        'top': 0,
                        'bottom': 0,
                        'right': 24,
                        'left': 24
                    }
                },
                'props': {
                    'text': ingestErrorMessage
                }
            }
        };

        const primaryBlockId = `block-${crypto.randomUUID()}`;

        report[primaryBlockId] = {
            'type': 'ColumnsContainer',
            'data': {
                'style': {
                    'padding': {
                        'top': 4,
                        'bottom': 12,
                        'right': 24,
                        'left': 24
                    }
                },
                'props': {
                    'columnsCount': 2,
                    'columnsGap': 16,
                    'columns': [
                        {
                            'childrenIds': [
                                blockAId,
                                blockBId
                            ]
                        },
                        {
                            'childrenIds': [
                                blockCId,
                                blockDId
                            ]
                        },
                        {
                            'childrenIds': []
                        }
                    ]
                }
            }
        };

        // Add the ingest error block to the root block
        report['root']['data']['childrenIds'].push(primaryBlockId);
    }

    private insertValidationError(report: TReaderDocument, validationError: IValidationErrorEventRecord) {
        const blockAId = `block-${crypto.randomUUID()}`;

        // Insert the new blocks into the report
        report[blockAId] = {
            'type': 'Heading',
            'data': {
                'props': {
                    'text': `Line ${validationError.recordNumber}`,
                    'level': 'h3'
                },
                'style': {
                    'color': '#2459A9',
                    'padding': {
                        'top': 0,
                        'bottom': 0,
                        'right': 24,
                        'left': 24
                    }
                }
            }
        };

        const blockBId = `block-${crypto.randomUUID()}`;

        const errorText: string[] = [];

        /* Format the error map structure into an error string:
         * errors: { 'licenseType': ['must be one of X, Y', 'smells bad'] }
         *
         * becomes
         *
         * licenseType:
         * must be one of X, Y
         * smells bad
         */
        for (const [ key, value ] of Object.entries(validationError.errors)) {
            this.logger.debug('Assembling text', { key: key, value: value });

            errorText.push(`${key}:\n${value.join('\n')}`);
        }

        report[blockBId] = {
            'type': 'Text',
            'data': {
                'style': {
                    'color': null,
                    'fontWeight': 'normal',
                    'padding': {
                        'top': 0,
                        'bottom': 0,
                        'right': 24,
                        'left': 24
                    }
                },
                'props': {
                    'markdown': true,
                    'text': errorText.sort().join('\n'),
                }
            }
        };

        const blockCId = `block-${crypto.randomUUID()}`;
        const validDataText: string[] = [];

        for (const [ key, value ] of Object.entries(validationError.validData)) {
            validDataText.push(`${key}: ${value}`);
        }

        report[blockCId] = {
            'type': 'Text',
            'data': {
                'style': {
                    'color': '#A3A3A3',
                    'fontSize': 14,
                    'fontWeight': 'normal',
                    'padding': {
                        'top': 0,
                        'bottom': 0,
                        'right': 24,
                        'left': 24
                    }
                },
                'props': {
                    'markdown': true,
                    'text': 'PRACTITIONER INFO'
                }
            }
        };

        const blockDId = `block-${crypto.randomUUID()}`;

        report[blockDId] = {
            'type': 'Text',
            'data': {
                'style': {
                    'color': null,
                    'fontSize': 16,
                    'fontWeight': 'normal',
                    'padding': {
                        'top': 0,
                        'bottom': 0,
                        'right': 24,
                        'left': 24
                    }
                },
                'props': {
                    'markdown': true,
                    'text': validDataText.sort().join('\n')
                }
            }
        };

        const primaryBlockId = `block-${crypto.randomUUID()}`;

        report[primaryBlockId] = {
            'type': 'ColumnsContainer',
            'data': {
                'style': {
                    'padding': {
                        'top': 4,
                        'bottom': 0,
                        'right': 24,
                        'left': 24
                    }
                },
                'props': {
                    'columnsCount': 2,
                    'columnsGap': 16,
                    'contentAlignment': 'top',
                    'columns': [
                        {
                            'childrenIds': [
                                blockAId,
                                blockBId
                            ]
                        },
                        {
                            'childrenIds': [
                                blockCId,
                                blockDId
                            ]
                        },
                        {
                            'childrenIds': []
                        }
                    ]
                }
            }
        };

        // Add the ingest error block to the root block
        report['root']['data']['childrenIds'].push(primaryBlockId);
    }

    private insertDiv(report: TReaderDocument) {
        // We use a constant block ID to reuse the same block
        const blockDivId = 'block-div';

        report[blockDivId] = {
            'type': 'Divider',
            'data': {
                'style': {
                    'padding': {
                        'top': 12,
                        'bottom': 16,
                        'right': 0,
                        'left': 0
                    }
                },
                'props': {
                    'lineColor': '#CCCCCC'
                }
            }
        };

        report['root']['data']['childrenIds'].push(blockDivId);
    }

    private insertHeaderWithJurisdiction(report: TReaderDocument,
        compact: string,
        jurisdiction: string,
        heading: string) {

        const blockLogoId = 'block-logo';
        const blockHeaderId = 'block-header';
        const blockJurisdictionId = 'block-jurisdiction';

        report[blockLogoId] = {
            'type': 'Image',
            'data': {
                'style': {
                    'padding': {
                        'top': 40,
                        'bottom': 8,
                        'right': 68,
                        'left': 68
                    },
                    'backgroundColor': null,
                    'textAlign': 'center'
                },
                'props': {
                    'width': null,
                    'height': 100,
                    'url': `${getEmailImageBaseUrl()}/compact-connect-logo-final.png`,
                    'alt': '',
                    'linkHref': null,
                    'contentAlignment': 'middle'
                }
            }
        };
        report[blockHeaderId] = {
            'type': 'Heading',
            'data': {
                'props': {
                    'text': heading,
                    'level': 'h1'
                },
                'style': {
                    'textAlign': 'center',
                    'padding': {
                        'top': 28,
                        'bottom': 12,
                        'right': 24,
                        'left': 24
                    }
                }
            }
        };
        report[blockJurisdictionId] = {
            'type': 'Text',
            'data': {
                'style': {
                    'color': '#2459A9',
                    'fontSize': 18,
                    'fontWeight': 'bold',
                    'textAlign': 'center',
                    'padding': {
                        'top': 0,
                        'bottom': 0,
                        'right': 24,
                        'left': 24
                    }
                },
                'props': {
                    'markdown': true,
                    'text': `${compact}  /  ${jurisdiction}`
                }
            }
        };

        report['root']['data']['childrenIds'].push(blockLogoId);
        report['root']['data']['childrenIds'].push(blockHeaderId);
        report['root']['data']['childrenIds'].push(blockJurisdictionId);
    }

    private insertSubHeading(report: TReaderDocument, subHeading: string) {
        const blockId = `block-${crypto.randomUUID()}`;

        report[blockId] = {
            'type': 'Text',
            'data': {
                'style': {
                    'fontSize': 18,
                    'fontWeight': 'normal',
                    'textAlign': 'center',
                    'padding': {
                        'top': 0,
                        'bottom': 52,
                        'right': 40,
                        'left': 40
                    }
                },
                'props': {
                    'text': subHeading
                }
            }
        };

        report['root']['data']['childrenIds'].push(blockId);
    }

    private insertClockImage(report: TReaderDocument) {
        const blockId = `block-clock-image`;

        report[blockId] = {
            'type': 'Image',
            'data': {
                'style': {
                    'padding': {
                        'top': 68,
                        'bottom': 16,
                        'right': 24,
                        'left': 24
                    },
                    'textAlign': 'center'
                },
                'props': {
                    'width': 100,
                    'height': 100,
                    'url': `${getEmailImageBaseUrl()}/ico-noupdates@2x.png`,
                    'alt': 'Clock icon',
                    'linkHref': null,
                    'contentAlignment': 'middle'
                }
            }
        };

        report['root']['data']['childrenIds'].push(blockId);
    }

    private insertNoErrorImage(report: TReaderDocument) {
        const blockId = `block-no-error-image`;

        report[blockId] = {
            'type': 'Image',
            'data': {
                'style': {
                    'padding': {
                        'top': 68,
                        'bottom': 16,
                        'right': 24,
                        'left': 24
                    },
                    'textAlign': 'center'
                },
                'props': {
                    'width': 100,
                    'height': 100,
                    'url': `${getEmailImageBaseUrl()}/ico-noerrors@2x.png`,
                    'alt': 'Success icon',
                    'linkHref': null,
                    'contentAlignment': 'middle'
                }
            }
        };

        report['root']['data']['childrenIds'].push(blockId);
    }

    private insertFooter(report: TReaderDocument) {
        const blockId = `block-footer`;

        report[blockId] = {
            'type': 'Text',
            'data': {
                'style': {
                    'color': '#ffffff',
                    'backgroundColor': '#2459A9',
                    'fontSize': 13,
                    'fontFamily': 'MODERN_SANS',
                    'fontWeight': 'normal',
                    'textAlign': 'center',
                    'padding': {
                        'top': 40,
                        'bottom': 40,
                        'right': 68,
                        'left': 68
                    }
                },
                'props': {
                    'text': '© 2025 CompactConnect'
                }
            }
        };

        report['root']['data']['childrenIds'].push(blockId);
    }

    /**
     * Adds a standard header block with Compact Connect logo to the report.
     *
     * @param report The report object to insert the block into.
     * @param heading The text to insert into the block.
     */
    private insertHeader(report: TReaderDocument, heading: string) {
        const blockLogoId = 'block-logo';
        const blockHeaderId = 'block-header';

        report[blockLogoId] = {
            'type': 'Image',
            'data': {
                'style': {
                    'padding': {
                        'top': 40,
                        'bottom': 8,
                        'right': 68,
                        'left': 68
                    },
                    'backgroundColor': null,
                    'textAlign': 'center'
                },
                'props': {
                    'width': null,
                    'height': 100,
                    'url': `${getEmailImageBaseUrl()}/compact-connect-logo-final.png`,
                    'alt': '',
                    'linkHref': null,
                    'contentAlignment': 'middle'
                }
            }
        };

        report[blockHeaderId] = {
            'type': 'Heading',
            'data': {
                'props': {
                    'text': heading,
                    'level': 'h1'
                },
                'style': {
                    'textAlign': 'center',
                    'color': '#242424',
                    'padding': {
                        'top': 28,
                        'bottom': 12,
                        'right': 24,
                        'left': 24
                    }
                }
            }
        };

        report['root']['data']['childrenIds'].push(blockLogoId);
        report['root']['data']['childrenIds'].push(blockHeaderId);
    }

    /**
     * Inserts a body text block into the report.
     *
     * @param report The report object to insert the block into.
     * @param bodyText The text to insert into the block.
     */
    private insertBody(report: TReaderDocument, bodyText: string) {
        const blockId = `block-body`;

        report[blockId] = {
            'type': 'Text',
            'data': {
                'style': {
                    'fontSize': 16,
                    'fontWeight': 'normal',
                    'color': '#A3A3A3',
                    'padding': {
                        'top': 24,
                        'bottom': 24,
                        'right': 40,
                        'left': 40
                    }
                },
                'props': {
                    'text': bodyText
                }
            }
        };

        report['root']['data']['childrenIds'].push(blockId);
    }

    /**
     * Inserts a body text block into the email that can be formatted using markdown.
     *
     * @param report The report object to insert the block into.
     * @param bodyText The text to insert into the block.
     */
    private insertMarkdownBody(report: TReaderDocument, bodyText: string) {
        const blockId = `block-markdown-body`;

        report[blockId] = {
            'type': 'Text',
            'data': {
                'style': {
                    'fontSize': 16,
                    'fontWeight': 'normal',
                    'textAlign': 'left',
                    'color': '#A3A3A3',
                    'padding': {
                        'top': 24,
                        'bottom': 24,
                        'right': 40,
                        'left': 40
                    }
                },
                'props': {
                    'markdown': true,
                    'text': bodyText
                }
            }
        };

        report['root']['data']['childrenIds'].push(blockId);
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
                    filename: `${compact}-settled-transaction-report.zip`,
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
                    filename: `${jurisdiction}-settled-transaction-report.zip`,
                    content: reportZipBuffer,
                    contentType: 'application/zip'
                }
            ]
        });
    }
}
