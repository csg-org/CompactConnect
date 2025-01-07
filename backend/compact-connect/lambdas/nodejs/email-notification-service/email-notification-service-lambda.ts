import type { LambdaInterface } from '@aws-lambda-powertools/commons/lib/esm/types';
import { Logger } from '@aws-lambda-powertools/logger';
import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { SESClient } from '@aws-sdk/client-ses';
import { Context } from 'aws-lambda';

import { EnvironmentVariablesService } from '../lib/environment-variables-service';
import { CompactConfigurationClient } from '../lib/compact-configuration-client';
import { EmailService } from '../lib/email-service';
import { EmailNotificationEvent, EmailNotificationResponse } from '../lib/models/email-notification-service-event';

const environmentVariables = new EnvironmentVariablesService();
const logger = new Logger({ logLevel: environmentVariables.getLogLevel() });

interface LambdaProperties {
    dynamoDBClient: DynamoDBClient;
    sesClient: SESClient;
}

export class Lambda implements LambdaInterface {
    private readonly emailService: EmailService;

    constructor(props: LambdaProperties) {
        const compactConfigurationClient = new CompactConfigurationClient({
            logger: logger,
            dynamoDBClient: props.dynamoDBClient,
        });

        this.emailService = new EmailService({
            logger: logger,
            sesClient: props.sesClient,
            compactConfigurationClient: compactConfigurationClient,
        });
    }

    /**
     * Lambda handler for email notification service
     * 
     * This handler sends an email notification based on the requested email template.
     * See README in this directory for information on using this service.
     *
     * @param event - Email notification event
     * @param context - Lambda context
     * @returns Email notification response
     */
    @logger.injectLambdaContext({ resetKeys: true })
    public async handler(event: EmailNotificationEvent, context: Context): Promise<EmailNotificationResponse> {
        logger.info('Processing event', { event: event });

        // Check if FROM_ADDRESS is configured
        if (environmentVariables.getFromAddress() === 'NONE') {
            logger.info('No from address configured for environment');
            return {
                message: 'No from address configured for environment, unable to send email'
            };
        }

        switch (event.template) {
        case 'transactionBatchSettlementFailure':
            await this.emailService.sendTransactionBatchSettlementFailureEmail(
                event.compact,
                event.recipientType,
                event.specificEmails
            );
            break;
        default:
            logger.info('Unsupported email template provided', { template: event.template });
            throw new Error(`Unsupported email template: ${event.template}`);
        }

        logger.info('Completing handler');
        return {
            message: 'Email message sent'
        };
    }
}
