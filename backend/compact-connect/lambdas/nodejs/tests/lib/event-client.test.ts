import { Logger } from '@aws-lambda-powertools/logger';
import { DynamoDBClient, QueryCommand } from '@aws-sdk/client-dynamodb';
import { mockClient } from 'aws-sdk-client-mock';
import { EventClient } from '../../lib/event-client';
import { describe, it, expect, beforeAll, beforeEach, jest } from '@jest/globals';


/*
 * Double casting to allow us to pass a mock in for the real thing
 */
const asDynamoDBClient = (mock: ReturnType<typeof mockClient>) =>
    mock as unknown as DynamoDBClient;



describe('EventClient', () => {
    let mockDynamoDBClient: ReturnType<typeof mockClient>;

    const withErrorsInDynamoDB = () => {
        mockDynamoDBClient.on(QueryCommand).callsFake((input) => {
            if (input?.ExpressionAttributeValues?.[':skBegin']['S']?.startsWith(
                'TYPE#license.validation-error#TIME#'
            )) {
                return Promise.resolve({
                    Items: [{ 'eventType': { 'S': 'license.validation-error' }}]
                });
            }
            if (input?.ExpressionAttributeValues?.[':skBegin']['S']?.startsWith(
                'TYPE#license.ingest-failure#TIME#'
            )) {
                return Promise.resolve({
                    Items: [{ 'eventType': { 'S': 'license.ingest-failure' }}]
                });
            }
            if (input?.ExpressionAttributeValues?.[':skBegin']['S']?.startsWith(
                'TYPE#license.ingest#TIME#'
            )) {
                return Promise.resolve({
                    Items: []
                });
            }
            throw Error(`Unexpected query ${input}`);
        });
    };

    const withoutErrorsInDynamoDB = () => {
        mockDynamoDBClient.on(QueryCommand).callsFake((input) => {
            if (input?.ExpressionAttributeValues?.[':skBegin']['S']?.startsWith(
                'TYPE#license.validation-error#TIME#'
            )) {
                return Promise.resolve({});
            }
            if (input?.ExpressionAttributeValues?.[':skBegin']['S']?.startsWith(
                'TYPE#license.ingest-failure#TIME#'
            )) {
                return Promise.resolve({});
            }
            if (input?.ExpressionAttributeValues?.[':skBegin']['S']?.startsWith(
                'TYPE#license.ingest#TIME#'
            )) {
                return Promise.resolve({
                    Items: [{ 'eventType': { 'S': 'license.ingest' }}]
                });
            }
            throw Error('Unexpected query');
        });
    };

    beforeAll(async () => {
        process.env.DEBUG = 'true';
        process.env.DATA_EVENT_TABLE_NAME = 'some-table';

        mockDynamoDBClient = mockClient(DynamoDBClient);
    });

    beforeEach(() => {
        jest.clearAllMocks();
    });

    it('should produce 15-minute timestamps 900 seconds (15 minutes) apart', async () => {
        const eventClient = new EventClient({
            logger: new Logger(),
            dynamoDBClient: asDynamoDBClient(mockDynamoDBClient)
        });

        const [ startStamp, endStamp ] = eventClient.getLast15MinuteTimestamps();

        expect(endStamp - startStamp).toEqual(900);
    });

    it('should produce 15-minute blocks', async () => {
        const eventClient = new EventClient({
            logger: new Logger(),
            dynamoDBClient: asDynamoDBClient(mockDynamoDBClient)
        });

        // Test case 1: if 'now' is at 11:01, it should return timestamps at 10:45-11:00
        jest.useFakeTimers();
        jest.setSystemTime(new Date('2025-01-01T11:01:00.000Z'));

        const [ startStamp1, endStamp1 ] = eventClient.getLast15MinuteTimestamps();
        const expectedStart1 = Math.floor(new Date('2025-01-01T10:45:00.000Z').getTime() / 1000);
        const expectedEnd1 = Math.floor(new Date('2025-01-01T11:00:00.000Z').getTime() / 1000);

        expect(startStamp1).toEqual(expectedStart1);
        expect(endStamp1).toEqual(expectedEnd1);
        expect(endStamp1 - startStamp1).toEqual(900); // 15 minutes (10:45 to 11:00)

        // Test case 2: if 'now' is at 2025-01-01T00:00:00.001Z, it should return timestamps for 2024-12-31T23:45:00.000Z-2025-01-01T00:00:00.000Z
        jest.setSystemTime(new Date('2025-01-01T00:00:00.001Z'));

        const [ startStamp2, endStamp2 ] = eventClient.getLast15MinuteTimestamps();
        const expectedStart2 = Math.floor(new Date('2024-12-31T23:45:00.000Z').getTime() / 1000);
        const expectedEnd2 = Math.floor(new Date('2025-01-01T00:00:00.000Z').getTime() / 1000);

        expect(startStamp2).toEqual(expectedStart2);
        expect(endStamp2).toEqual(expectedEnd2);
        expect(endStamp2 - startStamp2).toEqual(900); // 15 minutes (23:45 to 00:00)

        // Test case 3: if 'now' is at 12:35, it should return timestamps at 12:15-12:30
        jest.setSystemTime(new Date('2025-01-01T12:35:00.000Z'));

        const [ startStamp3, endStamp3 ] = eventClient.getLast15MinuteTimestamps();
        const expectedStart3 = Math.floor(new Date('2025-01-01T12:15:00.000Z').getTime() / 1000);
        const expectedEnd3 = Math.floor(new Date('2025-01-01T12:30:00.000Z').getTime() / 1000);

        expect(startStamp3).toEqual(expectedStart3);
        expect(endStamp3).toEqual(expectedEnd3);
        expect(endStamp3 - startStamp3).toEqual(900); // 15 minutes (12:15 to 12:30)

        // Restore real timers
        jest.useRealTimers();
    });

    it('should produce nightly timestamps 86400 seconds (24 hours) apart', async () => {
        const eventClient = new EventClient({
            logger: new Logger(),
            dynamoDBClient: asDynamoDBClient(mockDynamoDBClient)
        });

        const [ startStamp, endStamp ] = eventClient.getYesterdayTimestamps();

        expect(endStamp - startStamp).toEqual(86400);
    });

    it('should produce weekly timestamps 604800 seconds (7 days) apart', async () => {
        const eventClient = new EventClient({
            logger: new Logger(),
            dynamoDBClient: asDynamoDBClient(mockDynamoDBClient)
        });

        const [ startStamp, endStamp ] = eventClient.getLastWeekTimestamps();

        expect(endStamp - startStamp).toEqual(604800);
    });

    it('should return validation errors from the getValidationErrors method', async () => {
        withErrorsInDynamoDB();

        const eventClient = new EventClient({
            logger: new Logger(),
            dynamoDBClient: asDynamoDBClient(mockDynamoDBClient)
        });

        const validationErrors = await eventClient.getValidationErrors('aslp', 'oh', 0, 1);

        expect(validationErrors).toEqual([{ 'eventType': 'license.validation-error' }]);
    });


    it('should return an empty array if there are no validation errors', async () => {
        withoutErrorsInDynamoDB();

        const eventClient = new EventClient({
            logger: new Logger(),
            dynamoDBClient: asDynamoDBClient(mockDynamoDBClient)
        });

        const validationErrors = await eventClient.getValidationErrors('aslp', 'oh', 0, 1);

        expect(validationErrors).toEqual([]);
    });

    it('should return ingest failures from the getIngestFailures method', async () => {
        withErrorsInDynamoDB();

        const eventClient = new EventClient({
            logger: new Logger(),
            dynamoDBClient: asDynamoDBClient(mockDynamoDBClient)
        });

        const validationErrors = await eventClient.getIngestFailures('aslp', 'oh', 0, 1);

        expect(validationErrors).toEqual([{ 'eventType': 'license.ingest-failure' }]);
    });

    it('should return an empty array if there are no ingest failures', async () => {
        withoutErrorsInDynamoDB();

        const eventClient = new EventClient({
            logger: new Logger(),
            dynamoDBClient: asDynamoDBClient(mockDynamoDBClient)
        });

        const validationErrors = await eventClient.getIngestFailures('aslp', 'oh', 0, 1);

        expect(validationErrors).toEqual([]);
    });

    it('should return ingest successes', async () => {
        withoutErrorsInDynamoDB();

        const eventClient = new EventClient({
            logger: new Logger(),
            dynamoDBClient: asDynamoDBClient(mockDynamoDBClient)
        });

        const ingestSuccesses = await eventClient.getIngestSuccesses('aslp', 'oh', 0, 1);

        expect(ingestSuccesses).toEqual([{ 'eventType': 'license.ingest' }]);
    });

    it('should return empty array if no ingest successes', async () => {
        withErrorsInDynamoDB();

        const eventClient = new EventClient({
            logger: new Logger(),
            dynamoDBClient: asDynamoDBClient(mockDynamoDBClient)
        });

        const ingestSuccesses = await eventClient.getIngestSuccesses('aslp', 'oh', 0, 1);

        expect(ingestSuccesses).toEqual([]);
    });

    it('should return ingest failures, successes, and validation errors from the getEvents method when errors', async() => {
        withErrorsInDynamoDB();

        const eventClient = new EventClient({
            logger: new Logger(),
            dynamoDBClient: asDynamoDBClient(mockDynamoDBClient)
        });

        const ingestEvents = await eventClient.getEvents('aslp', 'oh', 0, 1);

        expect(ingestEvents).toEqual({
            ingestFailures: [{ 'eventType': 'license.ingest-failure' }],
            validationErrors: [{ 'eventType': 'license.validation-error' }],
            ingestSuccesses: []
        });
    });

    it('should return ingest failures, successes, and validation errors from the getEvents method when no errors', async() => {
        withoutErrorsInDynamoDB();

        const eventClient = new EventClient({
            logger: new Logger(),
            dynamoDBClient: asDynamoDBClient(mockDynamoDBClient)
        });

        const ingestEvents = await eventClient.getEvents('aslp', 'oh', 0, 1);

        expect(ingestEvents).toEqual({
            ingestFailures: [],
            validationErrors: [],
            ingestSuccesses: [{ 'eventType': 'license.ingest' }]
        });
    });
});
