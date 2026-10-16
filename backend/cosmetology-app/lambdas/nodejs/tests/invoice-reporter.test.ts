import { BatchGetItemCommand, DynamoDBClient, GetItemCommand, QueryCommand } from '@aws-sdk/client-dynamodb';
import { SESv2Client } from '@aws-sdk/client-sesv2';
import { mockClient } from 'aws-sdk-client-mock';
import { Context } from 'aws-lambda';
import { afterEach, beforeAll, beforeEach, describe, expect, it, jest } from '@jest/globals';

import { Lambda } from '../invoice-reporter/lambda';
import {
    SAMPLE_COMPACT_CONFIGURATION,
    SAMPLE_GSI_LICENSE_UPLOAD_RECORD,
    SAMPLE_GSI_LICENSE_UPLOAD_RECORD_ESTHETICIAN,
    SAMPLE_JURISDICTION_CONFIGURATION,
    SAMPLE_JURISDICTION_CONFIGURATION_KY,
    SAMPLE_LICENSE_RECORD_ESTHETICIAN,
    SAMPLE_LICENSE_RECORD_NEW
} from './sample-records';

const asDynamoDBClient = (mock: ReturnType<typeof mockClient>) =>
    mock as unknown as DynamoDBClient;
const asSESClient = (mock: ReturnType<typeof mockClient>) =>
    mock as unknown as SESv2Client;

const mockSendInvoiceEmail = jest.fn<(
    report: { licenseType: string; billingMonth?: string; totalBillable?: number; totalOwed?: number },
    recipients: string[]
) => Promise<string>>().mockImplementation(
    () => Promise.resolve('message-id-123')
);

jest.mock('../lib/email/invoice-email-service', () => {
    return {
        InvoiceEmailService: jest.fn().mockImplementation(() => ({
            sendInvoiceEmail: mockSendInvoiceEmail,
        })),
    };
});

const SAMPLE_CONTEXT: Context = {
    callbackWaitsForEmptyEventLoop: true,
    functionVersion: '$LATEST',
    functionName: 'invoice-reporter',
    memoryLimitInMB: '128',
    logGroupName: '/aws/lambda/invoice-reporter',
    logStreamName: '2024/10/02/[$LATEST]abcdef',
    invokedFunctionArn: 'arn:aws:lambda:us-east-1:123456789012:function:invoice-reporter',
    awsRequestId: 'c6af9ac6-7b61-11e6-9a41-93e812345678',
    getRemainingTimeInMillis: () => 1234,
    done: () => undefined,
    fail: () => undefined,
    succeed: () => undefined,
};

const COMPACT_OPS_EMAILS = ['compact-ops@example.com'];

describe('Invoice reporter', () => {
    let mockDynamoDBClient: ReturnType<typeof mockClient>;
    let mockSESClient: ReturnType<typeof mockClient>;

    beforeAll(() => {
        process.env.DEBUG = 'true';
        process.env.COMPACTS = '["cosm"]';
        process.env.PROVIDER_TABLE_NAME = 'provider-table';
        process.env.COMPACT_CONFIGURATION_TABLE_NAME = 'compact-table';
        process.env.FEE_PER_LICENSE = '25';
        process.env.FROM_ADDRESS = 'noreply@example.org';
        process.env.AWS_REGION = 'us-east-1';
    });

    beforeEach(() => {
        jest.clearAllMocks();
        jest.useFakeTimers();
        jest.setSystemTime(new Date('2024-10-02T12:00:00.000Z'));
        mockSESClient = mockClient(SESv2Client);
        mockDynamoDBClient = mockClient(DynamoDBClient);
    });

    afterEach(() => {
        jest.useRealTimers();
    });

    const lambda = () => new Lambda({
        dynamoDBClient: asDynamoDBClient(mockDynamoDBClient),
        sesClient: asSESClient(mockSESClient),
    });

    const gsiQueries = () => mockDynamoDBClient.commandCalls(QueryCommand).filter(
        (call) => call.args[0].input.IndexName === 'licenseUploadDateGSI'
    );

    const mockCompactAndJurisdictions = (
        jurisdictions: object[] = [SAMPLE_JURISDICTION_CONFIGURATION]
    ) => {
        mockDynamoDBClient.on(GetItemCommand).resolves({
            Item: SAMPLE_COMPACT_CONFIGURATION,
        });
        mockDynamoDBClient.on(QueryCommand).callsFake((input) => {
            if (input.TableName === 'compact-table') {
                return Promise.resolve({ Items: jurisdictions });
            }
            if (input.TableName === 'provider-table' && input.IndexName === 'licenseUploadDateGSI') {
                const partitionKey = input.ExpressionAttributeValues?.[':pk']?.S;

                if (partitionKey === 'C#cosm#J#oh#D#2024-09') {
                    return Promise.resolve({
                        Items: [SAMPLE_GSI_LICENSE_UPLOAD_RECORD, SAMPLE_GSI_LICENSE_UPLOAD_RECORD_ESTHETICIAN],
                    });
                }
                return Promise.resolve({ Items: []});
            }
            return Promise.reject(new Error(`Unexpected query ${JSON.stringify(input)}`));
        });
        mockDynamoDBClient.on(BatchGetItemCommand).resolves({
            Responses: {
                'provider-table': [SAMPLE_LICENSE_RECORD_NEW, SAMPLE_LICENSE_RECORD_ESTHETICIAN],
            },
        });
    };

    describe('Monthly invoice run', () => {
        it('should send one invoice email per license type', async () => {
            mockCompactAndJurisdictions();

            await lambda().handler({ eventType: 'monthly' }, SAMPLE_CONTEXT);

            expect(mockSendInvoiceEmail).toHaveBeenCalledTimes(2);
            expect(mockSendInvoiceEmail.mock.calls.map((call) => call[0].licenseType).sort()).toEqual([
                'cosmetologist',
                'esthetician',
            ]);
        });

        it('should bill the previous calendar month when the event does not name one', async () => {
            mockCompactAndJurisdictions();

            await lambda().handler({ eventType: 'monthly' }, SAMPLE_CONTEXT);

            expect(gsiQueries().map((call) => call.args[0].input.ExpressionAttributeValues?.[':pk']?.S)).toContain(
                'C#cosm#J#oh#D#2024-09'
            );
        });

        it('should query every configured jurisdiction', async () => {
            mockCompactAndJurisdictions([
                SAMPLE_JURISDICTION_CONFIGURATION,
                SAMPLE_JURISDICTION_CONFIGURATION_KY,
            ]);

            await lambda().handler({ eventType: 'monthly' }, SAMPLE_CONTEXT);

            expect(gsiQueries().map((call) => call.args[0].input.ExpressionAttributeValues?.[':pk']?.S).sort())
                .toEqual([
                    'C#cosm#J#ky#D#2024-09',
                    'C#cosm#J#oh#D#2024-09',
                ]);
        });

        it('should send both invoices to the compact operations team', async () => {
            mockCompactAndJurisdictions();

            await lambda().handler({ eventType: 'monthly' }, SAMPLE_CONTEXT);

            expect(mockSendInvoiceEmail).toHaveBeenNthCalledWith(
                1,
                expect.objectContaining({ billingMonth: '2024-09' }),
                COMPACT_OPS_EMAILS
            );
            expect(mockSendInvoiceEmail).toHaveBeenNthCalledWith(
                2,
                expect.objectContaining({ billingMonth: '2024-09' }),
                COMPACT_OPS_EMAILS
            );
        });

        it('should skip the compact when its configuration is missing', async () => {
            mockDynamoDBClient.on(GetItemCommand).rejects(new Error('No configuration found for compact: cosm'));

            await expect(lambda().handler({ eventType: 'monthly' }, SAMPLE_CONTEXT)).resolves.toBeUndefined();
            expect(mockSendInvoiceEmail).not.toHaveBeenCalled();
        });

        it('should let DynamoDB errors escape', async () => {
            mockDynamoDBClient.on(GetItemCommand).resolves({ Item: SAMPLE_COMPACT_CONFIGURATION });
            mockDynamoDBClient.on(QueryCommand).rejects(new Error('DynamoDB error'));

            await expect(lambda().handler({ eventType: 'monthly' }, SAMPLE_CONTEXT)).rejects.toThrow('DynamoDB error');
        });

        it('should still send both invoices when no licenses are billable', async () => {
            mockDynamoDBClient.on(GetItemCommand).resolves({ Item: SAMPLE_COMPACT_CONFIGURATION });
            mockDynamoDBClient.on(QueryCommand).callsFake((input) => {
                if (input.TableName === 'compact-table') {
                    return Promise.resolve({ Items: [SAMPLE_JURISDICTION_CONFIGURATION]});
                }
                return Promise.resolve({ Items: []});
            });

            await lambda().handler({ eventType: 'monthly' }, SAMPLE_CONTEXT);

            expect(mockSendInvoiceEmail).toHaveBeenCalledTimes(2);
            expect(mockSendInvoiceEmail).toHaveBeenCalledWith(
                expect.objectContaining({
                    licenseType: 'cosmetologist',
                    totalBillable: 0,
                    totalOwed: 0,
                }),
                COMPACT_OPS_EMAILS
            );
            expect(mockSendInvoiceEmail).toHaveBeenCalledWith(
                expect.objectContaining({
                    licenseType: 'esthetician',
                    totalBillable: 0,
                    totalOwed: 0,
                }),
                COMPACT_OPS_EMAILS
            );
        });
    });

    describe('Manual invoice run', () => {
        it('should use the billing month from the event instead of the previous month', async () => {
            jest.setSystemTime(new Date('2024-11-02T12:00:00.000Z'));
            mockCompactAndJurisdictions();

            await lambda().handler({ eventType: 'manual', billingMonth: '2024-09' }, SAMPLE_CONTEXT);

            const partitionKeys = gsiQueries().map((call) => call.args[0].input.ExpressionAttributeValues?.[':pk']?.S);

            expect(partitionKeys).toContain('C#cosm#J#oh#D#2024-09');
            expect(partitionKeys.some((key) => key?.includes('D#2024-10'))).toBe(false);
        });

        it('should still send one email per license type', async () => {
            mockCompactAndJurisdictions();

            await lambda().handler({ eventType: 'manual', billingMonth: '2024-09' }, SAMPLE_CONTEXT);

            expect(mockSendInvoiceEmail).toHaveBeenCalledTimes(2);
            expect(mockSendInvoiceEmail.mock.calls.map((call) => call[0].licenseType).sort()).toEqual([
                'cosmetologist',
                'esthetician',
            ]);
        });
    });
});
