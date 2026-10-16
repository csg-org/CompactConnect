import type { LambdaInterface } from '@aws-lambda-powertools/commons/types';
import { Logger } from '@aws-lambda-powertools/logger';
import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { SESv2Client } from '@aws-sdk/client-sesv2';
import { Context } from 'aws-lambda';

import { CompactConfigurationClient } from '../lib/compact-configuration-client';
import { EnvironmentVariablesService } from '../lib/environment-variables-service';
import { InvoiceEmailService } from '../lib/email/invoice-email-service';
import { InvoiceClient } from '../lib/invoice-client';
import { JurisdictionClient } from '../lib/jurisdiction-client';
import { InvoiceReport, InvoiceReporterEvent, StateInvoiceSection } from '../lib/models/invoice';

const environmentVariables = new EnvironmentVariablesService();
const logger = new Logger({ logLevel: environmentVariables.getLogLevel() });

const INVOICE_LICENSE_TYPES = ['cosmetologist', 'esthetician'];
const BILLING_MONTH_PATTERN = /^\d{4}-(0[1-9]|1[0-2])$/;
const EMAIL_PATTERN = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

interface LambdaProperties {
    dynamoDBClient: DynamoDBClient;
    sesClient: SESv2Client;
}

export class Lambda implements LambdaInterface {
    private readonly jurisdictionClient: JurisdictionClient;
    private readonly compactConfigurationClient: CompactConfigurationClient;
    private readonly invoiceClient: InvoiceClient;
    private readonly emailService: InvoiceEmailService;

    constructor(props: LambdaProperties) {
        this.jurisdictionClient = new JurisdictionClient({
            logger: logger,
            dynamoDBClient: props.dynamoDBClient,
        });

        this.compactConfigurationClient = new CompactConfigurationClient({
            logger: logger,
            dynamoDBClient: props.dynamoDBClient,
        });

        this.invoiceClient = new InvoiceClient({
            logger: logger,
            dynamoDBClient: props.dynamoDBClient,
        });

        this.emailService = new InvoiceEmailService({
            logger: logger,
            sesClient: props.sesClient,
            compactConfigurationClient: this.compactConfigurationClient,
            jurisdictionClient: this.jurisdictionClient,
        });
    }

    @logger.injectLambdaContext({ resetKeys: true })
    public async handler(event: InvoiceReporterEvent, context: Context): Promise<void> {
        logger.info('Processing invoice event', { event });
        logger.debug('Context wait for event loop', {
            wait_for_empty_event_loop: context.callbackWaitsForEmptyEventLoop,
        });

        const billingMonth = this.resolveBillingMonth(event);
        const manualRecipient = this.resolveManualRecipient(event);

        for (const compact of environmentVariables.getCompacts()) {
            let compactConfig;

            try {
                compactConfig = await this.compactConfigurationClient.getCompactConfiguration(compact);
            } catch (error) {
                const errorMessage = error instanceof Error ? error.message : String(error);

                logger.warn('Compact configuration not found, skipping compact', { compact, error: errorMessage });
                continue;
            }

            const jurisdictions = await this.jurisdictionClient.getJurisdictionConfigurations(
                compactConfig.compactAbbr
            );
            const sectionsByLicenseType: Record<string, StateInvoiceSection[]> = Object.fromEntries(
                INVOICE_LICENSE_TYPES.map((licenseType) => [licenseType, []])
            );
            let totalUploaded = 0;

            for (const jurisdiction of jurisdictions) {
                const uploads = await this.invoiceClient.getLicenseUploadsForMonth(
                    compactConfig.compactAbbr,
                    jurisdiction.postalAbbreviation,
                    billingMonth
                );

                totalUploaded += uploads.totalUploaded;

                for (const licenseType of INVOICE_LICENSE_TYPES) {
                    sectionsByLicenseType[licenseType].push({
                        jurisdictionName: jurisdiction.jurisdictionName,
                        postalAbbreviation: jurisdiction.postalAbbreviation,
                        lineItems: uploads.byLicenseType[licenseType] ?? [],
                    });
                }
            }

            for (const licenseType of INVOICE_LICENSE_TYPES) {
                const stateSections = sectionsByLicenseType[licenseType];
                const lineItems = stateSections.flatMap((section) => section.lineItems);
                const report: InvoiceReport = {
                    compactName: compactConfig.compactName,
                    licenseType,
                    billingMonth,
                    stateSections,
                    totalUploaded,
                    totalBillable: lineItems.length,
                    totalOwed: lineItems.reduce((sum, item) => sum + item.fee, 0),
                };

                const recipients = manualRecipient
                    ? [manualRecipient]
                    : compactConfig.compactOperationsTeamEmails;
                const messageId = await this.emailService.sendInvoiceEmail(report, recipients);

                logger.info('Sent invoice email', {
                    compact: compactConfig.compactAbbr,
                    licenseType,
                    billingMonth,
                    totalBillable: report.totalBillable,
                    totalOwed: report.totalOwed,
                    message_id: messageId,
                });
            }
        }

        logger.info('Completing invoice handler');
    }

    private resolveBillingMonth(event: InvoiceReporterEvent): string {
        if (event.billingMonth === undefined) {
            return this.previousBillingMonth(new Date());
        }
        if (!BILLING_MONTH_PATTERN.test(event.billingMonth)) {
            throw new Error(`billingMonth must be YYYY-MM, got ${event.billingMonth}`);
        }

        return event.billingMonth;
    }

    /**
     * Manual runs must name one recipient. They do not fall back to compact operations,
     * so a retry or a direct invoke cannot email the operations team by accident.
     */
    private resolveManualRecipient(event: InvoiceReporterEvent): string | undefined {
        if (event.eventType !== 'manual') {
            return undefined;
        }

        const email = event.recipientEmail?.trim() ?? '';

        if (!EMAIL_PATTERN.test(email)) {
            throw new Error(`Manual invoice runs require a recipientEmail, got ${event.recipientEmail ?? ''}`);
        }

        return email;
    }

    private previousBillingMonth(now: Date): string {
        const previous = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() - 1, 1));
        const month = String(previous.getUTCMonth() + 1).padStart(2, '0');

        return `${previous.getUTCFullYear()}-${month}`;
    }
}
