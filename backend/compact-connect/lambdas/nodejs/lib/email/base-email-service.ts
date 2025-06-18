import * as crypto from 'crypto';
import * as nodemailer from 'nodemailer';

import { Logger } from '@aws-lambda-powertools/logger';
import { SendEmailCommand, SendRawEmailCommand, SESClient } from '@aws-sdk/client-ses';
import { S3Client } from '@aws-sdk/client-s3';
import { TReaderDocument } from '@usewaypoint/email-builder';
import { CompactConfigurationClient } from '../compact-configuration-client';
import { JurisdictionClient } from '../jurisdiction-client';
import { EnvironmentVariablesService } from '../environment-variables-service';

const environmentVariableService = new EnvironmentVariablesService();

interface EmailServiceProperties {
    logger: Logger;
    sesClient: SESClient;
    s3Client: S3Client;
    compactConfigurationClient: CompactConfigurationClient;
    jurisdictionClient: JurisdictionClient;
}

/**
 * Base class for email services that provides common email functionality
 */
export abstract class BaseEmailService {
    protected readonly logger: Logger;
    protected readonly sesClient: SESClient;
    protected readonly s3Client: S3Client;
    protected readonly compactConfigurationClient: CompactConfigurationClient;
    protected readonly jurisdictionClient: JurisdictionClient;
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

    protected getNewEmailTemplate() {
        // Make a deep copy of the template so we can modify it without affecting the original
        return JSON.parse(JSON.stringify(this.emailTemplate));
    }

    public constructor(props: EmailServiceProperties) {
        this.logger = props.logger;
        this.sesClient = props.sesClient;
        this.s3Client = props.s3Client;
        this.compactConfigurationClient = props.compactConfigurationClient;
        this.jurisdictionClient = props.jurisdictionClient;
    }

    protected static getEmailImageBaseUrl() {
        return `${environmentVariableService.getUiBasePathUrl()}/img/email`;
    }

    protected async sendEmail({ htmlContent, subject, recipients, errorMessage }:
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

    protected async sendEmailWithAttachments({
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

    protected insertDiv(report: TReaderDocument) {
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

    protected insertHeaderWithJurisdiction(report: TReaderDocument,
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
                    'url': `${BaseEmailService.getEmailImageBaseUrl()}/compact-connect-logo-final.png`,
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
                    'color': '#09122B',
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

    protected insertSubHeading(report: TReaderDocument, subHeading: string) {
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

    protected insertHeader(report: TReaderDocument, heading: string) {
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
                    'url': `${BaseEmailService.getEmailImageBaseUrl()}/compact-connect-logo-final.png`,
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
                    'color': '#09122B',
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

    protected insertBody(
        report: TReaderDocument,
        bodyText: string,
        textAlign: 'center' | 'right' | 'left' | null = null,
        markdown: boolean = false
    ) {
        const blockId = `block-${crypto.randomUUID()}`;

        report[blockId] = {
            'type': 'Text',
            'data': {
                'style': {
                    'fontSize': 16,
                    'fontWeight': 'normal',
                    'color': '#09122B',
                    'padding': {
                        'top': 24,
                        'bottom': 24,
                        'right': 40,
                        'left': 40
                    }
                },
                'props': {
                    'text': bodyText,
                    'markdown': markdown
                }
            }
        };

        if (textAlign && report[blockId]['data']['style']) {
            report[blockId]['data']['style']['textAlign'] = textAlign;
        }

        report['root']['data']['childrenIds'].push(blockId);
    }

    protected insertTuple(report: TReaderDocument, keyText: string, valueText: string) {
        const containerBlockId = `block-${crypto.randomUUID()}`;
        const keyBlockId = `block-${crypto.randomUUID()}`;
        const valueBlockId = `block-${crypto.randomUUID()}`;


        report[keyBlockId] = {
            'type': 'Text',
            'data': {
                'style': {
                    'fontWeight': 'bold',
                    'padding': {
                        'top': 16,
                        'bottom': 0,
                        'right': 12,
                        'left': 24
                    }
                },
                'props': {
                    'text': keyText
                }
            }
        };

        report[valueBlockId] = {
            'type': 'Text',
            'data': {
                'style': {
                    'color': '#525252',
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
                    'text': valueText
                }
            }
        };

        report[containerBlockId] = {
            'type': 'Container',
            'data': {
                'style': {
                    'padding': {
                        'top': 0,
                        'bottom': 0,
                        'right': 72,
                        'left': 76
                    }
                },
                'props': {
                    'childrenIds': [
                        keyBlockId,
                        valueBlockId
                    ]
                }
            }
        };

        report['root']['data']['childrenIds'].push(containerBlockId);
    }

    protected insertTwoColumnTable(report: TReaderDocument, title: string, rows: { left: string, right: string }[]) {
        const titleBlockId = `block-${crypto.randomUUID()}`;


        report[titleBlockId] = {
            'type': 'Text',
            'data': {
                'style': {
                    'fontWeight': 'bold',
                    'padding': {
                        'top': 24,
                        'bottom': 16,
                        'right': 24,
                        'left': 68
                    }
                },
                'props': {
                    'text': title
                }
            }
        };

        report['root']['data']['childrenIds'].push(titleBlockId);

        rows.forEach((row) => {
            this.insertTwoColumnRow(report, row.left, row.right, false, 6);
        });
    }

    protected insertTwoColumnRow(
        report: TReaderDocument,
        leftContent: string,
        rightContent: string,
        isBold: boolean,
        bottomPadding: number
    ) {
        const containerId = `block-${crypto.randomUUID()}`;
        const leftCellId = `block-${crypto.randomUUID()}`;
        const rightCellId = `block-${crypto.randomUUID()}`;

        report[leftCellId] = {
            'type': 'Text',
            'data': {
                'style': {
                    'fontWeight': 'normal',
                    'textAlign': 'left',
                    'padding': {
                        'top': 0,
                        'bottom': 0,
                        'right': 24,
                        'left': 24
                    }
                },
                'props': {
                    'text': leftContent
                }
            }
        };

        report[rightCellId] = {
            'type': 'Text',
            'data': {
                'style': {
                    'fontWeight': 'normal',
                    'textAlign': 'right',
                    'padding': {
                        'top': 0,
                        'bottom': 0,
                        'right': 24,
                        'left': 24
                    }
                },
                'props': {
                    'text': rightContent
                }
            }
        };

        report[containerId] = {
            'type': 'ColumnsContainer',
            'data': {
                'style': {
                    'padding': {
                        'top': 0,
                        'bottom': bottomPadding || 6,
                        'right': 44,
                        'left': 44
                    }
                },
                'props': {
                    'fixedWidths': [
                        null,
                        null,
                        null
                    ],
                    'columnsCount': 2,
                    'columnsGap': 10,
                    'columns': [
                        {
                            'childrenIds': [
                                leftCellId
                            ]
                        },
                        {
                            'childrenIds': [
                                rightCellId
                            ]
                        },
                        {
                            'childrenIds': []
                        }
                    ]
                }
            }
        };

        if (
            isBold
            && report[leftCellId]['data']['style']
            && report[rightCellId]['data']['style']
        ) {
            report[leftCellId]['data']['style']['fontWeight'] = 'bold';
            report[rightCellId]['data']['style']['fontWeight'] = 'bold';
        }

        report['root']['data']['childrenIds'].push(containerId);
    }

    protected insertFooter(report: TReaderDocument) {
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
}
