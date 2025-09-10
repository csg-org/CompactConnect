import * as crypto from 'crypto';
import { renderToStaticMarkup, TReaderDocument } from '@usewaypoint/email-builder';
import { IIngestFailureEventRecord, IValidationErrorEventRecord } from '../models';
import { BaseEmailService } from './base-email-service';

interface IIngestEvents {
    ingestFailures: IIngestFailureEventRecord[];
    validationErrors: IValidationErrorEventRecord[];
}

/**
 * Email service for handling ingest event reporting
 */
export class IngestEventEmailService extends BaseEmailService {
    public async sendReportEmail(events: IIngestEvents,
        compactName: string,
        jurisdiction: string,
        recipients: string[]
    ) {
        this.logger.info('Sending report email', { recipients: recipients });

        // Generate the HTML report
        const htmlContent = this.generateReport(events, compactName, jurisdiction);

        return this.sendEmail({
            htmlContent,
            subject: `License Data Error Summary: ${compactName} / ${jurisdiction}`,
            recipients,
            errorMessage: 'Error sending report email'
        });
    }

    public async sendAllsWellEmail(compactName: string, jurisdiction: string, recipients: string[]) {
        this.logger.info('Sending alls well email', { recipients: recipients });

        // Generate the HTML report
        const report = this.getNewEmailTemplate();

        this.insertHeaderWithJurisdiction(report, compactName, jurisdiction, 'License Data Summary');
        this.insertNoErrorImage(report);
        this.insertSubHeading(report, 'There have been no license data errors this week!');
        this.insertFooter(report);

        const htmlContent = renderToStaticMarkup(report, { rootBlockId: 'root' });

        return this.sendEmail({
            htmlContent,
            subject: `License Data Summary: ${compactName} / ${jurisdiction}`,
            recipients,
            errorMessage: 'Error sending alls well email'
        });
    }

    public async sendNoLicenseUpdatesEmail(compactName: string, jurisdiction: string, recipients: string[]) {
        this.logger.info('Sending no license updates email', { recipients: recipients });

        // Generate the HTML report
        const report = this.getNewEmailTemplate();

        this.insertHeaderWithJurisdiction(report, compactName, jurisdiction, 'License Data Summary');
        this.insertClockImage(report);
        this.insertSubHeading(report, 'There have been no licenses uploaded in the last 7 days.');
        this.insertFooter(report);

        const htmlContent = renderToStaticMarkup(report, { rootBlockId: 'root' });

        return this.sendEmail({
            htmlContent,
            subject: `No License Updates for Last 7 Days: ${compactName} / ${jurisdiction}`,
            recipients,
            errorMessage: 'Error sending no license updates email'
        });
    }

    public generateReport(events: IIngestEvents, compactName: string, jurisdiction: string): string {
        const report = this.getNewEmailTemplate();

        this.insertHeaderWithJurisdiction(
            report,
            compactName,
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
            if (a.recordNumber != b.recordNumber) {
                return a.recordNumber - b.recordNumber;
            } else {
                return new Date(a.eventTime).getTime() - new Date(b.eventTime).getTime();
            }
        });
        return validationErrors;
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
        for (const [key, value] of Object.entries(validationError.errors)) {
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

        for (const [key, value] of Object.entries(validationError.validData)) {
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
                    'url': `${IngestEventEmailService.getEmailImageBaseUrl()}/ico-noupdates@2x.png`,
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
                    'url': `${IngestEventEmailService.getEmailImageBaseUrl()}/ico-noerrors@2x.png`,
                    'alt': 'Success icon',
                    'linkHref': null,
                    'contentAlignment': 'middle'
                }
            }
        };

        report['root']['data']['childrenIds'].push(blockId);
    }
}
