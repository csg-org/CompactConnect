import * as crypto from 'crypto';

import { Logger } from '@aws-lambda-powertools/logger';
import { SendEmailCommand, SESClient } from '@aws-sdk/client-ses';
import { renderToStaticMarkup, TReaderBlock, TReaderDocument } from '@usewaypoint/email-builder';
import { EnvironmentVariablesService } from './environment-variables-service';
import { IIngestFailureEventRecord, IValidationErrorEventRecord } from './models';

const environmentVariableService = new EnvironmentVariablesService();

interface IIngestEvents {
    ingestFailures: IIngestFailureEventRecord[];
    validationErrors: IValidationErrorEventRecord[];
}

interface ReportEmailerProperties {
    logger: Logger;
    sesClient: SESClient;
}


export class ReportEmailer {
    logger: Logger;
    sesClient: SESClient;
    emailTemplate: TReaderDocument = {
        'root': {
            'type': 'EmailLayout',
            'data': {
                'backdropColor': '#E9EFF9',
                'canvasColor': '#FFFFFF',
                'textColor': '#242424',
                'fontFamily': 'MODERN_SANS',
                'childrenIds': [
                    'block-logo',
                    'block-header',
                    'block-sub-heading',
                ]
            }
        },
        'block-logo': {
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
                    'url': 'https://compactconnect.org/wp-content/uploads/2024/07/Compact-Connect-logo_FINAL.png',
                    'alt': '',
                    'linkHref': null,
                    'contentAlignment': 'middle'
                }
            }
        },
        'block-header': {
            'type': 'Heading',
            'data': {
                'props': {
                    'text': 'License Data Error Summary',
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
        },
        'block-sub-heading': {
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
                    'text': 'There have been some license data errors that prevented ingest. They are listed below:'
                }
            }
        },
        'block-div': {
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
        },
    };

    allsWellEmailTemplate: TReaderDocument = {
        'root': {
            'type': 'EmailLayout',
            'data': {
                'backdropColor': '#E9EFF9',
                'canvasColor': '#FFFFFF',
                'textColor': '#242424',
                'fontFamily': 'MODERN_SANS',
                'childrenIds': [
                    'block-logo',
                    'block-header',
                    'block-sub-heading',
                ]
            }
        },
        'block-logo': {
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
                    'url': 'https://compactconnect.org/wp-content/uploads/2024/07/Compact-Connect-logo_FINAL.png',
                    'alt': '',
                    'linkHref': null,
                    'contentAlignment': 'middle'
                }
            }
        },
        'block-header': {
            'type': 'Heading',
            'data': {
                'props': {
                    'text': 'Congrats!',
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
        },
        'block-sub-heading': {
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
                    'text': 'There have been no license data errors in your jurisdiction for the last 7 days!'
                }
            }
        },
        'block-div': {
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
        },
        'block-footer': {
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
        }
    };

    public constructor(props: ReportEmailerProperties) {
        this.logger = props.logger;
        this.sesClient = props.sesClient;
    }

    public generateReport(events: IIngestEvents): string {
        const report = JSON.parse(JSON.stringify(this.emailTemplate));

        for (const ingestFailure of events.ingestFailures) {
            this.insertDiv(report);
            this.insertIngestFailure(report, ingestFailure);
        }

        for (const validationError of events.validationErrors) {
            this.insertDiv(report);
            this.insertValidationError(report, validationError);
        }

        this.insertFooter(report);

        return renderToStaticMarkup(report, { rootBlockId: 'root' });
    }

    public async sendReportEmail(events: IIngestEvents, recipients: string[]) {
        this.logger.info('Sending report email', { recipients: recipients });

        // Generate the HTML report
        const htmlContent = this.generateReport(events);

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
                        Data: 'Data Validation Report'
                    }
                },
                // We're required by the IAM policy to use this display name
                Source: `Compact Connect <${environmentVariableService.getFromAddress()}>`,
            });

            return (await this.sesClient.send(command)).MessageId;
        } catch (error) {
            this.logger.error('Error sending report email', { error: error });
            throw error;
        }
    }

    public async sendAllsWellEmail(recipients: string[]) {
        this.logger.info('Sending alls well email', { recipients: recipients });

        // Generate the HTML report
        const htmlContent = renderToStaticMarkup(this.allsWellEmailTemplate, { rootBlockId: 'root' });

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
                        Data: 'Data Validation Report'
                    }
                },
                // We're required by the IAM policy to use this display name
                Source: `Compact Connect <${environmentVariableService.getFromAddress()}>`,
            });

            return (await this.sesClient.send(command)).MessageId;
        } catch (error) {
            this.logger.error('Error sending alls well email', { error: error });
            throw error;
        }
    }

    private insertIngestFailure(report: TReaderDocument, ingestFailure: IIngestFailureEventRecord) {
        const blockAId = `block-${crypto.randomUUID()}`;
        const blockA: TReaderBlock = {
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
                        'bottom': 4,
                        'right': 24,
                        'left': 24
                    }
                }
            }
        };

        // Insert the new blocks into the report
        report[blockAId] = blockA;

        const ingestErrorMessage = ingestFailure.errors.join('\n');

        const blockB: TReaderBlock = {
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
        const blockBId: string = `block-${crypto.randomUUID()}`;

        report[blockBId] = blockB;

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
                                blockCId
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
        // The div block is already in the template, so we can just add a reference
        report['root']['data']['childrenIds'].push('block-div');
    }

    private insertFooter(report: TReaderDocument) {
        const blockId = `block-${crypto.randomUUID()}`;

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
}
