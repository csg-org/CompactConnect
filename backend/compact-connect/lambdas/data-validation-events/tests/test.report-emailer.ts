import { Logger } from '@aws-lambda-powertools/logger';
import { SESClient } from '@aws-sdk/client-ses';
import { ReportEmailer } from '../lib/report-emailer';

describe('Report emailer', () => {
    let reportEmailer: ReportEmailer;

    beforeAll(async () => {
        process.env.DEBUG = 'true';
        process.env.DATA_EVENT_TABLE_NAME = 'some-table';
        // Tells the logger to pretty print logs for easier manual reading
        process.env.POWERTOOLS_DEV = 'true';
    });

    it('should render an html document', async () => {
        const logger = new Logger();
        const sesClient = new SESClient();
        const reportEmailer = new ReportEmailer({
            logger: logger,
            sesClient: sesClient
        });
        const template = reportEmailer.generateReport([]);

        // Any HTML document would start with a '<' and end with a '>'
        expect(template.charAt(0)).toBe('<');
        expect(template.charAt(template.length - 1)).toBe('>');
    });
});
