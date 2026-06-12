const dotenv = require('dotenv');
const { Amplify } = require('aws-amplify');
const { signIn, fetchAuthSession } = require('@aws-amplify/auth');

dotenv.config();

// --mode=staff reads STAFF_COGNITO_*, --mode=provider reads PROVIDER_COGNITO_*.
const modeArg = process.argv.find((arg) => arg.startsWith('--mode='));
const mode = modeArg ? modeArg.split('=')[1] : '';
if (!mode) {
    console.error('Missing --mode=staff|provider');
    process.exit(1);
}
const prefix = `${mode.toUpperCase()}_`;

const cognitoUserPoolId = process.env[`${prefix}COGNITO_USER_POOL_ID`];
const cognitoUserPoolClientId = process.env[`${prefix}COGNITO_USER_POOL_CLIENT_ID`];
const cognitoUsername = process.env[`${prefix}COGNITO_USERNAME`];
const cognitoPassword = process.env[`${prefix}COGNITO_PASSWORD`];

if (!cognitoUserPoolId || !cognitoUserPoolClientId || !cognitoUsername || !cognitoPassword) {
    console.error(`Missing environment variables for mode=${mode}`);
    process.exit(1);
}

Amplify.configure({
    Auth: {
        Cognito: {
            userPoolId: cognitoUserPoolId,
            userPoolClientId: cognitoUserPoolClientId
        }
    }
});

async function getTokens() {
    const session = await fetchAuthSession();

    return {
        accessToken: session.tokens?.accessToken.toString(),
        idToken: session.tokens?.idToken.toString()
    };
}

async function signInUser(username, password) {
    try {
        const {
            isSignedIn,
            nextStep
        } = await signIn({ username, password });

        if (isSignedIn) {
            console.error('User signed in successfully');
            const tokens = await getTokens();

            console.log(JSON.stringify(tokens));
        } else {
            console.error('Additional steps required:', nextStep);
            process.exitCode = 3;
        }
    } catch (error) {
        console.error('Error signing in:', error);
        process.exitCode = 3;
    }
}

signInUser(cognitoUsername, cognitoPassword);
