import { mockClient } from 'aws-sdk-client-mock';
import 'aws-sdk-client-mock-jest';
import { Logger } from '@aws-lambda-powertools/logger';
import { SendEmailCommand, SESv2Client } from '@aws-sdk/client-sesv2';
import { IngestEventEmailService } from '../../../lib/email';
import { EmailTemplateCapture } from '../../utils/email-template-capture';
import { TReaderDocument } from '@csg-org/email-builder';
import {
    SAMPLE_SORTABLE_VALIDATION_ERROR_RECORDS,
    SAMPLE_UNMARSHALLED_INGEST_FAILURE_ERROR_RECORD,
    SAMPLE_UNMARSHALLED_VALIDATION_ERROR_RECORD,
    SAMPLE_UNMARSHALLED_VALIDATION_ERROR_RECORD_NO_RECORD_NUMBER
} from '../../sample-records';
import { describe, it, beforeEach, beforeAll, afterAll, jest } from '@jest/globals';

const asSESClient = (mock: ReturnType<typeof mockClient>) =>
    mock as unknown as SESv2Client;

describe('IngestEventEmailService', () => {
    let emailService: IngestEventEmailService;
    let mockSESClient: ReturnType<typeof mockClient>;

    beforeAll(() => {
        // Mock the renderTemplate method if template capture is enabled
        if (EmailTemplateCapture.isEnabled()) {
            const original = (IngestEventEmailService.prototype as any).renderTemplate;

            jest.spyOn(IngestEventEmailService.prototype as any, 'renderTemplate').mockImplementation(function (this: any, ...args: any[]) {
                const [template, options] = args as [TReaderDocument, any];

                EmailTemplateCapture.captureTemplate(template);
                const html = original.apply(this, args);

                EmailTemplateCapture.captureHtml(html, template, options);
                return html;
            });
        }
    });

    afterAll(() => {
        jest.restoreAllMocks();
    });

    beforeEach(() => {
        jest.clearAllMocks();
        mockSESClient = mockClient(SESv2Client);

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
            'Audiology and Speech Language Pathology',
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
            'Audiology and Speech Language Pathology',
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
                Content: {
                    Simple: {
                        Body: {
                            Html: {
                                Charset: 'UTF-8',
                                Data: expect.stringContaining('<!DOCTYPE html>')
                            }
                        },
                        Subject: {
                            Charset: 'UTF-8',
                            Data: 'License Data Error Summary: Audiology and Speech Language Pathology / Ohio'
                        }
                    }
                },
                FromEmailAddress: 'CompactConnect <noreply@example.org>'
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

    it('should sort unnumbered errors after numbered errors, then by time', () => {
        const unnumbered1 = { ...SAMPLE_UNMARSHALLED_VALIDATION_ERROR_RECORD_NO_RECORD_NUMBER, eventTime: '2024-10-30T03:00:00.000000+00:00' };
        const unnumbered2 = { ...SAMPLE_UNMARSHALLED_VALIDATION_ERROR_RECORD_NO_RECORD_NUMBER, eventTime: '2024-10-30T05:00:00.000000+00:00' };
        const numbered = { ...SAMPLE_UNMARSHALLED_VALIDATION_ERROR_RECORD, recordNumber: 2 };

        const sorted = emailService['sortValidationErrors']([unnumbered2, numbered, unnumbered1]);

        expect(sorted[0]).toEqual(numbered);
        expect(sorted[1]).toEqual(unnumbered1);
        expect(sorted[2]).toEqual(unnumbered2);
    });

    it('should render a validation error without a "Line N" heading when recordNumber is absent', () => {
        const html = emailService.generateReport(
            {
                ingestFailures: [],
                validationErrors: [ SAMPLE_UNMARSHALLED_VALIDATION_ERROR_RECORD_NO_RECORD_NUMBER ]
            },
            'Social Work',
            'Ohio'
        );

        expect(html).not.toContain('Line ');
        expect(html).toContain('Validation error');
    });

    it('should send an alls well email', async () => {
        const messageId = await emailService.sendAllsWellEmail(
            'Audiology and Speech Language Pathology',
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
                Content: {
                    Simple: {
                        Body: {
                            Html: {
                                Charset: 'UTF-8',
                                Data: expect.stringContaining('<!DOCTYPE html>')
                            }
                        },
                        Subject: {
                            Charset: 'UTF-8',
                            Data: 'License Data Summary: Audiology and Speech Language Pathology / Ohio'
                        }
                    }
                },
                FromEmailAddress: 'CompactConnect <noreply@example.org>'
            }
        );
    });

    it('should send a "no license updates" email with expected image url', async () => {
        const messageId = await emailService.sendNoLicenseUpdatesEmail(
            'Audiology and Speech Language Pathology',
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
                Content: {
                    Simple: {
                        Body: {
                            Html: {
                                Charset: 'UTF-8',
                                Data: expect.stringContaining('src=\"https://app.test.compactconnect.org/img/email/ico-noupdates@2x.png\"')
                            }
                        },
                        Subject: {
                            Charset: 'UTF-8',
                            Data: 'No License Updates for Last 7 Days: Audiology and Speech Language Pathology / Ohio'
                        }
                    }
                },
                FromEmailAddress: 'CompactConnect <noreply@example.org>'
            }
        );
    });
});
