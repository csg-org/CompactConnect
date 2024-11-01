import type { LambdaInterface } from '@aws-lambda-powertools/commons/lib/esm/types';
import { Logger } from '@aws-lambda-powertools/logger';
import { DynamoDBClient, ScanCommand } from '@aws-sdk/client-dynamodb';
import { unmarshall } from '@aws-sdk/util-dynamodb';
import { Context, EventBridgeEvent } from 'aws-lambda';

import { EnvironmentVariablesService } from './environment-variables-service';

const environmentVariables = new EnvironmentVariablesService();
const logger = new Logger({ logLevel: environmentVariables.getLogLevel() });


interface LambdaOptions {
    dynamoDBClient: DynamoDBClient,
}

export class Lambda implements LambdaInterface {
    private dynamoDBClient: DynamoDBClient;

    constructor(lambdaOptions: LambdaOptions) {
        this.dynamoDBClient = lambdaOptions.dynamoDBClient;
    }

    @logger.injectLambdaContext({ resetKeys: true })
    public async handler(event: EventBridgeEvent<string, any>, context: Context): Promise<any> {
        logger.info('Processing event', { event: event });

        const resp = await this.dynamoDBClient.send(new ScanCommand({
            TableName: environmentVariables.getDataEventTableName(),
            Select: 'ALL_ATTRIBUTES',
        }));

        // Transform the items using unmarshall
        const transformedItems = resp.Items?.map((item) => unmarshall(item)) || [];

        logger.debug('Retrieved records', { items: transformedItems });

        return transformedItems;
    }
}
