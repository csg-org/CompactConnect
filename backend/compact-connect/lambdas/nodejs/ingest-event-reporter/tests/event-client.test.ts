import { Logger } from '@aws-lambda-powertools/logger';
import { DynamoDBClient, QueryCommand } from '@aws-sdk/client-dynamodb';
import { mockClient } from 'aws-sdk-client-mock';
import { EventClient } from '../lib/event-client';


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
            throw Error('Unexpected query');
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

    it('should produce nightly timestamps 86400 seconds (24 hours) apart', async () => {
        const eventClient = new EventClient({
            logger: new Logger(),
            dynamoDBClient: asDynamoDBClient(mockDynamoDBClient)
        });

        const [ startStamp, endStamp ] = eventClient.getYesterdayTimestamps();

        expect(endStamp - startStamp).toEqual(86400);
        const endDate = new Date(endStamp * 1000);

        // After the UTC_OFFSET, our timestamp should be 4AM UTC on whatever day
        expect(endDate.getUTCHours()).toEqual(4);
    });

    it('should produce weekly timestamps 604800 seconds (7 days) apart', async () => {
        const eventClient = new EventClient({
            logger: new Logger(),
            dynamoDBClient: asDynamoDBClient(mockDynamoDBClient)
        });

        const [ startStamp, endStamp ] = eventClient.getLastWeekTimestamps();

        expect(endStamp - startStamp).toEqual(604800);
        const endDate = new Date(endStamp * 1000);

        // After the UTC_OFFSET, our timestamp should be 4AM UTC on whatever day
        expect(endDate.getUTCHours()).toEqual(4);
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

    it('should return ingest failures and validation errors from the getEvents method', async() => {
        withErrorsInDynamoDB();

        const eventClient = new EventClient({
            logger: new Logger(),
            dynamoDBClient: asDynamoDBClient(mockDynamoDBClient)
        });

        const ingestEvents = await eventClient.getEvents('aslp', 'oh', 0, 1);

        expect(ingestEvents).toEqual({
            ingestFailures: [{ 'eventType': 'license.ingest-failure' }],
            validationErrors: [{ 'eventType': 'license.validation-error' }]
        });
    });
});
