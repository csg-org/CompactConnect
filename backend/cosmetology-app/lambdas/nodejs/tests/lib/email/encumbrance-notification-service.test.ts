import { mockClient } from 'aws-sdk-client-mock';
import 'aws-sdk-client-mock-jest';
import { Logger } from '@aws-lambda-powertools/logger';
import { SendEmailCommand, SESv2Client } from '@aws-sdk/client-sesv2';
import { EncumbranceNotificationService } from '../../../lib/email';
import { CompactConfigurationClient } from '../../../lib/compact-configuration-client';
import { JurisdictionClient } from '../../../lib/jurisdiction-client';
import { EmailTemplateCapture } from '../../utils/email-template-capture';
import { TReaderDocument } from '@csg-org/email-builder';
import { describe, it, beforeEach, beforeAll, afterAll, jest } from '@jest/globals';
import { Compact } from '../../../lib/models/compact';
import { DynamoDBClient } from '@aws-sdk/client-dynamodb';

const SAMPLE_COMPACT_CONFIG: Compact = {
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

const SAMPLE_JURISDICTION_CONFIG = {
    pk: 'aslp#CONFIGURATION',
    sk: 'aslp#JURISDICTION#oh',
    jurisdictionName: 'Ohio',
    postalAbbreviation: 'oh',
    compact: 'aslp',
    jurisdictionOperationsTeamEmails: ['oh-ops@example.com'],
    jurisdictionAdverseActionsNotificationEmails: ['oh-adverse@example.com'],
    jurisdictionSummaryReportNotificationEmails: ['oh-summary@example.com']
};

const asSESClient = (mock: ReturnType<typeof mockClient>) =>
    mock as unknown as SESv2Client;

class MockCompactConfigurationClient extends CompactConfigurationClient {
    constructor() {
        super({
            logger: new Logger({ serviceName: 'test' }),
            dynamoDBClient: {} as DynamoDBClient
        });
    }

    public async getCompactConfiguration(_compact: string): Promise<Compact> {
        return SAMPLE_COMPACT_CONFIG;
    }
}

describe('EncumbranceNotificationService', () => {
    let encumbranceService: EncumbranceNotificationService;
    let mockSESClient: ReturnType<typeof mockClient>;
    let mockCompactConfigurationClient: MockCompactConfigurationClient;
    let mockJurisdictionClient: jest.Mocked<JurisdictionClient>;

    beforeAll(() => {
        // Mock the renderTemplate method if template capture is enabled
        if (EmailTemplateCapture.isEnabled()) {
            const original = (EncumbranceNotificationService.prototype as any).renderTemplate;

            jest.spyOn(EncumbranceNotificationService.prototype as any, 'renderTemplate').mockImplementation(function (this: any, ...args: any[]) {
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
        mockCompactConfigurationClient = new MockCompactConfigurationClient();
        mockJurisdictionClient = {
            getJurisdictionConfigurations: jest.fn(),
            getJurisdictionConfiguration: jest.fn()
        } as any;

        // Reset environment variables
        process.env.FROM_ADDRESS = 'noreply@example.org';
        process.env.UI_BASE_PATH_URL = 'https://app.test.compactconnect.org';

        // Set up default successful responses
        mockSESClient.on(SendEmailCommand).resolves({
            MessageId: 'message-id-123'
        });

        mockJurisdictionClient.getJurisdictionConfiguration.mockResolvedValue(SAMPLE_JURISDICTION_CONFIG);

        encumbranceService = new EncumbranceNotificationService({
            logger: new Logger({ serviceName: 'test' }),
            sesClient: asSESClient(mockSESClient),
            compactConfigurationClient: mockCompactConfigurationClient,
            jurisdictionClient: mockJurisdictionClient
        });
    });

    describe('License Encumbrance Provider Notification', () => {
        it('should send license encumbrance provider notification email', async () => {
            await encumbranceService.sendLicenseEncumbranceProviderNotificationEmail(
                'aslp',
                ['provider@example.com'],
                'John',
                'Doe',
                'OH',
                'Audiologist',
                '2024-01-15'
            );

            expect(mockSESClient).toHaveReceivedCommandWith(SendEmailCommand, {
                Destination: {
                    ToAddresses: ['provider@example.com']
                },
                Content: {
                    Simple: {
                        Body: {
                            Html: {
                                Charset: 'UTF-8',
                                Data: expect.stringContaining('Your Audiologist license in Ohio is encumbered')
                            }
                        },
                        Subject: {
                            Charset: 'UTF-8',
                            Data: 'Your Audiologist license in Ohio is encumbered'
                        }
                    }
                },
                FromEmailAddress: 'Compact Connect <noreply@example.org>'
            });
        });

        it('should throw error when no recipients provided', async () => {
            await expect(encumbranceService.sendLicenseEncumbranceProviderNotificationEmail(
                'aslp',
                [],
                'John',
                'Doe',
                'OH',
                'Audiologist',
                '2024-01-15'
            )).rejects.toThrow('No recipients specified for provider license encumbrance notification email');
        });
    });

    describe('License Encumbrance State Notification', () => {
        it('should send license encumbrance state notification email', async () => {
            mockJurisdictionClient.getJurisdictionConfiguration.mockResolvedValue(SAMPLE_JURISDICTION_CONFIG);

            await encumbranceService.sendLicenseEncumbranceStateNotificationEmail(
                'aslp',
                'oh',
                'John',
                'Doe',
                'provider-123',
                'OH',
                'Audiologist',
                '2024-01-15'
            );

            expect(mockSESClient).toHaveReceivedCommandWith(SendEmailCommand, {
                Destination: {
                    ToAddresses: ['oh-adverse@example.com']
                },
                Content: {
                    Simple: {
                        Body: {
                            Html: {
                                Charset: 'UTF-8',
                                Data: expect.stringContaining('License Encumbrance Notification - John Doe')
                            }
                        },
                        Subject: {
                            Charset: 'UTF-8',
                            Data: 'License Encumbrance Notification - John Doe'
                        }
                    }
                },
                FromEmailAddress: 'Compact Connect <noreply@example.org>'
            });
        });

        it('should log warning and continue when no recipients found', async () => {
            mockJurisdictionClient.getJurisdictionConfiguration.mockResolvedValue({
                ...SAMPLE_JURISDICTION_CONFIG,
                jurisdictionAdverseActionsNotificationEmails: []
            });

            await encumbranceService.sendLicenseEncumbranceStateNotificationEmail(
                'aslp',
                'oh',
                'John',
                'Doe',
                'provider-123',
                'OH',
                'Audiologist',
                '2024-01-15'
            );

            // Should not send email when no recipients
            expect(mockSESClient).not.toHaveReceivedCommand(SendEmailCommand);
        });

        it('should log warning and continue when jurisdiction configuration is missing', async () => {
            mockJurisdictionClient.getJurisdictionConfiguration.mockRejectedValue(
                new Error('Jurisdiction configuration not found for oh')
            );

            await encumbranceService.sendLicenseEncumbranceStateNotificationEmail(
                'aslp',
                'oh',
                'John',
                'Doe',
                'provider-123',
                'OH',
                'Audiologist',
                '2024-01-15'
            );

            // Should not send email when jurisdiction config is missing
            expect(mockSESClient).not.toHaveReceivedCommand(SendEmailCommand);
        });
    });

    describe('License Encumbrance Lifting Provider Notification', () => {
        it('should send license encumbrance lifting provider notification email with correct content', async () => {
            await encumbranceService.sendLicenseEncumbranceLiftingProviderNotificationEmail(
                'aslp',
                ['provider@example.com'],
                'John',
                'Doe',
                'OH',
                'Audiologist',
                '2024-02-15'
            );

            expect(mockSESClient).toHaveReceivedCommandWith(
                SendEmailCommand,
                {
                    Destination: {
                        ToAddresses: ['provider@example.com']
                    },
                    Content: {
                        Simple: {
                            Body: {
                                Html: {
                                    Charset: 'UTF-8',
                                    Data: expect.stringContaining('Your Audiologist license in Ohio is no longer encumbered')
                                }
                            },
                            Subject: {
                                Charset: 'UTF-8',
                                Data: 'Your Audiologist license in Ohio is no longer encumbered'
                            }
                        }
                    },
                    FromEmailAddress: 'Compact Connect <noreply@example.org>'
                }
            );
        });

        it('should throw error when no recipients provided', async () => {
            await expect(encumbranceService.sendLicenseEncumbranceLiftingProviderNotificationEmail(
                'aslp',
                [],
                'John',
                'Doe',
                'OH',
                'Audiologist',
                '2024-02-15'
            )).rejects.toThrow('No recipients specified for provider license encumbrance lifting notification email');
        });
    });

    describe('License Encumbrance Lifting State Notification', () => {
        it('should send license encumbrance lifting state notification email with correct content', async () => {
            mockJurisdictionClient.getJurisdictionConfiguration.mockResolvedValue({
                ...SAMPLE_JURISDICTION_CONFIG,
                jurisdictionAdverseActionsNotificationEmails: ['state-adverse@example.com']
            });

            await encumbranceService.sendLicenseEncumbranceLiftingStateNotificationEmail(
                'aslp',
                'ca',
                'John',
                'Doe',
                'provider-123',
                'OH',
                'Audiologist',
                '2024-02-15'
            );

            expect(mockSESClient).toHaveReceivedCommandWith(
                SendEmailCommand,
                {
                    Destination: {
                        ToAddresses: ['state-adverse@example.com']
                    },
                    Content: {
                        Simple: {
                            Body: {
                                Html: {
                                    Charset: 'UTF-8',
                                    Data: expect.stringContaining('License Encumbrance Lifted Notification - John Doe')
                                }
                            },
                            Subject: {
                                Charset: 'UTF-8',
                                Data: 'License Encumbrance Lifted Notification - John Doe'
                            }
                        }
                    },
                    FromEmailAddress: 'Compact Connect <noreply@example.org>'
                }
            );
        });

        it('should log warning and continue when no recipients found for jurisdiction', async () => {
            mockJurisdictionClient.getJurisdictionConfiguration.mockResolvedValue({
                ...SAMPLE_JURISDICTION_CONFIG,
                jurisdictionAdverseActionsNotificationEmails: []
            });

            await encumbranceService.sendLicenseEncumbranceLiftingStateNotificationEmail(
                'aslp',
                'oh',
                'John',
                'Doe',
                'provider-123',
                'OH',
                'Audiologist',
                '2024-02-15'
            );

            // Should not send email when no recipients
            expect(mockSESClient).not.toHaveReceivedCommand(SendEmailCommand);
        });

        it('should log warning and continue when jurisdiction configuration is missing', async () => {
            mockJurisdictionClient.getJurisdictionConfiguration.mockRejectedValue(
                new Error('Jurisdiction configuration not found for oh')
            );

            await encumbranceService.sendLicenseEncumbranceLiftingStateNotificationEmail(
                'aslp',
                'oh',
                'John',
                'Doe',
                'provider-123',
                'OH',
                'Audiologist',
                '2024-02-15'
            );

            // Should not send email when jurisdiction config is missing
            expect(mockSESClient).not.toHaveReceivedCommand(SendEmailCommand);
        });
    });

    describe('Privilege Encumbrance Provider Notification', () => {
        it('should send privilege encumbrance provider notification email with correct content', async () => {
            await encumbranceService.sendPrivilegeEncumbranceProviderNotificationEmail(
                'aslp',
                ['provider@example.com'],
                'John',
                'Doe',
                'OH',
                'Audiologist',
                '2024-01-15'
            );

            expect(mockSESClient).toHaveReceivedCommandWith(
                SendEmailCommand,
                {
                    Destination: {
                        ToAddresses: ['provider@example.com']
                    },
                    Content: {
                        Simple: {
                            Body: {
                                Html: {
                                    Charset: 'UTF-8',
                                    Data: expect.stringContaining('Your Audiologist privilege in Ohio is encumbered')
                                }
                            },
                            Subject: {
                                Charset: 'UTF-8',
                                Data: 'Your Audiologist privilege in Ohio is encumbered'
                            }
                        }
                    },
                    FromEmailAddress: 'Compact Connect <noreply@example.org>'
                }
            );
        });

        it('should throw error when no recipients provided', async () => {
            await expect(encumbranceService.sendPrivilegeEncumbranceProviderNotificationEmail(
                'aslp',
                [],
                'John',
                'Doe',
                'OH',
                'Audiologist',
                '2024-01-15'
            )).rejects.toThrow('No recipients specified for provider privilege encumbrance notification email');
        });
    });

    describe('Privilege Encumbrance State Notification', () => {
        it('should send privilege encumbrance state notification email with correct content', async () => {
            mockJurisdictionClient.getJurisdictionConfiguration.mockResolvedValue({
                ...SAMPLE_JURISDICTION_CONFIG,
                jurisdictionAdverseActionsNotificationEmails: ['state-adverse@example.com']
            });

            await encumbranceService.sendPrivilegeEncumbranceStateNotificationEmail(
                'aslp',
                'ca',
                'John',
                'Doe',
                'provider-123',
                'OH',
                'Audiologist',
                '2024-01-15'
            );

            expect(mockSESClient).toHaveReceivedCommandWith(
                SendEmailCommand,
                {
                    Destination: {
                        ToAddresses: ['state-adverse@example.com']
                    },
                    Content: {
                        Simple: {
                            Body: {
                                Html: {
                                    Charset: 'UTF-8',
                                    Data: expect.stringContaining('Privilege Encumbrance Notification - John Doe')
                                }
                            },
                            Subject: {
                                Charset: 'UTF-8',
                                Data: 'Privilege Encumbrance Notification - John Doe'
                            }
                        }
                    },
                    FromEmailAddress: 'Compact Connect <noreply@example.org>'
                }
            );

            const emailContent = mockSESClient.commandCalls(SendEmailCommand)[0]
                .args[0].input.Content?.Simple?.Body?.Html?.Data;

            expect(emailContent).toContain('This encumbrance restricts the provider\'s ability to practice in Ohio under the Audiology and Speech Language Pathology compact');
        });

        it('should include provider detail link in email content', async () => {
            await encumbranceService.sendPrivilegeEncumbranceStateNotificationEmail(
                'aslp',
                'ca',
                'John',
                'Doe',
                'provider-123',
                'oh',
                'Audiologist',
                '2024-01-15'
            );

            const emailContent = mockSESClient.commandCalls(SendEmailCommand)[0].args[0]
                .input.Content?.Simple?.Body?.Html?.Data;

            expect(emailContent).toContain('Provider Details: <a href="https://app.test.compactconnect.org/aslp/Licensing/provider-123" target="_blank">https://app.test.compactconnect.org/aslp/Licensing/provider-123</a>');
            expect(emailContent).toContain('This encumbrance restricts the provider\'s ability to practice in Ohio under the Audiology and Speech Language Pathology compact');
        });

        it('should log warning and continue when no recipients found for jurisdiction', async () => {
            mockJurisdictionClient.getJurisdictionConfiguration.mockResolvedValue({
                ...SAMPLE_JURISDICTION_CONFIG,
                jurisdictionAdverseActionsNotificationEmails: []
            });

            await encumbranceService.sendPrivilegeEncumbranceStateNotificationEmail(
                'aslp',
                'oh',
                'John',
                'Doe',
                'provider-123',
                'OH',
                'Audiologist',
                '2024-01-15'
            );

            // Should not send email when no recipients
            expect(mockSESClient).not.toHaveReceivedCommand(SendEmailCommand);
        });

        it('should log warning and continue when jurisdiction configuration is missing', async () => {
            mockJurisdictionClient.getJurisdictionConfiguration.mockRejectedValue(
                new Error('Jurisdiction configuration not found for oh')
            );

            await encumbranceService.sendPrivilegeEncumbranceStateNotificationEmail(
                'aslp',
                'oh',
                'John',
                'Doe',
                'provider-123',
                'OH',
                'Audiologist',
                '2024-01-15'
            );

            // Should not send email when jurisdiction config is missing
            expect(mockSESClient).not.toHaveReceivedCommand(SendEmailCommand);
        });
    });

    describe('Privilege Encumbrance Lifting Provider Notification', () => {
        it('should send privilege encumbrance lifting provider notification email with correct content', async () => {
            await encumbranceService.sendPrivilegeEncumbranceLiftingProviderNotificationEmail(
                'aslp',
                ['provider@example.com'],
                'John',
                'Doe',
                'OH',
                'Audiologist',
                '2024-02-15'
            );

            expect(mockSESClient).toHaveReceivedCommandWith(
                SendEmailCommand,
                {
                    Destination: {
                        ToAddresses: ['provider@example.com']
                    },
                    Content: {
                        Simple: {
                            Body: {
                                Html: {
                                    Charset: 'UTF-8',
                                    Data: expect.stringContaining('Your Audiologist privilege in Ohio is no longer encumbered')
                                }
                            },
                            Subject: {
                                Charset: 'UTF-8',
                                Data: 'Your Audiologist privilege in Ohio is no longer encumbered'
                            }
                        }
                    },
                    FromEmailAddress: 'Compact Connect <noreply@example.org>'
                }
            );
        });

        it('should throw error when no recipients provided', async () => {
            await expect(encumbranceService.sendPrivilegeEncumbranceLiftingProviderNotificationEmail(
                'aslp',
                [],
                'John',
                'Doe',
                'OH',
                'Audiologist',
                '2024-02-15'
            )).rejects.toThrow('No recipients specified for provider privilege encumbrance lifting notification email');
        });
    });

    describe('Privilege Encumbrance Lifting State Notification', () => {
        it('should send privilege encumbrance lifting state notification email with correct content', async () => {
            mockJurisdictionClient.getJurisdictionConfiguration.mockResolvedValue({
                ...SAMPLE_JURISDICTION_CONFIG,
                jurisdictionAdverseActionsNotificationEmails: ['state-adverse@example.com']
            });

            await encumbranceService.sendPrivilegeEncumbranceLiftingStateNotificationEmail(
                'aslp',
                'ca',
                'John',
                'Doe',
                'provider-123',
                'OH',
                'Audiologist',
                '2024-02-15'
            );

            expect(mockSESClient).toHaveReceivedCommandWith(
                SendEmailCommand,
                {
                    Destination: {
                        ToAddresses: ['state-adverse@example.com']
                    },
                    Content: {
                        Simple: {
                            Body: {
                                Html: {
                                    Charset: 'UTF-8',
                                    Data: expect.stringContaining('Privilege Encumbrance Lifted Notification - John Doe')
                                }
                            },
                            Subject: {
                                Charset: 'UTF-8',
                                Data: 'Privilege Encumbrance Lifted Notification - John Doe'
                            }
                        }
                    },
                    FromEmailAddress: 'Compact Connect <noreply@example.org>'
                }
            );

            const emailContent = mockSESClient.commandCalls(SendEmailCommand)[0]
                .args[0].input.Content?.Simple?.Body?.Html?.Data;

            expect(emailContent).toContain('Provider Details: <a href="https://app.test.compactconnect.org/aslp/Licensing/provider-123" target="_blank">https://app.test.compactconnect.org/aslp/Licensing/provider-123</a>');
            expect(emailContent).toContain('The encumbrance no longer restricts the provider\'s ability to practice in Ohio under the Audiology and Speech Language Pathology compact');
        });

        it('should log warning and continue when no recipients found for jurisdiction', async () => {
            mockJurisdictionClient.getJurisdictionConfiguration.mockResolvedValue({
                ...SAMPLE_JURISDICTION_CONFIG,
                jurisdictionAdverseActionsNotificationEmails: []
            });

            await encumbranceService.sendPrivilegeEncumbranceLiftingStateNotificationEmail(
                'aslp',
                'oh',
                'John',
                'Doe',
                'provider-123',
                'OH',
                'Audiologist',
                '2024-02-15'
            );

            // Should not send email when no recipients
            expect(mockSESClient).not.toHaveReceivedCommand(SendEmailCommand);
        });

        it('should log warning and continue when jurisdiction configuration is missing', async () => {
            mockJurisdictionClient.getJurisdictionConfiguration.mockRejectedValue(
                new Error('Jurisdiction configuration not found for oh')
            );

            await encumbranceService.sendPrivilegeEncumbranceLiftingStateNotificationEmail(
                'aslp',
                'oh',
                'John',
                'Doe',
                'provider-123',
                'OH',
                'Audiologist',
                '2024-02-15'
            );

            // Should not send email when jurisdiction config is missing
            expect(mockSESClient).not.toHaveReceivedCommand(SendEmailCommand);
        });
    });
});
