import type { LambdaInterface } from '@aws-lambda-powertools/commons/lib/esm/types';
import { Logger } from '@aws-lambda-powertools/logger';
import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { SESClient } from '@aws-sdk/client-ses';
import { S3Client } from '@aws-sdk/client-s3';
import { Context } from 'aws-lambda';

import { EnvironmentVariablesService } from '../lib/environment-variables-service';
import { CompactConfigurationClient } from '../lib/compact-configuration-client';
import { JurisdictionClient } from '../lib/jurisdiction-client';
import { EmailNotificationService } from '../lib/email';
import { EmailNotificationEvent, EmailNotificationResponse } from '../lib/models/email-notification-service-event';

const environmentVariables = new EnvironmentVariablesService();
const logger = new Logger({ logLevel: environmentVariables.getLogLevel() });

interface LambdaProperties {
    dynamoDBClient: DynamoDBClient;
    sesClient: SESClient;
    s3Client: S3Client;
}

export class Lambda implements LambdaInterface {
    private readonly emailService: EmailNotificationService;

    constructor(props: LambdaProperties) {
        const compactConfigurationClient = new CompactConfigurationClient({
            logger: logger,
            dynamoDBClient: props.dynamoDBClient,
        });

        const jurisdictionClient = new JurisdictionClient({
            logger: logger,
            dynamoDBClient: props.dynamoDBClient,
        });

        this.emailService = new EmailNotificationService({
            logger: logger,
            sesClient: props.sesClient,
            s3Client: props.s3Client,
            compactConfigurationClient: compactConfigurationClient,
            jurisdictionClient: jurisdictionClient
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
        logger.info('Processing event', { template: event.template, compact: event.compact, jurisdiction: event.jurisdiction });

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
        case 'privilegeDeactivationJurisdictionNotification':
            if (!event.jurisdiction) {
                throw new Error('Missing required jurisdiction field.');
            }
            if (!event.templateVariables.privilegeId 
                || !event.templateVariables.providerFirstName 
                || !event.templateVariables.providerLastName) {
                throw new Error('Missing required template variables for privilegeDeactivationJurisdictionNotification template.');
            }
            await this.emailService.sendPrivilegeDeactivationJurisdictionNotificationEmail(
                event.compact,
                event.jurisdiction,
                event.recipientType,
                event.templateVariables.privilegeId,
                event.templateVariables.providerFirstName,
                event.templateVariables.providerLastName
            );
            break;
        case 'privilegeDeactivationProviderNotification':
            await this.emailService.sendPrivilegeDeactivationProviderNotificationEmail(
                event.compact,
                event.specificEmails,
                event.templateVariables.privilegeId
            );
            break;
        case 'CompactTransactionReporting':
            if (!event.templateVariables?.reportS3Path) {
                throw new Error('Missing required template variables for CompactTransactionReporting template');
            }
            await this.emailService.sendCompactTransactionReportEmail(
                event.compact,
                event.templateVariables.reportS3Path,
                event.templateVariables.reportingCycle,
                event.templateVariables.startDate,
                event.templateVariables.endDate
            );
            break;
        case 'JurisdictionTransactionReporting':
            if (!event.jurisdiction) {
                throw new Error('Missing required jurisdiction field for JurisdictionTransactionReporting template');
            }
            if (!event.templateVariables?.reportS3Path) {
                throw new Error('Missing required template variables for JurisdictionTransactionReporting template');
            }
            await this.emailService.sendJurisdictionTransactionReportEmail(
                event.compact,
                event.jurisdiction,
                event.templateVariables.reportS3Path,
                event.templateVariables.reportingCycle,
                event.templateVariables.startDate,
                event.templateVariables.endDate
            );
            break;
        case 'privilegePurchaseProviderNotification':
            await this.emailService.sendPrivilegePurchaseProviderNotificationEmail(
                event.specificEmails,
                event.templateVariables.transactionDate,
                event.templateVariables.privileges,
                event.templateVariables.totalCost,
                event.templateVariables.costLineItems
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
