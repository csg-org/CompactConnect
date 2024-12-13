import { Logger } from '@aws-lambda-powertools/logger';
import { DynamoDBClient, QueryCommand } from '@aws-sdk/client-dynamodb';
import { unmarshall } from '@aws-sdk/util-dynamodb';
import { EnvironmentVariablesService } from './environment-variables-service';
import { IIngestFailureEventRecord, IValidationErrorEventRecord } from './models';

const environmentVariables = new EnvironmentVariablesService();


interface EventClientProps {
    logger: Logger;
    dynamoDBClient: DynamoDBClient;
}


/*
 * Event Client that can retrieve validation error and ingest failure events from the License Events
 * DynamoDB table.
 */
export class EventClient {
    private readonly logger: Logger;
    private readonly dynamoDBClient: DynamoDBClient;

    public constructor(props: EventClientProps) {
        this.logger = props.logger;
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
        // Uncomment to manually force today's events into the time window (for development/testing)
        // today.setUTCDate(today.getUTCDate() + 1);
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
     * Returns timestamps for the beginning and end of the previous UTC week (rolling)
     */
    public getLastWeekTimestamps() {
        const today: Date = new Date();
        const lastWeek: Date = new Date();

        today.setUTCHours(0, 0, 0, 0);
        lastWeek.setUTCHours(0, 0, 0, 0);

        lastWeek.setUTCDate(today.getUTCDate() - 7);
        // Uncomment to manually force today's events into the time window (for development/testing)
        // today.setUTCDate(today.getUTCDate() + 1);
        return [
            Number.parseInt(
                (lastWeek.valueOf()/1000).toString()
            ),
            Number.parseInt(
                (today.valueOf()/1000).toString()
            )
        ];
    }

    /*
     * Queries the data event table for validation errors by looking for validation errors for the
     * given compact/jurisdiction in the given time window.
     */
    public async getValidationErrors(
        compact: string,
        jurisdiction: string,
        startTimeStamp: number,
        endTimeStamp: number
    ): Promise<IValidationErrorEventRecord[]> {
        this.logger.info('Getting validation errors', {
            compact: compact,
            jurisdiction: jurisdiction,
            start_time_stamp: startTimeStamp,
            end_time_stamp: endTimeStamp,
        });
        const tableName = environmentVariables.getDataEventTableName();
        const resp = await this.dynamoDBClient.send(new QueryCommand({
            TableName: tableName,
            Select: 'ALL_ATTRIBUTES',
            // We don't really want to present more than 100 errors in an email, so we won't bother
            // querying that many up
            Limit: 100,
            KeyConditionExpression: 'pk = :pk and sk BETWEEN :skBegin and :skEnd',
            ExpressionAttributeValues: {
                ':pk': { 'S': `COMPACT#${compact}#JURISDICTION#${jurisdiction}` },
                ':skBegin': { 'S': `TYPE#license.validation-error#TIME#${startTimeStamp}#` },
                ':skEnd': { 'S': `TYPE#license.validation-error#TIME#${endTimeStamp}#` },
            }
        }));

        return resp.Items?.map((item) => unmarshall(item) as IValidationErrorEventRecord) || [];
    }

    /*
     * Queries the data event table for ingest failures by looking for each comp
     */
    public async getIngestFailures(
        compact: string,
        jurisdiction: string,
        startTimeStamp: number,
        endTimeStamp: number
    ): Promise<IIngestFailureEventRecord[]> {
        this.logger.info('Getting ingest failures', {
            compact: compact,
            jurisdiction: jurisdiction,
            start_time_stamp: startTimeStamp,
            end_time_stamp: endTimeStamp,
        });
        const resp = await this.dynamoDBClient.send(new QueryCommand({
            TableName: environmentVariables.getDataEventTableName(),
            Select: 'ALL_ATTRIBUTES',
            // We don't really want to present more than 100 errors in an email, so we won't bother
            // querying that many up
            Limit: 100,
            KeyConditionExpression: 'pk = :pk and sk BETWEEN :skBegin and :skEnd',
            ExpressionAttributeValues: {
                ':pk': { 'S': `COMPACT#${compact}#JURISDICTION#${jurisdiction}` },
                ':skBegin': { 'S': `TYPE#license.ingest-failure#TIME#${startTimeStamp}#` },
                ':skEnd': { 'S': `TYPE#license.ingest-failure#TIME#${endTimeStamp}#` },
            }
        }));

        return resp.Items?.map((item) => unmarshall(item) as IIngestFailureEventRecord) || [];
    }

    public async getEvents(compact: string, jurisdiction: string, startTimeStamp: number, endTimeStamp: number) {
        this.logger.info('Gathering events', {
            compact: compact,
            jurisdiction: jurisdiction,
            start_time_stamp: startTimeStamp,
            end_time_stamp: endTimeStamp,
        });

        const validationPromise = this.getValidationErrors(
            compact, jurisdiction, startTimeStamp, endTimeStamp
        );

        const ingestPromise = this.getIngestFailures(
            compact, jurisdiction, startTimeStamp, endTimeStamp
        );
        const [ validationErrors, ingestFailures ] = await Promise.all([validationPromise, ingestPromise]);

        return {
            ingestFailures: ingestFailures,
            validationErrors: validationErrors,
        };
    }
}
