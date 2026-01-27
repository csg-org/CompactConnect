import { mockClient } from 'aws-sdk-client-mock';
import 'aws-sdk-client-mock-jest';
import { Logger } from '@aws-lambda-powertools/logger';
import { SendEmailCommand, SESv2Client } from '@aws-sdk/client-sesv2';
import * as nodemailer from 'nodemailer';
import { EmailNotificationService } from '../../../lib/email';
import { CompactConfigurationClient } from '../../../lib/compact-configuration-client';
import { JurisdictionClient } from '../../../lib/jurisdiction-client';
import { EmailTemplateCapture } from '../../utils/email-template-capture';
import { TReaderDocument } from '@csg-org/email-builder';
import { describe, it, beforeEach, beforeAll, afterAll, jest } from '@jest/globals';

jest.mock('nodemailer');

const SAMPLE_COMPACT_CONFIG = {
    pk: 'cosm#CONFIGURATION',
    sk: 'cosm#CONFIGURATION',
    compactAdverseActionsNotificationEmails: ['adverse@example.com'],
    compactCommissionFee: {
        feeAmount: 3.5,
        feeType: 'FLAT_RATE'
    },
    compactAbbr: 'cosm',
    compactName: 'Audiology and Speech Language Pathology',
    compactOperationsTeamEmails: ['operations@example.com'],
    compactSummaryReportNotificationEmails: ['summary@example.com'],
    dateOfUpdate: '2024-12-10T19:27:28+00:00',
    type: 'compact'
};

const SAMPLE_JURISDICTION_CONFIG = {
    pk: 'cosm#CONFIGURATION',
    sk: 'cosm#JURISDICTION#OH',
    jurisdictionName: 'Ohio',
    postalAbbreviation: 'OH',
    compact: 'cosm',
    jurisdictionOperationsTeamEmails: ['oh-ops@example.com'],
    jurisdictionAdverseActionsNotificationEmails: ['oh-adverse@example.com'],
    jurisdictionSummaryReportNotificationEmails: ['oh-summary@example.com']
};

const asSESClient = (mock: ReturnType<typeof mockClient>) =>
    mock as unknown as SESv2Client;

const MOCK_TRANSPORT = {
    sendMail: jest.fn().mockImplementation(async () => ({ messageId: 'test-message-id' }))
};

describe('EmailNotificationService', () => {
    let emailService: EmailNotificationService;
    let mockSESClient: ReturnType<typeof mockClient>;
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
            compactConfigurationClient: mockCompactConfigurationClient,
            jurisdictionClient: mockJurisdictionClient
        });
    });

    describe('Transaction Batch Settlement Failure', () => {
        it('should send email using compact operations team emails', async () => {
            mockCompactConfigurationClient.getCompactConfiguration.mockResolvedValue(SAMPLE_COMPACT_CONFIG);

            await emailService.sendTransactionBatchSettlementFailureEmail(
                'cosm',
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
                                Data: 'Transactions Failed to Settle for Audiology and Speech Language Pathology Payment Processor'
                            }
                        }
                    },
                    FromEmailAddress: 'Compact Connect <noreply@example.org>'
                }
            );
        });

        it('should send email using specific emails', async () => {
            mockCompactConfigurationClient.getCompactConfiguration.mockResolvedValue(SAMPLE_COMPACT_CONFIG);

            await emailService.sendTransactionBatchSettlementFailureEmail(
                'cosm',
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
                                Data: 'Transactions Failed to Settle for Audiology and Speech Language Pathology Payment Processor'
                            }
                        }
                    },
                    FromEmailAddress: 'Compact Connect <noreply@example.org>'
                }
            );
        });

        it('should throw error when no recipients found', async () => {
            mockCompactConfigurationClient.getCompactConfiguration.mockResolvedValue({
                ...SAMPLE_COMPACT_CONFIG,
                compactOperationsTeamEmails: []
            });

            await expect(emailService.sendTransactionBatchSettlementFailureEmail(
                'cosm',
                'COMPACT_OPERATIONS_TEAM'
            )).rejects.toThrow('No recipients found for compact cosm with recipient type COMPACT_OPERATIONS_TEAM');
        });

        it('should throw error for specific recipient type without emails', async () => {
            await expect(emailService.sendTransactionBatchSettlementFailureEmail(
                'cosm',
                'SPECIFIC'
            )).rejects.toThrow('SPECIFIC recipientType requested but no specific email addresses provided');
        });

        it('should throw error for unsupported recipient type', async () => {
            await expect(emailService.sendTransactionBatchSettlementFailureEmail(
                'cosm',
                'JURISDICTION_OPERATIONS_TEAM'
            )).rejects.toThrow('Unsupported recipient type for compact configuration: JURISDICTION_OPERATIONS_TEAM');
        });

        it('should include logo in email', async () => {
            mockCompactConfigurationClient.getCompactConfiguration.mockResolvedValue(SAMPLE_COMPACT_CONFIG);

            await emailService.sendTransactionBatchSettlementFailureEmail(
                'cosm',
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
                                Data: 'Transactions Failed to Settle for Audiology and Speech Language Pathology Payment Processor'
                            }
                        }
                    },
                    FromEmailAddress: 'Compact Connect <noreply@example.org>'
                }
            );
        });
    });

    describe('Privilege Deactivation Jurisdiction Notification', () => {
        it('should send jurisdiction privilege deactivation notification email with expected subject', async () => {
            mockCompactConfigurationClient.getCompactConfiguration.mockResolvedValue(SAMPLE_COMPACT_CONFIG);
            mockJurisdictionClient.getJurisdictionConfiguration.mockResolvedValue(SAMPLE_JURISDICTION_CONFIG);

            await emailService.sendPrivilegeDeactivationJurisdictionNotificationEmail(
                'cosm',
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
                                Data: `A Privilege was Deactivated in the Audiology and Speech Language Pathology Compact`
                            }
                        }
                    },
                    FromEmailAddress: 'Compact Connect <noreply@example.org>'
                }
            );
        });

        it('should throw error when no recipients found for jurisdiction privilege deactivation notification email', async () => {
            mockJurisdictionClient.getJurisdictionConfiguration.mockResolvedValue({
                ...SAMPLE_JURISDICTION_CONFIG,
                jurisdictionSummaryReportNotificationEmails: []
            });

            await expect(emailService.sendPrivilegeDeactivationJurisdictionNotificationEmail(
                'cosm',
                'oh',
                'JURISDICTION_SUMMARY_REPORT',
                'some-privilege-id',
                'John',
                'Doe'
            )).rejects.toThrow('No recipients found for jurisdiction oh in compact cosm');
        });
    });
});
