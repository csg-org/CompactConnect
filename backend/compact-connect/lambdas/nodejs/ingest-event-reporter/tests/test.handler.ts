import { AwsStub, mockClient } from 'aws-sdk-client-mock';
import 'aws-sdk-client-mock-jest';
import { DynamoDBClient, QueryCommand } from '@aws-sdk/client-dynamodb';
import { SendEmailCommand, SESClient } from '@aws-sdk/client-ses';
import { Context, EventBridgeEvent } from 'aws-lambda';
import { Lambda } from '../lib/lambda';
import { IEventBridgeEventDetail } from '../lib/models/event-bridge-event-detail';


const SAMPLE_NIGHTLY_EVENT: EventBridgeEvent<string, IEventBridgeEventDetail> = {
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
    'detail': {
        'eventType': 'nightly'
    }
};

const SAMPLE_WEEKLY_EVENT: EventBridgeEvent<string, IEventBridgeEventDetail> = {
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
    'detail': {
        'eventType': 'weekly'
    }
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

const SAMPLE_INGEST_FAILURE_ERROR_RECORD = {
    'pk': {
        'S': 'COMPACT#octp#JURISDICTION#oh'
    },
    'sk': {
        'S': 'TYPE#license.ingest-failure#TIME#1731618012#EVENT#08ff0b63-4492-89c6-4372-3e95f03ee984'
    },
    'compact': {
        'S': 'octp'
    },
    'errors': {
        'L': [
            {
                'S': '\'utf-8\' codec can\'t decode byte 0x83 in position 0: invalid start byte'
            }
        ]
    },
    'eventExpiry': {
        'N': '1739394328'
    },
    'eventTime': {
        'S': '2024-11-14T21:00:12.382000+00:00'
    },
    'eventType': {
        'S': 'license.ingest-failure'
    },
    'jurisdiction': {
        'S': 'oh'
    }
};

const SAMPLE_VALIDATION_ERROR_RECORD = {
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

const SAMPLE_JURISDICTION_CONFIGURATION = {
    'pk': {
        'S': 'aslp#CONFIGURATION'
    },
    'sk': {
        'S': 'aslp#JURISDICTION#oh'
    },
    'compact': {
        'S': 'aslp'
    },
    'dateOfUpdate': {
        'S': '2024-11-14'
    },
    'jurisdictionAdverseActionsNotificationEmails': {
        'L': []
    },
    'jurisdictionFee': {
        'N': '100'
    },
    'jurisdictionName': {
        'S': 'ohio'
    },
    'jurisdictionOperationsTeamEmails': {
        'L': [
            {
                'S': 'justin@inspiringapps.com'
            }
        ]
    },
    'jurisdictionSummaryReportNotificationEmails': {
        'L': []
    },
    'jurisprudenceRequirements': {
        'M': {
            'required': {
                'BOOL': true
            }
        }
    },
    'militaryDiscount': {
        'M': {
            'active': {
                'BOOL': true
            },
            'discountAmount': {
                'N': '10'
            },
            'discountType': {
                'S': 'FLAT_RATE'
            }
        }
    },
    'postalAbbreviation': {
        'S': 'oh'
    },
    'type': {
        'S': 'jurisdiction'
    }
};

/*
 * Double casting to allow us to pass a mock in for the real thing
 */
const asDynamoDBClient = (mock: ReturnType<typeof mockClient>) =>
  mock as unknown as DynamoDBClient;
const asSESClient = (mock: ReturnType<typeof mockClient>) =>
    mock as unknown as SESClient;


describe('Nightly runs', () => {
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

    it('should run with no errors', async () => {
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

        expect(mockSESClient).toHaveReceivedCommand(SendEmailCommand);
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

        // Verify the send method was called
        expect(mockSESClient).not.toHaveReceivedCommand(SendEmailCommand);
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
