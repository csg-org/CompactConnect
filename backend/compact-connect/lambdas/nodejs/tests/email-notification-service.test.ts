import { mockClient } from 'aws-sdk-client-mock';
import 'aws-sdk-client-mock-jest';
import { DynamoDBClient, GetItemCommand } from '@aws-sdk/client-dynamodb';
import { SESClient, SendEmailCommand, SendRawEmailCommand } from '@aws-sdk/client-ses';
import { S3Client, GetObjectCommand } from '@aws-sdk/client-s3';
import { Readable } from 'stream';
import { sdkStreamMixin } from '@smithy/util-stream';
import { Lambda } from '../email-notification-service/lambda';
import { EmailNotificationEvent } from '../lib/models/email-notification-service-event';
import { describe, it, expect, beforeAll, beforeEach, jest } from '@jest/globals';

const SAMPLE_EVENT: EmailNotificationEvent = {
    template: 'transactionBatchSettlementFailure',
    recipientType: 'COMPACT_OPERATIONS_TEAM',
    compact: 'aslp',
    templateVariables: {}
};

const SAMPLE_COMPACT_CONFIGURATION = {
    'pk': { S: 'aslp#CONFIGURATION' },
    'sk': { S: 'aslp#CONFIGURATION' },
    'compactAdverseActionsNotificationEmails': { L: [{ S: 'adverse@example.com' }]},
    'compactCommissionFee': {
        M: {
            'feeAmount': { N: '3.5' },
            'feeType': { S: 'FLAT_RATE' }
        }
    },
    'compactAbbr': { S: 'aslp' },
    'compactName': { S: 'Audiology and Speech Language Pathology' },
    'compactOperationsTeamEmails': { L: [{ S: 'operations@example.com' }]},
    'compactSummaryReportNotificationEmails': { L: [{ S: 'summary@example.com' }]},
    'dateOfUpdate': { S: '2024-12-10T19:27:28+00:00' },
    'type': { S: 'compact' }
};

const SAMPLE_JURISDICTION_CONFIGURATION = {
    'pk': { S: 'aslp#CONFIGURATION' },
    'sk': { S: 'aslp#JURISDICTION#oh' },
    'jurisdictionName': { S: 'Ohio' },
    'jurisdictionSummaryReportNotificationEmails': { L: [{ S: 'ohio@example.com' }]},
    'type': { S: 'jurisdiction' }
};

/*
 * Double casting to allow us to pass a mock in for the real thing
 */
const asDynamoDBClient = (mock: ReturnType<typeof mockClient>) =>
    mock as unknown as DynamoDBClient;

const asSESClient = (mock: ReturnType<typeof mockClient>) =>
    mock as unknown as SESClient;

const asS3Client = (mock: ReturnType<typeof mockClient>) =>
    mock as unknown as S3Client;

describe('EmailNotificationServiceLambda', () => {
    let lambda: Lambda;
    let mockDynamoDBClient: ReturnType<typeof mockClient>;
    let mockSESClient: ReturnType<typeof mockClient>;
    let mockS3Client: ReturnType<typeof mockClient>;

    beforeAll(async () => {
        process.env.DEBUG = 'true';
        process.env.COMPACT_CONFIGURATION_TABLE_NAME = 'compact-table';
        process.env.AWS_REGION = 'us-east-1';
    });

    beforeEach(() => {
        jest.clearAllMocks();
        mockDynamoDBClient = mockClient(DynamoDBClient);
        mockSESClient = mockClient(SESClient);
        mockS3Client = mockClient(S3Client);

        // Reset environment variables
        process.env.FROM_ADDRESS = 'noreply@example.org';
        process.env.UI_BASE_PATH_URL = 'https://app.test.compactconnect.org';
        process.env.TRANSACTION_REPORTS_BUCKET_NAME = 'test-transaction-reports-bucket';

        // Set up default successful responses
        mockDynamoDBClient.on(GetItemCommand).callsFake((input) => {
            const key = input.Key;

            if (key.sk.S === 'aslp#CONFIGURATION') {
                return Promise.resolve({
                    Item: SAMPLE_COMPACT_CONFIGURATION
                });
            } else if (key.sk.S === 'aslp#JURISDICTION#oh') {
                return Promise.resolve({
                    Item: SAMPLE_JURISDICTION_CONFIGURATION
                });
            }
            return Promise.resolve({});
        });

        mockSESClient.on(SendEmailCommand).resolves({
            MessageId: 'message-id-123'
        });

        mockSESClient.on(SendRawEmailCommand).resolves({
            MessageId: 'message-id-raw'
        });

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

        lambda = new Lambda({
            dynamoDBClient: asDynamoDBClient(mockDynamoDBClient),
            sesClient: asSESClient(mockSESClient),
            s3Client: asS3Client(mockS3Client)
        });
    });

    it('should return early when FROM_ADDRESS is NONE', async () => {
        process.env.FROM_ADDRESS = 'NONE';

        const response = await lambda.handler(SAMPLE_EVENT, {} as any);

        expect(response).toEqual({
            message: 'No from address configured for environment, unable to send email'
        });

        // Verify no calls were made to DynamoDB or SES
        expect(mockDynamoDBClient).not.toHaveReceivedAnyCommand();
        expect(mockSESClient).not.toHaveReceivedAnyCommand();
    });

    it('should successfully send transaction batch settlement failure email', async () => {
        const response = await lambda.handler(SAMPLE_EVENT, {} as any);

        expect(response).toEqual({
            message: 'Email message sent'
        });

        // Verify DynamoDB was queried for compact configuration
        expect(mockDynamoDBClient).toHaveReceivedCommandWith(GetItemCommand, {
            TableName: 'compact-table',
            Key: {
                'pk': { S: 'aslp#CONFIGURATION' },
                'sk': { S: 'aslp#CONFIGURATION' }
            }
        });

        // Verify email was sent with correct parameters
        expect(mockSESClient).toHaveReceivedCommandWith(SendEmailCommand, {
            Destination: {
                ToAddresses: ['operations@example.com']
            },
            Message: {
                Body: {
                    Html: {
                        Charset: 'UTF-8',
                        Data: expect.stringContaining('A transaction settlement error was detected')
                    }
                },
                Subject: {
                    Charset: 'UTF-8',
                    Data: 'Transactions Failed to Settle for ASLP Payment Processor'
                }
            },
            Source: 'Compact Connect <noreply@example.org>'
        });
    });

    it('should throw error for unsupported template', async () => {
        const event: EmailNotificationEvent = {
            ...SAMPLE_EVENT,
            template: 'unsupportedTemplate'
        };

        await expect(lambda.handler(event, {} as any))
            .rejects
            .toThrow('Unsupported email template: unsupportedTemplate');

        // Verify no AWS calls were made
        expect(mockDynamoDBClient).not.toHaveReceivedAnyCommand();
        expect(mockSESClient).not.toHaveReceivedAnyCommand();
    });

    describe('Compact Transaction Report', () => {
        const SAMPLE_COMPACT_TRANSACTION_REPORT_EVENT: EmailNotificationEvent = {
            template: 'CompactTransactionReporting',
            recipientType: 'COMPACT_SUMMARY_REPORT',
            compact: 'aslp',
            templateVariables: {
                reportS3Path: 'compact/aslp/reports/test-report.zip',
                reportingCycle: 'weekly',
                startDate: '2024-03-01',
                endDate: '2024-03-07'
            }
        };

        it('should successfully send compact transaction report email', async () => {
            const response = await lambda.handler(SAMPLE_COMPACT_TRANSACTION_REPORT_EVENT, {} as any);

            expect(response).toEqual({
                message: 'Email message sent'
            });

            // Verify DynamoDB was queried for compact configuration
            expect(mockDynamoDBClient).toHaveReceivedCommandWith(GetItemCommand, {
                TableName: 'compact-table',
                Key: {
                    'pk': { S: 'aslp#CONFIGURATION' },
                    'sk': { S: 'aslp#CONFIGURATION' }
                }
            });

            // Verify S3 was queried for the report
            expect(mockS3Client).toHaveReceivedCommandWith(GetObjectCommand, {
                Bucket: 'test-transaction-reports-bucket',
                Key: 'compact/aslp/reports/test-report.zip'
            });

            // Verify email was sent with correct parameters
            expect(mockSESClient).toHaveReceivedCommandWith(SendRawEmailCommand, {
                RawMessage: {
                    Data: expect.any(Buffer)
                }
            });

            // Get the raw email data and verify it contains the attachments
            const rawEmailData = mockSESClient.commandCalls(SendRawEmailCommand)[0].args[0].input.RawMessage?.Data;

            expect(rawEmailData).toBeDefined();
            const rawEmailString = rawEmailData?.toString();

            expect(rawEmailString).toContain('Content-Type: application/zip;');
            expect(rawEmailString).toContain('name=aslp-settled-transaction-report-2024-03-01--2024-03-07.zip');
            expect(rawEmailString).toContain('Content-Disposition: attachment;');
            expect(rawEmailString).toContain('filename=aslp-settled-transaction-report-2024-03-01--2024-03-07.zip');
            expect(rawEmailString).toContain('Weekly Report for Compact ASLP');
            expect(rawEmailString).toContain('Please find attached the weekly settled');
            expect(rawEmailString).toContain('transaction reports for the compact for the period 2024-03-01 to');
            expect(rawEmailString).toContain('2024-03-07:</p>');
            expect(rawEmailString).toContain('To: summary@example.com');
        });

        it('should throw error when no recipients found', async () => {
            // Mock empty recipients list
            mockDynamoDBClient.on(GetItemCommand).resolves({
                Item: {
                    ...SAMPLE_COMPACT_CONFIGURATION,
                    compactSummaryReportNotificationEmails: { L: []}
                }
            });

            await expect(lambda.handler(SAMPLE_COMPACT_TRANSACTION_REPORT_EVENT, {} as any))
                .rejects
                .toThrow('No recipients found for compact aslp with recipient type COMPACT_SUMMARY_REPORT');
        });

        it('should throw error when required template variables are missing', async () => {
            const eventWithMissingVariables: EmailNotificationEvent = {
                ...SAMPLE_COMPACT_TRANSACTION_REPORT_EVENT,
                templateVariables: {}
            };

            await expect(lambda.handler(eventWithMissingVariables, {} as any))
                .rejects
                .toThrow('Missing required template variables for CompactTransactionReporting template');
        });

        it('should throw error when S3 fails to return compact report', async () => {
            mockS3Client.on(GetObjectCommand).resolves({
                Body: undefined
            });

            await expect(lambda.handler(SAMPLE_COMPACT_TRANSACTION_REPORT_EVENT, {} as any))
                .rejects
                .toThrow('Failed to retrieve report from S3: compact/aslp/reports/test-report.zip');
        });
    });

    describe('Jurisdiction Transaction Report', () => {
        const SAMPLE_JURISDICTION_TRANSACTION_REPORT_EVENT: EmailNotificationEvent = {
            template: 'JurisdictionTransactionReporting',
            recipientType: 'JURISDICTION_SUMMARY_REPORT',
            compact: 'aslp',
            jurisdiction: 'oh',
            templateVariables: {
                reportS3Path: 'compact/aslp/reports/jurisdiction-transactions/jurisdiction/oh/reporting-cycle/weekly/2024/03/07/transaction-report.zip',
                reportingCycle: 'weekly',
                startDate: '2024-03-01',
                endDate: '2024-03-07'
            }
        };

        it('should successfully send jurisdiction transaction report email', async () => {
            const response = await lambda.handler(SAMPLE_JURISDICTION_TRANSACTION_REPORT_EVENT, {} as any);

            expect(response).toEqual({
                message: 'Email message sent'
            });

            // Verify DynamoDB was queried for jurisdiction configuration
            expect(mockDynamoDBClient).toHaveReceivedCommandWith(GetItemCommand, {
                TableName: 'compact-table',
                Key: {
                    'pk': { S: 'aslp#CONFIGURATION' },
                    'sk': { S: 'aslp#JURISDICTION#oh' }
                }
            });

            // Verify S3 was queried for the report
            expect(mockS3Client).toHaveReceivedCommandWith(GetObjectCommand, {
                Bucket: 'test-transaction-reports-bucket',
                Key: 'compact/aslp/reports/jurisdiction-transactions/jurisdiction/oh/reporting-cycle/weekly/2024/03/07/transaction-report.zip'
            });

            // Verify email was sent with correct parameters
            expect(mockSESClient).toHaveReceivedCommandWith(SendRawEmailCommand, {
                RawMessage: {
                    Data: expect.any(Buffer)
                }
            });

            // Get the raw email data and verify it contains the attachments
            const rawEmailData = mockSESClient.commandCalls(SendRawEmailCommand)[0].args[0].input.RawMessage?.Data;

            expect(rawEmailData).toBeDefined();
            const rawEmailString = rawEmailData?.toString();

            expect(rawEmailString).toContain('Content-Type: application/zip;');
            expect(rawEmailString).toContain('name=oh-settled-transaction-report-2024-03-01--2024-03-07.zip');
            expect(rawEmailString).toContain('Content-Disposition: attachment;');
            expect(rawEmailString).toContain('filename=oh-settled-transaction-report-2024-03-01--2024-03-07.zip');
            expect(rawEmailString).toContain('Ohio Weekly Report for Compact ASLP');
            expect(rawEmailString).toContain('Please find attached the weekly settled');
            expect(rawEmailString).toContain('transaction report for your jurisdiction for the period 2024-03-01 to');
            expect(rawEmailString).toContain('2024-03-07.</div>');
            expect(rawEmailString).toContain('To: ohio@example.com');
        });

        it('should throw error when no recipients found', async () => {
            // Mock empty recipients list
            mockDynamoDBClient.on(GetItemCommand).resolves({
                Item: {
                    ...SAMPLE_JURISDICTION_CONFIGURATION,
                    jurisdictionSummaryReportNotificationEmails: { L: []}
                }
            });

            await expect(lambda.handler(SAMPLE_JURISDICTION_TRANSACTION_REPORT_EVENT, {} as any))
                .rejects
                .toThrow('No recipients found for jurisdiction oh in compact aslp');
        });

        it('should throw error when required template variables are missing', async () => {
            const eventWithMissingVariables: EmailNotificationEvent = {
                ...SAMPLE_JURISDICTION_TRANSACTION_REPORT_EVENT,
                templateVariables: {}
            };

            await expect(lambda.handler(eventWithMissingVariables, {} as any))
                .rejects
                .toThrow('Missing required template variables for JurisdictionTransactionReporting template');
        });

        it('should throw error when jurisdiction is missing', async () => {
            const eventWithMissingJurisdiction: EmailNotificationEvent = {
                ...SAMPLE_JURISDICTION_TRANSACTION_REPORT_EVENT,
                jurisdiction: undefined
            };

            await expect(lambda.handler(eventWithMissingJurisdiction, {} as any))
                .rejects
                .toThrow('Missing required jurisdiction field for JurisdictionTransactionReporting template');
        });

        it('should throw error when S3 fails to return jurisdiction report', async () => {
            mockS3Client.on(GetObjectCommand).resolves({
                Body: undefined
            });

            await expect(lambda.handler(SAMPLE_JURISDICTION_TRANSACTION_REPORT_EVENT, {} as any))
                .rejects
                .toThrow('Failed to retrieve report from S3: compact/aslp/reports/jurisdiction-transactions/jurisdiction/oh/reporting-cycle/weekly/2024/03/07/transaction-report.zip');
        });
    });

    describe('Privilege Deactivation Jurisdiction Notification', () => {
        const SAMPLE_PRIVILEGE_DEACTIVATION_JURISDICTION_NOTIFICATION_EVENT: EmailNotificationEvent = {
            template: 'privilegeDeactivationJurisdictionNotification',
            recipientType: 'JURISDICTION_SUMMARY_REPORT',
            compact: 'aslp',
            jurisdiction: 'oh',
            templateVariables: {
                privilegeId: '123',
                providerFirstName: 'John',
                providerLastName: 'Doe'
            }
        };

        it('should successfully send privilege deactivation jurisdiction notification email', async () => {
            const response = await lambda.handler(
                SAMPLE_PRIVILEGE_DEACTIVATION_JURISDICTION_NOTIFICATION_EVENT, {} as any);

            expect(response).toEqual({
                message: 'Email message sent'
            });

            // Verify DynamoDB was queried for jurisdiction configuration
            expect(mockDynamoDBClient).toHaveReceivedCommandWith(GetItemCommand, {
                TableName: 'compact-table',
                Key: {
                    'pk': { S: 'aslp#CONFIGURATION' },
                    'sk': { S: 'aslp#JURISDICTION#oh' }
                }
            });

            // Verify email was sent with correct parameters
            expect(mockSESClient).toHaveReceivedCommandWith(SendEmailCommand, {
                Destination: {
                    ToAddresses: ['ohio@example.com']
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
                        Data: 'A Privilege was Deactivated in the ASLP Compact'
                    }
                },
                Source: 'Compact Connect <noreply@example.org>'
            });
        });
    });

    describe('Privilege Deactivation Provider Notification', () => {
        const SAMPLE_PRIVILEGE_DEACTIVATION_PROVIDER_NOTIFICATION_EVENT: EmailNotificationEvent = {
            template: 'privilegeDeactivationProviderNotification',
            recipientType: 'SPECIFIC',
            compact: 'aslp',
            specificEmails: ['specific@example.com'],
            templateVariables: {
                privilegeId: '123',
            }
        };

        it('should successfully send privilege deactivation provider notification email', async () => {
            const response = await lambda.handler(SAMPLE_PRIVILEGE_DEACTIVATION_PROVIDER_NOTIFICATION_EVENT, {} as any);

            expect(response).toEqual({
                message: 'Email message sent'
            });

            // Verify email was sent with correct parameters
            expect(mockSESClient).toHaveReceivedCommandWith(SendEmailCommand, {
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
                        Data: 'Your Privilege 123 is Deactivated'
                    }
                },
                Source: 'Compact Connect <noreply@example.org>'
            });
        });

        it('should throw error when no recipients specified for provider privilege deactivation notification email', async () => {
            const eventWithMissingRecipients: EmailNotificationEvent = {
                ...SAMPLE_PRIVILEGE_DEACTIVATION_PROVIDER_NOTIFICATION_EVENT,
                recipientType: 'SPECIFIC',
                specificEmails: []
            };

            await expect(lambda.handler(eventWithMissingRecipients, {} as any))
                .rejects
                .toThrow('No recipients specified for provider privilege deactivation notification email');
        });
    });
    describe('Privilege Purchase Provider Notification', () => {
        const SAMPLE_PRIVILEGE_PURCHASE_PROVIDER_NOTIFICATION_EVENT: EmailNotificationEvent = {
            template: 'privilegePurchaseProviderNotification',
            recipientType: 'SPECIFIC',
            compact: 'aslp',
            specificEmails: ['provider@example.com'],
            templateVariables: {
                transactionDate: '12/12/2004',
                privileges: [
                    {
                        privilegeId: 'OTA-OH-019',
                        jurisdiction: 'OH',
                        licenseTypeAbbrev: 'OTA'
                    }
                ],
                totalCost: '45.0',
                costLineItems: [
                    {
                        name: 'OH OTA fee', quantity: '2', unitPrice: '45'
                    },
                    {
                        name: 'cc fees', quantity: '1', unitPrice: '3.5'
                    }
                ]
            }
        };

        it('should successfully send privilege purchase provider notification email', async () => {
            const response = await lambda.handler(SAMPLE_PRIVILEGE_PURCHASE_PROVIDER_NOTIFICATION_EVENT, {} as any);

            expect(response).toEqual({
                message: 'Email message sent'
            });

            // Verify email was sent with correct parameters
            expect(mockSESClient).toHaveReceivedCommandWith(SendEmailCommand, {
                Destination: {
                    ToAddresses: ['provider@example.com']
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
                        Data: 'Compact Connect Privilege Purchase Confirmation'
                    }
                },
                Source: 'Compact Connect <noreply@example.org>'
            });
        });

        it('should throw error when no recipients found', async () => {
            // Mock empty recipients list
            SAMPLE_PRIVILEGE_PURCHASE_PROVIDER_NOTIFICATION_EVENT.specificEmails = [];

            await expect(lambda.handler(SAMPLE_PRIVILEGE_PURCHASE_PROVIDER_NOTIFICATION_EVENT, {} as any))
                .rejects
                .toThrow('No recipients found');
        });
    });

    describe('Multiple Registration Attempt Notification', () => {
        const SAMPLE_MULTIPLE_REGISTRATION_ATTEMPT_NOTIFICATION_EVENT: EmailNotificationEvent = {
            template: 'multipleRegistrationAttemptNotification',
            recipientType: 'SPECIFIC',
            compact: 'aslp',
            specificEmails: ['user@example.com'],
            templateVariables: {}
        };

        it('should successfully send multiple registration attempt notification email', async () => {
            const response = await lambda.handler(SAMPLE_MULTIPLE_REGISTRATION_ATTEMPT_NOTIFICATION_EVENT, {} as any);

            expect(response).toEqual({
                message: 'Email message sent'
            });

            // Verify email was sent with correct parameters
            expect(mockSESClient).toHaveReceivedCommandWith(SendEmailCommand, {
                Destination: {
                    ToAddresses: ['user@example.com']
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
                        Data: 'Registration Attempt Notification - Compact Connect'
                    }
                },
                Source: 'Compact Connect <noreply@example.org>'
            });
        });

        it('should throw error when no recipients found', async () => {
            const eventWithNoRecipients: EmailNotificationEvent = {
                ...SAMPLE_MULTIPLE_REGISTRATION_ATTEMPT_NOTIFICATION_EVENT,
                specificEmails: []
            };

            await expect(lambda.handler(eventWithNoRecipients, {} as any))
                .rejects
                .toThrow('No recipients found for multiple registration attempt notification email');
        });
    });

    describe('License Encumbrance Provider Notification', () => {
        const SAMPLE_LICENSE_ENCUMBRANCE_PROVIDER_NOTIFICATION_EVENT: EmailNotificationEvent = {
            template: 'licenseEncumbranceProviderNotification',
            recipientType: 'SPECIFIC',
            compact: 'aslp',
            specificEmails: ['provider@example.com'],
            templateVariables: {
                providerFirstName: 'John',
                providerLastName: 'Doe',
                encumberedJurisdiction: 'OH',
                licenseType: 'Audiologist',
                effectiveStartDate: 'January 15, 2024'
            }
        };

        it('should successfully send license encumbrance provider notification email', async () => {
            const response = await lambda.handler(SAMPLE_LICENSE_ENCUMBRANCE_PROVIDER_NOTIFICATION_EVENT, {} as any);

            expect(response).toEqual({
                message: 'Email message sent'
            });

            expect(mockSESClient).toHaveReceivedCommandWith(SendEmailCommand, {
                Destination: {
                    ToAddresses: ['provider@example.com']
                },
                Message: {
                    Body: {
                        Html: {
                            Charset: 'UTF-8',
                            Data: expect.stringContaining('Your Audiologist license in Ohio is encumbered')
                        }
                    },
                    Subject: {
                        Charset: 'UTF-8',
                        Data: 'Your Audiologist license in Ohio is encumbered'
                    }
                },
                Source: 'Compact Connect <noreply@example.org>'
            });
        });

        it('should throw error when required template variables are missing', async () => {
            const eventWithMissingVariables: EmailNotificationEvent = {
                ...SAMPLE_LICENSE_ENCUMBRANCE_PROVIDER_NOTIFICATION_EVENT,
                templateVariables: {}
            };

            await expect(lambda.handler(eventWithMissingVariables, {} as any))
                .rejects
                .toThrow('Missing required template variables for licenseEncumbranceProviderNotification template.');
        });
    });

    describe('License Encumbrance State Notification', () => {
        const SAMPLE_LICENSE_ENCUMBRANCE_STATE_NOTIFICATION_EVENT: EmailNotificationEvent = {
            template: 'licenseEncumbranceStateNotification',
            recipientType: 'JURISDICTION_ADVERSE_ACTIONS',
            compact: 'aslp',
            jurisdiction: 'ca',
            templateVariables: {
                providerFirstName: 'John',
                providerLastName: 'Doe',
                providerId: 'provider-123',
                encumberedJurisdiction: 'OH',
                licenseType: 'Audiologist',
                effectiveStartDate: 'January 15, 2024'
            }
        };

        it('should successfully send license encumbrance state notification email', async () => {
            const mockJurisdictionConfig = {
                'pk': { S: 'aslp#CONFIGURATION' },
                'sk': { S: 'aslp#JURISDICTION#ca' },
                'jurisdictionName': { S: 'California' },
                'jurisdictionAdverseActionsNotificationEmails': { L: [{ S: 'ca-adverse@example.com' }]},
                'type': { S: 'jurisdiction' }
            };

            mockDynamoDBClient.on(GetItemCommand).callsFake((input) => {
                if (input.Key.sk.S === 'aslp#JURISDICTION#ca') {
                    return Promise.resolve({ Item: mockJurisdictionConfig });
                }
                return Promise.resolve({ Item: SAMPLE_COMPACT_CONFIGURATION });
            });

            const response = await lambda.handler(SAMPLE_LICENSE_ENCUMBRANCE_STATE_NOTIFICATION_EVENT, {} as any);

            expect(response).toEqual({
                message: 'Email message sent'
            });

            expect(mockSESClient).toHaveReceivedCommandWith(SendEmailCommand, {
                Destination: {
                    ToAddresses: ['ca-adverse@example.com']
                },
                Message: {
                    Body: {
                        Html: {
                            Charset: 'UTF-8',
                            Data: expect.stringContaining('License Encumbrance Notification - John Doe')
                        }
                    },
                    Subject: {
                        Charset: 'UTF-8',
                        Data: 'License Encumbrance Notification - John Doe'
                    }
                },
                Source: 'Compact Connect <noreply@example.org>'
            });
        });

        it('should include provider detail link with correct environment URL', async () => {
            const mockJurisdictionConfig = {
                'pk': { S: 'aslp#CONFIGURATION' },
                'sk': { S: 'aslp#JURISDICTION#ca' },
                'jurisdictionAdverseActionsNotificationEmails': { L: [{ S: 'ca-adverse@example.com' }]},
                'type': { S: 'jurisdiction' }
            };

            mockDynamoDBClient.on(GetItemCommand).callsFake((input) => {
                if (input.Key.sk.S === 'aslp#JURISDICTION#ca') {
                    return Promise.resolve({ Item: mockJurisdictionConfig });
                }
                return Promise.resolve({ Item: SAMPLE_COMPACT_CONFIGURATION });
            });

            await lambda.handler(SAMPLE_LICENSE_ENCUMBRANCE_STATE_NOTIFICATION_EVENT, {} as any);

            const emailData = mockSESClient.commandCalls(SendEmailCommand)[0].args[0].input.Message?.Body?.Html?.Data;

            expect(emailData).toContain('Provider Details: https://app.test.compactconnect.org/aslp/Licensing/provider-123');
        });

        it('should throw error when required template variables are missing', async () => {
            const eventWithMissingVariables: EmailNotificationEvent = {
                ...SAMPLE_LICENSE_ENCUMBRANCE_STATE_NOTIFICATION_EVENT,
                templateVariables: {}
            };

            await expect(lambda.handler(eventWithMissingVariables, {} as any))
                .rejects
                .toThrow('Missing required template variables for licenseEncumbranceStateNotification template.');
        });

        it('should throw error when jurisdiction is missing', async () => {
            const eventWithMissingJurisdiction: EmailNotificationEvent = {
                ...SAMPLE_LICENSE_ENCUMBRANCE_STATE_NOTIFICATION_EVENT,
                jurisdiction: undefined
            };

            await expect(lambda.handler(eventWithMissingJurisdiction, {} as any))
                .rejects
                .toThrow('Missing required jurisdiction field for licenseEncumbranceStateNotification template.');
        });
    });

    describe('License Encumbrance Lifting Provider Notification', () => {
        const SAMPLE_LICENSE_ENCUMBRANCE_LIFTING_PROVIDER_NOTIFICATION_EVENT: EmailNotificationEvent = {
            template: 'licenseEncumbranceLiftingProviderNotification',
            recipientType: 'SPECIFIC',
            compact: 'aslp',
            specificEmails: ['provider@example.com'],
            templateVariables: {
                providerFirstName: 'John',
                providerLastName: 'Doe',
                liftedJurisdiction: 'OH',
                licenseType: 'Audiologist',
                effectiveLiftDate: 'February 15, 2024'
            }
        };

        it('should successfully send license encumbrance lifting provider notification email', async () => {
            const response = await lambda.handler(
                SAMPLE_LICENSE_ENCUMBRANCE_LIFTING_PROVIDER_NOTIFICATION_EVENT, {} as any
            );

            expect(response).toEqual({
                message: 'Email message sent'
            });

            expect(mockSESClient).toHaveReceivedCommandWith(SendEmailCommand, {
                Destination: {
                    ToAddresses: ['provider@example.com']
                },
                Message: {
                    Body: {
                        Html: {
                            Charset: 'UTF-8',
                            Data: expect.stringContaining('Your Audiologist license in Ohio is no longer encumbered')
                        }
                    },
                    Subject: {
                        Charset: 'UTF-8',
                        Data: 'Your Audiologist license in Ohio is no longer encumbered'
                    }
                },
                Source: 'Compact Connect <noreply@example.org>'
            });
        });

        it('should throw error when required template variables are missing', async () => {
            const eventWithMissingVariables: EmailNotificationEvent = {
                ...SAMPLE_LICENSE_ENCUMBRANCE_LIFTING_PROVIDER_NOTIFICATION_EVENT,
                templateVariables: {}
            };

            await expect(lambda.handler(eventWithMissingVariables, {} as any))
                .rejects
                .toThrow('Missing required template variables for licenseEncumbranceLiftingProviderNotification template.');
        });
    });

    describe('License Encumbrance Lifting State Notification', () => {
        const SAMPLE_LICENSE_ENCUMBRANCE_LIFTING_STATE_NOTIFICATION_EVENT: EmailNotificationEvent = {
            template: 'licenseEncumbranceLiftingStateNotification',
            recipientType: 'JURISDICTION_ADVERSE_ACTIONS',
            compact: 'aslp',
            jurisdiction: 'ca',
            templateVariables: {
                providerFirstName: 'John',
                providerLastName: 'Doe',
                providerId: 'provider-123',
                liftedJurisdiction: 'OH',
                licenseType: 'Audiologist',
                effectiveLiftDate: 'February 15, 2024'
            }
        };

        it('should successfully send license encumbrance lifting state notification email', async () => {
            const mockJurisdictionConfig = {
                'pk': { S: 'aslp#CONFIGURATION' },
                'sk': { S: 'aslp#JURISDICTION#ca' },
                'jurisdictionAdverseActionsNotificationEmails': { L: [{ S: 'ca-adverse@example.com' }]},
                'type': { S: 'jurisdiction' }
            };

            mockDynamoDBClient.on(GetItemCommand).callsFake((input) => {
                if (input.Key.sk.S === 'aslp#JURISDICTION#ca') {
                    return Promise.resolve({ Item: mockJurisdictionConfig });
                }
                return Promise.resolve({ Item: SAMPLE_COMPACT_CONFIGURATION });
            });

            const response = await lambda.handler(
                SAMPLE_LICENSE_ENCUMBRANCE_LIFTING_STATE_NOTIFICATION_EVENT, {} as any
            );

            expect(response).toEqual({
                message: 'Email message sent'
            });

            expect(mockSESClient).toHaveReceivedCommandWith(SendEmailCommand, {
                Destination: {
                    ToAddresses: ['ca-adverse@example.com']
                },
                Message: {
                    Body: {
                        Html: {
                            Charset: 'UTF-8',
                            Data: expect.stringContaining('License Encumbrance Lifted Notification - John Doe')
                        }
                    },
                    Subject: {
                        Charset: 'UTF-8',
                        Data: 'License Encumbrance Lifted Notification - John Doe'
                    }
                },
                Source: 'Compact Connect <noreply@example.org>'
            });
        });

        it('should throw error when required template variables are missing', async () => {
            const eventWithMissingVariables: EmailNotificationEvent = {
                ...SAMPLE_LICENSE_ENCUMBRANCE_LIFTING_STATE_NOTIFICATION_EVENT,
                templateVariables: {}
            };

            await expect(lambda.handler(eventWithMissingVariables, {} as any))
                .rejects
                .toThrow('Missing required template variables for licenseEncumbranceLiftingStateNotification template.');
        });

        it('should throw error when jurisdiction is missing', async () => {
            const eventWithMissingJurisdiction: EmailNotificationEvent = {
                ...SAMPLE_LICENSE_ENCUMBRANCE_LIFTING_STATE_NOTIFICATION_EVENT,
                jurisdiction: undefined
            };

            await expect(lambda.handler(eventWithMissingJurisdiction, {} as any))
                .rejects
                .toThrow('Missing required jurisdiction field for licenseEncumbranceLiftingStateNotification template.');
        });
    });

    describe('Privilege Encumbrance Provider Notification', () => {
        const SAMPLE_PRIVILEGE_ENCUMBRANCE_PROVIDER_NOTIFICATION_EVENT: EmailNotificationEvent = {
            template: 'privilegeEncumbranceProviderNotification',
            recipientType: 'SPECIFIC',
            compact: 'aslp',
            specificEmails: ['provider@example.com'],
            templateVariables: {
                providerFirstName: 'John',
                providerLastName: 'Doe',
                encumberedJurisdiction: 'OH',
                licenseType: 'Audiologist',
                effectiveStartDate: 'January 15, 2024'
            }
        };

        it('should successfully send privilege encumbrance provider notification email', async () => {
            const response = await lambda.handler(SAMPLE_PRIVILEGE_ENCUMBRANCE_PROVIDER_NOTIFICATION_EVENT, {} as any);

            expect(response).toEqual({
                message: 'Email message sent'
            });

            expect(mockSESClient).toHaveReceivedCommandWith(SendEmailCommand, {
                Destination: {
                    ToAddresses: ['provider@example.com']
                },
                Message: {
                    Body: {
                        Html: {
                            Charset: 'UTF-8',
                            Data: expect.stringContaining('Your Audiologist privilege in Ohio is encumbered')
                        }
                    },
                    Subject: {
                        Charset: 'UTF-8',
                        Data: 'Your Audiologist privilege in Ohio is encumbered'
                    }
                },
                Source: 'Compact Connect <noreply@example.org>'
            });
        });

        it('should throw error when required template variables are missing', async () => {
            const eventWithMissingVariables: EmailNotificationEvent = {
                ...SAMPLE_PRIVILEGE_ENCUMBRANCE_PROVIDER_NOTIFICATION_EVENT,
                templateVariables: {}
            };

            await expect(lambda.handler(eventWithMissingVariables, {} as any))
                .rejects
                .toThrow('Missing required template variables for privilegeEncumbranceProviderNotification template.');
        });
    });

    describe('Privilege Encumbrance State Notification', () => {
        const SAMPLE_PRIVILEGE_ENCUMBRANCE_STATE_NOTIFICATION_EVENT: EmailNotificationEvent = {
            template: 'privilegeEncumbranceStateNotification',
            recipientType: 'JURISDICTION_ADVERSE_ACTIONS',
            compact: 'aslp',
            jurisdiction: 'ca',
            templateVariables: {
                providerFirstName: 'John',
                providerLastName: 'Doe',
                providerId: 'provider-123',
                encumberedJurisdiction: 'OH',
                licenseType: 'Audiologist',
                effectiveStartDate: 'January 15, 2024'
            }
        };

        it('should successfully send privilege encumbrance state notification email', async () => {
            const mockJurisdictionConfig = {
                'pk': { S: 'aslp#CONFIGURATION' },
                'sk': { S: 'aslp#JURISDICTION#ca' },
                'jurisdictionAdverseActionsNotificationEmails': { L: [{ S: 'ca-adverse@example.com' }]},
                'type': { S: 'jurisdiction' }
            };

            mockDynamoDBClient.on(GetItemCommand).callsFake((input) => {
                if (input.Key.sk.S === 'aslp#JURISDICTION#ca') {
                    return Promise.resolve({ Item: mockJurisdictionConfig });
                }
                return Promise.resolve({ Item: SAMPLE_COMPACT_CONFIGURATION });
            });

            const response = await lambda.handler(SAMPLE_PRIVILEGE_ENCUMBRANCE_STATE_NOTIFICATION_EVENT, {} as any);

            expect(response).toEqual({
                message: 'Email message sent'
            });

            expect(mockSESClient).toHaveReceivedCommandWith(SendEmailCommand, {
                Destination: {
                    ToAddresses: ['ca-adverse@example.com']
                },
                Message: {
                    Body: {
                        Html: {
                            Charset: 'UTF-8',
                            Data: expect.stringContaining('Privilege Encumbrance Notification - John Doe')
                        }
                    },
                    Subject: {
                        Charset: 'UTF-8',
                        Data: 'Privilege Encumbrance Notification - John Doe'
                    }
                },
                Source: 'Compact Connect <noreply@example.org>'
            });
        });

        it('should throw error when required template variables are missing', async () => {
            const eventWithMissingVariables: EmailNotificationEvent = {
                ...SAMPLE_PRIVILEGE_ENCUMBRANCE_STATE_NOTIFICATION_EVENT,
                templateVariables: {}
            };

            await expect(lambda.handler(eventWithMissingVariables, {} as any))
                .rejects
                .toThrow('Missing required template variables for privilegeEncumbranceStateNotification template.');
        });

        it('should throw error when jurisdiction is missing', async () => {
            const eventWithMissingJurisdiction: EmailNotificationEvent = {
                ...SAMPLE_PRIVILEGE_ENCUMBRANCE_STATE_NOTIFICATION_EVENT,
                jurisdiction: undefined
            };

            await expect(lambda.handler(eventWithMissingJurisdiction, {} as any))
                .rejects
                .toThrow('Missing required jurisdiction field for privilegeEncumbranceStateNotification template.');
        });
    });

    describe('Privilege Encumbrance Lifting Provider Notification', () => {
        const SAMPLE_PRIVILEGE_ENCUMBRANCE_LIFTING_PROVIDER_NOTIFICATION_EVENT: EmailNotificationEvent = {
            template: 'privilegeEncumbranceLiftingProviderNotification',
            recipientType: 'SPECIFIC',
            compact: 'aslp',
            specificEmails: ['provider@example.com'],
            templateVariables: {
                providerFirstName: 'John',
                providerLastName: 'Doe',
                liftedJurisdiction: 'OH',
                licenseType: 'Audiologist',
                effectiveLiftDate: 'February 15, 2024'
            }
        };

        it('should successfully send privilege encumbrance lifting provider notification email', async () => {
            const response = await lambda.handler(
                SAMPLE_PRIVILEGE_ENCUMBRANCE_LIFTING_PROVIDER_NOTIFICATION_EVENT, {} as any
            );

            expect(response).toEqual({
                message: 'Email message sent'
            });

            expect(mockSESClient).toHaveReceivedCommandWith(SendEmailCommand, {
                Destination: {
                    ToAddresses: ['provider@example.com']
                },
                Message: {
                    Body: {
                        Html: {
                            Charset: 'UTF-8',
                            Data: expect.stringContaining('Your Audiologist privilege in Ohio is no longer encumbered')
                        }
                    },
                    Subject: {
                        Charset: 'UTF-8',
                        Data: 'Your Audiologist privilege in Ohio is no longer encumbered'
                    }
                },
                Source: 'Compact Connect <noreply@example.org>'
            });
        });

        it('should throw error when required template variables are missing', async () => {
            const eventWithMissingVariables: EmailNotificationEvent = {
                ...SAMPLE_PRIVILEGE_ENCUMBRANCE_LIFTING_PROVIDER_NOTIFICATION_EVENT,
                templateVariables: {}
            };

            await expect(lambda.handler(eventWithMissingVariables, {} as any))
                .rejects
                .toThrow('Missing required template variables for privilegeEncumbranceLiftingProviderNotification template.');
        });
    });

    describe('Privilege Encumbrance Lifting State Notification', () => {
        const SAMPLE_PRIVILEGE_ENCUMBRANCE_LIFTING_STATE_NOTIFICATION_EVENT: EmailNotificationEvent = {
            template: 'privilegeEncumbranceLiftingStateNotification',
            recipientType: 'JURISDICTION_ADVERSE_ACTIONS',
            compact: 'aslp',
            jurisdiction: 'ca',
            templateVariables: {
                providerFirstName: 'John',
                providerLastName: 'Doe',
                providerId: 'provider-123',
                liftedJurisdiction: 'OH',
                licenseType: 'Audiologist',
                effectiveLiftDate: 'February 15, 2024'
            }
        };

        it('should successfully send privilege encumbrance lifting state notification email', async () => {
            const mockJurisdictionConfig = {
                'pk': { S: 'aslp#CONFIGURATION' },
                'sk': { S: 'aslp#JURISDICTION#ca' },
                'jurisdictionAdverseActionsNotificationEmails': { L: [{ S: 'ca-adverse@example.com' }]},
                'type': { S: 'jurisdiction' }
            };

            mockDynamoDBClient.on(GetItemCommand).callsFake((input) => {
                if (input.Key.sk.S === 'aslp#JURISDICTION#ca') {
                    return Promise.resolve({ Item: mockJurisdictionConfig });
                }
                return Promise.resolve({ Item: SAMPLE_COMPACT_CONFIGURATION });
            });

            const response = await lambda.handler(
                SAMPLE_PRIVILEGE_ENCUMBRANCE_LIFTING_STATE_NOTIFICATION_EVENT, {} as any
            );

            expect(response).toEqual({
                message: 'Email message sent'
            });

            expect(mockSESClient).toHaveReceivedCommandWith(SendEmailCommand, {
                Destination: {
                    ToAddresses: ['ca-adverse@example.com']
                },
                Message: {
                    Body: {
                        Html: {
                            Charset: 'UTF-8',
                            Data: expect.stringContaining('Privilege Encumbrance Lifted Notification - John Doe')
                        }
                    },
                    Subject: {
                        Charset: 'UTF-8',
                        Data: 'Privilege Encumbrance Lifted Notification - John Doe'
                    }
                },
                Source: 'Compact Connect <noreply@example.org>'
            });
        });

        it('should throw error when required template variables are missing', async () => {
            const eventWithMissingVariables: EmailNotificationEvent = {
                ...SAMPLE_PRIVILEGE_ENCUMBRANCE_LIFTING_STATE_NOTIFICATION_EVENT,
                templateVariables: {}
            };

            await expect(lambda.handler(eventWithMissingVariables, {} as any))
                .rejects
                .toThrow('Missing required template variables for privilegeEncumbranceLiftingStateNotification template.');
        });

        it('should throw error when jurisdiction is missing', async () => {
            const eventWithMissingJurisdiction: EmailNotificationEvent = {
                ...SAMPLE_PRIVILEGE_ENCUMBRANCE_LIFTING_STATE_NOTIFICATION_EVENT,
                jurisdiction: undefined
            };

            await expect(lambda.handler(eventWithMissingJurisdiction, {} as any))
                .rejects
                .toThrow('Missing required jurisdiction field for privilegeEncumbranceLiftingStateNotification template.');
        });
    });
});
