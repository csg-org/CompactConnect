import { mockClient } from 'aws-sdk-client-mock';
import 'aws-sdk-client-mock-jest';
import { Logger } from '@aws-lambda-powertools/logger';
import { SendEmailCommand, SESClient } from '@aws-sdk/client-ses';
import { IngestEventEmailService } from '../../../lib/email';
import {
    SAMPLE_SORTABLE_VALIDATION_ERROR_RECORDS,
    SAMPLE_UNMARSHALLED_INGEST_FAILURE_ERROR_RECORD,
    SAMPLE_UNMARSHALLED_VALIDATION_ERROR_RECORD
} from '../../sample-records';
import { describe, it, expect, beforeEach, jest } from '@jest/globals';

const asSESClient = (mock: ReturnType<typeof mockClient>) =>
    mock as unknown as SESClient;

describe('IngestEventEmailService', () => {
    let emailService: IngestEventEmailService;
    let mockSESClient: ReturnType<typeof mockClient>;

    beforeEach(() => {
        jest.clearAllMocks();
        mockSESClient = mockClient(SESClient);

        // Reset environment variables
        process.env.FROM_ADDRESS = 'noreply@example.org';
        process.env.UI_BASE_PATH_URL = 'https://app.test.compactconnect.org';

        // Set up default successful responses
        mockSESClient.on(SendEmailCommand).resolves({
            MessageId: 'message-id-123'
        });

        emailService = new IngestEventEmailService({
            logger: new Logger({ serviceName: 'test' }),
            sesClient: asSESClient(mockSESClient),
            s3Client: {} as any,
            compactConfigurationClient: {} as any,
            jurisdictionClient: {} as any
        });
    });

    it('should render an html document', async () => {
        const template = emailService.generateReport(
            {
                ingestFailures: [ SAMPLE_UNMARSHALLED_INGEST_FAILURE_ERROR_RECORD ],
                validationErrors: [ SAMPLE_UNMARSHALLED_VALIDATION_ERROR_RECORD ]
            },
            'aslp',
            'Ohio'
        );

        // Any HTML document would start with a '<' and end with a '>'
        expect(template.charAt(0)).toBe('<');
        expect(template.charAt(template.length - 1)).toBe('>');
    });

    it('should send a report email', async () => {
        const messageId = await emailService.sendReportEmail(
            {
                ingestFailures: [ SAMPLE_UNMARSHALLED_INGEST_FAILURE_ERROR_RECORD ],
                validationErrors: [ SAMPLE_UNMARSHALLED_VALIDATION_ERROR_RECORD ]
            },
            'aslp',
            'Ohio',
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
                        Data: 'License Data Error Summary: aslp / Ohio'
                    }
                },
                Source: 'Compact Connect <noreply@example.org>'
            }
        );
    });

    it('should sort validation errors by record number then time', async () => {
        const sorted = emailService['sortValidationErrors'](
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
        const messageId = await emailService.sendAllsWellEmail(
            'aslp',
            'Ohio',
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
                        Data: 'License Data Summary: aslp / Ohio'
                    }
                },
                Source: 'Compact Connect <noreply@example.org>'
            }
        );
    });

    it('should send a "no license updates" email with expected image url', async () => {
        const messageId = await emailService.sendNoLicenseUpdatesEmail(
            'aslp',
            'Ohio',
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
                            Data: expect.stringContaining('src=\"https://app.test.compactconnect.org/img/email/ico-noupdates@2x.png\"')
                        }
                    },
                    Subject: {
                        Charset: 'UTF-8',
                        Data: 'No License Updates for Last 7 Days: aslp / Ohio'
                    }
                },
                Source: 'Compact Connect <noreply@example.org>'
            }
        );
    });
});
