import type { LambdaInterface } from '@aws-lambda-powertools/commons/lib/esm/types';
import { Logger } from '@aws-lambda-powertools/logger';
import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { SESv2Client } from '@aws-sdk/client-sesv2';
import { S3Client } from '@aws-sdk/client-s3';
import { Context } from 'aws-lambda';

import { EnvironmentVariablesService } from '../lib/environment-variables-service';
import { CompactConfigurationClient } from '../lib/compact-configuration-client';
import { JurisdictionClient } from '../lib/jurisdiction-client';
import { EmailNotificationService, EncumbranceNotificationService, InvestigationNotificationService, type PrivilegeExpirationReminderRow } from '../lib/email';
import { EmailNotificationEvent, EmailNotificationResponse } from '../lib/models/email-notification-service-event';

const environmentVariables = new EnvironmentVariablesService();
const logger = new Logger({ logLevel: environmentVariables.getLogLevel() });

interface LambdaProperties {
    dynamoDBClient: DynamoDBClient;
    sesClient: SESv2Client;
    s3Client: S3Client;
}

export class Lambda implements LambdaInterface {
    private readonly emailService: EmailNotificationService;
    private readonly encumbranceService: EncumbranceNotificationService;
    private readonly investigationService: InvestigationNotificationService;

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

        this.investigationService = new InvestigationNotificationService({
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
    public async handler(event: EmailNotificationEvent, _context: Context): Promise<EmailNotificationResponse> {
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
                event.specificEmails,
                event.templateVariables.batchFailureErrorMessage
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
        case 'providerEmailVerificationCode':
            if (!event.specificEmails?.length) {
                throw new Error('No recipients found for provider email verification code email');
            }
            if (!event.templateVariables?.verificationCode) {
                throw new Error('Missing required template variables for providerEmailVerificationCode template');
            }
            await this.emailService.sendProviderEmailVerificationCode(
                event.compact,
                event.specificEmails[0],
                event.templateVariables.verificationCode
            );
            break;
        case 'providerEmailChangeNotification':
            if (!event.specificEmails?.length) {
                throw new Error('No recipients found for provider email change notification email');
            }
            if (!event.templateVariables?.newEmailAddress) {
                throw new Error('Missing required template variables for providerEmailChangeNotification template');
            }
            await this.emailService.sendProviderEmailChangeNotification(
                event.compact,
                event.specificEmails[0],
                event.templateVariables.newEmailAddress
            );
            break;
        case 'providerAccountRecoveryConfirmation':
            if (!event.specificEmails?.length) {
                throw new Error('No recipients found for provider account recovery confirmation email');
            }
            if (!event.templateVariables?.providerId || !event.templateVariables?.recoveryToken) {
                throw new Error('Missing required template variables for providerAccountRecoveryConfirmation template');
            }
            await this.emailService.sendProviderAccountRecoveryConfirmationEmail(
                event.compact,
                event.specificEmails,
                event.templateVariables.providerId,
                event.templateVariables.recoveryToken
            );
            break;
        case 'militaryAuditApprovedNotification':
            if (!event.specificEmails?.length) {
                throw new Error('No recipients found for military audit approved notification email');
            }
            await this.emailService.sendMilitaryAuditApprovedNotificationEmail(
                event.compact,
                event.specificEmails
            );
            break;
        case 'militaryAuditDeclinedNotification':
            if (!event.specificEmails?.length) {
                throw new Error('No recipients found for military audit declined notification email');
            }
            await this.emailService.sendMilitaryAuditDeclinedNotificationEmail(
                event.compact,
                event.specificEmails,
                event.templateVariables?.auditNote || ''
            );
            break;
        case 'privilegeExpirationReminder': {
            if (!event.specificEmails?.length) {
                throw new Error('No recipients found for privilege expiration reminder email');
            }
            if (!event.templateVariables?.providerFirstName
                || !event.templateVariables?.expirationDate
                || !event.templateVariables?.privileges) {
                throw new Error('Missing required template variables for privilegeExpirationReminder template.');
            }
            const privileges = event.templateVariables.privileges as Array<{ jurisdiction?: string;
                licenseType?: string; privilegeId?:
                string; dateOfExpiration?: string;
                formattedExpirationDate?: string }>;

            if (!Array.isArray(privileges) || privileges.length === 0) {
                throw new Error('privilegeExpirationReminder template requires a non-empty privileges array.');
            }
            for (let i = 0; i < privileges.length; i++) {
                const p = privileges[i];

                if (!p?.jurisdiction || !p?.licenseType || !p?.privilegeId || !p?.dateOfExpiration) {
                    throw new Error(
                        `privilegeExpirationReminder template requires each privilege to have jurisdiction, licenseType, privilegeId, and dateOfExpiration (ISO 8601). Invalid privilege at index ${i}.`
                    );
                }
            }
            await this.emailService.sendPrivilegeExpirationReminderEmail(
                event.compact,
                event.specificEmails,
                event.templateVariables.providerFirstName,
                event.templateVariables.expirationDate,
                privileges as PrivilegeExpirationReminderRow[]
            );
            break;
        }
        case 'licenseInvestigationStateNotification':
            if (!event.jurisdiction) {
                throw new Error('No jurisdiction provided for license investigation state notification email');
            }
            if (!event.templateVariables?.providerFirstName
                || !event.templateVariables?.providerLastName
                || !event.templateVariables?.providerId
                || !event.templateVariables?.investigationJurisdiction
                || !event.templateVariables?.licenseType) {
                throw new Error('Missing required template variables for licenseInvestigationStateNotification template.');
            }
            await this.investigationService.sendLicenseInvestigationStateNotificationEmail(
                event.compact,
                event.jurisdiction,
                event.templateVariables.providerFirstName,
                event.templateVariables.providerLastName,
                event.templateVariables.providerId,
                event.templateVariables.investigationJurisdiction,
                event.templateVariables.licenseType
            );
            break;
        case 'licenseInvestigationClosedStateNotification':
            if (!event.jurisdiction) {
                throw new Error('No jurisdiction provided for license investigation closed state notification email');
            }
            if (!event.templateVariables?.providerFirstName
                || !event.templateVariables?.providerLastName
                || !event.templateVariables?.providerId
                || !event.templateVariables?.investigationJurisdiction
                || !event.templateVariables?.licenseType) {
                throw new Error('Missing required template variables for licenseInvestigationClosedStateNotification template.');
            }
            await this.investigationService.sendLicenseInvestigationClosedStateNotificationEmail(
                event.compact,
                event.jurisdiction,
                event.templateVariables.providerFirstName,
                event.templateVariables.providerLastName,
                event.templateVariables.providerId,
                event.templateVariables.investigationJurisdiction,
                event.templateVariables.licenseType
            );
            break;
        case 'privilegeInvestigationStateNotification':
            if (!event.jurisdiction) {
                throw new Error('No jurisdiction provided for privilege investigation state notification email');
            }
            if (!event.templateVariables?.providerFirstName
                || !event.templateVariables?.providerLastName
                || !event.templateVariables?.providerId
                || !event.templateVariables?.investigationJurisdiction
                || !event.templateVariables?.licenseType) {
                throw new Error('Missing required template variables for privilegeInvestigationStateNotification template.');
            }
            await this.investigationService.sendPrivilegeInvestigationStateNotificationEmail(
                event.compact,
                event.jurisdiction,
                event.templateVariables.providerFirstName,
                event.templateVariables.providerLastName,
                event.templateVariables.providerId,
                event.templateVariables.investigationJurisdiction,
                event.templateVariables.licenseType
            );
            break;
        case 'privilegeInvestigationClosedStateNotification':
            if (!event.jurisdiction) {
                throw new Error('No jurisdiction provided for privilege investigation closed state notification email');
            }
            if (!event.templateVariables?.providerFirstName
                || !event.templateVariables?.providerLastName
                || !event.templateVariables?.providerId
                || !event.templateVariables?.investigationJurisdiction
                || !event.templateVariables?.licenseType) {
                throw new Error('Missing required template variables for privilegeInvestigationClosedStateNotification template.');
            }
            await this.investigationService.sendPrivilegeInvestigationClosedStateNotificationEmail(
                event.compact,
                event.jurisdiction,
                event.templateVariables.providerFirstName,
                event.templateVariables.providerLastName,
                event.templateVariables.providerId,
                event.templateVariables.investigationJurisdiction,
                event.templateVariables.licenseType
            );
            break;
        case 'homeJurisdictionChangeOldStateNotification':
        case 'homeJurisdictionChangeNewStateNotification':
            if (!event.jurisdiction) {
                throw new Error('Missing required jurisdiction field for home jurisdiction change notification template.');
            }
            if (!event.templateVariables?.providerFirstName
                || !event.templateVariables?.providerLastName
                || !event.templateVariables?.providerId
                || !event.templateVariables?.previousJurisdiction
                || !event.templateVariables?.newJurisdiction) {
                throw new Error('Missing required template variables for home jurisdiction change notification template.');
            }
            // Both templates call the same method
            await this.emailService.sendHomeJurisdictionChangeStateNotificationEmail(
                event.compact,
                event.jurisdiction,
                event.templateVariables.providerFirstName,
                event.templateVariables.providerLastName,
                event.templateVariables.providerId,
                event.templateVariables.previousJurisdiction,
                event.templateVariables.newJurisdiction
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
