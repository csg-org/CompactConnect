import { mockClient } from 'aws-sdk-client-mock';
import 'aws-sdk-client-mock-jest';
import { Logger } from '@aws-lambda-powertools/logger';
import { SendEmailCommand, SESClient } from '@aws-sdk/client-ses';
import { ReportEmailer } from '../lib/report-emailer';
import {
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
        const template = reportEmailer.generateReport({
            ingestFailures: [ SAMPLE_UNMARSHALLED_INGEST_FAILURE_ERROR_RECORD ],
            validationErrors: [ SAMPLE_UNMARSHALLED_VALIDATION_ERROR_RECORD ]
        });

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
                        Data: 'Data Validation Report'
                    }
                },
                Source: 'Compact Connect <noreply@example.org>'
            }
        );
    });

    it('should send an alls well email', async () => {
        const logger = new Logger();
        const sesClient = new SESClient();
        const reportEmailer = new ReportEmailer({
            logger: logger,
            sesClient: sesClient
        });
        const messageId = await reportEmailer.sendAllsWellEmail([ 'operations@example.com' ]);

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
                        Data: 'License Data Summary'
                    }
                },
                Source: 'Compact Connect <noreply@example.org>'
            }
        );
    });
});
