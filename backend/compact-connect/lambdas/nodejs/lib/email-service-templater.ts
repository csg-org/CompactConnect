import { Logger } from '@aws-lambda-powertools/logger';
import { SendEmailCommand, SESClient } from '@aws-sdk/client-ses';
import { renderToStaticMarkup, TReaderDocument } from '@usewaypoint/email-builder';
import { CompactConfigurationClient } from './compact-configuration-client';
import { EnvironmentVariablesService } from './environment-variables-service';
import { RecipientType } from './models/email-notification-service-event';

const environmentVariableService = new EnvironmentVariablesService();

interface EmailServiceTemplaterProperties {
    logger: Logger;
    sesClient: SESClient;
    compactConfigurationClient: CompactConfigurationClient;
}

const getEmailImageBaseUrl = () => {
    return `${environmentVariableService.getUiBasePathUrl()}/img/email`;
};

export class EmailServiceTemplater {
    private readonly logger: Logger;
    private readonly sesClient: SESClient;
    private readonly compactConfigurationClient: CompactConfigurationClient;
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

    constructor(props: EmailServiceTemplaterProperties) {
        this.logger = props.logger;
        this.sesClient = props.sesClient;
        this.compactConfigurationClient = props.compactConfigurationClient;
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

    private insertBody(report: TReaderDocument, bodyText: string) {
        const blockId = `block-body`;

        report[blockId] = {
            'type': 'Text',
            'data': {
                'style': {
                    'fontSize': 16,
                    'fontWeight': 'normal',
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
                    'text': '© 2024 CompactConnect'
                }
            }
        };

        report['root']['data']['childrenIds'].push(blockId);
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
        case 'COMPACT_ADVERSE_ACTIONS':
            return compactConfig.compactAdverseActionsNotificationEmails;
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
}
