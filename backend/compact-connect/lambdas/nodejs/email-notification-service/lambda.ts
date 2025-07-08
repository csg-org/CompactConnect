import type { LambdaInterface } from '@aws-lambda-powertools/commons/lib/esm/types';
import { Logger } from '@aws-lambda-powertools/logger';
import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { SESClient } from '@aws-sdk/client-ses';
import { S3Client } from '@aws-sdk/client-s3';
import { Context } from 'aws-lambda';

import { EnvironmentVariablesService } from '../lib/environment-variables-service';
import { CompactConfigurationClient } from '../lib/compact-configuration-client';
import { JurisdictionClient } from '../lib/jurisdiction-client';
import { EmailNotificationService, EncumbranceNotificationService } from '../lib/email';
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
    private readonly encumbranceService: EncumbranceNotificationService;

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

        this.encumbranceService = new EncumbranceNotificationService({
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
                event.templateVariables.transactionDate,
                event.templateVariables.privileges,
                event.templateVariables.totalCost,
                event.templateVariables.costLineItems,
                event.specificEmails
            );
            break;
        case 'licenseEncumbranceProviderNotification':
            if (!event.templateVariables.providerFirstName
                || !event.templateVariables.providerLastName
                || !event.templateVariables.encumberedJurisdiction
                || !event.templateVariables.licenseType
                || !event.templateVariables.effectiveStartDate) {
                throw new Error('Missing required template variables for licenseEncumbranceProviderNotification template.');
            }
            await this.encumbranceService.sendLicenseEncumbranceProviderNotificationEmail(
                event.compact,
                event.specificEmails || [],
                event.templateVariables.providerFirstName,
                event.templateVariables.providerLastName,
                event.templateVariables.encumberedJurisdiction,
                event.templateVariables.licenseType,
                event.templateVariables.effectiveStartDate
            );
            break;
        case 'licenseEncumbranceStateNotification':
            if (!event.jurisdiction) {
                throw new Error('Missing required jurisdiction field for licenseEncumbranceStateNotification template.');
            }
            if (!event.templateVariables.providerFirstName
                || !event.templateVariables.providerLastName
                || !event.templateVariables.providerId
                || !event.templateVariables.encumberedJurisdiction
                || !event.templateVariables.licenseType
                || !event.templateVariables.effectiveStartDate) {
                throw new Error('Missing required template variables for licenseEncumbranceStateNotification template.');
            }
            await this.encumbranceService.sendLicenseEncumbranceStateNotificationEmail(
                event.compact,
                event.jurisdiction,
                event.templateVariables.providerFirstName,
                event.templateVariables.providerLastName,
                event.templateVariables.providerId,
                event.templateVariables.encumberedJurisdiction,
                event.templateVariables.licenseType,
                event.templateVariables.effectiveStartDate
            );
            break;
        case 'licenseEncumbranceLiftingProviderNotification':
            if (!event.templateVariables.providerFirstName
                || !event.templateVariables.providerLastName
                || !event.templateVariables.liftedJurisdiction
                || !event.templateVariables.licenseType
                || !event.templateVariables.effectiveLiftDate) {
                throw new Error('Missing required template variables for licenseEncumbranceLiftingProviderNotification template.');
            }
            await this.encumbranceService.sendLicenseEncumbranceLiftingProviderNotificationEmail(
                event.compact,
                event.specificEmails || [],
                event.templateVariables.providerFirstName,
                event.templateVariables.providerLastName,
                event.templateVariables.liftedJurisdiction,
                event.templateVariables.licenseType,
                event.templateVariables.effectiveLiftDate
            );
            break;
        case 'licenseEncumbranceLiftingStateNotification':
            if (!event.jurisdiction) {
                throw new Error('Missing required jurisdiction field for licenseEncumbranceLiftingStateNotification template.');
            }
            if (!event.templateVariables.providerFirstName
                || !event.templateVariables.providerLastName
                || !event.templateVariables.providerId
                || !event.templateVariables.liftedJurisdiction
                || !event.templateVariables.licenseType
                || !event.templateVariables.effectiveLiftDate) {
                throw new Error('Missing required template variables for licenseEncumbranceLiftingStateNotification template.');
            }
            await this.encumbranceService.sendLicenseEncumbranceLiftingStateNotificationEmail(
                event.compact,
                event.jurisdiction,
                event.templateVariables.providerFirstName,
                event.templateVariables.providerLastName,
                event.templateVariables.providerId,
                event.templateVariables.liftedJurisdiction,
                event.templateVariables.licenseType,
                event.templateVariables.effectiveLiftDate
            );
            break;
        case 'privilegeEncumbranceProviderNotification':
            if (!event.templateVariables.providerFirstName
                || !event.templateVariables.providerLastName
                || !event.templateVariables.encumberedJurisdiction
                || !event.templateVariables.licenseType
                || !event.templateVariables.effectiveStartDate) {
                throw new Error('Missing required template variables for privilegeEncumbranceProviderNotification template.');
            }
            await this.encumbranceService.sendPrivilegeEncumbranceProviderNotificationEmail(
                event.compact,
                event.specificEmails || [],
                event.templateVariables.providerFirstName,
                event.templateVariables.providerLastName,
                event.templateVariables.encumberedJurisdiction,
                event.templateVariables.licenseType,
                event.templateVariables.effectiveStartDate
            );
            break;
        case 'privilegeEncumbranceStateNotification':
            if (!event.jurisdiction) {
                throw new Error('Missing required jurisdiction field for privilegeEncumbranceStateNotification template.');
            }
            if (!event.templateVariables.providerFirstName
                || !event.templateVariables.providerLastName
                || !event.templateVariables.providerId
                || !event.templateVariables.encumberedJurisdiction
                || !event.templateVariables.licenseType
                || !event.templateVariables.effectiveStartDate) {
                throw new Error('Missing required template variables for privilegeEncumbranceStateNotification template.');
            }
            await this.encumbranceService.sendPrivilegeEncumbranceStateNotificationEmail(
                event.compact,
                event.jurisdiction,
                event.templateVariables.providerFirstName,
                event.templateVariables.providerLastName,
                event.templateVariables.providerId,
                event.templateVariables.encumberedJurisdiction,
                event.templateVariables.licenseType,
                event.templateVariables.effectiveStartDate
            );
            break;
        case 'privilegeEncumbranceLiftingProviderNotification':
            if (!event.templateVariables.providerFirstName
                || !event.templateVariables.providerLastName
                || !event.templateVariables.liftedJurisdiction
                || !event.templateVariables.licenseType
                || !event.templateVariables.effectiveLiftDate) {
                throw new Error('Missing required template variables for privilegeEncumbranceLiftingProviderNotification template.');
            }
            await this.encumbranceService.sendPrivilegeEncumbranceLiftingProviderNotificationEmail(
                event.compact,
                event.specificEmails || [],
                event.templateVariables.providerFirstName,
                event.templateVariables.providerLastName,
                event.templateVariables.liftedJurisdiction,
                event.templateVariables.licenseType,
                event.templateVariables.effectiveLiftDate
            );
            break;
        case 'privilegeEncumbranceLiftingStateNotification':
            if (!event.jurisdiction) {
                throw new Error('Missing required jurisdiction field for privilegeEncumbranceLiftingStateNotification template.');
            }
            if (!event.templateVariables.providerFirstName
                || !event.templateVariables.providerLastName
                || !event.templateVariables.providerId
                || !event.templateVariables.liftedJurisdiction
                || !event.templateVariables.licenseType
                || !event.templateVariables.effectiveLiftDate) {
                throw new Error('Missing required template variables for privilegeEncumbranceLiftingStateNotification template.');
            }
            await this.encumbranceService.sendPrivilegeEncumbranceLiftingStateNotificationEmail(
                event.compact,
                event.jurisdiction,
                event.templateVariables.providerFirstName,
                event.templateVariables.providerLastName,
                event.templateVariables.providerId,
                event.templateVariables.liftedJurisdiction,
                event.templateVariables.licenseType,
                event.templateVariables.effectiveLiftDate
            );
            break;
        case 'multipleRegistrationAttemptNotification':
            if (!event.specificEmails?.length) {
                throw new Error('No recipients found for multiple registration attempt notification email');
            }
            await this.emailService.sendMultipleRegistrationAttemptNotificationEmail(
                event.compact,
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
