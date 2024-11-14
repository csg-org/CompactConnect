import { DynamoDBClient, QueryCommand } from '@aws-sdk/client-dynamodb';
import { SESClient } from '@aws-sdk/client-ses';
import { Context, EventBridgeEvent } from 'aws-lambda';
import { Lambda } from '../lib/lambda';


const SAMPLE_SCHEDULED_EVENT: EventBridgeEvent<string, any> = {
    'version': '0',
    'id': '4dd7e0e4-dfe8-29ab-a1d7-5dd5efc2a4fe',
    'detail-type': 'Scheduled Event',
    'source': 'aws.events',
    'account': '992382587219',
    'time': '2024-11-01T04:08:00Z',
    'region': 'us-east-1',
    'resources': [
        'arn:aws:events:us-east-1:992382587219:rule/Sandbox-ReportingStack-ScheduleRuleDA5BD877-Kqysj6AhkI6E'
    ],
    'detail': {}
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

const SAMPLE_DB_RECORD = {
    'pk': {
        'S': 'COMPACT#octp#JURISDICTION#oh'
    },
    'sk': {
        'S': 'TYPE#license.validation-error#TIME#1730263675#EVENT#182d8d8b-7fee-6e0c-2e3c-1189a47d5a0c'
    },
    'eventType': {
        'S': 'license.validation-error'
    },
    'time': {
        'S': '2024-10-30T04:47:55.843000+00:00'
    },
    'compact': {
        'S': 'octp'
    },
    'jurisdiction': {
        'S': 'oh'
    },
    'errors': {
        'M': {
            'dateOfRenewal': {
                'L': [
                    {
                        'S': 'Not a valid date.'
                    }
                ]
            }
        }
    },
    'recordNumber': {
        'N': '5'
    },
    'validData': {
        'M': {}
    },
};


// Mock the entire DynamoDBClient
jest.mock('@aws-sdk/client-dynamodb', () => {
    return {
        DynamoDBClient: jest.fn(() => ({
            send: jest.fn(() => ({
                Items: [SAMPLE_DB_RECORD]
            }))
        })),
        QueryCommand: jest.fn()
    };
});

// Mock the SESClient
jest.mock('@aws-sdk/client-ses', () => {
    return {
        SESClient: jest.fn(() => ({
            send: jest.fn(() => ({
                MessageId: 'foo-123'
            }))
        })),
        SendEmailCommand: jest.fn()
    };
});


describe('Event collector', () => {
    let mockDynamoDBClient: jest.Mocked<DynamoDBClient>;
    let mockSESClient: jest.Mocked<SESClient>;
    let lambda: Lambda;

    beforeAll(async () => {
        process.env.DEBUG = 'true';
        process.env.COMPACTS = '["aslp", "octp", "coun"]';
        process.env.DATA_EVENT_TABLE_NAME = 'some-table';
        process.env.AWS_REGION = 'us-east-1';
        // Tells the logger to pretty print logs for easier manual reading
        process.env.POWERTOOLS_DEV = 'true';
    });

    beforeEach(() => {
        // Clear all instances and calls to constructor and all methods:
        jest.clearAllMocks();

        // Get the mocked client instances
        mockDynamoDBClient = new DynamoDBClient() as jest.Mocked<DynamoDBClient>;
        mockSESClient = new SESClient() as jest.Mocked<SESClient>;

        lambda = new Lambda({
            dynamoDBClient: mockDynamoDBClient,
            sesClient: mockSESClient
        });
    });

    it('should run with no errors', async () => {
        const resp = await lambda.handler(
            SAMPLE_SCHEDULED_EVENT,
            SAMPLE_CONTEXT
        );

        // Verify the DynamoDB client was called correctly
        expect(QueryCommand).toHaveBeenCalledWith(
            expect.objectContaining({
                TableName: 'some-table',
            })
        );

        // Verify the send method was called
        expect(mockDynamoDBClient.send).toHaveBeenCalled();
        expect(mockSESClient.send).toHaveBeenCalled();
    });

    it('should let DynamoDB errors escape', async () => {
        // Mock a DynamoDB error
        (mockDynamoDBClient.send as jest.Mock).mockRejectedValueOnce(
            new Error('DynamoDB error')
        );

        // Expect the function to throw or handle the error appropriately
        await expect(lambda.handler(
            SAMPLE_SCHEDULED_EVENT,
            SAMPLE_CONTEXT
        )).rejects.toThrow('DynamoDB error');
    });
});
