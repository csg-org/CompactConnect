const dotenv = require('dotenv');
const { Amplify } = require('aws-amplify');
const { signIn, fetchAuthSession } = require('@aws-amplify/auth');

// Load environment variables
dotenv.config();

const cognitoUserPoolId = process.env.COGNITO_USER_POOL_ID;
const cognitoUserPoolClientId = process.env.COGNITO_USER_POOL_CLIENT_ID;
// Main execution
const cognitoUsername = process.env.COGNITO_USERNAME;
const cognitoPassword = process.env.COGNITO_PASSWORD;

if (!cognitoUserPoolId || !cognitoUserPoolClientId || !cognitoUsername || !cognitoPassword) {
    console.error('Missing environment variables');
    process.exit(1);
}

// Configure Amplify
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
