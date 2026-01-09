/*
 * Jurisdiction Client that can retrieve jurisdiction configuration data from the compact configuration
 * DynamoDB table.
 */
import { Logger } from '@aws-lambda-powertools/logger';
import { DynamoDBClient, QueryCommand, GetItemCommand } from '@aws-sdk/client-dynamodb';
import { unmarshall } from '@aws-sdk/util-dynamodb';
import { EnvironmentVariablesService } from './environment-variables-service';
import { IJurisdiction } from './models';

const environmentVariables = new EnvironmentVariablesService();

interface JurisdictionClientProps {
    logger: Logger;
    dynamoDBClient: DynamoDBClient;
}

export class JurisdictionClient {
    private readonly logger: Logger;
    private readonly dynamoDBClient: DynamoDBClient;
    private readonly tableName: string;

    public constructor(props: JurisdictionClientProps) {
        this.logger = props.logger;
        this.dynamoDBClient = props.dynamoDBClient;
        this.tableName = environmentVariables.getCompactConfigurationTableName();
    }

    /*
     * Queries the table for configured jurisdictions in the given compact
     */
    public async getJurisdictionConfigurations(
        compactAbbr: string
    ): Promise<IJurisdiction[]> {
        const resp = await this.dynamoDBClient.send(new QueryCommand({
            TableName: this.tableName,
            Select: 'ALL_ATTRIBUTES',
            KeyConditionExpression: 'pk = :pk and begins_with (sk, :sk)',
            ExpressionAttributeValues: {
                ':pk': { 'S': `${compactAbbr}#CONFIGURATION` },
                ':sk': { 'S': `${compactAbbr}#JURISDICTION#` },
            }
        }));

        return resp.Items?.map((item) => unmarshall(item) as IJurisdiction) || [];
    }

    /**
     * Get a specific jurisdiction configuration
     * 
     * @param compact - The compact abbreviation
     * @param jurisdiction - The jurisdiction postal abbreviation
     * @returns The jurisdiction configuration
     * @throws CCNotFoundException if the jurisdiction configuration is not found
     */
    public async getJurisdictionConfiguration(compact: string, jurisdiction: string): Promise<IJurisdiction> {
        this.logger.info('Getting jurisdiction configuration', { compact, jurisdiction });

        const response = await this.dynamoDBClient.send(
            new GetItemCommand({
                TableName: this.tableName,
                Key: {
                    'pk': { S: `${compact}#CONFIGURATION` },
                    'sk': { S: `${compact}#JURISDICTION#${jurisdiction.toLowerCase()}` }
                }
            })
        );

        if (!response.Item) {
            throw new Error(`Jurisdiction configuration not found for ${jurisdiction}`);
        }

        return unmarshall(response.Item) as IJurisdiction;

    }
}
