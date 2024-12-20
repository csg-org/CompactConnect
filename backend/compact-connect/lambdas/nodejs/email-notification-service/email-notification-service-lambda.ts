import type { LambdaInterface } from '@aws-lambda-powertools/commons/lib/esm/types';
import { Logger } from '@aws-lambda-powertools/logger';
import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { SESClient } from '@aws-sdk/client-ses';
import { Context } from 'aws-lambda';

import { EnvironmentVariablesService } from '../lib/environment-variables-service';
import { JurisdictionClient } from '../lib/jurisdiction-client';

const environmentVariables = new EnvironmentVariablesService();
const logger = new Logger({ logLevel: environmentVariables.getLogLevel() });


interface LambdaProperties {
    dynamoDBClient: DynamoDBClient;
    sesClient: SESClient;
}

/*
 * Basic Lambda class to integrate the primary lambda entrypoint logic, logging, and error handling
 */
export class Lambda implements LambdaInterface {
    private readonly jurisdictionClient: JurisdictionClient;

    constructor(props: LambdaProperties) {
        this.jurisdictionClient = new JurisdictionClient({
            logger: logger,
            dynamoDBClient: props.dynamoDBClient,
        });
    }

    @logger.injectLambdaContext({ resetKeys: true })
    public async handler(event: any, context: Context): Promise<any> {
        logger.info('Processing event', { event: event });

        // For now, just return a 200
        logger.info('Completing handler');
        return {
            statusCode: 200,
            body: 'Success',
        };


    }
}
