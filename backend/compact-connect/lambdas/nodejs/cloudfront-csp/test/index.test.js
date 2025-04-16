//
//  index.test.js
//  CompactConnect
//
//  Created by InspiringApps on 7/22/2024.
//

const fs = require('fs');
const path = require('path');
const {
    expect,
    testFilename,
    runLambda,
    lambdaConfig
} = require('./config');

// ================================================================================================
// =                                        SETUP                                                 =
// ================================================================================================
const environment_values = {
    webFrontend: 'app.compactconnect.org',
    dataApi: 'api.compactconnect.org',
    s3UploadUrlState: 'prod-persistentstack-bulkuploadsbucketda4bdcd0-zq5o0q8uqq5i.s3.amazonaws.com',
    s3UploadUrlProvider: 'prod-persistentstack-providerusersbucket5c7b202b-ffpgh4fyozwk.s3.amazonaws.com',
    cognitoStaff: 'compact-connect-staff.auth.us-east-1.amazoncognito.com',
    cognitoProvider: 'compact-connect-provider.auth.us-east-1.amazoncognito.com',
};

/**
 * Helper function to replace placeholders in the Lambda code with test values
 * 
 * At deploy time, there are placeholders in the Lambda code that are replaced with the actual values.
 * From the CDK deployment. To run these tests, we need to replace the placeholders
 * with test values.
 * 
 * @returns {string} The relative path to the prepared Lambda file for testing
 */
const prepareLambdaForTest = () => {
    // Path to the original Lambda file
    const originalLambdaPath = path.join(__dirname, '..', 'index.js');
    // Path to the temporary test Lambda file
    const testLambdaPath = path.join(__dirname, 'temp-index.js');
    
    // Read the original Lambda file
    let lambdaCode = fs.readFileSync(originalLambdaPath, 'utf8');
    
    // Replace placeholders with test values
    const replacements = {
        '##WEB_FRONTEND##': environment_values.webFrontend,
        '##DATA_API##': environment_values.dataApi,
        '##S3_UPLOAD_URL_STATE##': environment_values.s3UploadUrlState,
        '##S3_UPLOAD_URL_PROVIDER##': environment_values.s3UploadUrlProvider,
        '##COGNITO_STAFF##': environment_values.cognitoStaff,
        '##COGNITO_PROVIDER##': environment_values.cognitoProvider,
    };
    
    // Apply all replacements to the Lambda code
    for (const [placeholder, value] of Object.entries(replacements)) {
        lambdaCode = lambdaCode.replace(new RegExp(placeholder, 'g'), value);
    }
    
    // Write the modified Lambda code to the temporary test file
    fs.writeFileSync(testLambdaPath, lambdaCode);
    
    console.log(`Created temporary Lambda test file at: ${testLambdaPath}`);
    
    // Return a relative path that will work correctly with the lambdaPath function in config
    // lambdaPath joins with __dirname, '../..' so this needs to be a path relative to the lambda root
    return 'test/temp-index.js';
};

const buildCspHeaders = (environment) => {
    const dataApiUrl = (environment?.dataApi) ? `https://${environment.dataApi}` : '';
    const s3UploadUrlState = (environment?.s3UploadUrlState) ? `https://${environment.s3UploadUrlState}` : '';
    const s3UploadUrlProvider = (environment?.s3UploadUrlProvider) ? `https://${environment.s3UploadUrlProvider}` : '';
    const cognitoStaffUrl = (environment?.cognitoStaff) ? `https://${environment.cognitoStaff}` : '';
    const cognitoProviderUrl = (environment?.cognitoProvider) ? `https://${environment.cognitoProvider}` : '';
    const cognitoIdpUrl = 'https://cognito-idp.us-east-1.amazonaws.com';
    // src configs are maintained here as arrays for ease of maintenance;
    // defining them as static strings could lead to long lines of code.
    const cspDefaultSrc = [
        '\'none\'',
    ].join(' ');
    const cspManifestSrc = [
        '\'self\'',
    ].join(' ');
    const cspScriptSrc = [
        '\'self\'',
        'https://www.google.com/recaptcha/',
        'https://www.gstatic.com/recaptcha/',
    ].join(' ');
    const cspScriptSrcElem = [
        '\'self\'',
        'https://www.google.com/recaptcha/',
        'https://www.gstatic.com/recaptcha/',
    ].join(' ');
    const cspScriptSrcAttr = [
        '\'self\'',
    ].join(' ');
    const cspWorkerSrc = [
        '\'self\'',
    ].join(' ');
    const cspStyleSrc = [
        '\'self\'',
        'https://fonts.googleapis.com',
        'https://www.gstatic.com/recaptcha/',
    ].join(' ');
    const cspStyleSrcElem = [
        '\'self\'',
        'https://fonts.googleapis.com',
    ].join(' ');
    const cspStyleSrcAttr = [
        '\'self\'',
    ].join(' ');
    const cspFontSrc = [
        '\'self\'',
        'https://fonts.gstatic.com',
    ].join(' ');
    const cspImgSrc = [
        '\'self\'',
        'data:',
        dataApiUrl,
        'https://www.gstatic.com/recaptcha/',
    ].join(' ');
    const cspMediaSrc = [
        '\'self\'',
        dataApiUrl,
    ].join(' ');
    const cspFrameSrc = [
        '\'self\'',
        'https://www.google.com/recaptcha/',
        'https://recaptcha.google.com/recaptcha/',
    ].join(' ');
    const cspFrameAncestorsSrc = [
        '\'none\'',
    ].join(' ');
    const cspObjectSrc = [
        '\'none\'',
    ].join(' ');
    const cspFormActionSrc = [
        '\'none\'',
    ].join(' ');
    const cspConnectSrc = [
        '\'self\'',
        dataApiUrl,
        s3UploadUrlState,
        s3UploadUrlProvider,
        cognitoStaffUrl,
        cognitoProviderUrl,
        cognitoIdpUrl,
        'https://www.google.com/recaptcha/',
    ].join(' ');

    return `${[
        `default-src ${cspDefaultSrc};`,
        `manifest-src ${cspManifestSrc};`,
        `script-src ${cspScriptSrc};`,
        `script-src-elem ${cspScriptSrcElem};`,
        `script-src-attr ${cspScriptSrcAttr};`,
        `worker-src ${cspWorkerSrc};`,
        `style-src ${cspStyleSrc};`,
        `style-src-elem ${cspStyleSrcElem};`,
        `style-src-attr ${cspStyleSrcAttr};`,
        `font-src ${cspFontSrc};`,
        `img-src ${cspImgSrc};`,
        `media-src ${cspMediaSrc};`,
        `frame-src ${cspFrameSrc};`,
        `frame-ancestors ${cspFrameAncestorsSrc};`,
        `object-src ${cspObjectSrc};`,
        `form-action ${cspFormActionSrc};`,
        `connect-src ${cspConnectSrc};`,
    ].join(' ')}`;
};

const checkLambdaResult = (result) => {
    expect(result.headers['strict-transport-security'][0].key).to.equal('Strict-Transport-Security');
    expect(result.headers['strict-transport-security'][0].value).to.equal('max-age=31536000; includeSubdomains; preload');
    expect(result.headers['x-content-type-options'][0].key).to.equal('X-Content-Type-Options');
    expect(result.headers['x-content-type-options'][0].value).to.equal('nosniff');
    expect(result.headers['x-frame-options'][0].key).to.equal('X-Frame-Options');
    expect(result.headers['x-frame-options'][0].value).to.equal('DENY');
    expect(result.headers['referrer-policy'][0].key).to.equal('Referrer-Policy');
    expect(result.headers['referrer-policy'][0].value).to.equal('strict-origin-when-cross-origin');
    expect(result.headers['content-security-policy'][0].key).to.equal('Content-Security-Policy');
    expect(result.headers['content-security-policy'][0].value).to.equal(buildCspHeaders(environment_values));
    expect(result.headers.server[0].key).to.equal('Server');
    expect(result.headers.server[0].value).to.equal('CompactConnect');
};

// ================================================================================================
// =                                        TESTS                                                 =
// ================================================================================================
describe(testFilename(__filename), () => {
    // Prepare the Lambda test file once before all tests
    let testLambdaPath;
    
    before(() => {
        testLambdaPath = prepareLambdaForTest();
    });
    
    // Clean up the test Lambda file after all tests
    after(() => {
        // Get the full path to the file for deletion
        const fullPath = path.join(__dirname, 'temp-index.js');
        if (fs.existsSync(fullPath)) {
            fs.unlinkSync(fullPath);
            console.log(`Removed temporary test file: ${fullPath}`);
        }
    });
    
    describe('Cloudfront security headers', () => {
        it('should successfully return the security headers', async () => {
            const request = {
                headers: {
                    host: [{
                        value: environment_values.webFrontend,
                    }],
                },
            };
            const response = {
                headers: {},
            };
            const config = lambdaConfig({
                lambdaPath: testLambdaPath,
                request,
                response,
            });
            const result = await runLambda(config);

            checkLambdaResult(result);
        });
        it('should successfully return the security headers when subdomain is missing', async () => {
            const request = {
                origin: {
                    custom: {
                        domainName: `compactconnect.org`,
                    },
                },
            };
            const response = {
                headers: {},
            };
            const config = lambdaConfig({
                lambdaPath: testLambdaPath,
                request,
                response,
            });
            const result = await runLambda(config);

            checkLambdaResult(result);
        });
        it('should successfully return the security headers when lambda event is missing the request domain', async () => {
            const request = {
                origin: {},
            };
            const response = {
                headers: {},
            };
            const config = lambdaConfig({
                lambdaPath: testLambdaPath,
                request,
                response,
            });
            const result = await runLambda(config);

            checkLambdaResult(result);
        });
    });
});
