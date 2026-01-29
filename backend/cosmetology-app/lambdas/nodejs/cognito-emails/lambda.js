import { __decorate } from "tslib";
import { Logger } from '@aws-lambda-powertools/logger';
import { EnvironmentVariablesService } from '../lib/environment-variables-service';
import { CompactConfigurationClient } from '../lib/compact-configuration-client';
import { JurisdictionClient } from '../lib/jurisdiction-client';
import { CognitoEmailService } from '../lib/email';
const environmentVariables = new EnvironmentVariablesService();
const logger = new Logger({ logLevel: environmentVariables.getLogLevel() });
export class Lambda {
    emailService;
    constructor(props) {
        const compactConfigurationClient = new CompactConfigurationClient({
            logger: logger,
            dynamoDBClient: props.dynamoDBClient,
        });
        const jurisdictionClient = new JurisdictionClient({
            logger: logger,
            dynamoDBClient: props.dynamoDBClient,
        });
        this.emailService = new CognitoEmailService({
            logger: logger,
            sesClient: props.sesClient,
            s3Client: props.s3Client,
            compactConfigurationClient: compactConfigurationClient,
            jurisdictionClient: jurisdictionClient
        });
    }
    /**
     * Lambda handler for Cognito custom messages
     * https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-lambda-custom-message.html
     *
     * This handler generates custom email templates for various Cognito triggers
     * like sign up verification, password reset, etc.
     *
     * @param event - Cognito custom message event
     * @param context - Lambda context
     * @returns Modified event with custom email message and subject
     */
    async handler(event, _context) {
        logger.info('Processing Cognito custom message event', {
            triggerSource: event.triggerSource,
            userPoolId: event.userPoolId,
            userName: event.userName
        });
        try {
            const { subject, htmlContent } = this.emailService.generateCognitoMessage(event.triggerSource, event.request.codeParameter, event.request.usernameParameter);
            // Update the event response with our custom message
            event.response.emailSubject = subject;
            event.response.emailMessage = htmlContent;
            logger.info('Successfully generated custom message');
            return event;
        }
        catch (error) {
            logger.error('Error generating custom message', { error: error });
            throw error;
        }
    }
}
__decorate([
    logger.injectLambdaContext({ resetKeys: true })
], Lambda.prototype, "handler", null);
//# sourceMappingURL=lambda.js.map