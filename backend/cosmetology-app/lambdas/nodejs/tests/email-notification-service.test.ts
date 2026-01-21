import { mockClient } from 'aws-sdk-client-mock';
import 'aws-sdk-client-mock-jest';
import { DynamoDBClient, GetItemCommand } from '@aws-sdk/client-dynamodb';
import { SESv2Client, SendEmailCommand } from '@aws-sdk/client-sesv2';
import { Lambda } from '../email-notification-service/lambda';
import { EmailNotificationEvent } from '../lib/models/email-notification-service-event';
import { describe, it, beforeAll, beforeEach, jest } from '@jest/globals';

const SAMPLE_EVENT: EmailNotificationEvent = {
    template: 'transactionBatchSettlementFailure',
    recipientType: 'COMPACT_OPERATIONS_TEAM',
    compact: 'cosm',
    templateVariables: {}
};

const SAMPLE_COMPACT_CONFIGURATION = {
    'pk': { S: 'cosm#CONFIGURATION' },
    'sk': { S: 'cosm#CONFIGURATION' },
    'compactAdverseActionsNotificationEmails': { L: [{ S: 'adverse@example.com' }]},
    'compactCommissionFee': {
        M: {
            'feeAmount': { N: '3.5' },
            'feeType': { S: 'FLAT_RATE' }
        }
    },
    'compactAbbr': { S: 'cosm' },
    'compactName': { S: 'Audiology and Speech Language Pathology' },
    'compactOperationsTeamEmails': { L: [{ S: 'operations@example.com' }]},
    'compactSummaryReportNotificationEmails': { L: [{ S: 'summary@example.com' }]},
    'dateOfUpdate': { S: '2024-12-10T19:27:28+00:00' },
    'type': { S: 'compact' }
};

const SAMPLE_JURISDICTION_CONFIGURATION = {
    'pk': { S: 'cosm#CONFIGURATION' },
    'sk': { S: 'cosm#JURISDICTION#oh' },
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
    mock as unknown as SESv2Client;

describe('EmailNotificationServiceLambda', () => {
    let lambda: Lambda;
    let mockDynamoDBClient: ReturnType<typeof mockClient>;
    let mockSESClient: ReturnType<typeof mockClient>;

    beforeAll(async () => {
        process.env.DEBUG = 'true';
        process.env.COMPACT_CONFIGURATION_TABLE_NAME = 'compact-table';
        process.env.AWS_REGION = 'us-east-1';
    });

    beforeEach(() => {
        jest.clearAllMocks();
        mockDynamoDBClient = mockClient(DynamoDBClient);
        mockSESClient = mockClient(SESv2Client);

        // Reset environment variables
        process.env.FROM_ADDRESS = 'noreply@example.org';
        process.env.UI_BASE_PATH_URL = 'https://app.test.compactconnect.org';
        process.env.TRANSACTION_REPORTS_BUCKET_NAME = 'test-transaction-reports-bucket';

        // Set up default successful responses
        mockDynamoDBClient.on(GetItemCommand).callsFake((input) => {
            const key = input.Key;

            if (key.sk.S === 'cosm#CONFIGURATION') {
                return Promise.resolve({
                    Item: SAMPLE_COMPACT_CONFIGURATION
                });
            } else if (key.sk.S === 'cosm#JURISDICTION#oh') {
                return Promise.resolve({
                    Item: SAMPLE_JURISDICTION_CONFIGURATION
                });
            }
            return Promise.resolve({});
        });

        mockSESClient.on(SendEmailCommand).resolves({
            MessageId: 'message-id-123'
        });

        // Note: SESv2 with nodemailer 7.0.7 uses SendEmailCommand for all email sending

        lambda = new Lambda({
            dynamoDBClient: asDynamoDBClient(mockDynamoDBClient),
            sesClient: asSESClient(mockSESClient)
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
            Content: {
                Simple: {
                    Body: {
                        Html: {
                            Charset: 'UTF-8',
                            Data: expect.stringContaining('A transaction settlement error was detected')
                        }
                    },
                    Subject: {
                        Charset: 'UTF-8',
                        Data: 'Transactions Failed to Settle for Audiology and Speech Language Pathology Payment Processor'
                    }
                }
            },
            FromEmailAddress: 'Compact Connect <noreply@example.org>'
        });
    });

    it('should include detailed error information for failed transactions', async () => {
        const eventWithFailedTransactions: EmailNotificationEvent = {
            ...SAMPLE_EVENT,
            templateVariables: {
                batchFailureErrorMessage: JSON.stringify({
                    message: 'Settlement errors detected in one or more transactions.',
                    failedTransactionIds: ['tx-123', 'tx-456', 'tx-789']
                })
            }
        };

        const response = await lambda.handler(eventWithFailedTransactions, {} as any);

        expect(response).toEqual({
            message: 'Email message sent'
        });

        // Get the actual HTML content for detailed validation
        const emailCall = mockSESClient.commandCalls(SendEmailCommand)[0];
        const htmlContent = emailCall.args[0].input.Content?.Simple?.Body?.Html?.Data;

        expect(htmlContent).toBeDefined();
        expect(htmlContent).toContain('A transaction settlement error was detected within the payment processing account for the compact.');
        expect(htmlContent).toContain('Please reach out to your payment processing representative if needed to determine the cause.');
        expect(htmlContent).toContain('Detailed Error Information:');
        expect(htmlContent).toContain('Error Message: Settlement errors detected in one or more transactions.');
        expect(htmlContent).toContain('Failed Transaction IDs: tx-123, tx-456, tx-789');
    });

    it('should include detailed error information for unsettled transactions', async () => {
        const eventWithUnsettledTransactions: EmailNotificationEvent = {
            ...SAMPLE_EVENT,
            templateVariables: {
                batchFailureErrorMessage: JSON.stringify({
                    message: 'One or more transactions have not settled in over 48 hours.',
                    unsettledTransactionIds: ['unsettled-tx-001', 'unsettled-tx-002']
                })
            }
        };

        const response = await lambda.handler(eventWithUnsettledTransactions, {} as any);

        expect(response).toEqual({
            message: 'Email message sent'
        });

        // Get the actual HTML content for detailed validation
        const emailCall = mockSESClient.commandCalls(SendEmailCommand)[0];
        const htmlContent = emailCall.args[0].input.Content?.Simple?.Body?.Html?.Data;

        expect(htmlContent).toBeDefined();
        expect(htmlContent).toContain('A transaction settlement error was detected within the payment processing account for the compact.');
        expect(htmlContent).toContain('Please reach out to your payment processing representative if needed to determine the cause.');
        expect(htmlContent).toContain('Detailed Error Information:');
        expect(htmlContent).toContain('Error Message: One or more transactions have not settled in over 48 hours.');
        expect(htmlContent).toContain('Unsettled Transaction IDs (older than 48 hours): unsettled-tx-001, unsettled-tx-002');
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

    describe('Privilege Deactivation Jurisdiction Notification', () => {
        const SAMPLE_PRIVILEGE_DEACTIVATION_JURISDICTION_NOTIFICATION_EVENT: EmailNotificationEvent = {
            template: 'privilegeDeactivationJurisdictionNotification',
            recipientType: 'JURISDICTION_SUMMARY_REPORT',
            compact: 'cosm',
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
                    'pk': { S: 'cosm#CONFIGURATION' },
                    'sk': { S: 'cosm#JURISDICTION#oh' }
                }
            });

            // Verify email was sent with correct parameters
            expect(mockSESClient).toHaveReceivedCommandWith(SendEmailCommand, {
                Destination: {
                    ToAddresses: ['ohio@example.com']
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
                            Data: 'A Privilege was Deactivated in the Audiology and Speech Language Pathology Compact'
                        }
                    }
                },
                FromEmailAddress: 'Compact Connect <noreply@example.org>'
            }
            );
        });
    });

    describe('License Encumbrance Provider Notification', () => {
        const SAMPLE_LICENSE_ENCUMBRANCE_PROVIDER_NOTIFICATION_EVENT: EmailNotificationEvent = {
            template: 'licenseEncumbranceProviderNotification',
            recipientType: 'SPECIFIC',
            compact: 'cosm',
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
                Content: {
                    Simple: {
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
                    }
                },
                FromEmailAddress: 'Compact Connect <noreply@example.org>'
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
            compact: 'cosm',
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
                'pk': { S: 'cosm#CONFIGURATION' },
                'sk': { S: 'cosm#JURISDICTION#ca' },
                'jurisdictionName': { S: 'California' },
                'jurisdictionAdverseActionsNotificationEmails': { L: [{ S: 'ca-adverse@example.com' }]},
                'type': { S: 'jurisdiction' }
            };

            mockDynamoDBClient.on(GetItemCommand).callsFake((input) => {
                if (input.Key.sk.S === 'cosm#JURISDICTION#ca') {
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
                Content: {
                    Simple: {
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
                    }
                },
                FromEmailAddress: 'Compact Connect <noreply@example.org>'
            });
        });

        it('should include provider detail link with correct environment URL', async () => {
            const mockJurisdictionConfig = {
                'pk': { S: 'cosm#CONFIGURATION' },
                'sk': { S: 'cosm#JURISDICTION#ca' },
                'jurisdictionAdverseActionsNotificationEmails': { L: [{ S: 'ca-adverse@example.com' }]},
                'type': { S: 'jurisdiction' }
            };

            mockDynamoDBClient.on(GetItemCommand).callsFake((input) => {
                if (input.Key.sk.S === 'cosm#JURISDICTION#ca') {
                    return Promise.resolve({ Item: mockJurisdictionConfig });
                }
                return Promise.resolve({ Item: SAMPLE_COMPACT_CONFIGURATION });
            });

            await lambda.handler(SAMPLE_LICENSE_ENCUMBRANCE_STATE_NOTIFICATION_EVENT, {} as any);

            const emailData = mockSESClient.commandCalls(
                SendEmailCommand)[0].args[0].input.Content?.Simple?.Body?.Html?.Data;

            expect(emailData).toContain('Provider Details: <a href="https://app.test.compactconnect.org/cosm/Licensing/provider-123" target="_blank">https://app.test.compactconnect.org/cosm/Licensing/provider-123</a>');
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
            compact: 'cosm',
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
                Content: {
                    Simple: {
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
                    }
                },
                FromEmailAddress: 'Compact Connect <noreply@example.org>'
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
            compact: 'cosm',
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
                'pk': { S: 'cosm#CONFIGURATION' },
                'sk': { S: 'cosm#JURISDICTION#ca' },
                'jurisdictionAdverseActionsNotificationEmails': { L: [{ S: 'ca-adverse@example.com' }]},
                'type': { S: 'jurisdiction' }
            };

            mockDynamoDBClient.on(GetItemCommand).callsFake((input) => {
                if (input.Key.sk.S === 'cosm#JURISDICTION#ca') {
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
                Content: {
                    Simple: {
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
                    }
                },
                FromEmailAddress: 'Compact Connect <noreply@example.org>'
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
            compact: 'cosm',
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
                Content: {
                    Simple: {
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
                    }
                },
                FromEmailAddress: 'Compact Connect <noreply@example.org>'
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
            compact: 'cosm',
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
                'pk': { S: 'cosm#CONFIGURATION' },
                'sk': { S: 'cosm#JURISDICTION#ca' },
                'jurisdictionAdverseActionsNotificationEmails': { L: [{ S: 'ca-adverse@example.com' }]},
                'type': { S: 'jurisdiction' }
            };

            mockDynamoDBClient.on(GetItemCommand).callsFake((input) => {
                if (input.Key.sk.S === 'cosm#JURISDICTION#ca') {
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
                Content: {
                    Simple: {
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
                    }
                },
                FromEmailAddress: 'Compact Connect <noreply@example.org>'
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
            compact: 'cosm',
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
                Content: {
                    Simple: {
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
                    }
                },
                FromEmailAddress: 'Compact Connect <noreply@example.org>'
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
            compact: 'cosm',
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
                'pk': { S: 'cosm#CONFIGURATION' },
                'sk': { S: 'cosm#JURISDICTION#ca' },
                'jurisdictionAdverseActionsNotificationEmails': { L: [{ S: 'ca-adverse@example.com' }]},
                'type': { S: 'jurisdiction' }
            };

            mockDynamoDBClient.on(GetItemCommand).callsFake((input) => {
                if (input.Key.sk.S === 'cosm#JURISDICTION#ca') {
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
                Content: {
                    Simple: {
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
                    }},
                FromEmailAddress: 'Compact Connect <noreply@example.org>'
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

    describe('License Investigation State Notification', () => {
        const SAMPLE_LICENSE_INVESTIGATION_STATE_NOTIFICATION_EVENT: EmailNotificationEvent = {
            template: 'licenseInvestigationStateNotification',
            recipientType: 'JURISDICTION_ADVERSE_ACTIONS',
            compact: 'cosm',
            jurisdiction: 'ca',
            templateVariables: {
                providerFirstName: 'John',
                providerLastName: 'Doe',
                providerId: 'provider-123',
                investigationJurisdiction: 'OH',
                licenseType: 'Audiologist'
            }
        };

        it('should successfully send license investigation state notification email', async () => {
            const mockCaJurisdictionConfig = {
                'pk': { S: 'cosm#CONFIGURATION' },
                'sk': { S: 'cosm#JURISDICTION#ca' },
                'jurisdictionAdverseActionsNotificationEmails': { L: [{ S: 'ca-adverse@example.com' }]},
                'type': { S: 'jurisdiction' }
            };

            const mockOhJurisdictionConfig = {
                'pk': { S: 'cosm#CONFIGURATION' },
                'sk': { S: 'cosm#JURISDICTION#oh' },
                'jurisdictionName': { S: 'Ohio' },
                'type': { S: 'jurisdiction' }
            };

            mockDynamoDBClient.on(GetItemCommand).callsFake((input) => {
                if (input.Key.sk.S === 'cosm#JURISDICTION#ca') {
                    return Promise.resolve({ Item: mockCaJurisdictionConfig });
                } else if (input.Key.sk.S === 'cosm#JURISDICTION#oh') {
                    return Promise.resolve({ Item: mockOhJurisdictionConfig });
                }
                return Promise.resolve({ Item: SAMPLE_COMPACT_CONFIGURATION });
            });

            const response = await lambda.handler(SAMPLE_LICENSE_INVESTIGATION_STATE_NOTIFICATION_EVENT, {} as any);

            expect(response).toEqual({
                message: 'Email message sent'
            });

            expect(mockSESClient).toHaveReceivedCommandWith(SendEmailCommand, {
                Destination: {
                    ToAddresses: ['ca-adverse@example.com']
                },
                Content: {
                    Simple: {
                        Body: {
                            Html: {
                                Charset: 'UTF-8',
                                Data: expect.stringContaining('John Doe holding Audiologist license in Ohio is under investigation')
                            }
                        },
                        Subject: {
                            Charset: 'UTF-8',
                            Data: 'John Doe holding Audiologist license in Ohio is under investigation'
                        }
                    }
                },
                FromEmailAddress: 'Compact Connect <noreply@example.org>'
            });
        });

        it('should throw error when jurisdiction is missing', async () => {
            const eventWithMissingJurisdiction: EmailNotificationEvent = {
                ...SAMPLE_LICENSE_INVESTIGATION_STATE_NOTIFICATION_EVENT,
                jurisdiction: undefined
            };

            await expect(lambda.handler(eventWithMissingJurisdiction, {} as any))
                .rejects
                .toThrow('No jurisdiction provided for license investigation state notification email');
        });

        it('should throw error when required template variables are missing', async () => {
            const eventWithMissingVariables: EmailNotificationEvent = {
                ...SAMPLE_LICENSE_INVESTIGATION_STATE_NOTIFICATION_EVENT,
                templateVariables: {}
            };

            await expect(lambda.handler(eventWithMissingVariables, {} as any))
                .rejects
                .toThrow('Missing required template variables for licenseInvestigationStateNotification template.');
        });
    });

    describe('License Investigation Closed State Notification', () => {
        const SAMPLE_LICENSE_INVESTIGATION_CLOSED_STATE_NOTIFICATION_EVENT: EmailNotificationEvent = {
            template: 'licenseInvestigationClosedStateNotification',
            recipientType: 'JURISDICTION_ADVERSE_ACTIONS',
            compact: 'cosm',
            jurisdiction: 'ca',
            templateVariables: {
                providerFirstName: 'John',
                providerLastName: 'Doe',
                providerId: 'provider-123',
                investigationJurisdiction: 'OH',
                licenseType: 'Audiologist'
            }
        };

        it('should successfully send license investigation closed state notification email', async () => {
            const mockCaJurisdictionConfig = {
                'pk': { S: 'cosm#CONFIGURATION' },
                'sk': { S: 'cosm#JURISDICTION#ca' },
                'jurisdictionAdverseActionsNotificationEmails': { L: [{ S: 'ca-adverse@example.com' }]},
                'type': { S: 'jurisdiction' }
            };

            const mockOhJurisdictionConfig = {
                'pk': { S: 'cosm#CONFIGURATION' },
                'sk': { S: 'cosm#JURISDICTION#oh' },
                'jurisdictionName': { S: 'Ohio' },
                'type': { S: 'jurisdiction' }
            };

            mockDynamoDBClient.on(GetItemCommand).callsFake((input) => {
                if (input.Key.sk.S === 'cosm#JURISDICTION#ca') {
                    return Promise.resolve({ Item: mockCaJurisdictionConfig });
                } else if (input.Key.sk.S === 'cosm#JURISDICTION#oh') {
                    return Promise.resolve({ Item: mockOhJurisdictionConfig });
                }
                return Promise.resolve({ Item: SAMPLE_COMPACT_CONFIGURATION });
            });

            const response = await lambda.handler(
                SAMPLE_LICENSE_INVESTIGATION_CLOSED_STATE_NOTIFICATION_EVENT, {} as any
            );

            expect(response).toEqual({
                message: 'Email message sent'
            });

            expect(mockSESClient).toHaveReceivedCommandWith(SendEmailCommand, {
                Destination: {
                    ToAddresses: ['ca-adverse@example.com']
                },
                Content: {
                    Simple: {
                        Body: {
                            Html: {
                                Charset: 'UTF-8',
                                Data: expect.stringContaining('Investigation on John Doe')
                            }
                        },
                        Subject: {
                            Charset: 'UTF-8',
                            Data: expect.stringMatching(/Investigation on John Doe.s Audiologist license in Ohio has been closed/)
                        }
                    }
                },
                FromEmailAddress: 'Compact Connect <noreply@example.org>'
            });
        });

        it('should throw error when jurisdiction is missing', async () => {
            const eventWithMissingJurisdiction: EmailNotificationEvent = {
                ...SAMPLE_LICENSE_INVESTIGATION_CLOSED_STATE_NOTIFICATION_EVENT,
                jurisdiction: undefined
            };

            await expect(lambda.handler(eventWithMissingJurisdiction, {} as any))
                .rejects
                .toThrow('No jurisdiction provided for license investigation closed state notification email');
        });

        it('should throw error when required template variables are missing', async () => {
            const eventWithMissingVariables: EmailNotificationEvent = {
                ...SAMPLE_LICENSE_INVESTIGATION_CLOSED_STATE_NOTIFICATION_EVENT,
                templateVariables: {}
            };

            await expect(lambda.handler(eventWithMissingVariables, {} as any))
                .rejects
                .toThrow('Missing required template variables for licenseInvestigationClosedStateNotification template.');
        });
    });

    describe('Privilege Investigation State Notification', () => {
        const SAMPLE_PRIVILEGE_INVESTIGATION_STATE_NOTIFICATION_EVENT: EmailNotificationEvent = {
            template: 'privilegeInvestigationStateNotification',
            recipientType: 'JURISDICTION_ADVERSE_ACTIONS',
            compact: 'cosm',
            jurisdiction: 'ca',
            templateVariables: {
                providerFirstName: 'John',
                providerLastName: 'Doe',
                providerId: 'provider-123',
                investigationJurisdiction: 'OH',
                licenseType: 'Audiologist'
            }
        };

        it('should successfully send privilege investigation state notification email', async () => {
            const mockCaJurisdictionConfig = {
                'pk': { S: 'cosm#CONFIGURATION' },
                'sk': { S: 'cosm#JURISDICTION#ca' },
                'jurisdictionAdverseActionsNotificationEmails': { L: [{ S: 'ca-adverse@example.com' }]},
                'type': { S: 'jurisdiction' }
            };

            const mockOhJurisdictionConfig = {
                'pk': { S: 'cosm#CONFIGURATION' },
                'sk': { S: 'cosm#JURISDICTION#oh' },
                'jurisdictionName': { S: 'Ohio' },
                'type': { S: 'jurisdiction' }
            };

            mockDynamoDBClient.on(GetItemCommand).callsFake((input) => {
                if (input.Key.sk.S === 'cosm#JURISDICTION#ca') {
                    return Promise.resolve({ Item: mockCaJurisdictionConfig });
                } else if (input.Key.sk.S === 'cosm#JURISDICTION#oh') {
                    return Promise.resolve({ Item: mockOhJurisdictionConfig });
                }
                return Promise.resolve({ Item: SAMPLE_COMPACT_CONFIGURATION });
            });

            const response = await lambda.handler(SAMPLE_PRIVILEGE_INVESTIGATION_STATE_NOTIFICATION_EVENT, {} as any);

            expect(response).toEqual({
                message: 'Email message sent'
            });

            expect(mockSESClient).toHaveReceivedCommandWith(SendEmailCommand, {
                Destination: {
                    ToAddresses: ['ca-adverse@example.com']
                },
                Content: {
                    Simple: {
                        Body: {
                            Html: {
                                Charset: 'UTF-8',
                                Data: expect.stringContaining('John Doe holding Audiologist privilege in Ohio is under investigation')
                            }
                        },
                        Subject: {
                            Charset: 'UTF-8',
                            Data: 'John Doe holding Audiologist privilege in Ohio is under investigation'
                        }
                    }
                },
                FromEmailAddress: 'Compact Connect <noreply@example.org>'
            });
        });

        it('should throw error when jurisdiction is missing', async () => {
            const eventWithMissingJurisdiction: EmailNotificationEvent = {
                ...SAMPLE_PRIVILEGE_INVESTIGATION_STATE_NOTIFICATION_EVENT,
                jurisdiction: undefined
            };

            await expect(lambda.handler(eventWithMissingJurisdiction, {} as any))
                .rejects
                .toThrow('No jurisdiction provided for privilege investigation state notification email');
        });

        it('should throw error when required template variables are missing', async () => {
            const eventWithMissingVariables: EmailNotificationEvent = {
                ...SAMPLE_PRIVILEGE_INVESTIGATION_STATE_NOTIFICATION_EVENT,
                templateVariables: {}
            };

            await expect(lambda.handler(eventWithMissingVariables, {} as any))
                .rejects
                .toThrow('Missing required template variables for privilegeInvestigationStateNotification template.');
        });
    });

    describe('Privilege Investigation Closed State Notification', () => {
        const SAMPLE_PRIVILEGE_INVESTIGATION_CLOSED_STATE_NOTIFICATION_EVENT: EmailNotificationEvent = {
            template: 'privilegeInvestigationClosedStateNotification',
            recipientType: 'JURISDICTION_ADVERSE_ACTIONS',
            compact: 'cosm',
            jurisdiction: 'ca',
            templateVariables: {
                providerFirstName: 'John',
                providerLastName: 'Doe',
                providerId: 'provider-123',
                investigationJurisdiction: 'OH',
                licenseType: 'Audiologist'
            }
        };

        it('should successfully send privilege investigation closed state notification email', async () => {
            const mockCaJurisdictionConfig = {
                'pk': { S: 'cosm#CONFIGURATION' },
                'sk': { S: 'cosm#JURISDICTION#ca' },
                'jurisdictionAdverseActionsNotificationEmails': { L: [{ S: 'ca-adverse@example.com' }]},
                'type': { S: 'jurisdiction' }
            };

            const mockOhJurisdictionConfig = {
                'pk': { S: 'cosm#CONFIGURATION' },
                'sk': { S: 'cosm#JURISDICTION#oh' },
                'jurisdictionName': { S: 'Ohio' },
                'type': { S: 'jurisdiction' }
            };

            mockDynamoDBClient.on(GetItemCommand).callsFake((input) => {
                if (input.Key.sk.S === 'cosm#JURISDICTION#ca') {
                    return Promise.resolve({ Item: mockCaJurisdictionConfig });
                } else if (input.Key.sk.S === 'cosm#JURISDICTION#oh') {
                    return Promise.resolve({ Item: mockOhJurisdictionConfig });
                }
                return Promise.resolve({ Item: SAMPLE_COMPACT_CONFIGURATION });
            });

            const response = await lambda.handler(
                SAMPLE_PRIVILEGE_INVESTIGATION_CLOSED_STATE_NOTIFICATION_EVENT, {} as any
            );

            expect(response).toEqual({
                message: 'Email message sent'
            });

            expect(mockSESClient).toHaveReceivedCommandWith(SendEmailCommand, {
                Destination: {
                    ToAddresses: ['ca-adverse@example.com']
                },
                Content: {
                    Simple: {
                        Body: {
                            Html: {
                                Charset: 'UTF-8',
                                Data: expect.stringContaining('Investigation on John Doe')
                            }
                        },
                        Subject: {
                            Charset: 'UTF-8',
                            Data: expect.stringMatching(/Investigation on John Doe.s Audiologist privilege in Ohio has been closed/)
                        }
                    }
                },
                FromEmailAddress: 'Compact Connect <noreply@example.org>'
            });
        });

        it('should throw error when jurisdiction is missing', async () => {
            const eventWithMissingJurisdiction: EmailNotificationEvent = {
                ...SAMPLE_PRIVILEGE_INVESTIGATION_CLOSED_STATE_NOTIFICATION_EVENT,
                jurisdiction: undefined
            };

            await expect(lambda.handler(eventWithMissingJurisdiction, {} as any))
                .rejects
                .toThrow('No jurisdiction provided for privilege investigation closed state notification email');
        });

        it('should throw error when required template variables are missing', async () => {
            const eventWithMissingVariables: EmailNotificationEvent = {
                ...SAMPLE_PRIVILEGE_INVESTIGATION_CLOSED_STATE_NOTIFICATION_EVENT,
                templateVariables: {}
            };

            await expect(lambda.handler(eventWithMissingVariables, {} as any))
                .rejects
                .toThrow('Missing required template variables for privilegeInvestigationClosedStateNotification template.');
        });
    });
});
