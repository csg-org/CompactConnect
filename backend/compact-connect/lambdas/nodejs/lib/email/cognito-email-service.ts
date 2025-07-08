import { renderToStaticMarkup } from '@usewaypoint/email-builder';
import { BaseEmailService } from './base-email-service';
import { EnvironmentVariablesService } from '../environment-variables-service';

const environmentVariableService = new EnvironmentVariablesService();

/**
 * Email service for handling Cognito custom messages
 */
export class CognitoEmailService extends BaseEmailService {
    /**
     * Generates the appropriate email template based on Cognito trigger source
     * @param triggerSource - The Cognito trigger source
     * @param codeParameter - The code parameter to include in the message (if applicable)
     * @param usernameParameter - The username parameter to include in the message (if applicable)
     * @returns An object containing the subject and HTML content for the email
     */
    public generateCognitoMessage(
        triggerSource: string,
        codeParameter?: string,
        usernameParameter?: string
    ): { subject: string; htmlContent: string } {
        /*
         * We don't actually anticipate using all of these triggers, but we're including them just to avoid breaking
         * any Cognito flows.
         */
        switch (triggerSource) {
        // Sent as an invite, after a user is created by our API.
        // Based on the triggerSource value, we know which parameters are defined, so we will
        // assert that they are defined for each particular template.
        case 'CustomMessage_AdminCreateUser':
            return this.generateAdminCreateUserTemplate(codeParameter!, usernameParameter!);
        // Sent if a user requests to reset their password
        case 'CustomMessage_ForgotPassword':
            return this.generateForgotPasswordTemplate(codeParameter!);
        // Sent if a user changes their email attribute
        case 'CustomMessage_UpdateUserAttribute':
            return this.generateUpdateUserAttributeTemplate(codeParameter!);
        // These next ones, we don't anticipate actually using
        case 'CustomMessage_VerifyUserAttribute':
            return this.generateVerifyUserAttributeTemplate(codeParameter!);
        case 'CustomMessage_ResendCode':
            return this.generateResendCodeTemplate(codeParameter!);
        case 'CustomMessage_SignUp':
            return this.generateSignUpTemplate(codeParameter!);
        default:
            throw new Error(`Unsupported Cognito trigger source: ${triggerSource}`);
        }
    }

    /**
     * Generates a template for when an admin creates a new user
     */
    private generateAdminCreateUserTemplate(
        codeParameter: string,
        usernameParameter: string
    ): { subject: string; htmlContent: string } {
        const subject = 'Welcome to CompactConnect';
        // Make a deep copy of the template so we can modify it without affecting the original
        const template = this.getNewEmailTemplate();

        this.insertHeader(template, subject);
        const userPoolType = environmentVariableService.getUserPoolType();

        if (userPoolType === 'provider') {
            this.insertBody(template,
                `Your temporary password is: \n\n${codeParameter}\n\nYour username is: \n\n${usernameParameter}\n\nThis temporary password is valid for 24 hours. Please sign in at ${environmentVariableService.getUiBasePathUrl()}/Dashboard within the next 24 hours and change your password when prompted.`,
                'center',
                true
            );
        } else {
            this.insertBody(template,
                `Your temporary password is: \n\n${codeParameter}\n\nYour username is: \n\n${usernameParameter}\n\nPlease sign in at ${environmentVariableService.getUiBasePathUrl()}/Dashboard and change your password when prompted.`,
                'center',
                true
            );
        }

        this.insertFooter(template);

        return {
            subject,
            htmlContent: renderToStaticMarkup(template, { rootBlockId: 'root' })
        };
    }

    /**
     * Generates a template for password reset requests
     */
    private generateForgotPasswordTemplate(codeParameter: string): { subject: string; htmlContent: string } {
        const subject = 'Reset your password';
        // Make a deep copy of the template so we can modify it without affecting the original
        const template = this.getNewEmailTemplate();

        this.insertHeader(template, subject);
        this.insertBody(template,
            'You requested to reset your password. Enter the following code to proceed:',
            'center',
            true
        );
        this.insertSubHeading(template, codeParameter);
        this.insertFooter(template);

        return {
            subject,
            htmlContent: renderToStaticMarkup(template, { rootBlockId: 'root' })
        };
    }

    /**
     * Generates a template for email attribute updates
     */
    private generateUpdateUserAttributeTemplate(codeParameter: string): { subject: string; htmlContent: string } {
        const subject = 'Verify your email';
        // Make a deep copy of the template so we can modify it without affecting the original
        const template = this.getNewEmailTemplate();

        this.insertHeader(template, subject);
        this.insertBody(template,
            'Please verify your new email address by entering the following code:',
            'center',
            true
        );
        this.insertSubHeading(template, codeParameter);
        this.insertFooter(template);

        return {
            subject,
            htmlContent: renderToStaticMarkup(template, { rootBlockId: 'root' })
        };
    }

    /**
     * Generates a template for user attribute verification
     * Note: Not anticipated to be used in normal flows
     */
    private generateVerifyUserAttributeTemplate(codeParameter: string): { subject: string; htmlContent: string } {
        const subject = 'Verify your email';
        // Make a deep copy of the template so we can modify it without affecting the original
        const template = this.getNewEmailTemplate();

        this.insertHeader(template, subject);
        this.insertBody(template,
            'Please verify your email address by entering the following code:',
            'center',
            true
        );
        this.insertSubHeading(template, codeParameter);
        this.insertFooter(template);

        return {
            subject,
            htmlContent: renderToStaticMarkup(template, { rootBlockId: 'root' })
        };
    }

    /**
     * Generates a template for code resend requests
     * Note: Not anticipated to be used in normal flows
     */
    private generateResendCodeTemplate(codeParameter: string): { subject: string; htmlContent: string } {
        const subject = 'New verification code for CompactConnect';
        // Make a deep copy of the template so we can modify it without affecting the original
        const template = this.getNewEmailTemplate();

        this.insertHeader(template, subject);
        this.insertBody(template,
            'Your new verification code is:',
            'center',
            true
        );
        this.insertSubHeading(template, codeParameter);
        this.insertFooter(template);

        return {
            subject,
            htmlContent: renderToStaticMarkup(template, { rootBlockId: 'root' })
        };
    }

    /**
     * Generates a template for new user sign-ups
     * Note: Not anticipated to be used in normal flows
     */
    private generateSignUpTemplate(codeParameter: string): { subject: string; htmlContent: string } {
        const subject = 'Welcome to CompactConnect';
        // Make a deep copy of the template so we can modify it without affecting the original
        const template = this.getNewEmailTemplate();

        this.insertHeader(template, subject);
        this.insertBody(template,
            'Please verify your email address by entering the following code:',
            'center',
            true
        );
        this.insertSubHeading(template, codeParameter);
        this.insertFooter(template);

        return {
            subject,
            htmlContent: renderToStaticMarkup(template, { rootBlockId: 'root' })
        };
    }
}
