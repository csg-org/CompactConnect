import { mockClient } from 'aws-sdk-client-mock';
import 'aws-sdk-client-mock-jest';
import { Logger } from '@aws-lambda-powertools/logger';
import { SendEmailCommand, SendRawEmailCommand, SESClient } from '@aws-sdk/client-ses';
import { S3Client, GetObjectCommand } from '@aws-sdk/client-s3';
import { Readable } from 'stream';
import { sdkStreamMixin } from '@smithy/util-stream';
import * as nodemailer from 'nodemailer';
import { EmailNotificationService } from '../../../lib/email';
import { CompactConfigurationClient } from '../../../lib/compact-configuration-client';
import { JurisdictionClient } from '../../../lib/jurisdiction-client';
import { describe, it, expect, beforeEach, jest } from '@jest/globals';

jest.mock('nodemailer');

const SAMPLE_COMPACT_CONFIG = {
    pk: 'aslp#CONFIGURATION',
    sk: 'aslp#CONFIGURATION',
    compactAdverseActionsNotificationEmails: ['adverse@example.com'],
    compactCommissionFee: {
        feeAmount: 3.5,
        feeType: 'FLAT_RATE'
    },
    compactAbbr: 'aslp',
    compactName: 'Audiology and Speech Language Pathology',
    compactOperationsTeamEmails: ['operations@example.com'],
    compactSummaryReportNotificationEmails: ['summary@example.com'],
    dateOfUpdate: '2024-12-10T19:27:28+00:00',
    type: 'compact'
};

const SAMPLE_JURISDICTION_CONFIG = {
    pk: 'aslp#CONFIGURATION',
    sk: 'aslp#JURISDICTION#OH',
    jurisdictionName: 'Ohio',
    postalAbbreviation: 'OH',
    compact: 'aslp',
    jurisdictionOperationsTeamEmails: ['oh-ops@example.com'],
    jurisdictionAdverseActionsNotificationEmails: ['oh-adverse@example.com'],
    jurisdictionSummaryReportNotificationEmails: ['oh-summary@example.com']
};

const asSESClient = (mock: ReturnType<typeof mockClient>) =>
    mock as unknown as SESClient;

const asS3Client = (mock: ReturnType<typeof mockClient>) =>
    mock as unknown as S3Client;

interface MockMailResponse {
    messageId: string;
}

const MOCK_TRANSPORT = {
    sendMail: jest.fn().mockImplementation(async () => ({ messageId: 'test-message-id' }))
};

describe('EmailNotificationService', () => {
    let emailService: EmailNotificationService;
    let mockSESClient: ReturnType<typeof mockClient>;
    let mockS3Client: ReturnType<typeof mockClient>;
    let mockCompactConfigurationClient: jest.Mocked<CompactConfigurationClient>;
    let mockJurisdictionClient: jest.Mocked<JurisdictionClient>;

    beforeEach(() => {
        jest.clearAllMocks();
        mockSESClient = mockClient(SESClient);
        mockS3Client = mockClient(S3Client);
        mockCompactConfigurationClient = {
            getCompactConfiguration: jest.fn()
        } as any;
        mockJurisdictionClient = {
            getJurisdictionConfigurations: jest.fn(),
            getJurisdictionConfiguration: jest.fn()
        } as any;

        // Reset environment variables
        process.env.FROM_ADDRESS = 'noreply@example.org';
        process.env.UI_BASE_PATH_URL = 'https://app.test.compactconnect.org';
        process.env.TRANSACTION_REPORTS_BUCKET_NAME = 'test-transaction-reports-bucket';

        // Set up default successful responses
        mockSESClient.on(SendEmailCommand).resolves({
            MessageId: 'message-id-123'
        });

        mockSESClient.on(SendRawEmailCommand).resolves({
            MessageId: 'message-id-raw'
        });

        (nodemailer.createTransport as jest.Mock).mockReturnValue(MOCK_TRANSPORT);

        emailService = new EmailNotificationService({
            logger: new Logger({ serviceName: 'test' }),
            sesClient: asSESClient(mockSESClient),
            s3Client: asS3Client(mockS3Client),
            compactConfigurationClient: mockCompactConfigurationClient,
            jurisdictionClient: mockJurisdictionClient
        });
    });

    describe('Transaction Batch Settlement Failure', () => {
        it('should send email using compact operations team emails', async () => {
            mockCompactConfigurationClient.getCompactConfiguration.mockResolvedValue(SAMPLE_COMPACT_CONFIG);

            await emailService.sendTransactionBatchSettlementFailureEmail(
                'aslp',
                'COMPACT_OPERATIONS_TEAM'
            );

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
                            Data: 'Transactions Failed to Settle for ASLP Payment Processor'
                        }
                    },
                    Source: 'Compact Connect <noreply@example.org>'
                }
            );
        });

        it('should send email using specific emails', async () => {
            await emailService.sendTransactionBatchSettlementFailureEmail(
                'aslp',
                'SPECIFIC',
                ['specific@example.com']
            );

            expect(mockSESClient).toHaveReceivedCommandWith(
                SendEmailCommand,
                {
                    Destination: {
                        ToAddresses: ['specific@example.com']
                    },
                    Message: expect.any(Object),
                    Source: 'Compact Connect <noreply@example.org>'
                }
            );
        });

        it('should throw error when no recipients found', async () => {
            mockCompactConfigurationClient.getCompactConfiguration.mockResolvedValue({
                ...SAMPLE_COMPACT_CONFIG,
                compactOperationsTeamEmails: []
            });

            await expect(emailService.sendTransactionBatchSettlementFailureEmail(
                'aslp',
                'COMPACT_OPERATIONS_TEAM'
            )).rejects.toThrow('No recipients found for compact aslp with recipient type COMPACT_OPERATIONS_TEAM');
        });

        it('should throw error for specific recipient type without emails', async () => {
            await expect(emailService.sendTransactionBatchSettlementFailureEmail(
                'aslp',
                'SPECIFIC'
            )).rejects.toThrow('SPECIFIC recipientType requested but no specific email addresses provided');
        });

        it('should throw error for unsupported recipient type', async () => {
            await expect(emailService.sendTransactionBatchSettlementFailureEmail(
                'aslp',
                'JURISDICTION_OPERATIONS_TEAM'
            )).rejects.toThrow('Unsupported recipient type for compact configuration: JURISDICTION_OPERATIONS_TEAM');
        });

        it('should include logo in email', async () => {
            mockCompactConfigurationClient.getCompactConfiguration.mockResolvedValue(SAMPLE_COMPACT_CONFIG);

            await emailService.sendTransactionBatchSettlementFailureEmail(
                'aslp',
                'COMPACT_OPERATIONS_TEAM'
            );

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
                                Data: expect.stringContaining('src=\"https://app.test.compactconnect.org/img/email/compact-connect-logo-final.png\"')
                            }
                        },
                        Subject: {
                            Charset: 'UTF-8',
                            Data: 'Transactions Failed to Settle for ASLP Payment Processor'
                        }
                    },
                    Source: 'Compact Connect <noreply@example.org>'
                }
            );
        });
    });

    describe('Privilege Deactivation Provider Notification', () => {
        it('should send provider privilege deactivation notification email with expected subject', async () => {
            mockCompactConfigurationClient.getCompactConfiguration.mockResolvedValue(SAMPLE_COMPACT_CONFIG);

            await emailService.sendPrivilegeDeactivationProviderNotificationEmail(
                'aslp',
                ['specific@example.com'],
                'some-privilege-id'
            );

            expect(mockSESClient).toHaveReceivedCommandWith(
                SendEmailCommand,
                {
                    Destination: {
                        ToAddresses: ['specific@example.com']
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
                            Data: 'Your Privilege some-privilege-id is Deactivated'
                        }
                    },
                    Source: 'Compact Connect <noreply@example.org>'
                }
            );
        });

        it('should throw error when no recipients provided for provider privilege deactivation notification email', async () => {
            await expect(emailService.sendPrivilegeDeactivationProviderNotificationEmail(
                'aslp',
                undefined,
                'some-privilege-id'
            )).rejects.toThrow('No recipients specified for provider privilege deactivation notification email');
        });
    });

    describe('Privilege Deactivation Jurisdiction Notification', () => {
        it('should send jurisdiction privilege deactivation notification email with expected subject', async () => {
            mockJurisdictionClient.getJurisdictionConfiguration.mockResolvedValue(SAMPLE_JURISDICTION_CONFIG);

            await emailService.sendPrivilegeDeactivationJurisdictionNotificationEmail(
                'aslp',
                'oh',
                'JURISDICTION_SUMMARY_REPORT',
                'some-privilege-id',
                'John',
                'Doe'
            );

            expect(mockSESClient).toHaveReceivedCommandWith(
                SendEmailCommand,
                {
                    Destination: {
                        ToAddresses: ['oh-summary@example.com']
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
                            Data: `A Privilege was Deactivated in the ASLP Compact`
                        }
                    },
                    Source: 'Compact Connect <noreply@example.org>'
                }
            );
        });

        it('should throw error when no recipients found for jurisdiction privilege deactivation notification email', async () => {
            mockJurisdictionClient.getJurisdictionConfiguration.mockResolvedValue({
                ...SAMPLE_JURISDICTION_CONFIG,
                jurisdictionSummaryReportNotificationEmails: []
            });

            await expect(emailService.sendPrivilegeDeactivationJurisdictionNotificationEmail(
                'aslp',
                'oh',
                'JURISDICTION_SUMMARY_REPORT',
                'some-privilege-id',
                'John',
                'Doe'
            )).rejects.toThrow('No recipients found for jurisdiction oh in compact aslp');
        });
    });

    describe('Compact Transaction Report', () => {
        beforeEach(() => {
            mockCompactConfigurationClient.getCompactConfiguration.mockResolvedValue(SAMPLE_COMPACT_CONFIG);

            // Create a mock stream that implements the required AWS SDK interfaces
            const mockStream = sdkStreamMixin(
                new Readable({
                    read() {
                        this.push(Buffer.from('test data'));
                        this.push(null);
                    }
                })
            );

            // Mock S3 response
            mockS3Client.on(GetObjectCommand).resolves({
                Body: mockStream
            });
        });

        it('should send email with zip attachment', async () => {
            await emailService.sendCompactTransactionReportEmail(
                'aslp',
                'compact/aslp/reports/test-report.zip',
                'weekly',
                '2024-03-01',
                '2024-03-07'
            );

            // Verify S3 was queried for the report
            expect(mockS3Client).toHaveReceivedCommandWith(GetObjectCommand, {
                Bucket: 'test-transaction-reports-bucket',
                Key: 'compact/aslp/reports/test-report.zip'
            });

            // Verify nodemailer transport was created with correct SES config
            expect(nodemailer.createTransport).toHaveBeenCalledWith({
                SES: {
                    ses: expect.any(Object),
                    aws: { SendRawEmailCommand }
                }
            });

            // Verify email was sent with correct parameters
            expect(MOCK_TRANSPORT.sendMail).toHaveBeenCalledWith({
                from: 'Compact Connect <noreply@example.org>',
                to: ['summary@example.com'],
                subject: 'Weekly Report for Compact ASLP',
                html: expect.stringContaining('Please find attached the weekly settled transaction reports for the compact for the period 2024-03-01 to 2024-03-07'),
                attachments: [
                    {
                        filename: 'aslp-settled-transaction-report-2024-03-01--2024-03-07.zip',
                        content: expect.any(Buffer),
                        contentType: 'application/zip'
                    }
                ]
            });
        });

        it('should use monthly subject when reporting cycle is monthly', async () => {
            await emailService.sendCompactTransactionReportEmail(
                'aslp',
                'test-bucket/compact/aslp/reports/test-report.zip',
                'monthly',
                '2024-03-01',
                '2024-03-31'
            );

            expect(MOCK_TRANSPORT.sendMail).toHaveBeenCalledWith(
                expect.objectContaining({
                    subject: 'Monthly Report for Compact ASLP',
                    html: expect.stringContaining('Please find attached the monthly settled transaction reports for the compact for the period 2024-03-01 to 2024-03-31')
                })
            );
        });

        it('should throw error when no recipients found', async () => {
            mockCompactConfigurationClient.getCompactConfiguration.mockResolvedValue({
                ...SAMPLE_COMPACT_CONFIG,
                compactSummaryReportNotificationEmails: []
            });

            await expect(emailService.sendCompactTransactionReportEmail(
                'aslp',
                'test-bucket/compact/aslp/reports/test-report.zip',
                'weekly',
                '2024-03-01',
                '2024-03-07'
            )).rejects.toThrow('No recipients found for compact aslp with recipient type COMPACT_SUMMARY_REPORT');

            // Verify no email was sent
            expect(MOCK_TRANSPORT.sendMail).not.toHaveBeenCalled();
        });

        it('should throw error when S3 fails to return report', async () => {
            mockS3Client.on(GetObjectCommand).resolves({
                Body: undefined
            });

            await expect(emailService.sendCompactTransactionReportEmail(
                'aslp',
                'test-bucket/compact/aslp/reports/test-report.zip',
                'weekly',
                '2024-03-01',
                '2024-03-07'
            )).rejects.toThrow('Failed to retrieve report from S3: test-bucket/compact/aslp/reports/test-report.zip');

            // Verify no email was sent
            expect(MOCK_TRANSPORT.sendMail).not.toHaveBeenCalled();
        });
    });

    describe('Jurisdiction Transaction Report', () => {
        beforeEach(() => {
            mockCompactConfigurationClient.getCompactConfiguration.mockResolvedValue(SAMPLE_COMPACT_CONFIG);
            mockJurisdictionClient.getJurisdictionConfiguration.mockResolvedValue(SAMPLE_JURISDICTION_CONFIG);

            // Create a mock stream that implements the required AWS SDK interfaces
            const mockStream = sdkStreamMixin(
                new Readable({
                    read() {
                        this.push(Buffer.from('test data'));
                        this.push(null);
                    }
                })
            );

            // Mock S3 response
            mockS3Client.on(GetObjectCommand).resolves({
                Body: mockStream
            });
        });

        it('should send email with zip attachment', async () => {
            await emailService.sendJurisdictionTransactionReportEmail(
                'aslp',
                'oh',
                'jurisdiction/oh/reports/test-report.zip',
                'weekly',
                '2024-03-01',
                '2024-03-07'
            );

            // Verify S3 was queried for the report
            expect(mockS3Client).toHaveReceivedCommandWith(GetObjectCommand, {
                Bucket: 'test-transaction-reports-bucket',
                Key: 'jurisdiction/oh/reports/test-report.zip'
            });

            // Verify nodemailer transport was created with correct SES config
            expect(nodemailer.createTransport).toHaveBeenCalledWith({
                SES: {
                    ses: expect.any(Object),
                    aws: { SendRawEmailCommand }
                }
            });

            // Verify email was sent with correct parameters
            expect(MOCK_TRANSPORT.sendMail).toHaveBeenCalledWith({
                from: 'Compact Connect <noreply@example.org>',
                to: ['oh-summary@example.com'],
                subject: 'Ohio Weekly Report for Compact ASLP',
                html: expect.stringContaining('Please find attached the weekly settled transaction report for your jurisdiction for the period 2024-03-01 to 2024-03-07'),
                attachments: [
                    {
                        filename: 'oh-settled-transaction-report-2024-03-01--2024-03-07.zip',
                        content: expect.any(Buffer),
                        contentType: 'application/zip'
                    }
                ]
            });
        });

        it('should use monthly subject when reporting cycle is monthly', async () => {
            await emailService.sendJurisdictionTransactionReportEmail(
                'aslp',
                'oh',
                'test-bucket/jurisdiction/oh/reports/test-report.zip',
                'monthly',
                '2024-03-01',
                '2024-03-31'
            );

            expect(MOCK_TRANSPORT.sendMail).toHaveBeenCalledWith(
                expect.objectContaining({
                    subject: 'Ohio Monthly Report for Compact ASLP',
                    html: expect.stringContaining('Please find attached the monthly settled transaction report for your jurisdiction for the period 2024-03-01 to 2024-03-31')
                })
            );
        });

        it('should throw error when no recipients found', async () => {
            mockJurisdictionClient.getJurisdictionConfiguration.mockResolvedValue({
                ...SAMPLE_JURISDICTION_CONFIG,
                jurisdictionSummaryReportNotificationEmails: []
            });

            await expect(emailService.sendJurisdictionTransactionReportEmail(
                'aslp',
                'oh',
                'test-bucket/jurisdiction/oh/reports/test-report.zip',
                'weekly',
                '2024-03-01',
                '2024-03-07'
            )).rejects.toThrow('No recipients found for jurisdiction oh in compact aslp');

            // Verify no email was sent
            expect(MOCK_TRANSPORT.sendMail).not.toHaveBeenCalled();
        });

        it('should throw error when S3 fails to return report', async () => {
            mockS3Client.on(GetObjectCommand).resolves({
                Body: undefined
            });

            await expect(emailService.sendJurisdictionTransactionReportEmail(
                'aslp',
                'oh',
                'test-bucket/jurisdiction/oh/reports/test-report.zip',
                'weekly',
                '2024-03-01',
                '2024-03-07'
            )).rejects.toThrow('Failed to retrieve report from S3: test-bucket/jurisdiction/oh/reports/test-report.zip');

            // Verify no email was sent
            expect(MOCK_TRANSPORT.sendMail).not.toHaveBeenCalled();
        });
    });

    describe('Multiple Registration Attempt Notification', () => {
        it('should send multiple registration attempt notification email with expected content', async () => {
            await emailService.sendMultipleRegistrationAttemptNotificationEmail(
                'aslp',
                ['user@example.com']
            );

            expect(mockSESClient).toHaveReceivedCommandWith(
                SendEmailCommand,
                {
                    Destination: {
                        ToAddresses: ['user@example.com']
                    },
                    Message: {
                        Body: {
                            Html: {
                                Charset: 'UTF-8',
                                Data: expect.stringContaining(
                                    'A registration attempt was made in the Compact Connect system ')
                            }
                        },
                        Subject: {
                            Charset: 'UTF-8',
                            Data: 'Registration Attempt Notification - Compact Connect'
                        }
                    },
                    Source: 'Compact Connect <noreply@example.org>'
                }
            );
        });

        it('should include login URL in email content', async () => {
            await emailService.sendMultipleRegistrationAttemptNotificationEmail(
                'aslp',
                ['user@example.com']
            );

            expect(mockSESClient).toHaveReceivedCommandWith(
                SendEmailCommand,
                {
                    Destination: {
                        ToAddresses: ['user@example.com']
                    },
                    Message: {
                        Body: {
                            Html: {
                                Charset: 'UTF-8',
                                Data: expect.stringContaining('https://app.test.compactconnect.org/Dashboard')
                            }
                        },
                        Subject: expect.any(Object)
                    },
                    Source: 'Compact Connect <noreply@example.org>'
                }
            );
        });

        it('should include registration temp login instructions', async () => {
            await emailService.sendMultipleRegistrationAttemptNotificationEmail(
                'aslp',
                ['user@example.com']
            );

            expect(mockSESClient).toHaveReceivedCommandWith(
                SendEmailCommand,
                {
                    Destination: {
                        ToAddresses: ['user@example.com']
                    },
                    Message: {
                        Body: {
                            Html: {
                                Charset: 'UTF-8',
                                Data: expect.stringContaining('If you originally registered within the past 24 hours, make sure to login with your temporary password sent to this same email address.')
                            }
                        },
                        Subject: expect.any(Object)
                    },
                    Source: 'Compact Connect <noreply@example.org>'
                }
            );
        });

        it('should throw error when no recipients provided', async () => {
            await expect(emailService.sendMultipleRegistrationAttemptNotificationEmail(
                'aslp',
                []
            )).rejects.toThrow('No recipients found for multiple registration attempt notification email');
        });

        it('should throw error when recipients is undefined', async () => {
            await expect(emailService.sendMultipleRegistrationAttemptNotificationEmail(
                'aslp',
                undefined
            )).rejects.toThrow('No recipients found for multiple registration attempt notification email');
        });
    });

    describe('Privilege Purchase Provider Notification', () => {
        it('should send privilege purchase provider notification email with correct content', async () => {
            await emailService.sendPrivilegePurchaseProviderNotificationEmail(
                '12/12/2004',
                [
                    {
                        jurisdiction: 'OH',
                        licenseTypeAbbrev: 'OTA',
                        privilegeId: 'OTA-OH-019'
                    }
                ],
                '45.0',
                [
                    {
                        name: 'OH OTA fee', quantity: '2', unitPrice: '45'
                    },
                    {
                        name: 'cc fees', quantity: '1', unitPrice: '3.5'
                    }
                ],
                ['provider@example.com']
            );

            expect(mockSESClient).toHaveReceivedCommandWith(
                SendEmailCommand,
                {
                    Destination: {
                        ToAddresses: ['provider@example.com']
                    },
                    Message: {
                        Body: {
                            Html: {
                                Charset: 'UTF-8',
                                Data: expect.stringContaining('Privilege Purchase Confirmation')
                            }
                        },
                        Subject: {
                            Charset: 'UTF-8',
                            Data: 'Compact Connect Privilege Purchase Confirmation'
                        }
                    },
                    Source: 'Compact Connect <noreply@example.org>'
                }
            );
        });

        it('should throw error when no recipients found', async () => {
            await expect(emailService.sendPrivilegePurchaseProviderNotificationEmail(
                '12/12/2004',
                [
                    {
                        jurisdiction: 'OH',
                        licenseTypeAbbrev: 'OTA',
                        privilegeId: 'OTA-OH-019'
                    }
                ],
                '45.0',
                [
                    {
                        name: 'OH OTA fee', quantity: '2', unitPrice: '45'
                    },
                    {
                        name: 'cc fees', quantity: '1', unitPrice: '3.5'
                    }
                ],
                []
            )).rejects.toThrow('No recipients found');
        });
    });
});
