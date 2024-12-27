import type { LambdaInterface } from '@aws-lambda-powertools/commons/lib/esm/types';
import { Logger } from '@aws-lambda-powertools/logger';
import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { SESClient } from '@aws-sdk/client-ses';
import { Context } from 'aws-lambda';

import { EnvironmentVariablesService } from '../lib/environment-variables-service';
import { CompactConfigurationClient } from '../lib/compact-configuration-client';
import { EmailServiceTemplater } from '../lib/email-service-templater';
import { EmailNotificationEvent, EmailNotificationResponse } from '../lib/models/email-notification-service-event';

const environmentVariables = new EnvironmentVariablesService();
const logger = new Logger({ logLevel: environmentVariables.getLogLevel() });

interface LambdaProperties {
    dynamoDBClient: DynamoDBClient;
    sesClient: SESClient;
}

export class Lambda implements LambdaInterface {
    private readonly emailServiceTemplater: EmailServiceTemplater;

    constructor(props: LambdaProperties) {
        const compactConfigurationClient = new CompactConfigurationClient({
            logger: logger,
            dynamoDBClient: props.dynamoDBClient,
        });

        this.emailServiceTemplater = new EmailServiceTemplater({
            logger: logger,
            sesClient: props.sesClient,
            compactConfigurationClient: compactConfigurationClient,
        });
    }

    @logger.injectLambdaContext({ resetKeys: true })
    public async handler(event: EmailNotificationEvent, context: Context): Promise<EmailNotificationResponse> {
        logger.info('Processing event', { event: event });

        switch (event.template) {
        case 'transactionBatchSettlementFailure':
            await this.emailServiceTemplater.transactionBatchSettlementFailure(
                event.compact,
                event.recipientType,
                event.specificEmails
            );
            break;
        default:
            throw new Error(`Unsupported email template: ${event.template}`);
        }

        logger.info('Completing handler');
        return {
            message: 'Email message sent'
        };
    }
}
