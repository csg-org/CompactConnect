import { Logger } from '@aws-lambda-powertools/logger';
import {
    AttributeValue,
    BatchGetItemCommand,
    DynamoDBClient,
    QueryCommand,
    QueryCommandInput
} from '@aws-sdk/client-dynamodb';
import { unmarshall } from '@aws-sdk/util-dynamodb';

import { EnvironmentVariablesService } from './environment-variables-service';
import { InvoiceCategory, InvoiceLineItem, LicenseUploadsForMonth } from './models/invoice';

const environmentVariables = new EnvironmentVariablesService();
const BATCH_GET_LIMIT = 100;

interface InvoiceClientProps {
    logger: Logger;
    dynamoDBClient: DynamoDBClient;
}

interface LicenseRecord {
    pk?: string;
    sk?: string;
    givenName?: string;
    familyName?: string;
    jurisdiction?: string;
    licenseNumber?: string;
    licenseType?: string;
    /** What the jurisdiction reported. The calculated compactEligibility field is not stored. */
    jurisdictionUploadedCompactEligibility?: string;
    firstUploadDate?: string;
    dateOfRenewal?: string;
}

type LicenseKey = Record<string, AttributeValue>;

/*
 * Reads compact-eligible license uploads for a billing month.
 *
 * licenseUploadDateGSI partition key is C#{compact}#J#{jurisdiction}#D#{YYYY-MM}.
 * License rows are indexed by firstUploadDate. License update rows for upload events, including
 * renewals, are indexed by the update createDate. The index only projects providerId, so each hit
 * is resolved to the current license row and billed when that license was first uploaded or renewed
 * during the month.
 *
 * A license is billable when the jurisdiction uploaded it as multi-state
 * (jurisdictionUploadedCompactEligibility) and it was first uploaded or renewed in the billing
 * month. Expiration and encumbrance do not change the invoice.
 */
export class InvoiceClient {
    private readonly logger: Logger;
    private readonly dynamoDBClient: DynamoDBClient;

    public constructor(props: InvoiceClientProps) {
        this.logger = props.logger;
        this.dynamoDBClient = props.dynamoDBClient;
    }

    public async getLicenseUploadsForMonth(
        compact: string,
        jurisdiction: string,
        billingMonth: string
    ): Promise<LicenseUploadsForMonth> {
        const partitionKey = `C#${compact}#J#${jurisdiction}#D#${billingMonth}`;

        this.logger.info('Querying license uploads for invoice', {
            compact,
            jurisdiction,
            billingMonth,
            partitionKey,
        });

        const gsiItems = await this.queryLicenseUploadIndex(partitionKey);
        const byLicenseType: Record<string, InvoiceLineItem[]> = {};
        const uploadedByLicenseType: Record<string, number> = {};

        if (gsiItems.length === 0) {
            return {
                lineItems: [],
                totalUploaded: 0,
                byLicenseType,
                uploadedByLicenseType,
            };
        }

        const keys = this.licenseKeysForUploads(compact, jurisdiction, gsiItems);
        const records = await this.batchGetLicenses(keys);
        const recordsByKey = new Map<string, LicenseRecord>();

        for (const record of records) {
            if (record.pk && record.sk) {
                recordsByKey.set(`${record.pk}|${record.sk}`, record);
            }
        }

        const lineItems: InvoiceLineItem[] = [];

        for (const key of keys) {
            const record = recordsByKey.get(`${key.pk.S}|${key.sk.S}`);

            // Ineligible and otherwise non-billable licenses still count as uploads for this license type.
            if (record?.licenseType) {
                uploadedByLicenseType[record.licenseType] = (uploadedByLicenseType[record.licenseType] ?? 0) + 1;
            }

            const lineItem = record
                ? this.toLineItem(record, jurisdiction, billingMonth)
                : undefined;

            if (!lineItem) {
                continue;
            }

            lineItems.push(lineItem);
            if (!byLicenseType[lineItem.licenseType]) {
                byLicenseType[lineItem.licenseType] = [];
            }
            byLicenseType[lineItem.licenseType].push(lineItem);
        }

        return {
            lineItems,
            totalUploaded: gsiItems.length,
            byLicenseType,
            uploadedByLicenseType,
        };
    }

    private async queryLicenseUploadIndex(partitionKey: string): Promise<Record<string, AttributeValue>[]> {
        const tableName = environmentVariables.getProviderTableName();
        const items: Record<string, AttributeValue>[] = [];
        let exclusiveStartKey: Record<string, AttributeValue> | undefined;

        do {
            const input: QueryCommandInput = {
                TableName: tableName,
                IndexName: 'licenseUploadDateGSI',
                KeyConditionExpression: 'licenseUploadDateGSIPK = :pk',
                ExpressionAttributeValues: {
                    ':pk': { S: partitionKey },
                },
            };

            if (exclusiveStartKey) {
                input.ExclusiveStartKey = exclusiveStartKey;
            }

            const response = await this.dynamoDBClient.send(new QueryCommand(input));

            items.push(...(response.Items ?? []));
            exclusiveStartKey = response.LastEvaluatedKey;
        } while (exclusiveStartKey);

        return items;
    }

    private licenseKeysForUploads(
        compact: string,
        jurisdiction: string,
        gsiItems: Record<string, AttributeValue>[]
    ): LicenseKey[] {
        const keys: LicenseKey[] = [];
        const seen = new Set<string>();

        for (const item of gsiItems) {
            const sortKey = item.licenseUploadDateGSISK?.S ?? '';
            const providerId = item.providerId?.S ?? this.providerIdFromSortKey(sortKey);
            const licenseTypeAbbr = this.licenseTypeAbbrFromSortKey(sortKey);

            if (!providerId || !licenseTypeAbbr) {
                this.logger.warn('Skipping license upload index item with no provider or license type', {
                    sortKey,
                });
                continue;
            }

            const key: LicenseKey = {
                pk: { S: `${compact}#PROVIDER#${providerId}` },
                sk: { S: `${compact}#PROVIDER#license/${jurisdiction}/${licenseTypeAbbr}#` },
            };
            const keyId = `${key.pk.S}|${key.sk.S}`;

            if (seen.has(keyId)) {
                continue;
            }

            seen.add(keyId);
            keys.push(key);
        }

        return keys;
    }

    private async batchGetLicenses(keys: LicenseKey[]): Promise<LicenseRecord[]> {
        if (keys.length === 0) {
            return [];
        }

        const tableName = environmentVariables.getProviderTableName();
        const records: LicenseRecord[] = [];

        for (let offset = 0; offset < keys.length; offset += BATCH_GET_LIMIT) {
            let pending = keys.slice(offset, offset + BATCH_GET_LIMIT);

            while (pending.length > 0) {
                const response = await this.dynamoDBClient.send(new BatchGetItemCommand({
                    RequestItems: {
                        [tableName]: {
                            Keys: pending,
                        },
                    },
                }));

                const fetched = response.Responses?.[tableName] ?? [];

                records.push(...fetched.map((item) => unmarshall(item) as LicenseRecord));
                pending = response.UnprocessedKeys?.[tableName]?.Keys ?? [];
            }
        }

        return records;
    }

    private toLineItem(
        record: LicenseRecord,
        jurisdiction: string,
        billingMonth: string
    ): InvoiceLineItem | undefined {
        if (record.jurisdictionUploadedCompactEligibility !== 'eligible') {
            return undefined;
        }

        const category = this.categoryForBillingMonth(record, billingMonth);

        if (!category || !record.licenseType || !record.licenseNumber) {
            return undefined;
        }

        return {
            givenName: record.givenName ?? '',
            familyName: record.familyName ?? '',
            homeState: (record.jurisdiction ?? jurisdiction).toUpperCase(),
            licenseNumber: record.licenseNumber,
            licenseType: record.licenseType,
            category,
            fee: environmentVariables.getFeePerLicense(),
        };
    }

    private categoryForBillingMonth(record: LicenseRecord, billingMonth: string): InvoiceCategory | undefined {
        if (this.isInBillingMonth(record.firstUploadDate, billingMonth)) {
            return 'new';
        }
        if (this.isInBillingMonth(record.dateOfRenewal, billingMonth)) {
            return 'renewal';
        }
        return undefined;
    }

    private isInBillingMonth(value: string | undefined, billingMonth: string): boolean {
        if (!value) {
            return false;
        }
        if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
            return value.startsWith(billingMonth);
        }

        const parsed = new Date(value);

        if (Number.isNaN(parsed.getTime())) {
            return false;
        }

        const month = String(parsed.getUTCMonth() + 1).padStart(2, '0');

        return `${parsed.getUTCFullYear()}-${month}` === billingMonth;
    }

    private licenseTypeAbbrFromSortKey(sortKey: string): string | undefined {
        return sortKey.match(/#LT#([^#]+)#PID#/)?.[1];
    }

    private providerIdFromSortKey(sortKey: string): string | undefined {
        return sortKey.match(/#PID#(.+)$/)?.[1];
    }
}
