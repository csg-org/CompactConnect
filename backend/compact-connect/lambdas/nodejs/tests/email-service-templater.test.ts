import { mockClient } from 'aws-sdk-client-mock';
import 'aws-sdk-client-mock-jest';
import { Logger } from '@aws-lambda-powertools/logger';
import { SendEmailCommand, SESClient } from '@aws-sdk/client-ses';
import { EmailServiceTemplater } from '../lib/email-service-templater';
import { CompactConfigurationClient } from '../lib/compact-configuration-client';

const SAMPLE_COMPACT_CONFIG = {
    pk: 'aslp#CONFIGURATION',
    sk: 'aslp#CONFIGURATION',
    compactAdverseActionsNotificationEmails: ['adverse@example.com'],
    compactCommissionFee: {
        feeAmount: 3.5,
        feeType: 'FLAT_RATE'
    },
    compactName: 'aslp',
    compactOperationsTeamEmails: ['operations@example.com'],
    compactSummaryReportNotificationEmails: ['summary@example.com'],
    dateOfUpdate: '2024-12-10T19:27:28+00:00',
    type: 'compact'
};

/*
 * Double casting to allow us to pass a mock in for the real thing
 */
const asSESClient = (mock: ReturnType<typeof mockClient>) =>
    mock as unknown as SESClient;

describe('EmailServiceTemplater', () => {
    let mockSESClient: ReturnType<typeof mockClient>;
    let mockCompactConfigurationClient: jest.Mocked<CompactConfigurationClient>;
    let emailServiceTemplater: EmailServiceTemplater;

    beforeAll(async () => {
        process.env.DEBUG = 'true';
        process.env.FROM_ADDRESS = 'noreply@example.org';
        process.env.UI_BASE_PATH_URL = 'https://app.test.compactconnect.org';
    });

    beforeEach(() => {
        jest.clearAllMocks();
        mockSESClient = mockClient(SESClient);
        mockCompactConfigurationClient = {
            getCompactConfiguration: jest.fn(),
        } as unknown as jest.Mocked<CompactConfigurationClient>;

        mockSESClient.on(SendEmailCommand).resolves({
            MessageId: 'message-id-123'
        });

        emailServiceTemplater = new EmailServiceTemplater({
            logger: new Logger(),
            sesClient: asSESClient(mockSESClient),
            compactConfigurationClient: mockCompactConfigurationClient
        });
    });

    describe('transactionBatchSettlementFailure', () => {
        it('should send email using compact operations team emails', async () => {
            mockCompactConfigurationClient.getCompactConfiguration.mockResolvedValue(SAMPLE_COMPACT_CONFIG);

            await emailServiceTemplater.sendTransactionBatchSettlementFailureEmail(
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
            await emailServiceTemplater.sendTransactionBatchSettlementFailureEmail(
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

            await expect(emailServiceTemplater.sendTransactionBatchSettlementFailureEmail(
                'aslp',
                'COMPACT_OPERATIONS_TEAM'
            )).rejects.toThrow('No recipients found for compact aslp with recipient type COMPACT_OPERATIONS_TEAM');
        });

        it('should throw error for specific recipient type without emails', async () => {
            await expect(emailServiceTemplater.sendTransactionBatchSettlementFailureEmail(
                'aslp',
                'SPECIFIC'
            )).rejects.toThrow('SPECIFIC recipientType requested but no specific email addresses provided');
        });

        it('should throw error for unsupported recipient type', async () => {
            await expect(emailServiceTemplater.sendTransactionBatchSettlementFailureEmail(
                'aslp',
                'JURISDICTION_OPERATIONS_TEAM'
            )).rejects.toThrow('Unsupported recipient type for compact configuration: JURISDICTION_OPERATIONS_TEAM');
        });

        it('should include logo in email', async () => {
            mockCompactConfigurationClient.getCompactConfiguration.mockResolvedValue(SAMPLE_COMPACT_CONFIG);

            await emailServiceTemplater.sendTransactionBatchSettlementFailureEmail(
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
});
