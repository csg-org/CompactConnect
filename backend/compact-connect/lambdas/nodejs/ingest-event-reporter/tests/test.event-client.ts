import { Logger } from '@aws-lambda-powertools/logger';
import { DynamoDBClient, QueryCommand } from '@aws-sdk/client-dynamodb';
import { EventClient } from '../lib/event-client';


// Mock the entire DynamoDBClient
jest.mock('@aws-sdk/client-dynamodb', () => {
    return {
        DynamoDBClient: jest.fn(() => ({
            send: jest.fn((command: QueryCommand) => {
                if (command.input?.ExpressionAttributeValues?.[':skBegin']['S']?.startsWith(
                    'TYPE#license.validation-error#TIME#'
                )) {
                    return Promise.resolve({
                        Items: [{ 'eventType': { 'S': 'license.validation-error' }}]
                    });
                }
                if (command.input?.ExpressionAttributeValues?.[':skBegin']['S']?.startsWith(
                    'TYPE#license.ingest-failure#TIME#'
                )) {
                    return Promise.resolve({
                        Items: [{ 'eventType': { 'S': 'license.ingest-failure' }}]
                    });
                }
                throw Error('Unexpected query');
            })
        })),
        QueryCommand: jest.fn((params) => ({ input: params }))
    };
});


describe('EventClient', () => {
    let eventClient: EventClient;

    beforeAll(async () => {
        process.env.DEBUG = 'true';
        process.env.DATA_EVENT_TABLE_NAME = 'some-table';
    });

    beforeEach(() => {
        jest.clearAllMocks();

        const mockDynamoDBClient = new DynamoDBClient() as jest.Mocked<DynamoDBClient>;

        eventClient = new EventClient({
            logger: new Logger(),
            dynamoDBClient: mockDynamoDBClient
        });
    });

    it('should produce timestamps 86400 seconds (24 hours) apart', async () => {
        const [ startStamp, endStamp ] = eventClient.getYesterdayTimestamps();

        expect(endStamp - startStamp).toEqual(86400);
    });

    it('should produce timestamps 604800 seconds (7 days) apart', async () => {
        const [ startStamp, endStamp ] = eventClient.getLastWeekTimestamps();

        expect(endStamp - startStamp).toEqual(604800);
    });

    it('should return validation errors from the getValidationErrors method', async () => {
        const validationErrors = await eventClient.getValidationErrors('aslp', 'oh', 0, 1);

        expect(validationErrors).toEqual([{ 'eventType': 'license.validation-error' }]);
    });

    it('should return ingest failures from the getIngestFailures method', async () => {
        const validationErrors = await eventClient.getIngestFailures('aslp', 'oh', 0, 1);

        expect(validationErrors).toEqual([{ 'eventType': 'license.ingest-failure' }]);
    });

    it('should return ingest failures and validation errors from the getEvents method', async() => {
        const ingestEvents = await eventClient.getEvents('aslp', 'oh', 0, 1);

        expect(ingestEvents).toEqual({
            ingestFailures: [{ 'eventType': 'license.ingest-failure' }],
            validationErrors: [{ 'eventType': 'license.validation-error' }]
        });
    });
});
