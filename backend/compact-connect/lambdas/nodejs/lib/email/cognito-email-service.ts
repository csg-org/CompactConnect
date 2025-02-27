import { renderToStaticMarkup } from '@usewaypoint/email-builder';
import { BaseEmailService } from './base-email-service';
import { EnvironmentVariablesService } from '../environment-variables-service';

const environmentVariableService = new EnvironmentVariablesService();

/**
 * Email service for handling Cognito custom messages
 */
export class CognitoEmailService extends BaseEmailService {
    /**
     * Generates an HTML email template for Cognito custom messages
     * @param subject - The email subject
     * @param bodyText - The email body text
     * @returns HTML content for the email
     */
    public generateCognitoEmailTemplate(subject: string, bodyText: string): string {
        const report = JSON.parse(JSON.stringify(this.emailTemplate));

        this.insertHeader(report, subject);
        this.insertMarkdownBody(report, bodyText);
        this.insertFooter(report);

        return renderToStaticMarkup(report, { rootBlockId: 'root' });
    }

    /**
     * Generates the appropriate email template based on Cognito trigger source
     * @param triggerSource - The Cognito trigger source
     * @param codeParameter - The code parameter to include in the message (if applicable)
     * @param usernameParameter - The username parameter to include in the message (if applicable)
     * @returns An object containing the subject and HTML content for the email
     */
    public generateCognitoMessage(triggerSource: string, codeParameter?: string, usernameParameter?: string): { subject: string; htmlContent: string } {
        let subject: string;
        let bodyText: string;

        switch (triggerSource) {
            /*
             * We don't actually anticipate using all of these triggers, but we're including them just to avoid breaking
             * any Cognito flows.
             */
            // Sent as an invite, after a user is created by our API.
            case 'CustomMessage_AdminCreateUser':
                subject = 'Welcome to CompactConnect';
                bodyText = `Your temporary password is: ${codeParameter}\n\nUsername: ${usernameParameter}\n\n` +
                `Please sign in at ${environmentVariableService.getUiBasePathUrl()}/Login and change your password when prompted.`;
                break;
            // Sent if a user requests to reset their password
            case 'CustomMessage_ForgotPassword':
                subject = 'Reset your password';
                bodyText = `You requested to reset your password. Enter the following code to proceed: ${codeParameter}`;
                break;
            // Sent if a user changes their email attribute
            case 'CustomMessage_UpdateUserAttribute':
                subject = 'Verify your email';
                bodyText = `Please verify your new email address by entering the following code: ${codeParameter}`;
                break;
            // These next ones, we don't anticipate actually using
            case 'CustomMessage_VerifyUserAttribute':
                subject = 'Verify your email';
                bodyText = `Please verify your email address by entering the following code: ${codeParameter}`;
                break;
            case 'CustomMessage_ResendCode':
                subject = 'New verification code for CompactConnect';
                bodyText = `Your new verification code is: ${codeParameter}`;
                break;
            case 'CustomMessage_SignUp':
                subject = 'Welcome to CompactConnect';
                bodyText = `Please verify your email address by entering the following code: ${codeParameter}`;
                break;
            default:
                throw new Error(`Unsupported Cognito trigger source: ${triggerSource}`);
        }

        const htmlContent = this.generateCognitoEmailTemplate(subject, bodyText);
        return { subject, htmlContent };
    }
}
