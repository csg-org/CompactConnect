/*
 * Jurisdiction Client that can retrieve jurisdiction configuration data from the compact configuration
 * DynamoDB table.
 */
import { Logger } from '@aws-lambda-powertools/logger';
import { DynamoDBClient, QueryCommand, ScanCommand } from '@aws-sdk/client-dynamodb';
import { unmarshall } from '@aws-sdk/util-dynamodb';
import { EnvironmentVariablesService } from './environment-variables-service';
import { IJurisdiction, ILicenseErrorEventRecord, ILicenseValidationErrorEventRecord } from './models';

const environmentVariables = new EnvironmentVariablesService();


interface JurisdictionClientProps {
    logger: Logger;
    dynamoDBClient: DynamoDBClient;
}


export class JurisdictionClient {
    private readonly dynamoDBClient: DynamoDBClient;

    public constructor(props: JurisdictionClientProps) {
        this.dynamoDBClient = props.dynamoDBClient;
    }

    /*
     * Queries the table for configured jurisdictions in the given compact
     */
    public async getJurisdictions(
        compact: string,
    ): Promise<IJurisdiction[]> {
        const resp = await this.dynamoDBClient.send(new QueryCommand({
            TableName: environmentVariables.getCompactconfigurationTableName(),
            Select: 'ALL_ATTRIBUTES',
            KeyConditionExpression: 'pk = :pk and begins_with (sk, :sk)',
            ExpressionAttributeValues: {
                ':pk': { 'S': `${compact}#CONFIGURATION` },
                ':sk': { 'S': `${compact}#JURISDICTION#` },
            }
        }));

        return resp.Items?.map((item) => unmarshall(item) as IJurisdiction) || [];
    }
}
