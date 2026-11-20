import { Logger } from '@aws-lambda-powertools/logger';
import { EnvironmentVariablesService } from '../../lib/environment-variables-service';

describe('Environment variables service with debug', () => {
    let environmentVariables: EnvironmentVariablesService;

    beforeAll(async () => {
        process.env.DEBUG = 'true';
        process.env.DATA_EVENT_TABLE_NAME = 'some-table';
        // Tells the logger to pretty print logs for easier manual reading
        process.env.POWERTOOLS_DEV = 'true';

        environmentVariables = new EnvironmentVariablesService();
    });

    it('should produce a logger with debug log level', async () => {
        const logger = new Logger({ logLevel: environmentVariables.getLogLevel() });

        logger.debug('Test!');

        expect(logger.getLevelName()).toBe('DEBUG');
    });

    it('should produce the expected table name', async () => {
        expect(environmentVariables.getDataEventTableName()).toBe('some-table');
    });
});

describe('Environment variables service without debug', () => {
    let environmentVariables: EnvironmentVariablesService;

    beforeAll(async () => {
        delete process.env.DEBUG;
        process.env.DATA_EVENT_TABLE_NAME = 'some-table';

        environmentVariables = new EnvironmentVariablesService();
    });

    it('should produce a logger with info log level', async () => {
        const logger = new Logger({ logLevel: environmentVariables.getLogLevel() });

        logger.debug('Test!');

        expect(logger.getLevelName()).toBe('INFO');
    });
});

describe('Invoice and reporting environment variables', () => {
    const environmentVariables = new EnvironmentVariablesService();

    afterEach(() => {
        delete process.env.TRANSACTION_REPORTS_BUCKET_NAME;
        delete process.env.USER_POOL_TYPE;
        delete process.env.LICENSE_UPLOAD_DATE_INVOICE_INDEX_NAME;
        delete process.env.INVOICE_REPORTS_BUCKET_NAME;
        delete process.env.FEE_PER_LICENSE;
    });

    it('should read the transaction reports bucket and user pool type', () => {
        process.env.TRANSACTION_REPORTS_BUCKET_NAME = 'transaction-reports';
        process.env.USER_POOL_TYPE = 'staff';

        expect(environmentVariables.getTransactionReportsBucketName()).toBe('transaction-reports');
        expect(environmentVariables.getUserPoolType()).toBe('staff');
    });

    it('should read the invoice index and reports bucket', () => {
        process.env.LICENSE_UPLOAD_DATE_INVOICE_INDEX_NAME = 'licenseUploadDateInvoiceGSI';
        process.env.INVOICE_REPORTS_BUCKET_NAME = 'invoice-reports';

        expect(environmentVariables.getLicenseUploadDateInvoiceIndexName()).toBe('licenseUploadDateInvoiceGSI');
        expect(environmentVariables.getInvoiceReportsBucketName()).toBe('invoice-reports');
    });

    it('should reject a missing invoice index or reports bucket', () => {
        expect(() => environmentVariables.getLicenseUploadDateInvoiceIndexName())
            .toThrow('LICENSE_UPLOAD_DATE_INVOICE_INDEX_NAME is required');
        expect(() => environmentVariables.getInvoiceReportsBucketName())
            .toThrow('INVOICE_REPORTS_BUCKET_NAME is required');
    });

    it('should default the license fee and reject a fee that is not a number', () => {
        expect(environmentVariables.getFeePerLicense()).toBe(25);

        process.env.FEE_PER_LICENSE = 'not-a-fee';

        expect(() => environmentVariables.getFeePerLicense()).toThrow('Invalid FEE_PER_LICENSE: not-a-fee');
    });
});
