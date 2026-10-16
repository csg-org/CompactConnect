import { Logger } from '@aws-lambda-powertools/logger';
import { BatchGetItemCommand, DynamoDBClient, QueryCommand } from '@aws-sdk/client-dynamodb';
import { mockClient } from 'aws-sdk-client-mock';
import 'aws-sdk-client-mock-jest';
import { beforeAll, beforeEach, describe, expect, it, jest } from '@jest/globals';

import { InvoiceClient } from '../../lib/invoice-client';
import {
    SAMPLE_GSI_LICENSE_UPLOAD_RECORD,
    SAMPLE_GSI_LICENSE_UPLOAD_RECORD_CORRECTION,
    SAMPLE_GSI_LICENSE_UPLOAD_RECORD_ESTHETICIAN,
    SAMPLE_GSI_LICENSE_UPLOAD_RECORD_INELIGIBLE,
    SAMPLE_GSI_LICENSE_UPLOAD_RECORD_RENEWAL,
    SAMPLE_LICENSE_RECORD_CORRECTION,
    SAMPLE_LICENSE_RECORD_ESTHETICIAN,
    SAMPLE_LICENSE_RECORD_INELIGIBLE,
    SAMPLE_LICENSE_RECORD_NEW,
    SAMPLE_LICENSE_RECORD_RENEWAL
} from '../sample-records';

const asDynamoDBClient = (mock: ReturnType<typeof mockClient>) =>
    mock as unknown as DynamoDBClient;

const BILLING_MONTH = '2024-09';
const GSI_PK = 'C#cosm#J#oh#D#2024-09';

describe('InvoiceClient — getLicenseUploadsForMonth', () => {
    let mockDynamoDBClient: ReturnType<typeof mockClient>;

    beforeAll(() => {
        process.env.DEBUG = 'true';
        process.env.PROVIDER_TABLE_NAME = 'provider-table';
        process.env.FEE_PER_LICENSE = '25';
    });

    beforeEach(() => {
        jest.clearAllMocks();
        mockDynamoDBClient = mockClient(DynamoDBClient);
    });

    const client = () => new InvoiceClient({
        logger: new Logger(),
        dynamoDBClient: asDynamoDBClient(mockDynamoDBClient),
    });

    const queryGsi = (items: object[], lastEvaluatedKey?: Record<string, { S: string }>) => {
        mockDynamoDBClient.on(QueryCommand).callsFake(async () => ({
            Items: items,
            ...(lastEvaluatedKey ? { LastEvaluatedKey: lastEvaluatedKey } : {}),
        }));
    };

    const batchGet = (records: object[]) => {
        mockDynamoDBClient.on(BatchGetItemCommand).callsFake(async () => ({
            Responses: {
                'provider-table': records,
            },
        }));
    };

    it('should query the license upload date index for the compact, jurisdiction, and billing month', async () => {
        queryGsi([]);

        await client().getLicenseUploadsForMonth('cosm', 'oh', BILLING_MONTH);

        expect(mockDynamoDBClient).toHaveReceivedCommandWith(QueryCommand, {
            TableName: 'provider-table',
            IndexName: 'licenseUploadDateGSI',
            KeyConditionExpression: 'licenseUploadDateGSIPK = :pk',
            ExpressionAttributeValues: {
                ':pk': { S: GSI_PK },
            },
        });
    });

    it('should follow LastEvaluatedKey until the index query is exhausted', async () => {
        const pageBreak = {
            licenseUploadDateGSIPK: { S: GSI_PK },
            licenseUploadDateGSISK: SAMPLE_GSI_LICENSE_UPLOAD_RECORD.licenseUploadDateGSISK,
        };

        mockDynamoDBClient.on(QueryCommand)
            .resolvesOnce({
                Items: [SAMPLE_GSI_LICENSE_UPLOAD_RECORD],
                LastEvaluatedKey: pageBreak,
            })
            .resolvesOnce({
                Items: [SAMPLE_GSI_LICENSE_UPLOAD_RECORD_RENEWAL],
            });
        batchGet([SAMPLE_LICENSE_RECORD_NEW, SAMPLE_LICENSE_RECORD_RENEWAL]);

        const result = await client().getLicenseUploadsForMonth('cosm', 'oh', BILLING_MONTH);

        const secondPage = mockDynamoDBClient.commandCalls(QueryCommand)[1].args[0].input;

        expect(secondPage.ExclusiveStartKey).toEqual(pageBreak);
        expect(result.lineItems.map((item) => item.licenseNumber).sort()).toEqual(['COS-12345', 'COS-67890']);
    });

    it('should return no line items and skip the record fetch when the index is empty', async () => {
        queryGsi([]);

        const result = await client().getLicenseUploadsForMonth('cosm', 'oh', BILLING_MONTH);

        expect(result.lineItems).toEqual([]);
        expect(result.totalUploaded).toEqual(0);
        expect(mockDynamoDBClient).not.toHaveReceivedCommand(BatchGetItemCommand);
    });

    it('should load each license using the provider id and license type abbreviation in the index sort key', async () => {
        queryGsi([SAMPLE_GSI_LICENSE_UPLOAD_RECORD]);
        batchGet([SAMPLE_LICENSE_RECORD_NEW]);

        await client().getLicenseUploadsForMonth('cosm', 'oh', BILLING_MONTH);

        expect(mockDynamoDBClient).toHaveReceivedCommandWith(BatchGetItemCommand, {
            RequestItems: {
                'provider-table': {
                    Keys: [
                        {
                            pk: { S: 'cosm#PROVIDER#provider-uuid-1' },
                            sk: { S: 'cosm#PROVIDER#license/oh/cos#' },
                        },
                    ],
                },
            },
        });
    });

    it('should omit licenses that are not compact eligible', async () => {
        queryGsi([SAMPLE_GSI_LICENSE_UPLOAD_RECORD_INELIGIBLE]);
        batchGet([SAMPLE_LICENSE_RECORD_INELIGIBLE]);

        const result = await client().getLicenseUploadsForMonth('cosm', 'oh', BILLING_MONTH);

        expect(result.lineItems).toEqual([]);
        expect(result.totalUploaded).toEqual(1);
        expect(JSON.stringify(result.lineItems)).not.toContain('COS-00001');
    });

    it('should categorize a license as new when it was first uploaded during the billing month', async () => {
        queryGsi([SAMPLE_GSI_LICENSE_UPLOAD_RECORD]);
        batchGet([SAMPLE_LICENSE_RECORD_NEW]);

        const result = await client().getLicenseUploadsForMonth('cosm', 'oh', BILLING_MONTH);

        expect(result.lineItems).toEqual([
            expect.objectContaining({
                givenName: 'Jane',
                familyName: 'Smith',
                homeState: 'OH',
                licenseNumber: 'COS-12345',
                licenseType: 'cosmetologist',
                category: 'new',
                fee: 25,
            }),
        ]);
    });

    it('should categorize a license as a renewal when it was renewed during the billing month', async () => {
        queryGsi([SAMPLE_GSI_LICENSE_UPLOAD_RECORD_RENEWAL]);
        batchGet([SAMPLE_LICENSE_RECORD_RENEWAL]);

        const result = await client().getLicenseUploadsForMonth('cosm', 'oh', BILLING_MONTH);

        expect(result.lineItems).toEqual([
            expect.objectContaining({
                givenName: 'John',
                familyName: 'Doe',
                homeState: 'OH',
                licenseNumber: 'COS-67890',
                licenseType: 'cosmetologist',
                category: 'renewal',
                fee: 25,
            }),
        ]);
    });

    it('should omit eligible licenses that were neither first uploaded nor renewed in the billing month', async () => {
        queryGsi([SAMPLE_GSI_LICENSE_UPLOAD_RECORD_CORRECTION]);
        batchGet([SAMPLE_LICENSE_RECORD_CORRECTION]);

        const result = await client().getLicenseUploadsForMonth('cosm', 'oh', BILLING_MONTH);

        expect(result.lineItems).toEqual([]);
        expect(result.totalUploaded).toEqual(1);
        expect(JSON.stringify(result)).not.toContain('COS-99999');
    });

    it('should group billable licenses by license type', async () => {
        queryGsi([
            SAMPLE_GSI_LICENSE_UPLOAD_RECORD,
            SAMPLE_GSI_LICENSE_UPLOAD_RECORD_RENEWAL,
            SAMPLE_GSI_LICENSE_UPLOAD_RECORD_INELIGIBLE,
            SAMPLE_GSI_LICENSE_UPLOAD_RECORD_ESTHETICIAN,
            SAMPLE_GSI_LICENSE_UPLOAD_RECORD_CORRECTION,
        ]);
        batchGet([
            SAMPLE_LICENSE_RECORD_NEW,
            SAMPLE_LICENSE_RECORD_RENEWAL,
            SAMPLE_LICENSE_RECORD_INELIGIBLE,
            SAMPLE_LICENSE_RECORD_ESTHETICIAN,
            SAMPLE_LICENSE_RECORD_CORRECTION,
        ]);

        const result = await client().getLicenseUploadsForMonth('cosm', 'oh', BILLING_MONTH);

        expect(result.totalUploaded).toEqual(5);
        expect(result.byLicenseType.cosmetologist.map((item) => item.licenseNumber)).toEqual([
            'COS-12345',
            'COS-67890',
        ]);
        expect(result.byLicenseType.esthetician.map((item) => item.licenseNumber)).toEqual(['EST-11111']);
        expect(result.lineItems).toHaveLength(3);
    });

    it('should bill a license once when the index lists it more than once', async () => {
        queryGsi([SAMPLE_GSI_LICENSE_UPLOAD_RECORD, SAMPLE_GSI_LICENSE_UPLOAD_RECORD]);
        batchGet([SAMPLE_LICENSE_RECORD_NEW]);

        const result = await client().getLicenseUploadsForMonth('cosm', 'oh', BILLING_MONTH);

        expect(result.totalUploaded).toEqual(2);
        expect(result.lineItems.map((item) => item.licenseNumber)).toEqual(['COS-12345']);
    });

    it('should skip index items that do not identify a license', async () => {
        queryGsi([{ licenseUploadDateGSIPK: { S: GSI_PK }}]);

        const result = await client().getLicenseUploadsForMonth('cosm', 'oh', BILLING_MONTH);

        expect(result.lineItems).toEqual([]);
        expect(result.totalUploaded).toEqual(1);
        expect(mockDynamoDBClient).not.toHaveReceivedCommand(BatchGetItemCommand);
    });

    it('should skip an index hit whose license record is missing', async () => {
        queryGsi([SAMPLE_GSI_LICENSE_UPLOAD_RECORD]);
        batchGet([]);

        const result = await client().getLicenseUploadsForMonth('cosm', 'oh', BILLING_MONTH);

        expect(result.lineItems).toEqual([]);
        expect(result.totalUploaded).toEqual(1);
    });

    it('should read the provider id from the index sort key when the attribute is absent', async () => {
        const { providerId: _providerId, ...indexItem } = SAMPLE_GSI_LICENSE_UPLOAD_RECORD;

        queryGsi([indexItem]);
        batchGet([SAMPLE_LICENSE_RECORD_NEW]);

        const result = await client().getLicenseUploadsForMonth('cosm', 'oh', BILLING_MONTH);

        expect(result.lineItems.map((item) => item.licenseNumber)).toEqual(['COS-12345']);
    });

    it('should let DynamoDB errors escape', async () => {
        mockDynamoDBClient.on(QueryCommand).rejects(new Error('DynamoDB error'));

        await expect(client().getLicenseUploadsForMonth('cosm', 'oh', BILLING_MONTH)).rejects.toThrow('DynamoDB error');
    });
});
