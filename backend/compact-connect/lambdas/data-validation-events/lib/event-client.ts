/*
 * Event Client that can retrieve validation error and ingest failure events from the License Events
 * DynamoDB table.
 */
import { Logger } from '@aws-lambda-powertools/logger';
import { DynamoDBClient, QueryCommand, ScanCommand } from '@aws-sdk/client-dynamodb';
import { unmarshall } from '@aws-sdk/util-dynamodb';
import { EnvironmentVariablesService } from './environment-variables-service';
import { ILicenseErrorEventRecord, ILicenseValidationErrorEventRecord } from './models';

const environmentVariables = new EnvironmentVariablesService();


interface EventClientProps {
    logger: Logger;
    dynamoDBClient: DynamoDBClient;
}


export class EventClient {
    private readonly dynamoDBClient: DynamoDBClient;

    public constructor(props: EventClientProps) {
        this.dynamoDBClient = props.dynamoDBClient;
    }

    /*
     * Returns timestamps for the beginning and end of the previous UTC day
     */
    public getYesterdayTimestamps() {
        const today: Date = new Date();
        const yesterday: Date = new Date();

        today.setUTCHours(0, 0, 0, 0);
        yesterday.setUTCHours(0, 0, 0, 0);

        yesterday.setUTCDate(today.getUTCDate() - 1);

        return [
            Number.parseInt(
                (yesterday.valueOf()/1000).toString()
            ),
            Number.parseInt(
                (today.valueOf()/1000).toString()
            )
        ];
    }

    /*
     * Queries the data event table for validation errors by looking for each comp
     */
    public async getValidationErrors(
        compact: string,
        jurisdiction: string,
        startTimeStamp: number,
        endTimeStamp: number
    ): Promise<ILicenseValidationErrorEventRecord[]> {
        const resp = await this.dynamoDBClient.send(new QueryCommand({
            TableName: environmentVariables.getDataEventTableName(),
            Select: 'ALL_ATTRIBUTES',
            KeyConditionExpression: 'pk = :pk and sk BETWEEN :skBegin and sk :skEnd',
            ExpressionAttributeValues: {
                ':pk': { 'S': `COMPACT#${compact}#JURISDICTION#${jurisdiction}` },
                ':skBegin': { 'S': `TYPE#license.validation-error#TIME#${startTimeStamp}#` },
                ':skEnd': { 'S': `TYPE#license.validation-error#TIME#${endTimeStamp}#` },
            }
        }));

        return resp.Items?.map((item) => unmarshall(item) as ILicenseValidationErrorEventRecord) || [];
    }

    /*
     * Queries the data event table for ingest failures by looking for each comp
     */
    public async getIngestFailures(
        compact: string,
        jurisdiction: string,
        startTimeStamp: number,
        endTimeStamp: number
    ): Promise<ILicenseErrorEventRecord[]> {
        const resp = await this.dynamoDBClient.send(new QueryCommand({
            TableName: environmentVariables.getDataEventTableName(),
            Select: 'ALL_ATTRIBUTES',
            KeyConditionExpression: 'pk = :pk and sk BETWEEN :skBegin and sk :skEnd',
            ExpressionAttributeValues: {
                ':pk': { 'S': `COMPACT#${compact}#JURISDICTION#${jurisdiction}` },
                ':skBegin': { 'S': `TYPE#license.ingest-failure#TIME#${startTimeStamp}#` },
                ':skEnd': { 'S': `TYPE#license.ingest-failure#TIME#${endTimeStamp}#` },
            }
        }));

        return resp.Items?.map((item) => unmarshall(item) as ILicenseErrorEventRecord) || [];
    }
}
