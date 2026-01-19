import * as crypto from 'crypto';
import * as nodemailer from 'nodemailer';
import type SESTransport from 'nodemailer/lib/ses-transport';

import { Logger } from '@aws-lambda-powertools/logger';
import { SendEmailCommand, SESv2Client } from '@aws-sdk/client-sesv2';
import { TReaderDocument, renderToStaticMarkup } from '@csg-org/email-builder';
import { CompactConfigurationClient } from '../compact-configuration-client';
import { JurisdictionClient } from '../jurisdiction-client';
import { EnvironmentVariablesService } from '../environment-variables-service';
import { EnvironmentBannerService } from './environment-banner-service';

const environmentVariableService = new EnvironmentVariablesService();

interface EmailServiceProperties {
    logger: Logger;
    sesClient: SESv2Client;
    compactConfigurationClient: CompactConfigurationClient;
    jurisdictionClient: JurisdictionClient;
}

interface StyledBlockOptions {
    title: string;
    content: string;
    blockType: 'warning';
}

/**
 * Base class for email services that provides common email functionality
 */
export abstract class BaseEmailService {
    protected readonly logger: Logger;
    protected readonly sesClient: SESv2Client;
    protected readonly compactConfigurationClient: CompactConfigurationClient;
    protected readonly jurisdictionClient: JurisdictionClient;
    private readonly environmentBannerService = new EnvironmentBannerService();
    protected readonly shouldShowEnvironmentBannerIfNonProdEnvironment: boolean = true;
    private readonly emailTemplate: TReaderDocument = {
        'root': {
            'type': 'EmailLayout',
            'data': {
                'backdropColor': '#E9EFF9',
                'canvasColor': '#FFFFFF',
                'textColor': '#09122B',
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
                Content: {
                    Simple: {
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
                    }
                },
                // We're required by the IAM policy to use this display name
                FromEmailAddress: `Compact Connect <${environmentVariableService.getFromAddress()}>`,
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
            const sesTransportOptions: SESTransport.Options = {
                SES: { sesClient: this.sesClient, SendEmailCommand },
            };
            const transport = nodemailer.createTransport(sesTransportOptions);

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
        compactName: string,
        jurisdiction: string,
        heading: string) {

        // Insert environment banner first (above logo)
        if (this.shouldShowEnvironmentBannerIfNonProdEnvironment) {
            this.environmentBannerService.insertEnvironmentBannerIfNonProd(report);
        }

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
                    'text': `${compactName}  /  ${jurisdiction}`
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
        // Insert environment banner first (above logo)
        if (this.shouldShowEnvironmentBannerIfNonProdEnvironment) {
            this.environmentBannerService.insertEnvironmentBannerIfNonProd(report);
        }

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
        markdown: boolean = false,
        styleOverrides: Record<string, unknown> = {}
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
                    },
                    ...styleOverrides
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
                    'text': `© ${new Date().getFullYear()} CompactConnect`
                }
            }
        };

        report['root']['data']['childrenIds'].push(blockId);

        // Insert test email warning footer last (below copyright)
        if (this.shouldShowEnvironmentBannerIfNonProdEnvironment) {
            this.environmentBannerService.insertTestEmailFooterIfNonProd(report);
        }
    }

    /**
     * Inserts a styled block with title and content
     * Currently supports 'warning' style with orange/yellow color scheme
     */
    protected insertStyledBlock(report: TReaderDocument, options: StyledBlockOptions) {
        const outerContainerId = `block-${crypto.randomUUID()}`;
        const innerContainerId = `block-${crypto.randomUUID()}`;
        const titleBlockId = `block-${crypto.randomUUID()}`;
        const contentBlockId = `block-${crypto.randomUUID()}`;

        // Define styling based on block type
        const getBlockStyles = (blockType: 'warning') => {
            switch (blockType) {
            case 'warning':
                return {
                    backgroundColor: '#FFF9EE',
                    borderColor: '#FDBD4B',
                    textColor: '#9F2D00',
                    titleFontSize: 20,
                    contentFontSize: 16
                };
            default:
                throw new Error(`Unsupported block type: ${blockType}`);
            }
        };

        const styles = getBlockStyles(options.blockType);

        // Create the title text block
        report[titleBlockId] = {
            'type': 'Text',
            'data': {
                'style': {
                    'color': styles.textColor,
                    'fontSize': styles.titleFontSize,
                    'fontWeight': 'bold',
                    'textAlign': 'left',
                    'padding': {
                        'top': 0,
                        'bottom': 0,
                        'right': 0,
                        'left': 0
                    }
                },
                'props': {
                    'text': options.title
                }
            }
        };

        // Create the content text block
        report[contentBlockId] = {
            'type': 'Text',
            'data': {
                'style': {
                    'color': styles.textColor,
                    'fontSize': styles.contentFontSize,
                    'fontWeight': 'normal',
                    'padding': {
                        'top': 0,
                        'bottom': 0,
                        'right': 0,
                        'left': 0
                    }
                },
                'props': {
                    'markdown': true,
                    'text': options.content
                }
            }
        };

        // Create the inner container (styled)
        report[innerContainerId] = {
            'type': 'Container',
            'data': {
                'style': {
                    'backgroundColor': styles.backgroundColor,
                    'borderColor': styles.borderColor,
                    'borderRadius': 12,
                    'padding': {
                        'top': 16,
                        'bottom': 16,
                        'right': 24,
                        'left': 24
                    }
                },
                'props': {
                    'childrenIds': [
                        titleBlockId,
                        contentBlockId
                    ]
                }
            }
        };

        // Create the outer container (white background)
        report[outerContainerId] = {
            'type': 'Container',
            'data': {
                'style': {
                    'backgroundColor': '#FFFFFF',
                    'borderColor': '#FFFFFF',
                    'borderRadius': 12,
                    'padding': {
                        'top': 16,
                        'bottom': 16,
                        'right': 24,
                        'left': 24
                    }
                },
                'props': {
                    'childrenIds': [
                        innerContainerId
                    ]
                }
            }
        };

        // Add the outer container to the root
        report['root']['data']['childrenIds'].push(outerContainerId);
    }

    /**
     * Renders a template to HTML
     * This method should be used by all subclasses instead of calling renderToStaticMarkup directly
     * @param template - The TReaderDocument template to render
     * @returns The rendered HTML string
     */
    protected renderTemplate(template: TReaderDocument): string {
        return renderToStaticMarkup(template, { rootBlockId: 'root' });
    }
}
