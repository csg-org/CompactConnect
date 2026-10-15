import { mockClient } from 'aws-sdk-client-mock';
import 'aws-sdk-client-mock-jest';
import { Logger } from '@aws-lambda-powertools/logger';
import { SendEmailCommand, SESv2Client } from '@aws-sdk/client-sesv2';
import { S3Client, GetObjectCommand } from '@aws-sdk/client-s3';
import { Readable } from 'stream';
import { sdkStreamMixin } from '@smithy/util-stream';
import * as nodemailer from 'nodemailer';
import { EmailNotificationService } from '../../../lib/email';
import { CompactConfigurationClient } from '../../../lib/compact-configuration-client';
import { JurisdictionClient } from '../../../lib/jurisdiction-client';
import { EmailTemplateCapture } from '../../utils/email-template-capture';
import { TReaderDocument } from '@csg-org/email-builder';
import { describe, it, beforeEach, beforeAll, afterAll, jest } from '@jest/globals';

jest.mock('nodemailer');

const SAMPLE_COMPACT_CONFIG = {
    pk: 'diet#CONFIGURATION',
    sk: 'diet#CONFIGURATION',
    compactAdverseActionsNotificationEmails: ['adverse@example.com'],
    compactCommissionFee: {
        feeAmount: 3.5,
        feeType: 'FLAT_RATE'
    },
    compactAbbr: 'diet',
    compactName: 'Dietitian',
    compactOperationsTeamEmails: ['operations@example.com'],
    compactSummaryReportNotificationEmails: ['summary@example.com'],
    dateOfUpdate: '2024-12-10T19:27:28+00:00',
    type: 'compact'
};

const SAMPLE_JURISDICTION_CONFIG = {
    pk: 'diet#CONFIGURATION',
    sk: 'diet#JURISDICTION#OH',
    jurisdictionName: 'Ohio',
    postalAbbreviation: 'OH',
    compact: 'diet',
    jurisdictionOperationsTeamEmails: ['oh-ops@example.com'],
    jurisdictionAdverseActionsNotificationEmails: ['oh-adverse@example.com'],
    jurisdictionSummaryReportNotificationEmails: ['oh-summary@example.com']
};

const asSESClient = (mock: ReturnType<typeof mockClient>) =>
    mock as unknown as SESv2Client;

const asS3Client = (mock: ReturnType<typeof mockClient>) =>
    mock as unknown as S3Client;

const MOCK_TRANSPORT = {
    sendMail: jest.fn().mockImplementation(async () => ({ messageId: 'test-message-id' }))
};

describe('EmailNotificationService', () => {
    let emailService: EmailNotificationService;
    let mockSESClient: ReturnType<typeof mockClient>;
    let mockS3Client: ReturnType<typeof mockClient>;
    let mockCompactConfigurationClient: jest.Mocked<CompactConfigurationClient>;
    let mockJurisdictionClient: jest.Mocked<JurisdictionClient>;

    beforeAll(() => {
        // Mock the renderTemplate method if template capture is enabled
        if (EmailTemplateCapture.isEnabled()) {
            const original = (EmailNotificationService.prototype as any).renderTemplate;

            jest.spyOn(EmailNotificationService.prototype as any, 'renderTemplate').mockImplementation(function (this: any, ...args: any[]) {
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

        // Note: SESv2 with nodemailer 7.0.7 uses SendEmailCommand for all email sending

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
                'diet',
                'COMPACT_OPERATIONS_TEAM'
            );

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
                                Data: 'Transactions Failed to Settle for Dietitian Payment Processor'
                            }
                        }
                    },
                    FromEmailAddress: 'CompactConnect <noreply@example.org>'
                }
            );
        });

        it('should send email using specific emails', async () => {
            mockCompactConfigurationClient.getCompactConfiguration.mockResolvedValue(SAMPLE_COMPACT_CONFIG);

            await emailService.sendTransactionBatchSettlementFailureEmail(
                'diet',
                'SPECIFIC',
                ['specific@example.com']
            );

            expect(mockSESClient).toHaveReceivedCommandWith(
                SendEmailCommand,
                {
                    Destination: {
                        ToAddresses: ['specific@example.com']
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
                                Data: 'Transactions Failed to Settle for Dietitian Payment Processor'
                            }
                        }
                    },
                    FromEmailAddress: 'CompactConnect <noreply@example.org>'
                }
            );
        });

        it('should throw error when no recipients found', async () => {
            mockCompactConfigurationClient.getCompactConfiguration.mockResolvedValue({
                ...SAMPLE_COMPACT_CONFIG,
                compactOperationsTeamEmails: []
            });

            await expect(emailService.sendTransactionBatchSettlementFailureEmail(
                'diet',
                'COMPACT_OPERATIONS_TEAM'
            )).rejects.toThrow('No recipients found for compact diet with recipient type COMPACT_OPERATIONS_TEAM');
        });

        it('should throw error for specific recipient type without emails', async () => {
            await expect(emailService.sendTransactionBatchSettlementFailureEmail(
                'diet',
                'SPECIFIC'
            )).rejects.toThrow('SPECIFIC recipientType requested but no specific email addresses provided');
        });

        it('should throw error for unsupported recipient type', async () => {
            await expect(emailService.sendTransactionBatchSettlementFailureEmail(
                'diet',
                'JURISDICTION_OPERATIONS_TEAM'
            )).rejects.toThrow('Unsupported recipient type for compact configuration: JURISDICTION_OPERATIONS_TEAM');
        });

        it('should include logo in email', async () => {
            mockCompactConfigurationClient.getCompactConfiguration.mockResolvedValue(SAMPLE_COMPACT_CONFIG);

            await emailService.sendTransactionBatchSettlementFailureEmail(
                'diet',
                'COMPACT_OPERATIONS_TEAM'
            );

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
                                    Data: expect.stringContaining('src=\"https://app.test.compactconnect.org/img/email/compact-connect-logo-final.png\"')
                                }
                            },
                            Subject: {
                                Charset: 'UTF-8',
                                Data: 'Transactions Failed to Settle for Dietitian Payment Processor'
                            }
                        }
                    },
                    FromEmailAddress: 'CompactConnect <noreply@example.org>'
                }
            );
        });
    });

    describe('Privilege Deactivation Provider Notification', () => {
        it('should send provider privilege deactivation notification email with expected subject', async () => {
            mockCompactConfigurationClient.getCompactConfiguration.mockResolvedValue(SAMPLE_COMPACT_CONFIG);

            await emailService.sendPrivilegeDeactivationProviderNotificationEmail(
                'diet',
                ['specific@example.com'],
                'some-privilege-id'
            );

            expect(mockSESClient).toHaveReceivedCommandWith(
                SendEmailCommand,
                {
                    Destination: {
                        ToAddresses: ['specific@example.com']
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
                                Data: 'Your Privilege some-privilege-id is Deactivated'
                            }
                        }
                    },
                    FromEmailAddress: 'CompactConnect <noreply@example.org>'
                }
            );
        });

        it('should throw error when no recipients provided for provider privilege deactivation notification email', async () => {
            await expect(emailService.sendPrivilegeDeactivationProviderNotificationEmail(
                'diet',
                undefined,
                'some-privilege-id'
            )).rejects.toThrow('No recipients specified for provider privilege deactivation notification email');
        });
    });

    describe('Privilege Deactivation Jurisdiction Notification', () => {
        it('should send jurisdiction privilege deactivation notification email with expected subject', async () => {
            mockCompactConfigurationClient.getCompactConfiguration.mockResolvedValue(SAMPLE_COMPACT_CONFIG);
            mockJurisdictionClient.getJurisdictionConfiguration.mockResolvedValue(SAMPLE_JURISDICTION_CONFIG);

            await emailService.sendPrivilegeDeactivationJurisdictionNotificationEmail(
                'diet',
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
                                Data: `A Privilege was Deactivated in the Dietitian Compact`
                            }
                        }
                    },
                    FromEmailAddress: 'CompactConnect <noreply@example.org>'
                }
            );
        });

        it('should throw error when no recipients found for jurisdiction privilege deactivation notification email', async () => {
            mockJurisdictionClient.getJurisdictionConfiguration.mockResolvedValue({
                ...SAMPLE_JURISDICTION_CONFIG,
                jurisdictionSummaryReportNotificationEmails: []
            });

            await expect(emailService.sendPrivilegeDeactivationJurisdictionNotificationEmail(
                'diet',
                'oh',
                'JURISDICTION_SUMMARY_REPORT',
                'some-privilege-id',
                'John',
                'Doe'
            )).rejects.toThrow('No recipients found for jurisdiction oh in compact diet');
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
                'diet',
                'compact/diet/reports/test-report.zip',
                'weekly',
                '2024-03-01',
                '2024-03-07'
            );

            // Verify S3 was queried for the report
            expect(mockS3Client).toHaveReceivedCommandWith(GetObjectCommand, {
                Bucket: 'test-transaction-reports-bucket',
                Key: 'compact/diet/reports/test-report.zip'
            });

            // Verify nodemailer transport was created with correct SES config
            expect(nodemailer.createTransport).toHaveBeenCalledWith({
                SES: {
                    sesClient: expect.any(Object),
                    SendEmailCommand
                }
            });

            // Verify email was sent with correct parameters
            expect(MOCK_TRANSPORT.sendMail).toHaveBeenCalledWith({
                from: 'CompactConnect <noreply@example.org>',
                to: ['summary@example.com'],
                subject: 'Weekly Report for Dietitian',
                html: expect.any(String),
                attachments: [
                    {
                        filename: 'settled-transaction-report-2024-03-01--2024-03-07.zip',
                        content: expect.any(Buffer),
                        contentType: 'application/zip'
                    }
                ]
            });

            // Get the actual HTML content for detailed validation
            const emailCall = MOCK_TRANSPORT.sendMail.mock.calls[0][0] as any;
            const htmlContent = emailCall.html;

            expect(htmlContent).toBeDefined();
            expect(htmlContent).toContain('Please find attached the weekly settled transaction reports for the compact for the period 2024-03-01 to 2024-03-07');
            expect(htmlContent).toContain('Financial Summary Report - A summary of all settled transactions and fees');
            expect(htmlContent).toContain('Transaction Detail Report - A detailed list of all settled transactions');
        });

        it('should use monthly subject when reporting cycle is monthly', async () => {
            await emailService.sendCompactTransactionReportEmail(
                'diet',
                'test-bucket/compact/diet/reports/test-report.zip',
                'monthly',
                '2024-03-01',
                '2024-03-31'
            );

            expect(MOCK_TRANSPORT.sendMail).toHaveBeenCalledWith(
                expect.objectContaining({
                    subject: 'Monthly Report for Dietitian',
                    html: expect.any(String)
                })
            );

            // Get the actual HTML content for detailed validation
            const emailCall = MOCK_TRANSPORT.sendMail.mock.calls[0][0] as any;
            const htmlContent = emailCall.html;

            expect(htmlContent).toBeDefined();
            expect(htmlContent).toContain('Please find attached the monthly settled transaction reports for the compact for the period 2024-03-01 to 2024-03-31');
        });

        it('should throw error when no recipients found', async () => {
            mockCompactConfigurationClient.getCompactConfiguration.mockResolvedValue({
                ...SAMPLE_COMPACT_CONFIG,
                compactSummaryReportNotificationEmails: []
            });

            await expect(emailService.sendCompactTransactionReportEmail(
                'diet',
                'test-bucket/compact/diet/reports/test-report.zip',
                'weekly',
                '2024-03-01',
                '2024-03-07'
            )).rejects.toThrow('No recipients found for compact diet with recipient type COMPACT_SUMMARY_REPORT');

            // Verify no email was sent
            expect(MOCK_TRANSPORT.sendMail).not.toHaveBeenCalled();
        });

        it('should throw error when S3 fails to return report', async () => {
            mockS3Client.on(GetObjectCommand).resolves({
                Body: undefined
            });

            await expect(emailService.sendCompactTransactionReportEmail(
                'diet',
                'test-bucket/compact/diet/reports/test-report.zip',
                'weekly',
                '2024-03-01',
                '2024-03-07'
            )).rejects.toThrow('Failed to retrieve report from S3: test-bucket/compact/diet/reports/test-report.zip');

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
                'diet',
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
                    sesClient: expect.any(Object),
                    SendEmailCommand
                }
            });

            // Verify email was sent with correct parameters
            expect(MOCK_TRANSPORT.sendMail).toHaveBeenCalledWith({
                from: 'CompactConnect <noreply@example.org>',
                to: ['oh-summary@example.com'],
                subject: 'Ohio Weekly Report for Dietitian',
                html: expect.any(String),
                attachments: [
                    {
                        filename: 'oh-settled-transaction-report-2024-03-01--2024-03-07.zip',
                        content: expect.any(Buffer),
                        contentType: 'application/zip'
                    }
                ]
            });

            // Get the actual HTML content for detailed validation
            const emailCall = MOCK_TRANSPORT.sendMail.mock.calls[0][0] as any;
            const htmlContent = emailCall.html;

            expect(htmlContent).toBeDefined();
            expect(htmlContent).toContain('Please find attached the weekly settled transaction report for your jurisdiction for the period 2024-03-01 to 2024-03-07');
        });

        it('should use monthly subject when reporting cycle is monthly', async () => {
            await emailService.sendJurisdictionTransactionReportEmail(
                'diet',
                'oh',
                'test-bucket/jurisdiction/oh/reports/test-report.zip',
                'monthly',
                '2024-03-01',
                '2024-03-31'
            );

            expect(MOCK_TRANSPORT.sendMail).toHaveBeenCalledWith(
                expect.objectContaining({
                    subject: 'Ohio Monthly Report for Dietitian',
                    html: expect.any(String)
                })
            );

            // Get the actual HTML content for detailed validation
            const emailCall = MOCK_TRANSPORT.sendMail.mock.calls[0][0] as any;
            const htmlContent = emailCall.html;

            expect(htmlContent).toBeDefined();
            expect(htmlContent).toContain('Please find attached the monthly settled transaction report for your jurisdiction for the period 2024-03-01 to 2024-03-31');
        });

        it('should throw error when no recipients found', async () => {
            mockJurisdictionClient.getJurisdictionConfiguration.mockResolvedValue({
                ...SAMPLE_JURISDICTION_CONFIG,
                jurisdictionSummaryReportNotificationEmails: []
            });

            await expect(emailService.sendJurisdictionTransactionReportEmail(
                'diet',
                'oh',
                'test-bucket/jurisdiction/oh/reports/test-report.zip',
                'weekly',
                '2024-03-01',
                '2024-03-07'
            )).rejects.toThrow('No recipients found for jurisdiction oh in compact diet');

            // Verify no email was sent
            expect(MOCK_TRANSPORT.sendMail).not.toHaveBeenCalled();
        });

        it('should throw error when S3 fails to return report', async () => {
            mockS3Client.on(GetObjectCommand).resolves({
                Body: undefined
            });

            await expect(emailService.sendJurisdictionTransactionReportEmail(
                'diet',
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
                'diet',
                ['user@example.com']
            );

            expect(mockSESClient).toHaveReceivedCommandWith(
                SendEmailCommand,
                {
                    Destination: {
                        ToAddresses: ['user@example.com']
                    },
                    Content: {
                        Simple: {
                            Body: {
                                Html: {
                                    Charset: 'UTF-8',
                                    Data: expect.stringContaining(
                                        'A registration attempt was made in the CompactConnect system ')
                                }
                            },
                            Subject: {
                                Charset: 'UTF-8',
                                Data: 'Registration Attempt Notification - CompactConnect'
                            }
                        }
                    },
                    FromEmailAddress: 'CompactConnect <noreply@example.org>'
                }
            );
        });

        it('should include login URL in email content', async () => {
            await emailService.sendMultipleRegistrationAttemptNotificationEmail(
                'diet',
                ['user@example.com']
            );

            expect(mockSESClient).toHaveReceivedCommandWith(
                SendEmailCommand,
                {
                    Destination: {
                        ToAddresses: ['user@example.com']
                    },
                    Content: {
                        Simple: {
                            Body: {
                                Html: {
                                    Charset: 'UTF-8',
                                    Data: expect.stringContaining('https://app.test.compactconnect.org/Dashboard')
                                }
                            },
                            Subject: expect.any(Object)
                        }
                    },
                    FromEmailAddress: 'CompactConnect <noreply@example.org>'
                }
            );
        });

        it('should include registration temp login instructions', async () => {
            await emailService.sendMultipleRegistrationAttemptNotificationEmail(
                'diet',
                ['user@example.com']
            );

            expect(mockSESClient).toHaveReceivedCommandWith(
                SendEmailCommand,
                {
                    Destination: {
                        ToAddresses: ['user@example.com']
                    },
                    Content: {
                        Simple: {
                            Body: {
                                Html: {
                                    Charset: 'UTF-8',
                                    Data: expect.stringContaining('If you originally registered within the past 24 hours, make sure to login with your temporary password sent to this same email address.')
                                }
                            },
                            Subject: expect.any(Object)
                        }
                    },
                    FromEmailAddress: 'CompactConnect <noreply@example.org>'
                }
            );
        });

        it('should throw error when no recipients provided', async () => {
            await expect(emailService.sendMultipleRegistrationAttemptNotificationEmail(
                'diet',
                []
            )).rejects.toThrow('No recipients found for multiple registration attempt notification email');
        });

        it('should throw error when recipients is undefined', async () => {
            await expect(emailService.sendMultipleRegistrationAttemptNotificationEmail(
                'diet',
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
                        licenseTypeAbbrev: 'diet',
                        privilegeId: 'DIET-OH-019'
                    }
                ],
                '45.0',
                [
                    {
                        name: 'OH diet fee', quantity: '2', unitPrice: '45'
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
                    Content: {
                        Simple: {
                            Body: {
                                Html: {
                                    Charset: 'UTF-8',
                                    Data: expect.stringContaining('Privilege Purchase Confirmation')
                                }
                            },
                            Subject: {
                                Charset: 'UTF-8',
                                Data: 'CompactConnect Privilege Purchase Confirmation'
                            }
                        }
                    },
                    FromEmailAddress: 'CompactConnect <noreply@example.org>'
                }
            );
        });

        it('should throw error when no recipients found', async () => {
            await expect(emailService.sendPrivilegePurchaseProviderNotificationEmail(
                '12/12/2004',
                [
                    {
                        jurisdiction: 'OH',
                        licenseTypeAbbrev: 'diet',
                        privilegeId: 'DIET-OH-019'
                    }
                ],
                '45.0',
                [
                    {
                        name: 'OH diet fee', quantity: '2', unitPrice: '45'
                    },
                    {
                        name: 'cc fees', quantity: '1', unitPrice: '3.5'
                    }
                ],
                []
            )).rejects.toThrow('No recipients found');
        });
    });

    describe('Provider Email Verification Code', () => {
        it('should send email verification code with all expected content', async () => {
            const verificationCode = '1234';

            await emailService.sendProviderEmailVerificationCode(
                'diet',
                'newuser@example.com',
                verificationCode
            );

            // Check overall email structure and each content piece
            // Verify email was sent
            expect(mockSESClient).toHaveReceivedCommandWith(SendEmailCommand, {
                Destination: {
                    ToAddresses: ['newuser@example.com']
                },
                Content: {
                    Simple: {
                        Body: {
                            Html: {
                                Charset: 'UTF-8',
                                Data: expect.any(String)
                            }
                        },
                        Subject: {
                            Charset: 'UTF-8',
                            Data: 'Verify Your New Email Address - CompactConnect'
                        }
                    }
                },
                FromEmailAddress: 'CompactConnect <noreply@example.org>'
            });

            // Get the actual HTML content for detailed validation
            const emailCall = mockSESClient.commandCalls(SendEmailCommand)[0];
            const htmlContent = emailCall.args[0].input.Content?.Simple?.Body?.Html?.Data;

            expect(htmlContent).toBeDefined();
            expect(htmlContent).toContain('Please use the following verification code to complete your email address change');
            expect(htmlContent).toContain(`<h2>${verificationCode}</h2>`);
            expect(htmlContent).toContain('This code will expire in 15 minutes');
            expect(htmlContent).toContain('If you did not request this email change, please contact support immediately');
            expect(htmlContent).toContain('Email Update Verification');
        });
    });

    describe('Provider Email Change Notification', () => {
        it('should send email change notification with all expected content', async () => {
            await emailService.sendProviderEmailChangeNotification(
                'diet',
                'olduser@example.com',
                'newuser@example.com'
            );

            // Verify email was sent
            expect(mockSESClient).toHaveReceivedCommandWith(SendEmailCommand, {
                Destination: {
                    ToAddresses: ['olduser@example.com']
                },
                Content: {
                    Simple: {
                        Body: {
                            Html: {
                                Charset: 'UTF-8',
                                Data: expect.any(String)
                            }
                        },
                        Subject: {
                            Charset: 'UTF-8',
                            Data: 'Email Address Changed - CompactConnect'
                        }
                    }
                },
                FromEmailAddress: 'CompactConnect <noreply@example.org>'
            });

            // Get the actual HTML content for detailed validation
            const emailCall = mockSESClient.commandCalls(SendEmailCommand)[0];
            const htmlContent = emailCall.args[0].input.Content?.Simple?.Body?.Html?.Data;

            expect(htmlContent).toBeDefined();
            expect(htmlContent).toContain('Please use the new email address to login to your account from now on.');
            expect(htmlContent).toContain('If you did not make this change, please contact support immediately.');
            expect(htmlContent).toContain('Email Address Changed');
            expect(htmlContent).toContain('newuser@example.com');
        });
    });

    describe('Provider Account Recovery Confirmation', () => {
        it('should send account recovery confirmation email with all expected content', async () => {
            const providerId = 'provider-123';
            const recoveryToken = 'secure-recovery-token-abc123';

            await emailService.sendProviderAccountRecoveryConfirmationEmail(
                'diet',
                ['user@example.com'],
                providerId,
                recoveryToken
            );

            // Check overall email structure
            expect(mockSESClient).toHaveReceivedCommandWith(SendEmailCommand, {
                Destination: {
                    ToAddresses: ['user@example.com']
                },
                Content: {
                    Simple: {
                        Body: {
                            Html: {
                                Charset: 'UTF-8',
                                Data: expect.any(String)
                            }
                        },
                        Subject: {
                            Charset: 'UTF-8',
                            Data: 'Confirm Account Recovery - CompactConnect'
                        }
                    }
                },
                FromEmailAddress: 'CompactConnect <noreply@example.org>'
            });

            // Get the actual HTML content for detailed validation
            const emailCall = mockSESClient.commandCalls(SendEmailCommand)[0];
            const htmlContent = emailCall.args[0].input.Content?.Simple?.Body?.Html?.Data;

            expect(htmlContent).toBeDefined();
            expect(htmlContent).toContain('A request was made to recover access to your CompactConnect user account.');
            expect(htmlContent).toContain('If you initiated this request, please confirm by clicking the link below to continue account recovery.');
            expect(htmlContent).toContain('Confirm Account Recovery');

            // Verify recovery URL is correctly formatted (HTML encoded in email)
            const expectedRecoveryUrl = `https://app.test.compactconnect.org/Dashboard?bypass=recovery-practitioner&amp;compact=diet&amp;providerId=${providerId}&amp;recoveryId=${recoveryToken}`;

            expect(htmlContent).toContain(expectedRecoveryUrl);

            // Verify security warning text (HTML encoded)
            expect(htmlContent).toContain('<strong>If you did not request this, your password has likely been compromised and you should reset your password immediately</strong>');
            expect(htmlContent).toContain('https://app.test.compactconnect.org/Dashboard?bypass=login-practitioner');
            expect(htmlContent).toContain('Select \'Forgot your password?\' and follow the instructions');
        });

        it('should throw error when no recipients provided', async () => {
            await expect(emailService.sendProviderAccountRecoveryConfirmationEmail(
                'diet',
                [],
                'provider-123',
                'recovery-token'
            )).rejects.toThrow('No recipients found for provider account recovery confirmation email');
        });

        it('should throw error when recipients is undefined', async () => {
            await expect(emailService.sendProviderAccountRecoveryConfirmationEmail(
                'diet',
                undefined,
                'provider-123',
                'recovery-token'
            )).rejects.toThrow('No recipients found for provider account recovery confirmation email');
        });

        it('should include reset password URL in security warning', async () => {
            await emailService.sendProviderAccountRecoveryConfirmationEmail(
                'diet',
                ['user@example.com'],
                'provider-123',
                'recovery-token'
            );

            const emailCall = mockSESClient.commandCalls(SendEmailCommand)[0];
            const htmlContent = emailCall.args[0].input.Content?.Simple?.Body?.Html?.Data;

            // Verify reset password URL is present
            const expectedResetUrl = 'https://app.test.compactconnect.org/Dashboard?bypass=login-practitioner';

            expect(htmlContent).toContain(expectedResetUrl);
        });
    });

    describe('Home Jurisdiction Change State Notification', () => {
        it('should send home jurisdiction change state notification email with expected content', async () => {
            mockCompactConfigurationClient.getCompactConfiguration.mockResolvedValue(SAMPLE_COMPACT_CONFIG);
            mockJurisdictionClient.getJurisdictionConfiguration.mockResolvedValue(SAMPLE_JURISDICTION_CONFIG);

            await emailService.sendHomeJurisdictionChangeStateNotificationEmail(
                'diet',
                'oh',
                'John',
                'Doe',
                'provider-123',
                'TX',
                'OH'
            );

            expect(mockJurisdictionClient.getJurisdictionConfiguration).toHaveBeenCalledWith('diet', 'oh');

            expect(mockSESClient).toHaveReceivedCommandWith(
                SendEmailCommand,
                {
                    Destination: {
                        ToAddresses: ['oh-ops@example.com']
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
                                Data: 'Practitioner Home State Change - Dietitian'
                            }
                        }
                    },
                    FromEmailAddress: 'CompactConnect <noreply@example.org>'
                }
            );

            // Get the actual HTML content for detailed validation
            const emailCall = mockSESClient.commandCalls(SendEmailCommand)[0];
            const htmlContent = emailCall.args[0].input.Content?.Simple?.Body?.Html?.Data;

            expect(htmlContent).toBeDefined();
            expect(htmlContent).toContain('This is to notify you that John Doe has changed their home state from TX to OH.');
            expect(htmlContent).toContain('https://app.test.compactconnect.org/diet/Licensing/provider-123');
        });

        it('should throw error when no recipients found for jurisdiction', async () => {
            mockJurisdictionClient.getJurisdictionConfiguration.mockResolvedValue({
                ...SAMPLE_JURISDICTION_CONFIG,
                jurisdictionOperationsTeamEmails: []
            });

            await expect(emailService.sendHomeJurisdictionChangeStateNotificationEmail(
                'diet',
                'oh',
                'John',
                'Doe',
                'provider-123',
                'TX',
                'OH'
            )).rejects.toThrow('No recipients found for jurisdiction oh in compact diet');
        });

        it('should convert previous jurisdiction "other" to "an unlisted jurisdiction" in email content', async () => {
            mockCompactConfigurationClient.getCompactConfiguration.mockResolvedValue(SAMPLE_COMPACT_CONFIG);
            mockJurisdictionClient.getJurisdictionConfiguration.mockResolvedValue(SAMPLE_JURISDICTION_CONFIG);

            await emailService.sendHomeJurisdictionChangeStateNotificationEmail(
                'diet',
                'oh',
                'Jane',
                'Smith',
                'provider-456',
                'other',
                'OH'
            );

            const emailCall = mockSESClient.commandCalls(SendEmailCommand)[0];
            const htmlContent = emailCall.args[0].input.Content?.Simple?.Body?.Html?.Data;

            expect(htmlContent).toBeDefined();
            expect(htmlContent).toContain('This is to notify you that Jane Smith has changed their home state from an unlisted jurisdiction to OH.');
            expect(htmlContent).not.toContain('from other to OH');
        });

        it('should convert new jurisdiction "other" to "an unlisted jurisdiction" in email content', async () => {
            mockCompactConfigurationClient.getCompactConfiguration.mockResolvedValue(SAMPLE_COMPACT_CONFIG);
            mockJurisdictionClient.getJurisdictionConfiguration.mockResolvedValue(SAMPLE_JURISDICTION_CONFIG);

            await emailService.sendHomeJurisdictionChangeStateNotificationEmail(
                'diet',
                'oh',
                'Bob',
                'Johnson',
                'provider-789',
                'TX',
                'other'
            );

            const emailCall = mockSESClient.commandCalls(SendEmailCommand)[0];
            const htmlContent = emailCall.args[0].input.Content?.Simple?.Body?.Html?.Data;

            expect(htmlContent).toBeDefined();
            expect(htmlContent).toContain('This is to notify you that Bob Johnson has changed their home state from TX to an unlisted jurisdiction.');
            expect(htmlContent).not.toContain('from TX to other');
        });
    });

    describe('Privilege Expiration Reminder', () => {
        it('should send privilege expiration reminder email with expected subject and content', async () => {
            await emailService.sendPrivilegeExpirationReminderEmail(
                'diet',
                ['provider@example.com'],
                'John',
                '2026-02-16',
                [
                    {
                        jurisdiction: 'Ohio',
                        licenseType: 'dietitian',
                        privilegeId: 'DIET-OH-001',
                        dateOfExpiration: '2026-02-16',
                    },
                    {
                        jurisdiction: 'Kentucky',
                        licenseType: 'dietitian',
                        privilegeId: 'DIET-KY-002',
                        dateOfExpiration: '2026-03-01',
                    },
                ]
            );

            expect(mockSESClient).toHaveReceivedCommandWith(
                SendEmailCommand,
                {
                    Destination: {
                        ToAddresses: ['provider@example.com'],
                    },
                    Content: {
                        Simple: {
                            Body: {
                                Html: {
                                    Charset: 'UTF-8',
                                    Data: expect.stringContaining('Hi John,'),
                                },
                            },
                            Subject: {
                                Charset: 'UTF-8',
                                Data: 'Your CompactConnect Privileges Expire on February 16, 2026',
                            },
                        },
                    },
                    FromEmailAddress: 'CompactConnect <noreply@example.org>',
                }
            );

            const emailCall = mockSESClient.commandCalls(SendEmailCommand)[0];
            const htmlContent = emailCall.args[0].input.Content?.Simple?.Body?.Html?.Data;

            expect(htmlContent).toBeDefined();
            expect(htmlContent).toContain('Hi John,');
            expect(htmlContent).toContain('Your compact privilege(s) to practice expires on');
            expect(htmlContent).toContain('02/16/2026');
            expect(htmlContent).toContain('Ohio, dietitian');
            expect(htmlContent).toContain('#DIET-OH-001');
            expect(htmlContent).toContain('Kentucky, dietitian');
            expect(htmlContent).toContain('#DIET-KY-002');
            expect(htmlContent).toContain('03/01/2026');
            // Verify two-column table headers
            expect(htmlContent).toContain('Privilege');
            expect(htmlContent).toContain('Expires');
            // Verify dashboard link is present so user can navigate to CompactConnect
            expect(htmlContent).toContain('https://app.test.compactconnect.org/Dashboard');
            expect(htmlContent).toMatch(/<a[^>]+href=["']https:\/\/app\.test\.compactconnect\.org\/Dashboard["'][^>]*>/);
        });

        it('should throw error when no recipients provided', async () => {
            await expect(
                emailService.sendPrivilegeExpirationReminderEmail(
                    'diet',
                    [],
                    'John',
                    '2026-02-16',
                    [
                        {
                            jurisdiction: 'Ohio',
                            licenseType: 'diet',
                            privilegeId: 'DIET-OH-001',
                            dateOfExpiration: '2026-02-16',
                        },
                    ]
                )
            ).rejects.toThrow('No recipients found for privilege expiration reminder email');
        });

        it('should throw error when no privileges provided', async () => {
            await expect(
                emailService.sendPrivilegeExpirationReminderEmail(
                    'diet',
                    ['provider@example.com'],
                    'John',
                    '2026-02-16',
                    []
                )
            ).rejects.toThrow('No privileges provided for privilege expiration reminder email');
        });

        it('should send email with single privilege', async () => {
            await emailService.sendPrivilegeExpirationReminderEmail(
                'diet',
                ['provider@example.com'],
                'Jane',
                '2026-03-01',
                [
                    {
                        jurisdiction: 'Nebraska',
                        licenseType: 'dietitian',
                        privilegeId: 'DIET-NE-123',
                        dateOfExpiration: '2026-03-01',
                    },
                ]
            );

            const emailCall = mockSESClient.commandCalls(SendEmailCommand)[0];
            const htmlContent = emailCall.args[0].input.Content?.Simple?.Body?.Html?.Data;

            expect(htmlContent).toBeDefined();
            expect(htmlContent).toContain('Hi Jane,');
            expect(htmlContent).toContain('Your compact privilege(s) to practice expires on');
            expect(htmlContent).toContain('03/01/2026');
            expect(htmlContent).toContain('Nebraska, dietitian');
            expect(htmlContent).toContain('#DIET-NE-123');
            expect(htmlContent).toContain('https://app.test.compactconnect.org/Dashboard');
        });
    });
});
