import { mockClient } from 'aws-sdk-client-mock';
import 'aws-sdk-client-mock-jest';
import { Context, EventBridgeEvent } from 'aws-lambda';
import { DynamoDBClient, QueryCommand } from '@aws-sdk/client-dynamodb';
import { SendEmailCommand, SESClient } from '@aws-sdk/client-ses';

import { Lambda } from '../lib/lambda';
import { ReportEmailer } from '../lib/report-emailer';
import { IEventBridgeEvent } from '../lib/models/event-bridge-event-detail';
import {
    SAMPLE_INGEST_FAILURE_ERROR_RECORD,
    SAMPLE_JURISDICTION_CONFIGURATION,
    SAMPLE_VALIDATION_ERROR_RECORD
} from './sample-records';


const SAMPLE_NIGHTLY_EVENT: IEventBridgeEvent = {
    'eventType': 'nightly'
};

const SAMPLE_WEEKLY_EVENT: IEventBridgeEvent = {
    'eventType': 'weekly'
};


const SAMPLE_CONTEXT: Context = {
    callbackWaitsForEmptyEventLoop: true,
    functionVersion: '$LATEST',
    functionName: 'foo-bar-function',
    memoryLimitInMB: '128',
    logGroupName: '/aws/lambda/foo-bar-function-123456abcdef',
    logStreamName: '2021/03/09/[$LATEST]abcdef123456abcdef123456abcdef123456',
    invokedFunctionArn:
        'arn:aws:lambda:eu-west-1:123456789012:function:foo-bar-function',
    awsRequestId: 'c6af9ac6-7b61-11e6-9a41-93e812345678',
    getRemainingTimeInMillis: () => 1234,
    done: () => console.log('Done!'),
    fail: () => console.log('Failed!'),
    succeed: () => console.log('Succeeded!'),
};

/*
 * Double casting to allow us to pass a mock in for the real thing
 */
const asDynamoDBClient = (mock: ReturnType<typeof mockClient>) =>
  mock as unknown as DynamoDBClient;
const asSESClient = (mock: ReturnType<typeof mockClient>) =>
    mock as unknown as SESClient;


jest.mock('../lib/report-emailer');

const mockSendReportEmail = jest.fn(
    (events, recipients: string[]) => Promise.resolve('message-id-123')
);
const mockSendAllsWellEmail = jest.fn(
    (recipients: string[]) => Promise.resolve('message-id-123')
);

(ReportEmailer as jest.Mock) = jest.fn().mockImplementation(() => ({
    sendReportEmail: mockSendReportEmail,
    sendAllsWellEmail: mockSendAllsWellEmail
}));


describe('Nightly runs', () => {
    let mockSESClient: ReturnType<typeof mockClient>;
    let mockReportEmailer: jest.Mocked<ReportEmailer>;
    let lambda: Lambda;

    beforeAll(async () => {
        process.env.DEBUG = 'true';
        process.env.COMPACTS = '["aslp", "octp", "coun"]';
        process.env.DATA_EVENT_TABLE_NAME = 'data-table';
        process.env.COMPACT_CONFIGURATION_TABLE_NAME = 'compact-table';
        process.env.AWS_REGION = 'us-east-1';

        // Get the mocked client instances
        mockSESClient = mockClient(SESClient);
    });

    beforeEach(() => {
        // Clear all instances and calls to constructor and all methods:
        jest.clearAllMocks();
        mockSendReportEmail.mockClear();
        mockSendAllsWellEmail.mockClear();
    });

    it('should send a report email when there were errors', async () => {
        const mockDynamoDBClient = mockClient(DynamoDBClient);

        mockDynamoDBClient.on(QueryCommand).callsFake((input) => {
            const tableName = input.TableName;

            switch (tableName) {
            case 'data-table':
                if (input?.ExpressionAttributeValues?.[':skBegin']['S']?.startsWith(
                    'TYPE#license.validation-error#TIME#'
                )) {
                    return Promise.resolve({
                        Items: [SAMPLE_VALIDATION_ERROR_RECORD]
                    });
                }
                if (input?.ExpressionAttributeValues?.[':skBegin']['S']?.startsWith(
                    'TYPE#license.ingest-failure#TIME#'
                )) {
                    return Promise.resolve({
                        Items: [SAMPLE_INGEST_FAILURE_ERROR_RECORD]
                    });
                }
                throw Error('Unexpected query');
            case 'compact-table':
                return Promise.resolve({
                    Items: [SAMPLE_JURISDICTION_CONFIGURATION]
                });
            default:
                throw Error(`Table does not exist: ${tableName}`);
            }
        });

        lambda = new Lambda({
            dynamoDBClient: asDynamoDBClient(mockDynamoDBClient),
            sesClient: asSESClient(mockSESClient)
        });

        const resp = await lambda.handler(
            SAMPLE_NIGHTLY_EVENT,
            SAMPLE_CONTEXT
        );

        // Verify the DynamoDB client was called correctly
        expect(mockDynamoDBClient).toHaveReceivedCommandWith(
            QueryCommand,
            {
                TableName: 'data-table',
            }
        );

        // Verify an event report was sent
        expect(mockSendReportEmail).toHaveBeenCalled();
        expect(mockSendAllsWellEmail).not.toHaveBeenCalled();
    });

    it('should not send an email if there were no ingest events', async () => {
        const mockDynamoDBClient = mockClient(DynamoDBClient);

        mockDynamoDBClient.on(QueryCommand).callsFake((input) => {
            const tableName = input.TableName;

            switch (tableName) {
            case 'data-table':
                return Promise.resolve({
                    Items: []
                });
            case 'compact-table':
                return Promise.resolve({
                    Items: [SAMPLE_JURISDICTION_CONFIGURATION]
                });
            default:
                throw Error(`Table does not exist: ${tableName}`);
            }
        });

        lambda = new Lambda({
            dynamoDBClient: asDynamoDBClient(mockDynamoDBClient),
            sesClient: asSESClient(mockSESClient)
        });

        const resp = await lambda.handler(
            SAMPLE_NIGHTLY_EVENT,
            SAMPLE_CONTEXT
        );

        // Verify the DynamoDB client was called correctly
        // To get jurisdictions
        expect(mockDynamoDBClient).toHaveReceivedCommandWith(
            QueryCommand,
            {
                TableName: 'compact-table',
            }
        );

        // To get events
        expect(mockDynamoDBClient).toHaveReceivedCommandWith(
            QueryCommand,
            {
                TableName: 'data-table',
            }
        );

        // Verify no emails were sent
        expect(mockSendReportEmail).not.toHaveBeenCalled();
        expect(mockSendAllsWellEmail).not.toHaveBeenCalled();
    });

    it('should let DynamoDB errors escape', async () => {
        const mockDynamoDBClient = mockClient(DynamoDBClient);

        mockDynamoDBClient.on(QueryCommand).rejects(new Error('DynamoDB error'));

        lambda = new Lambda({
            dynamoDBClient: asDynamoDBClient(mockDynamoDBClient),
            sesClient: asSESClient(mockSESClient)
        });

        // Expect the function to throw or handle the error appropriately
        await expect(lambda.handler(
            SAMPLE_NIGHTLY_EVENT,
            SAMPLE_CONTEXT
        )).rejects.toThrow('DynamoDB error');
    });
});


describe('Weekly runs', () => {
    let mockSESClient: ReturnType<typeof mockClient>;
    let lambda: Lambda;

    beforeAll(async () => {
        process.env.DEBUG = 'true';
        process.env.COMPACTS = '["aslp", "octp", "coun"]';
        process.env.DATA_EVENT_TABLE_NAME = 'data-table';
        process.env.COMPACT_CONFIGURATION_TABLE_NAME = 'compact-table';
        process.env.AWS_REGION = 'us-east-1';
    });

    beforeEach(() => {
        // Clear all instances and calls to constructor and all methods:
        jest.clearAllMocks();

        // Get the mocked client instances
        mockSESClient = mockClient(SESClient);
        mockSESClient.on(SendEmailCommand).resolves({
            MessageId: 'foo-123'
        });
    });

    it('should send and "All\'s Well" email if there were no events', async () => {
        const mockDynamoDBClient = mockClient(DynamoDBClient);

        mockDynamoDBClient.on(QueryCommand).callsFake((input) => {
            const tableName = input.TableName;

            switch (tableName) {
            case 'data-table':
                return Promise.resolve({
                    // No ingest events
                    Items: []
                });
            case 'compact-table':
                return Promise.resolve({
                    Items: [SAMPLE_JURISDICTION_CONFIGURATION]
                });
            default:
                throw Error(`Table does not exist: ${tableName}`);
            }
        });

        lambda = new Lambda({
            dynamoDBClient: asDynamoDBClient(mockDynamoDBClient),
            sesClient: asSESClient(mockSESClient)
        });

        await lambda.handler(
            SAMPLE_WEEKLY_EVENT,
            SAMPLE_CONTEXT
        );

        // Verify the DynamoDB client was called correctly
        expect(mockDynamoDBClient).toHaveReceivedCommandWith(
            QueryCommand,
            {
                TableName: 'data-table',
            }
        );

        // Verify an "All's Well" email was sent
        expect(mockSendReportEmail).not.toHaveBeenCalled();
        expect(mockSendAllsWellEmail).toHaveBeenCalled();
    });

    it('should send a report email and not an alls well, when there were errors', async () => {
        const mockDynamoDBClient = mockClient(DynamoDBClient);

        mockDynamoDBClient.on(QueryCommand).callsFake((input) => {
            const tableName = input.TableName;

            switch (tableName) {
            case 'data-table':
                if (input?.ExpressionAttributeValues?.[':skBegin']['S']?.startsWith(
                    'TYPE#license.validation-error#TIME#'
                )) {
                    return Promise.resolve({
                        Items: [SAMPLE_VALIDATION_ERROR_RECORD]
                    });
                }
                if (input?.ExpressionAttributeValues?.[':skBegin']['S']?.startsWith(
                    'TYPE#license.ingest-failure#TIME#'
                )) {
                    return Promise.resolve({
                        Items: [SAMPLE_INGEST_FAILURE_ERROR_RECORD]
                    });
                }
                throw Error('Unexpected query');
            case 'compact-table':
                return Promise.resolve({
                    Items: [SAMPLE_JURISDICTION_CONFIGURATION]
                });
            default:
                throw Error(`Table does not exist: ${tableName}`);
            }
        });

        lambda = new Lambda({
            dynamoDBClient: asDynamoDBClient(mockDynamoDBClient),
            sesClient: asSESClient(mockSESClient)
        });

        const resp = await lambda.handler(
            SAMPLE_WEEKLY_EVENT,
            SAMPLE_CONTEXT
        );

        // Verify the DynamoDB client was called correctly
        expect(mockDynamoDBClient).toHaveReceivedCommandWith(
            QueryCommand,
            {
                TableName: 'data-table',
            }
        );

        // Verify an event report was sent
        expect(mockSendReportEmail).toHaveBeenCalled();
        expect(mockSendAllsWellEmail).not.toHaveBeenCalled();
    });
});
