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
