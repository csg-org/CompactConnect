import type { LambdaInterface } from '@aws-lambda-powertools/commons/lib/esm/types';
import { Logger } from '@aws-lambda-powertools/logger';
import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { Context, EventBridgeEvent } from 'aws-lambda';

import { EnvironmentVariablesService } from './environment-variables-service';
import { ILicenseErrorEventRecord } from './models';
import { ReportEmailer } from './report-emailer';
import { EventClient } from './event-client';

const environmentVariables = new EnvironmentVariablesService();
const logger = new Logger({ logLevel: environmentVariables.getLogLevel() });


interface LambdaOptions {
    dynamoDBClient: DynamoDBClient,
}

/*
 * Basic Lambda class to integrate the primary lambda entrypoint logic, logging, and error handling
 */
export class Lambda implements LambdaInterface {
    private readonly dynamoDBClient: DynamoDBClient;
    private readonly sesClient: SESClient;
    private readonly eventClient: EventClient;
    private readonly reportEmailer: ReportEmailer;

    constructor(props: LambdaProperties) {
        this.dynamoDBClient = props.dynamoDBClient;
        this.sesClient = props.sesClient;
        this.eventClient = new EventClient({
            logger: logger,
            dynamoDBClient: props.dynamoDBClient,
        });
        this.reportEmailer = new ReportEmailer({
            logger: logger,
            sesClient: props.sesClient,
        });
    }

    @logger.injectLambdaContext({ resetKeys: true })
    public async handler(event: EventBridgeEvent<string, any>, context: Context): Promise<any> {
        logger.info('Processing event', { event: event });

        // const resp = await this.dynamoDBClient.send(new ScanCommand({
        //     TableName: environmentVariables.getDataEventTableName(),
        //     Select: 'ALL_ATTRIBUTES',
        // }));
        //
        // // Transform the items using unmarshall
        // const transformedItems = resp.Items?.map((item) => unmarshall(item)) || [];

        const [ startTimeStamp, endTimeStamp ] = this.eventClient.getYesterdayTimestamps();

        for (jurisdiction of jurisdictions) {
            const errors: Promise<ILicenseErrorEventRecord> = this.eventClient.getValidationErrors(
                compact,
                jurisdiction,
                startTimeStamp,
                endTimeStamp
            );
            errors.then(
                this.reportEmailer.sendReportEmail(error);
            )
        }

        logger.debug('Retrieved records', { items: transformedItems });

        return transformedItems;
    }
}
