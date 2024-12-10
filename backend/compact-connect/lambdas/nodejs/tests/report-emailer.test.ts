import { mockClient } from 'aws-sdk-client-mock';
import 'aws-sdk-client-mock-jest';
import { Logger } from '@aws-lambda-powertools/logger';
import { SendEmailCommand, SESClient } from '@aws-sdk/client-ses';
import { IValidationErrorEventRecord } from '../lib/models';
import { ReportEmailer } from '../lib/report-emailer';
import {
    SAMPLE_SORTABLE_VALIDATION_ERROR_RECORDS,
    SAMPLE_UNMARSHALLED_INGEST_FAILURE_ERROR_RECORD,
    SAMPLE_UNMARSHALLED_VALIDATION_ERROR_RECORD
} from './sample-records';

/*
 * Double casting to allow us to pass a mock in for the real thing
 */
const asSESClient = (mock: ReturnType<typeof mockClient>) =>
    mock as unknown as SESClient;


describe('Report emailer', () => {
    let mockSESClient: ReturnType<typeof mockClient>;

    beforeAll(async () => {
        process.env.DEBUG = 'true';
        process.env.FROM_ADDRESS = 'noreply@example.org';

        mockSESClient = mockClient(SESClient);

        mockSESClient.on(SendEmailCommand).resolves({
            MessageId: 'message-id-123'
        });

    });

    it('should render an html document', async () => {
        const logger = new Logger();
        const reportEmailer = new ReportEmailer({
            logger: logger,
            sesClient: asSESClient(mockSESClient)
        });
        const template = reportEmailer.generateReport(
            {
                ingestFailures: [ SAMPLE_UNMARSHALLED_INGEST_FAILURE_ERROR_RECORD ],
                validationErrors: [ SAMPLE_UNMARSHALLED_VALIDATION_ERROR_RECORD ]
            },
            'aslp',
            'ohio'
        );

        // Any HTML document would start with a '<' and end with a '>'
        expect(template.charAt(0)).toBe('<');
        expect(template.charAt(template.length - 1)).toBe('>');
    });


    it('should send a report email', async () => {
        const logger = new Logger();
        const sesClient = new SESClient();
        const reportEmailer = new ReportEmailer({
            logger: logger,
            sesClient: sesClient
        });
        const messageId = await reportEmailer.sendReportEmail(
            {
                ingestFailures: [ SAMPLE_UNMARSHALLED_INGEST_FAILURE_ERROR_RECORD ],
                validationErrors: [ SAMPLE_UNMARSHALLED_VALIDATION_ERROR_RECORD ]
            },
            'aslp',
            'ohio',
            [
                'operations@example.com'
            ]
        );

        expect(messageId).toEqual('message-id-123');
        expect(mockSESClient).toHaveReceivedCommandWith(
            SendEmailCommand,
            {
                Destination: {
                    ToAddresses: ['operations@example.com']
                },
                Message: {
                    Body: {
                        Html: {
                            Charset: 'UTF-8',
                            Data: expect.stringContaining('<!DOCTYPE html>')
                        }
                    },
                    Subject: {
                        Charset: 'UTF-8',
                        Data: 'License Data Error Summary: aslp / ohio'
                    }
                },
                Source: 'Compact Connect <noreply@example.org>'
            }
        );
    });

    it('should sort validation errors by record number then time', async () => {
        const logger = new Logger();
        const sesClient = new SESClient();

        class TestableReportEmailer extends ReportEmailer {
            public testSortValidationErrors(validationErrors: IValidationErrorEventRecord[]) {
                return this.sortValidationErrors(validationErrors);
            }
        }

        const reportEmailer = new TestableReportEmailer({
            logger: logger,
            sesClient: sesClient
        });

        const sorted = reportEmailer.testSortValidationErrors(
            SAMPLE_SORTABLE_VALIDATION_ERROR_RECORDS
        );

        const flattenedErrors: string[] = sorted.flatMap((record) => record.errors.dateOfRenewal);

        expect(flattenedErrors).toEqual([
            'Row 4, 5:47',
            'Row 5, 4:47',
            'Row 5, 5:47'
        ]);
    });

    it('should send an alls well email', async () => {
        const logger = new Logger();
        const sesClient = new SESClient();
        const reportEmailer = new ReportEmailer({
            logger: logger,
            sesClient: sesClient
        });
        const messageId = await reportEmailer.sendAllsWellEmail(
            'aslp',
            'ohio',
            [ 'operations@example.com' ]
        );

        expect(messageId).toEqual('message-id-123');
        expect(mockSESClient).toHaveReceivedCommandWith(
            SendEmailCommand,
            {
                Destination: {
                    ToAddresses: ['operations@example.com']
                },
                Message: {
                    Body: {
                        Html: {
                            Charset: 'UTF-8',
                            Data: expect.stringContaining('<!DOCTYPE html>')
                        }
                    },
                    Subject: {
                        Charset: 'UTF-8',
                        Data: 'License Data Summary: aslp / ohio'
                    }
                },
                Source: 'Compact Connect <noreply@example.org>'
            }
        );
    });

    it('should send a "no license updates" email', async () => {
        const logger = new Logger();
        const sesClient = new SESClient();
        const reportEmailer = new ReportEmailer({
            logger: logger,
            sesClient: sesClient
        });
        const messageId = await reportEmailer.sendNoLicenseUpdatesEmail(
            'aslp',
            'ohio',
            [ 'operations@example.com' ]
        );

        expect(messageId).toEqual('message-id-123');
        expect(mockSESClient).toHaveReceivedCommandWith(
            SendEmailCommand,
            {
                Destination: {
                    ToAddresses: ['operations@example.com']
                },
                Message: {
                    Body: {
                        Html: {
                            Charset: 'UTF-8',
                            Data: expect.stringContaining('<!DOCTYPE html>')
                        }
                    },
                    Subject: {
                        Charset: 'UTF-8',
                        Data: 'No License Updates for Last 7 Days: aslp / ohio'
                    }
                },
                Source: 'Compact Connect <noreply@example.org>'
            }
        );
    });
});
