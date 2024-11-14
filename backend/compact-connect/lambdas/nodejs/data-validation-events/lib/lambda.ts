import type { LambdaInterface } from '@aws-lambda-powertools/commons/lib/esm/types';
import { Logger } from '@aws-lambda-powertools/logger';
import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { SESClient } from '@aws-sdk/client-ses';
import { Context, EventBridgeEvent } from 'aws-lambda';

import { EnvironmentVariablesService } from './environment-variables-service';
import { JurisdictionClient } from './jurisdiction-client';
import { ReportEmailer } from './report-emailer';
import { EventClient } from './event-client';

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
    private readonly eventClient: EventClient;
    private readonly reportEmailer: ReportEmailer;

    constructor(props: LambdaProperties) {
        this.jurisdictionClient = new JurisdictionClient({
            logger: logger,
            dynamoDBClient: props.dynamoDBClient,
        });
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
        logger.debug('Context wait for event loop', { waitForEmptyEventLoop: context.callbackWaitsForEmptyEventLoop });

        const [ startTimeStamp, endTimeStamp ] = this.eventClient.getYesterdayTimestamps();

        for (const compact of environmentVariables.getCompacts()) {
            const jurisdictions = await this.jurisdictionClient.getJurisdictions(compact);

            for (const jurisdiction of jurisdictions) {
                const ingestEvents = await this.getEvents(
                    compact, jurisdiction.postalAbbreviation, startTimeStamp, endTimeStamp
                );

                const messageId = await this.reportEmailer.sendReportEmail(
                    ingestEvents, jurisdiction.jurisdictionOperationsTeamEmails
                );

                logger.info('Sent email', { compact: compact, jurisdiction: jurisdiction, messageId: messageId });
            }
        }

        logger.info('Completing handler');
    }

    private async getEvents(compact: string, jurisdiction: string, startTimeStamp: number, endTimeStamp: number) {
        const validationErrors = await this.eventClient.getValidationErrors(
            compact, jurisdiction, startTimeStamp, endTimeStamp
        );

        const ingestFailures = await this.eventClient.getIngestFailures(
            compact, jurisdiction, startTimeStamp, endTimeStamp
        );

        return {
            ingestFailures: ingestFailures,
            validationErrors: validationErrors,
        };
    }
}
