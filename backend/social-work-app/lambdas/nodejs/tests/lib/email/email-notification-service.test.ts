import { mockClient } from 'aws-sdk-client-mock';
import 'aws-sdk-client-mock-jest';
import { Logger } from '@aws-lambda-powertools/logger';
import { SendEmailCommand, SESv2Client } from '@aws-sdk/client-sesv2';
import * as nodemailer from 'nodemailer';
import { EmailNotificationService } from '../../../lib/email';
import { CompactConfigurationClient } from '../../../lib/compact-configuration-client';
import { JurisdictionClient } from '../../../lib/jurisdiction-client';
import { EmailTemplateCapture } from '../../utils/email-template-capture';
import { TReaderDocument } from '@csg-org/email-builder';
import { describe, it, beforeEach, beforeAll, afterAll, jest } from '@jest/globals';

jest.mock('nodemailer');

const SAMPLE_COMPACT_CONFIG = {
    pk: 'aslp#CONFIGURATION',
    sk: 'aslp#CONFIGURATION',
    compactAdverseActionsNotificationEmails: ['adverse@example.com'],
    compactCommissionFee: {
        feeAmount: 3.5,
        feeType: 'FLAT_RATE'
    },
    compactAbbr: 'aslp',
    compactName: 'Audiology and Speech Language Pathology',
    compactOperationsTeamEmails: ['operations@example.com'],
    compactSummaryReportNotificationEmails: ['summary@example.com'],
    dateOfUpdate: '2024-12-10T19:27:28+00:00',
    type: 'compact'
};

/** Ohio — jurisdiction receiving the home-state change notification */
const JURISDICTION_CONFIG_OH = {
    pk: 'aslp#CONFIGURATION',
    sk: 'aslp#JURISDICTION#OH',
    jurisdictionName: 'Ohio',
    postalAbbreviation: 'OH',
    compact: 'aslp',
    jurisdictionOperationsTeamEmails: ['oh-ops@example.com'],
    jurisdictionAdverseActionsNotificationEmails: ['oh-adverse@example.com'],
    jurisdictionSummaryReportNotificationEmails: ['oh-summary@example.com']
};

/** Tennessee — prior home jurisdiction in TN → OH scenarios (both valid ASLP jurisdictions) */
const JURISDICTION_CONFIG_TN = {
    pk: 'aslp#CONFIGURATION',
    sk: 'aslp#JURISDICTION#TN',
    jurisdictionName: 'Tennessee',
    postalAbbreviation: 'TN',
    compact: 'aslp',
    jurisdictionOperationsTeamEmails: ['tn-ops@example.com'],
    jurisdictionAdverseActionsNotificationEmails: ['tn-adverse@example.com'],
    jurisdictionSummaryReportNotificationEmails: ['tn-summary@example.com']
};

function mockGetJurisdictionConfiguration(
    mock: jest.Mocked<JurisdictionClient>
): void {
    mock.getJurisdictionConfiguration.mockImplementation(async (_compact, jurisdiction) => {
        switch (jurisdiction.toLowerCase()) {
        case 'oh':
            return JURISDICTION_CONFIG_OH;
        case 'tn':
            return JURISDICTION_CONFIG_TN;
        default:
            throw new Error(`Unexpected jurisdiction in mock: ${jurisdiction}`);
        }
    });
}

const asSESClient = (mock: ReturnType<typeof mockClient>) =>
    mock as unknown as SESv2Client;

const MOCK_TRANSPORT = {
    sendMail: jest.fn().mockImplementation(async () => ({ messageId: 'test-message-id' }))
};

describe('EmailNotificationService', () => {
    let emailService: EmailNotificationService;
    let mockSESClient: ReturnType<typeof mockClient>;
    let mockCompactConfigurationClient: jest.Mocked<CompactConfigurationClient>;
    let mockJurisdictionClient: jest.Mocked<JurisdictionClient>;

    beforeAll(() => {
        // Mock the renderTemplate method if template capture is enabled
        if (EmailTemplateCapture.isEnabled()) {
            const original = (EmailNotificationService.prototype as any).renderTemplate;

            jest.spyOn(EmailNotificationService.prototype as any, 'renderTemplate').mockImplementation(function (this: any, ...args: any[]) {
                const [template, options] = args as [TReaderDocument, any];

                EmailTemplateCapture.captureTemplate(template);
                const html = original.apply(this, args);

                EmailTemplateCapture.captureHtml(html, template, options);
                return html;
            });
        }
    });

    afterAll(() => {
        jest.restoreAllMocks();
    });

    beforeEach(() => {
        jest.clearAllMocks();
        mockSESClient = mockClient(SESv2Client);
        mockCompactConfigurationClient = {
            getCompactConfiguration: jest.fn()
        } as any;
        mockJurisdictionClient = {
            getJurisdictionConfigurations: jest.fn(),
            getJurisdictionConfiguration: jest.fn()
        } as any;

        // Reset environment variables
        process.env.FROM_ADDRESS = 'noreply@example.org';
        process.env.UI_BASE_PATH_URL = 'https://app.test.compactconnect.org';
        process.env.TRANSACTION_REPORTS_BUCKET_NAME = 'test-transaction-reports-bucket';

        // Set up default successful responses
        mockSESClient.on(SendEmailCommand).resolves({
            MessageId: 'message-id-123'
        });

        // Note: SESv2 with nodemailer 7.0.7 uses SendEmailCommand for all email sending

        (nodemailer.createTransport as jest.Mock).mockReturnValue(MOCK_TRANSPORT);

        emailService = new EmailNotificationService({
            logger: new Logger({ serviceName: 'test' }),
            sesClient: asSESClient(mockSESClient),
            compactConfigurationClient: mockCompactConfigurationClient,
            jurisdictionClient: mockJurisdictionClient
        });
    });

    describe('Home Jurisdiction Change State Notification', () => {
        it('should send home jurisdiction change state notification email with expected content', async () => {
            mockCompactConfigurationClient.getCompactConfiguration.mockResolvedValue(SAMPLE_COMPACT_CONFIG);
            mockGetJurisdictionConfiguration(mockJurisdictionClient);

            await emailService.sendHomeJurisdictionChangeStateNotificationEmail(
                'aslp',
                'oh',
                'John',
                'Doe',
                'provider-123',
                'TN',
                'OH'
            );

            expect(mockJurisdictionClient.getJurisdictionConfiguration).toHaveBeenCalledWith('aslp', 'oh');

            expect(mockSESClient).toHaveReceivedCommandWith(
                SendEmailCommand,
                {
                    Destination: {
                        ToAddresses: ['oh-ops@example.com']
                    },
                    Content: {
                        Simple: {
                            Body: {
                                Html: {
                                    Charset: 'UTF-8',
                                    Data: expect.stringContaining('<!DOCTYPE html>')
                                }
                            },
                            Subject: {
                                Charset: 'UTF-8',
                                Data: 'Practitioner Home State Change - Audiology and Speech Language Pathology'
                            }
                        }
                    },
                    FromEmailAddress: 'CompactConnect <noreply@example.org>'
                }
            );

            // Get the actual HTML content for detailed validation
            const emailCall = mockSESClient.commandCalls(SendEmailCommand)[0];
            const htmlContent = emailCall.args[0].input.Content?.Simple?.Body?.Html?.Data;

            expect(htmlContent).toBeDefined();
            expect(htmlContent).toContain('This is to notify you that John Doe has changed their home state from TN to OH.');
            expect(htmlContent).toContain('https://app.test.compactconnect.org/aslp/Licensing/provider-123');
        });

        it('should throw error when no recipients found for jurisdiction', async () => {
            mockJurisdictionClient.getJurisdictionConfiguration.mockResolvedValue({
                ...JURISDICTION_CONFIG_OH,
                jurisdictionOperationsTeamEmails: []
            });

            await expect(emailService.sendHomeJurisdictionChangeStateNotificationEmail(
                'aslp',
                'oh',
                'John',
                'Doe',
                'provider-123',
                'TN',
                'OH'
            )).rejects.toThrow('No recipients found for jurisdiction oh in compact aslp');
        });
    });
});
