import { mockClient } from 'aws-sdk-client-mock';
import 'aws-sdk-client-mock-jest';
import { Logger } from '@aws-lambda-powertools/logger';
import { DynamoDBClient, GetItemCommand } from '@aws-sdk/client-dynamodb';
import { CompactConfigurationClient } from '../../lib/compact-configuration-client';

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

/*
 * Double casting to allow us to pass a mock in for the real thing
 */
const asDynamoDBClient = (mock: ReturnType<typeof mockClient>) =>
    mock as unknown as DynamoDBClient;

describe('CompactConfigurationClient', () => {
    let compactConfigurationClient: CompactConfigurationClient;
    let mockDynamoDBClient: ReturnType<typeof mockClient>;

    beforeAll(async () => {
        process.env.DEBUG = 'true';
        process.env.COMPACT_CONFIGURATION_TABLE_NAME = 'compact-table';
        process.env.AWS_REGION = 'us-east-1';
    });

    beforeEach(() => {
        jest.clearAllMocks();
        mockDynamoDBClient = mockClient(DynamoDBClient);
    });

    it('should return compact configuration from DynamoDB', async () => {
        mockDynamoDBClient.on(GetItemCommand).resolves({
            Item: SAMPLE_COMPACT_CONFIGURATION
        });

        compactConfigurationClient = new CompactConfigurationClient({
            logger: new Logger(),
            dynamoDBClient: asDynamoDBClient(mockDynamoDBClient)
        });

        const config = await compactConfigurationClient.getCompactConfiguration('cosm');

        expect(mockDynamoDBClient).toHaveReceivedCommandWith(
            GetItemCommand,
            {
                TableName: 'compact-table',
                Key: {
                    'pk': { S: 'cosm#CONFIGURATION' },
                    'sk': { S: 'cosm#CONFIGURATION' }
                }
            }
        );

        expect(config).toEqual({
            pk: 'cosm#CONFIGURATION',
            sk: 'cosm#CONFIGURATION',
            compactAdverseActionsNotificationEmails: ['adverse@example.com'],
            compactCommissionFee: {
                feeAmount: 3.5,
                feeType: 'FLAT_RATE'
            },
            compactAbbr: 'cosm',
            compactName: 'Audiology and Speech Language Pathology',
            compactOperationsTeamEmails: ['operations@example.com'],
            compactSummaryReportNotificationEmails: ['summary@example.com'],
            dateOfUpdate: '2024-12-10T19:27:28+00:00',
            type: 'compact'
        });
    });

    it('should throw error when no configuration found', async () => {
        mockDynamoDBClient.on(GetItemCommand).resolves({
            Item: undefined
        });

        compactConfigurationClient = new CompactConfigurationClient({
            logger: new Logger(),
            dynamoDBClient: asDynamoDBClient(mockDynamoDBClient)
        });

        await expect(compactConfigurationClient.getCompactConfiguration('invalid'))
            .rejects
            .toThrow('No configuration found for compact: invalid');
    });
});
