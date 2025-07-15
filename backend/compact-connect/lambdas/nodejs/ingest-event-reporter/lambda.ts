import type { LambdaInterface } from '@aws-lambda-powertools/commons/lib/esm/types';
import { Logger } from '@aws-lambda-powertools/logger';
import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { S3Client } from '@aws-sdk/client-s3';
import { SESClient } from '@aws-sdk/client-ses';
import { Context } from 'aws-lambda';

import { EnvironmentVariablesService } from '../lib/environment-variables-service';
import { CompactConfigurationClient } from '../lib/compact-configuration-client';
import { JurisdictionClient } from '../lib/jurisdiction-client';
import { IEventBridgeEvent } from '../lib/models/event-bridge-event-detail';
import { IngestEventEmailService } from '../lib/email';
import { EventClient } from '../lib/event-client';

const environmentVariables = new EnvironmentVariablesService();
const logger = new Logger({ logLevel: environmentVariables.getLogLevel() });

interface LambdaProperties {
    dynamoDBClient: DynamoDBClient;
    sesClient: SESClient;
    s3Client: S3Client;
}

/*
 * Basic Lambda class to integrate the primary lambda entrypoint logic, logging, and error handling
 */
export class Lambda implements LambdaInterface {
    private readonly jurisdictionClient: JurisdictionClient;
    private readonly compactConfigurationClient: CompactConfigurationClient;
    private readonly eventClient: EventClient;
    private readonly emailService: IngestEventEmailService;

    constructor(props: LambdaProperties) {
        this.jurisdictionClient = new JurisdictionClient({
            logger: logger,
            dynamoDBClient: props.dynamoDBClient,
        });

        this.compactConfigurationClient = new CompactConfigurationClient({
            logger: logger,
            dynamoDBClient: props.dynamoDBClient,
        });

        this.eventClient = new EventClient({
            logger: logger,
            dynamoDBClient: props.dynamoDBClient,
        });
        this.emailService = new IngestEventEmailService({
            logger: logger,
            sesClient: props.sesClient,
            s3Client: props.s3Client,
            compactConfigurationClient: this.compactConfigurationClient,
            jurisdictionClient: this.jurisdictionClient
        });
    }

    @logger.injectLambdaContext({ resetKeys: true })
    public async handler(event: IEventBridgeEvent, context: Context): Promise<any> {
        logger.info('Processing event', { event: event });
        logger.debug('Context wait for event loop', { wait_for_empty_event_loop: context.callbackWaitsForEmptyEventLoop });

        const [ startTimeStamp, endTimeStamp ] = this.eventClient.getYesterdayTimestamps();

        // Loop over each compact the system knows about
        for (const compact of environmentVariables.getCompacts()) {
            let compactConfig;

            try {
                compactConfig = await this.compactConfigurationClient.getCompactConfiguration(compact);
            } catch (error) {
                const errorMessage = error instanceof Error ? error.message : String(error);

                logger.warn('Compact configuration not found, skipping compact', { compact, error: errorMessage });
                continue;
            }

            const jurisdictionConfigs = await this.jurisdictionClient.getJurisdictionConfigurations(compact);

            // Loop over each jurisdiction that we have contacts configured for
            for (const jurisdictionConfig of jurisdictionConfigs) {
                const ingestEvents = await this.eventClient.getEvents(
                    compact, jurisdictionConfig.postalAbbreviation, startTimeStamp, endTimeStamp
                );

                // If there were any issues, send a report email summarizing them
                if (ingestEvents.ingestFailures.length || ingestEvents.validationErrors.length) {
                    const messageId = await this.emailService.sendReportEmail(
                        ingestEvents,
                        compactConfig.compactName,
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

                        // verify that the jurisdiction uploaded licenses within the last week without any errors
                        if (!weeklyIngestEvents.ingestFailures.length
                            && !weeklyIngestEvents.validationErrors.length
                            && weeklyIngestEvents.ingestSuccesses.length
                        ) {
                            const messageId = await this.emailService.sendAllsWellEmail(
                                compactConfig.compactName,
                                jurisdictionConfig.jurisdictionName,
                                jurisdictionConfig.jurisdictionOperationsTeamEmails
                            );

                            logger.info(
                                'Sent alls well email',
                                {
                                    compact: compactConfig.compactName,
                                    jurisdiction: jurisdictionConfig.postalAbbreviation,
                                    message_id: messageId
                                }
                            );
                        }
                        else if(!weeklyIngestEvents.ingestSuccesses.length) {
                            const messageId = await this.emailService.sendNoLicenseUpdatesEmail(
                                compactConfig.compactName,
                                jurisdictionConfig.jurisdictionName,
                                [
                                    ...jurisdictionConfig.jurisdictionOperationsTeamEmails,
                                    ...compactConfig.compactOperationsTeamEmails
                                ]
                            );

                            logger.warn(
                                'No licenses uploaded withinin the last week',
                                {
                                    compact: compactConfig.compactName,
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
