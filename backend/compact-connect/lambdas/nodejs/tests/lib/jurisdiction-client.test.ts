import { mockClient } from 'aws-sdk-client-mock';
import 'aws-sdk-client-mock-jest';
import { Logger } from '@aws-lambda-powertools/logger';
import { DynamoDBClient, QueryCommand, GetItemCommand } from '@aws-sdk/client-dynamodb';
import { JurisdictionClient } from '../../lib/jurisdiction-client';
import { describe, it, expect, beforeAll, beforeEach, jest } from '@jest/globals';


const SAMPLE_JURISDICTION_ITEMS = [
    {
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
        'privilegeFees': {
            'L': [
                {
                    'M': {
                        'licenseTypeAbbreviation': {
                            'S': 'aud'
                        },
                        'amount': {
                            'N': '100'
                        }
                    }
                },
                {
                    'M': {
                        'licenseTypeAbbreviation': {
                            'S': 'slp'
                        },
                        'amount': {
                            'N': '100'
                        }
                    }
                }
            ]
        },
        'jurisdictionName': {
            'S': 'Ohio'
        },
        'jurisdictionOperationsTeamEmails': {
            'L': [
                {
                    'S': 'operations@example.com'
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
        'postalAbbreviation': {
            'S': 'oh'
        },
        'type': {
            'S': 'jurisdiction'
        }
    },
    {
        'pk': {
            'S': 'aslp#CONFIGURATION'
        },
        'sk': {
            'S': 'aslp#JURISDICTION#ne'
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
        'privilegeFees': {
            'L': [
                {
                    'M': {
                        'licenseTypeAbbreviation': {
                            'S': 'aud'
                        },
                        'amount': {
                            'N': '100'
                        }
                    }
                },
                {
                    'M': {
                        'licenseTypeAbbreviation': {
                            'S': 'slp'
                        },
                        'amount': {
                            'N': '100'
                        }
                    }
                }
            ]
        },
        'jurisdictionName': {
            'S': 'Nebraska'
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
        'postalAbbreviation': {
            'S': 'ne'
        },
        'type': {
            'S': 'jurisdiction'
        }
    }
];


/*
 * Double casting to allow us to pass a mock in for the real thing
 */
const asDynamoDBClient = (mock: ReturnType<typeof mockClient>) =>
    mock as unknown as DynamoDBClient;


describe('JurisdictionClient', () => {
    let jurisdictionClient: JurisdictionClient;
    let mockDynamoDBClient: ReturnType<typeof mockClient>;


    beforeAll(async () => {
        process.env.DEBUG = 'true';
        process.env.COMPACTS = '["aslp", "octp", "coun"]';
        process.env.DATA_EVENT_TABLE_NAME = 'data-table';
        process.env.COMPACT_CONFIGURATION_TABLE_NAME = 'compact-table';
        process.env.AWS_REGION = 'us-east-1';

    });

    beforeEach(() => {
        jest.clearAllMocks();
    });

    it('should return jurisdiction data from the dynamo', async () => {
        mockDynamoDBClient = mockClient(DynamoDBClient);

        mockDynamoDBClient.on(QueryCommand).resolves({
            Items: SAMPLE_JURISDICTION_ITEMS
        });


        jurisdictionClient = new JurisdictionClient({
            logger: new Logger(),
            dynamoDBClient: asDynamoDBClient(mockDynamoDBClient)
        });

        const jurisdictions = await jurisdictionClient.getJurisdictionConfigurations('aslp');

        expect(jurisdictions).toHaveLength(2);
        expect(mockDynamoDBClient).toHaveReceivedCommandWith(
            QueryCommand,
            {
                TableName: 'compact-table',
                KeyConditionExpression: 'pk = :pk and begins_with (sk, :sk)',
                ExpressionAttributeValues: {
                    ':pk': { 'S': 'aslp#CONFIGURATION' },
                    ':sk': { 'S': 'aslp#JURISDICTION#' }
                }
            }
        );

        // Verify we got the expected jurisdictions back
        expect(jurisdictions.map((j) => j.jurisdictionName)).toEqual(expect.arrayContaining(['Ohio', 'Nebraska']));
    });

    it('should return an empty array if no records in dynamo', async () => {
        mockDynamoDBClient = mockClient(DynamoDBClient);

        mockDynamoDBClient.on(QueryCommand).resolves({});

        jurisdictionClient = new JurisdictionClient({
            logger: new Logger(),
            dynamoDBClient: asDynamoDBClient(mockDynamoDBClient)
        });

        const jurisdictions = await jurisdictionClient.getJurisdictionConfigurations('aslp');

        expect(jurisdictions).toEqual([]);
    });

    it('should get a specific jurisdiction configuration', async () => {
        mockDynamoDBClient = mockClient(DynamoDBClient);

        mockDynamoDBClient.on(GetItemCommand).resolves({
            Item: SAMPLE_JURISDICTION_ITEMS[0]
        });

        jurisdictionClient = new JurisdictionClient({
            logger: new Logger(),
            dynamoDBClient: asDynamoDBClient(mockDynamoDBClient)
        });

        const jurisdiction = await jurisdictionClient.getJurisdictionConfiguration('aslp', 'oh');

        expect(mockDynamoDBClient).toHaveReceivedCommandWith(
            GetItemCommand,
            {
                TableName: 'compact-table',
                Key: {
                    'pk': { S: 'aslp#CONFIGURATION' },
                    'sk': { S: 'aslp#JURISDICTION#oh' }
                }
            }
        );

        expect(jurisdiction.jurisdictionName).toBe('Ohio');
        expect(jurisdiction.postalAbbreviation).toBe('oh');
    });

    it('should throw error when jurisdiction not found', async () => {
        mockDynamoDBClient = mockClient(DynamoDBClient);

        mockDynamoDBClient.on(GetItemCommand).resolves({
            Item: undefined
        });

        jurisdictionClient = new JurisdictionClient({
            logger: new Logger(),
            dynamoDBClient: asDynamoDBClient(mockDynamoDBClient)
        });

        await expect(jurisdictionClient.getJurisdictionConfiguration('aslp', 'xx'))
            .rejects
            .toThrow('Jurisdiction configuration not found for xx');
    });

    it('should convert jurisdiction postal code to lowercase', async () => {
        mockDynamoDBClient = mockClient(DynamoDBClient);

        mockDynamoDBClient.on(GetItemCommand).resolves({
            Item: SAMPLE_JURISDICTION_ITEMS[0]
        });

        jurisdictionClient = new JurisdictionClient({
            logger: new Logger(),
            dynamoDBClient: asDynamoDBClient(mockDynamoDBClient)
        });

        await jurisdictionClient.getJurisdictionConfiguration('aslp', 'OH');

        expect(mockDynamoDBClient).toHaveReceivedCommandWith(
            GetItemCommand,
            {
                TableName: 'compact-table',
                Key: {
                    'pk': { S: 'aslp#CONFIGURATION' },
                    'sk': { S: 'aslp#JURISDICTION#oh' }
                }
            }
        );
    });
});
