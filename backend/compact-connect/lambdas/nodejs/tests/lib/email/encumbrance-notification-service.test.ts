import { mockClient } from 'aws-sdk-client-mock';
import 'aws-sdk-client-mock-jest';
import { Logger } from '@aws-lambda-powertools/logger';
import { SendEmailCommand, SESClient } from '@aws-sdk/client-ses';
import { S3Client } from '@aws-sdk/client-s3';
import { EncumbranceNotificationService } from '../../../lib/email';
import { CompactConfigurationClient } from '../../../lib/compact-configuration-client';
import { JurisdictionClient } from '../../../lib/jurisdiction-client';
import { describe, it, expect, beforeEach, jest } from '@jest/globals';

const SAMPLE_JURISDICTION_CONFIG = {
    pk: 'aslp#CONFIGURATION',
    sk: 'aslp#JURISDICTION#OH',
    jurisdictionName: 'Ohio',
    postalAbbreviation: 'OH',
    compact: 'aslp',
    jurisdictionOperationsTeamEmails: ['oh-ops@example.com'],
    jurisdictionAdverseActionsNotificationEmails: ['oh-adverse@example.com'],
    jurisdictionSummaryReportNotificationEmails: ['oh-summary@example.com']
};

const asSESClient = (mock: ReturnType<typeof mockClient>) =>
    mock as unknown as SESClient;

const asS3Client = (mock: ReturnType<typeof mockClient>) =>
    mock as unknown as S3Client;

describe('EncumbranceNotificationService', () => {
    let encumbranceService: EncumbranceNotificationService;
    let mockSESClient: ReturnType<typeof mockClient>;
    let mockS3Client: ReturnType<typeof mockClient>;
    let mockCompactConfigurationClient: jest.Mocked<CompactConfigurationClient>;
    let mockJurisdictionClient: jest.Mocked<JurisdictionClient>;

    beforeEach(() => {
        jest.clearAllMocks();
        mockSESClient = mockClient(SESClient);
        mockS3Client = mockClient(S3Client);
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

        // Set up default successful responses
        mockSESClient.on(SendEmailCommand).resolves({
            MessageId: 'message-id-123'
        });

        mockJurisdictionClient.getJurisdictionConfiguration.mockResolvedValue(SAMPLE_JURISDICTION_CONFIG);

        encumbranceService = new EncumbranceNotificationService({
            logger: new Logger({ serviceName: 'test' }),
            sesClient: asSESClient(mockSESClient),
            s3Client: asS3Client(mockS3Client),
            compactConfigurationClient: mockCompactConfigurationClient,
            jurisdictionClient: mockJurisdictionClient
        });
    });

    describe('License Encumbrance Provider Notification', () => {
        it('should send license encumbrance provider notification email with correct content', async () => {
            await encumbranceService.sendLicenseEncumbranceProviderNotificationEmail(
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
                    Message: {
                        Body: {
                            Html: {
                                Charset: 'UTF-8',
                                Data: expect.stringContaining('Your Audiologist license in OH is encumbered')
                            }
                        },
                        Subject: {
                            Charset: 'UTF-8',
                            Data: 'Your Audiologist license in OH is encumbered'
                        }
                    },
                    Source: 'Compact Connect <noreply@example.org>'
                }
            );
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
        it('should send jurisdiction license encumbrance state notification email', async () => {
            mockJurisdictionClient.getJurisdictionConfiguration.mockResolvedValue({
                ...SAMPLE_JURISDICTION_CONFIG,
                jurisdictionAdverseActionsNotificationEmails: ['state-adverse@example.com']
            });

            await encumbranceService.sendLicenseEncumbranceStateNotificationEmail(
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
                    Message: {
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
                    },
                    Source: 'Compact Connect <noreply@example.org>'
                }
            );
        });

        it('should throw error when no recipients found for jurisdiction', async () => {
            mockJurisdictionClient.getJurisdictionConfiguration.mockResolvedValue({
                ...SAMPLE_JURISDICTION_CONFIG,
                jurisdictionAdverseActionsNotificationEmails: []
            });

            await expect(encumbranceService.sendLicenseEncumbranceStateNotificationEmail(
                'aslp',
                'oh',
                'John',
                'Doe',
                'provider-123',
                'OH',
                'Audiologist',
                '2024-01-15'
            )).rejects.toThrow('No adverse action notification recipients found for jurisdiction oh in compact aslp');
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
                    Message: {
                        Body: {
                            Html: {
                                Charset: 'UTF-8',
                                Data: expect.stringContaining('Your Audiologist license in OH is no longer encumbered')
                            }
                        },
                        Subject: {
                            Charset: 'UTF-8',
                            Data: 'Your Audiologist license in OH is no longer encumbered'
                        }
                    },
                    Source: 'Compact Connect <noreply@example.org>'
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
                    Message: {
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
                    },
                    Source: 'Compact Connect <noreply@example.org>'
                }
            );
        });

        it('should throw error when no recipients found for jurisdiction', async () => {
            mockJurisdictionClient.getJurisdictionConfiguration.mockResolvedValue({
                ...SAMPLE_JURISDICTION_CONFIG,
                jurisdictionAdverseActionsNotificationEmails: []
            });

            await expect(encumbranceService.sendLicenseEncumbranceLiftingStateNotificationEmail(
                'aslp',
                'oh',
                'John',
                'Doe',
                'provider-123',
                'OH',
                'Audiologist',
                '2024-02-15'
            )).rejects.toThrow('No adverse action notification recipients found for jurisdiction oh in compact aslp');
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
                    Message: {
                        Body: {
                            Html: {
                                Charset: 'UTF-8',
                                Data: expect.stringContaining('Your Audiologist privilege in OH is encumbered')
                            }
                        },
                        Subject: {
                            Charset: 'UTF-8',
                            Data: 'Your Audiologist privilege in OH is encumbered'
                        }
                    },
                    Source: 'Compact Connect <noreply@example.org>'
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
                    Message: {
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
                    },
                    Source: 'Compact Connect <noreply@example.org>'
                }
            );

            const emailContent = mockSESClient.commandCalls(SendEmailCommand)[0].args[0].input.Message?.Body?.Html?.Data;
            expect(emailContent).toContain('This encumbrance restricts the provider&#x27;s ability to practice in OH under the ASLP Compact');
        });

        it('should include provider detail link in email content', async () => {
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

            const emailContent = mockSESClient.commandCalls(SendEmailCommand)[0].args[0].input.Message?.Body?.Html?.Data;
            expect(emailContent).toContain('Provider Details: https://app.test.compactconnect.org/aslp/Licensing/provider-123');
            expect(emailContent).toContain('This encumbrance restricts the provider&#x27;s ability to practice in OH under the ASLP Compact');
        });

        it('should throw error when no recipients found for jurisdiction', async () => {
            mockJurisdictionClient.getJurisdictionConfiguration.mockResolvedValue({
                ...SAMPLE_JURISDICTION_CONFIG,
                jurisdictionAdverseActionsNotificationEmails: []
            });

            await expect(encumbranceService.sendPrivilegeEncumbranceStateNotificationEmail(
                'aslp',
                'oh',
                'John',
                'Doe',
                'provider-123',
                'OH',
                'Audiologist',
                '2024-01-15'
            )).rejects.toThrow('No adverse action notification recipients found for jurisdiction oh in compact aslp');
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
                    Message: {
                        Body: {
                            Html: {
                                Charset: 'UTF-8',
                                Data: expect.stringContaining('Your Audiologist privilege in OH is no longer encumbered')
                            }
                        },
                        Subject: {
                            Charset: 'UTF-8',
                            Data: 'Your Audiologist privilege in OH is no longer encumbered'
                        }
                    },
                    Source: 'Compact Connect <noreply@example.org>'
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
                    Message: {
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
                    },
                    Source: 'Compact Connect <noreply@example.org>'
                }
            );

            const emailContent = mockSESClient.commandCalls(SendEmailCommand)[0].args[0].input.Message?.Body?.Html?.Data;
            expect(emailContent).toContain('Provider Details: https://app.test.compactconnect.org/aslp/Licensing/provider-123');
            expect(emailContent).toContain('The encumbrance no longer restricts the provider&#x27;s ability to practice in OH under the ASLP Compact');
        });

        it('should throw error when no recipients found for jurisdiction', async () => {
            mockJurisdictionClient.getJurisdictionConfiguration.mockResolvedValue({
                ...SAMPLE_JURISDICTION_CONFIG,
                jurisdictionAdverseActionsNotificationEmails: []
            });

            await expect(encumbranceService.sendPrivilegeEncumbranceLiftingStateNotificationEmail(
                'aslp',
                'oh',
                'John',
                'Doe',
                'provider-123',
                'OH',
                'Audiologist',
                '2024-02-15'
            )).rejects.toThrow('No adverse action notification recipients found for jurisdiction oh in compact aslp');
        });
    });
});
