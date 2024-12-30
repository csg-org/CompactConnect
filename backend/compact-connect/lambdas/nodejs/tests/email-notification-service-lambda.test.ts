import { mockClient } from 'aws-sdk-client-mock';
import 'aws-sdk-client-mock-jest';
import { DynamoDBClient, GetItemCommand } from '@aws-sdk/client-dynamodb';
import { SESClient, SendEmailCommand } from '@aws-sdk/client-ses';
import { Lambda } from '../email-notification-service/email-notification-service-lambda';
import { EmailNotificationEvent } from '../lib/models/email-notification-service-event';

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
    'compactName': { S: 'aslp' },
    'compactOperationsTeamEmails': { L: [{ S: 'operations@example.com' }]},
    'compactSummaryReportNotificationEmails': { L: [{ S: 'summary@example.com' }]},
    'dateOfUpdate': { S: '2024-12-10T19:27:28+00:00' },
    'type': { S: 'compact' }
};

/*
 * Double casting to allow us to pass a mock in for the real thing
 */
const asDynamoDBClient = (mock: ReturnType<typeof mockClient>) =>
    mock as unknown as DynamoDBClient;

const asSESClient = (mock: ReturnType<typeof mockClient>) =>
    mock as unknown as SESClient;

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
        mockSESClient = mockClient(SESClient);

        // Reset environment variables
        process.env.FROM_ADDRESS = 'noreply@example.org';
        process.env.UI_BASE_PATH_URL = 'https://app.test.compactconnect.org';

        // Set up default successful responses
        mockDynamoDBClient.on(GetItemCommand).resolves({
            Item: SAMPLE_COMPACT_CONFIGURATION
        });

        mockSESClient.on(SendEmailCommand).resolves({
            MessageId: 'message-id-123'
        });

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
});
