import type { LambdaInterface } from '@aws-lambda-powertools/commons/lib/esm/types';
import { Logger } from '@aws-lambda-powertools/logger';
import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { SESClient } from '@aws-sdk/client-ses';
import { Context } from 'aws-lambda';

import { EnvironmentVariablesService } from './environment-variables-service';
import { JurisdictionClient } from './jurisdiction-client';
import { IEventBridgeEvent } from './models/event-bridge-event-detail';
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
    public async handler(event: IEventBridgeEvent, context: Context): Promise<any> {
        logger.info('Processing event', { event: event });
        logger.debug('Context wait for event loop', { wait_for_empty_event_loop: context.callbackWaitsForEmptyEventLoop });

        const [ startTimeStamp, endTimeStamp ] = this.eventClient.getYesterdayTimestamps();

        // Loop over each compact the system knows about
        for (const compact of environmentVariables.getCompacts()) {
            const jurisdictionConfigs = await this.jurisdictionClient.getJurisdictionConfigurations(compact);

            // Loop over each jurisdiction that we have contacts configured for
            for (const jurisdictionConfig of jurisdictionConfigs) {
                const ingestEvents = await this.eventClient.getEvents(
                    compact, jurisdictionConfig.postalAbbreviation, startTimeStamp, endTimeStamp
                );

                // If there were any issues, send a report email summarizing them
                if (ingestEvents.ingestFailures.length || ingestEvents.validationErrors.length) {
                    const messageId = await this.reportEmailer.sendReportEmail(
                        ingestEvents,
                        compact,
                        jurisdictionConfig.jurisdictionName,
                        jurisdictionConfig.jurisdictionOperationsTeamEmails
                    );

                    logger.info(
                        'Sent event summary email',
                        {
                            compact: compact,
                            jurisdiction: jurisdictionConfig.postalAbbreviation,
                            message_id: messageId
                        }
                    );
                } else {
                    logger.info(
                        'No events in 24 hours',
                        {
                            compact: compact,
                            jurisdiction: jurisdictionConfig.postalAbbreviation
                        }
                    );
                    const eventType = event.eventType;

                    // If this is a weekly run and there have been no issues all week, we send an "All's Well" report
                    if (eventType === 'weekly') {
                        const [ weekStartStamp, weekEndStamp ] = this.eventClient.getLastWeekTimestamps();
                        const weeklyIngestEvents = await this.eventClient.getEvents(
                            compact,
                            jurisdictionConfig.postalAbbreviation,
                            weekStartStamp,
                            weekEndStamp
                        );

                        if (!weeklyIngestEvents.ingestFailures.length && !weeklyIngestEvents.validationErrors.length) {
                            const messageId = await this.reportEmailer.sendAllsWellEmail(
                                compact,
                                jurisdictionConfig.jurisdictionName,
                                jurisdictionConfig.jurisdictionOperationsTeamEmails
                            );

                            logger.info(
                                'Sent alls well email',
                                {
                                    compact: compact,
                                    jurisdiction: jurisdictionConfig.postalAbbreviation,
                                    message_id: messageId
                                }
                            );
                        }
                    }
                }
            }
        }
        logger.info('Completing handler');
    }
}
