import { Logger } from '@aws-lambda-powertools/logger';
import { SendEmailCommand, SESv2Client } from '@aws-sdk/client-sesv2';
import { mockClient } from 'aws-sdk-client-mock';
import 'aws-sdk-client-mock-jest';
import { beforeEach, describe, expect, it, jest } from '@jest/globals';

import { InvoiceEmailService } from '../../../lib/email/invoice-email-service';
import { InvoiceReport } from '../../../lib/models/invoice';

const asSESClient = (mock: ReturnType<typeof mockClient>) =>
    mock as unknown as SESv2Client;

const cosmetologistReport = (): InvoiceReport => ({
    compactName: 'Cosmetology Compact',
    licenseType: 'cosmetologist',
    billingMonth: '2024-09',
    stateSections: [
        {
            jurisdictionName: 'Ohio',
            postalAbbreviation: 'oh',
            lineItems: [
                {
                    givenName: 'Jane',
                    familyName: 'Smith',
                    homeState: 'OH',
                    licenseNumber: 'COS-12345',
                    licenseType: 'cosmetologist',
                    category: 'new',
                    fee: 25,
                },
                {
                    givenName: 'John',
                    familyName: 'Doe',
                    homeState: 'OH',
                    licenseNumber: 'COS-67890',
                    licenseType: 'cosmetologist',
                    category: 'renewal',
                    fee: 25,
                },
            ],
        },
        {
            jurisdictionName: 'Kentucky',
            postalAbbreviation: 'ky',
            lineItems: [
                {
                    givenName: 'Sam',
                    familyName: 'Taylor',
                    homeState: 'KY',
                    licenseNumber: 'COS-22222',
                    licenseType: 'cosmetologist',
                    category: 'new',
                    fee: 25,
                },
            ],
        },
    ],
    totalUploaded: 4,
    totalBillable: 3,
    totalOwed: 75,
});

const emptyReport = (): InvoiceReport => ({
    compactName: 'Cosmetology Compact',
    licenseType: 'esthetician',
    billingMonth: '2024-09',
    stateSections: [
        {
            jurisdictionName: 'Kentucky',
            postalAbbreviation: 'ky',
            lineItems: [],
        },
    ],
    totalUploaded: 0,
    totalBillable: 0,
    totalOwed: 0,
});

describe('InvoiceEmailService', () => {
    let emailService: InvoiceEmailService;
    let mockSESClient: ReturnType<typeof mockClient>;

    beforeEach(() => {
        jest.clearAllMocks();
        process.env.FROM_ADDRESS = 'noreply@example.org';
        process.env.UI_BASE_PATH_URL = 'https://app.test.compactconnect.org';

        mockSESClient = mockClient(SESv2Client);
        mockSESClient.on(SendEmailCommand).resolves({
            MessageId: 'message-id-123',
        });

        emailService = new InvoiceEmailService({
            logger: new Logger({ serviceName: 'test' }),
            sesClient: asSESClient(mockSESClient),
            compactConfigurationClient: {} as any,
            jurisdictionClient: {} as any,
        });
    });

    describe('generateInvoiceHtml', () => {
        it('should produce an HTML document', () => {
            const html = emailService.generateInvoiceHtml(cosmetologistReport());

            expect(html.startsWith('<!DOCTYPE html')).toBe(true);
        });

        it('should include the licensee name, license number, and home state', () => {
            const html = emailService.generateInvoiceHtml(cosmetologistReport());

            expect(html).toContain('Jane Smith');
            expect(html).toContain('COS-12345');
            expect(html).toContain('OH');
        });

        it('should label first uploads as New and renewals as Renewal', () => {
            const html = emailService.generateInvoiceHtml(cosmetologistReport());

            expect(html).toMatch(/\bNew\b/);
            expect(html).toMatch(/\bRenewal\b/);
        });

        it('should show the $25.00 fee on each line item', () => {
            const html = emailService.generateInvoiceHtml(cosmetologistReport());

            expect(html.match(/\$25\.00/g)?.length).toBeGreaterThanOrEqual(3);
        });

        it('should show each state subtotal as a license count and amount owed', () => {
            const html = emailService.generateInvoiceHtml(cosmetologistReport());

            expect(html).toContain('2 licenses — $50.00 owed');
            expect(html).toContain('1 license — $25.00 owed');
        });

        it('should show the grand total owed to the Cosmetology Compact', () => {
            const html = emailService.generateInvoiceHtml(cosmetologistReport());

            expect(html).toContain('Total owed to Cosmetology Compact: $75.00');
        });

        it('should show the total uploaded count separately from the billable count', () => {
            const html = emailService.generateInvoiceHtml(cosmetologistReport());

            expect(html).toContain('Total uploaded: 4');
            expect(html).toContain('Total billable: 3');
        });

        it('should render a state with no billable licenses as zero dollars', () => {
            const html = emailService.generateInvoiceHtml(emptyReport());

            expect(html).toContain('0 licenses — $0.00 owed');
            expect(html).toContain('Total owed to Cosmetology Compact: $0.00');
        });
    });

    describe('sendInvoiceEmail', () => {
        it('should send the invoice to the compact operations team', async () => {
            await emailService.sendInvoiceEmail(cosmetologistReport(), ['compact-ops@example.com']);

            expect(mockSESClient).toHaveReceivedCommandWith(SendEmailCommand, {
                Destination: {
                    ToAddresses: ['compact-ops@example.com'],
                },
            });
        });

        it('should set the subject from the compact, license type, and billing month', async () => {
            await emailService.sendInvoiceEmail(cosmetologistReport(), ['compact-ops@example.com']);

            const subject = mockSESClient.commandCalls(SendEmailCommand)[0].args[0].input.Content?.Simple?.Subject;

            expect(subject).toEqual({
                Charset: 'UTF-8',
                Data: '[Cosmetology Compact] Cosmetologist Invoice — September 2024',
            });
        });

        it('should send from the configured CompactConnect address', async () => {
            await emailService.sendInvoiceEmail(cosmetologistReport(), ['compact-ops@example.com']);

            expect(mockSESClient).toHaveReceivedCommandWith(SendEmailCommand, {
                FromEmailAddress: 'CompactConnect <noreply@example.org>',
            });
        });

        it('should return the SES message id', async () => {
            const messageId = await emailService.sendInvoiceEmail(
                cosmetologistReport(),
                ['compact-ops@example.com']
            );

            expect(messageId).toEqual('message-id-123');
        });

        it('should let SES errors escape', async () => {
            mockSESClient.on(SendEmailCommand).rejects(new Error('SES error'));

            await expect(
                emailService.sendInvoiceEmail(cosmetologistReport(), ['compact-ops@example.com'])
            ).rejects.toThrow('SES error');
        });
    });
});
