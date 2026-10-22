import { Logger } from '@aws-lambda-powertools/logger';
import { SendEmailCommand, SESv2Client } from '@aws-sdk/client-sesv2';
import { mockClient } from 'aws-sdk-client-mock';
import 'aws-sdk-client-mock-jest';
import { beforeEach, describe, expect, it, jest } from '@jest/globals';
import * as nodemailer from 'nodemailer';

import { formatBillingMonth, InvoiceEmailService } from '../../../lib/email/invoice-email-service';
import { InvoiceReport } from '../../../lib/models/invoice';

jest.mock('nodemailer');

const asSESClient = (mock: ReturnType<typeof mockClient>) =>
    mock as unknown as SESv2Client;

const MOCK_TRANSPORT = {
    sendMail: jest.fn<(mail?: unknown) => Promise<{ messageId?: string }>>()
        .mockResolvedValue({ messageId: 'message-id-123' }),
};

const cosmetologistReport = (): InvoiceReport => ({
    compactName: 'Cosmetology',
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
    compactName: 'Cosmetology',
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
        (nodemailer.createTransport as jest.Mock).mockReturnValue(MOCK_TRANSPORT);

        emailService = new InvoiceEmailService({
            logger: new Logger({ serviceName: 'test' }),
            sesClient: asSESClient(mockSESClient),
            compactConfigurationClient: {} as any,
            jurisdictionClient: {} as any,
        });
    });

    const sentMail = () => MOCK_TRANSPORT.sendMail.mock.calls[0][0] as {
        from: string;
        to: string[];
        subject: string;
        html: string;
        attachments: { filename: string; content: string; contentType: string }[];
    };

    describe('generateStateInvoiceCsv', () => {
        it('should list that state\'s billable licenses with category and fee', () => {
            const report = cosmetologistReport();
            const csv = emailService.generateStateInvoiceCsv(report.stateSections[0]);

            expect(csv).toContain('Jurisdiction,First Name,Last Name,Home State,License Number,Category,Fee');
            expect(csv).toContain('Ohio,Jane,Smith,OH,COS-12345,New,$25.00');
            expect(csv).toContain('Ohio,John,Doe,OH,COS-67890,Renewal,$25.00');
            expect(csv).not.toContain('COS-22222');
        });

        it('should total the fees owed by that state', () => {
            const report = cosmetologistReport();
            const ohio = emailService.generateStateInvoiceCsv(report.stateSections[0]);
            const kentucky = emailService.generateStateInvoiceCsv(report.stateSections[1]);

            expect(ohio).toContain('Total Billable,2');
            expect(ohio).toContain('Total Owed,$50.00');
            expect(ohio).not.toContain('Total Owed,$75.00');
            expect(kentucky).toContain('Total Billable,1');
            expect(kentucky).toContain('Total Owed,$25.00');
        });

        it('should show a state with no billable licenses as zero dollars', () => {
            const csv = emailService.generateStateInvoiceCsv(emptyReport().stateSections[0]);

            expect(csv).toContain('Total Billable,0');
            expect(csv).toContain('Total Owed,$0.00');
        });

        it('should quote csv cells that contain commas or quotes', () => {
            const report = cosmetologistReport();

            report.stateSections[0].lineItems[0].familyName = 'Smith, "Jr."';

            const csv = emailService.generateStateInvoiceCsv(report.stateSections[0]);

            expect(csv).toContain('Ohio,Jane,"Smith, ""Jr.""",OH,COS-12345,New,$25.00');
        });
    });

    describe('formatBillingMonth', () => {
        it('should format YYYY-MM as an English month and year', () => {
            expect(formatBillingMonth('2024-09')).toEqual('September 2024');
        });
    });

    describe('sendInvoiceEmail', () => {
        it('should send the invoice to the compact operations team', async () => {
            await emailService.sendInvoiceEmail(cosmetologistReport(), ['compact-ops@example.com']);

            expect(MOCK_TRANSPORT.sendMail).toHaveBeenCalledWith(expect.objectContaining({
                to: ['compact-ops@example.com'],
            }));
        });

        it('should set the subject from the license type and compact', async () => {
            await emailService.sendInvoiceEmail(cosmetologistReport(), ['compact-ops@example.com']);

            expect(sentMail().subject).toEqual('Monthly Cosmetologist Invoice for Cosmetology Compact');
        });

        it('should use the compact report body and attach the invoice csv', async () => {
            await emailService.sendInvoiceEmail(cosmetologistReport(), ['compact-ops@example.com']);

            const mail = sentMail();

            expect(mail.html).toContain(
                'Please find attached the monthly Cosmetologist invoices for the Cosmetology Compact for September 2024.'
            );
            expect(mail.html).toContain('CompactConnect');
            expect(mail.html).not.toContain('COS-12345');
            expect(mail.attachments).toEqual([
                expect.objectContaining({
                    filename: 'ohio-cosmetologist-invoice-2024-09.csv',
                    contentType: 'text/csv',
                }),
                expect.objectContaining({
                    filename: 'kentucky-cosmetologist-invoice-2024-09.csv',
                    contentType: 'text/csv',
                }),
            ]);
            expect(mail.attachments[0].content).toContain('Ohio,Jane,Smith,OH,COS-12345,New,$25.00');
            expect(mail.attachments[0].content).toContain('Total Owed,$50.00');
            expect(mail.attachments[1].content).toContain('Kentucky,Sam,Taylor,KY,COS-22222,New,$25.00');
            expect(mail.attachments[1].content).not.toContain('COS-12345');
        });

        it('should send from the configured CompactConnect address', async () => {
            await emailService.sendInvoiceEmail(cosmetologistReport(), ['compact-ops@example.com']);

            expect(sentMail().from).toEqual('CompactConnect <noreply@example.org>');
        });

        it('should return the SES message id', async () => {
            const messageId = await emailService.sendInvoiceEmail(
                cosmetologistReport(),
                ['compact-ops@example.com']
            );

            expect(messageId).toEqual('message-id-123');
        });

        it('should let SES errors escape', async () => {
            MOCK_TRANSPORT.sendMail.mockImplementationOnce(
                () => Promise.reject(new Error('SES error'))
            );

            await expect(
                emailService.sendInvoiceEmail(cosmetologistReport(), ['compact-ops@example.com'])
            ).rejects.toThrow('SES error');
        });

        it('should throw when SES accepts the email without a message id', async () => {
            MOCK_TRANSPORT.sendMail.mockResolvedValueOnce({ messageId: undefined });

            await expect(
                emailService.sendInvoiceEmail(cosmetologistReport(), ['compact-ops@example.com'])
            ).rejects.toThrow('Invoice email was accepted without a message id');
        });
    });
});
