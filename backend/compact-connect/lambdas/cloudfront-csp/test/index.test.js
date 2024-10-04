//
//  index.test.js
//  CompactConnect
//
//  Created by InspiringApps on 7/22/2024.
//

const {
    expect,
    testFilename,
    runLambda,
    lambdaConfig
} = require('./config');

// ================================================================================================
// =                                        SETUP                                                 =
// ================================================================================================
const environments = {
    csg: {
        prod: {
            webFrontend: `app.compactconnect.org`,
            dataApi: `api.compactconnect.org`,
            s3Upload: `prod-persistentstack-bulkuploadsbucketda4bdcd0-zq5o0q8uqq5i.s3.amazonaws.com`,
            cognitoStaff: `compact-connect-staff.auth.us-east-1.amazoncognito.com`,
            cognitoProvider: `compact-connect-provider.auth.us-east-1.amazoncognito.com`,
        },
        test: {
            webFrontend: `app.test.compactconnect.org`,
            dataApi: `api.test.compactconnect.org`,
            s3Upload: `test-persistentstack-bulkuploadsbucketda4bdcd0-gxzuwbuqfepm.s3.amazonaws.com`,
            cognitoStaff: `compact-connect-staff-test.auth.us-east-1.amazoncognito.com`,
            cognitoProvider: `compact-connect-provider-test.auth.us-east-1.amazoncognito.com`,
        },
    },
    ia: {
        prod: {
            webFrontend: `app.jcc.iaapi.io`,
            dataApi: `api.jcc.iaapi.io`,
            s3Upload: ``,
            cognitoStaff: ``,
            cognitoProvider: ``,
        },
        test: {
            webFrontend: `app.test.jcc.iaapi.io`,
            dataApi: `api.test.jcc.iaapi.io`,
            s3Upload: `test-persistentstack-bulkuploadsbucketda4bdcd0-er1izmgsrdva.s3.amazonaws.com`,
            cognitoStaff: `ia-cc-staff-test.auth.us-east-1.amazoncognito.com`,
            cognitoProvider: `ia-cc-provider-test.auth.us-east-1.amazoncognito.com`,
        },
        justin: {
            webFrontend: `app.justin.jcc.iaapi.io`,
            dataApi: `api.test.jcc.iaapi.io`,
            s3Upload: `test-persistentstack-mockbulkuploadsbucket0e8f27eb-4h1anohxetmp.s3.amazonaws.com`,
            cognitoStaff: ``,
            cognitoProvider: ``,
        },
    },
};
const buildCspHeaders = (environment) => {
    const dataApiUrl = (environment?.dataApi) ? `https://${environment.dataApi}` : '';
    const s3Url = (environment?.s3Upload) ? `https://${environment.s3Upload}` : '';
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
    ].join(' ');
    const cspScriptSrcElem = [
        '\'self\'',
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
    ].join(' ');
    const cspMediaSrc = [
        '\'self\'',
        dataApiUrl,
    ].join(' ');
    const cspFrameSrc = [
        '\'self\'',
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
        s3Url,
        cognitoStaffUrl,
        cognitoProviderUrl,
        cognitoIdpUrl,
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
const checkLambdaResult = (environment, result) => {
    expect(result.headers['strict-transport-security'][0].key).to.equal('Strict-Transport-Security');
    expect(result.headers['strict-transport-security'][0].value).to.equal('max-age=31536000; includeSubdomains; preload');
    expect(result.headers['x-content-type-options'][0].key).to.equal('X-Content-Type-Options');
    expect(result.headers['x-content-type-options'][0].value).to.equal('nosniff');
    expect(result.headers['x-frame-options'][0].key).to.equal('X-Frame-Options');
    expect(result.headers['x-frame-options'][0].value).to.equal('DENY');
    expect(result.headers['referrer-policy'][0].key).to.equal('Referrer-Policy');
    expect(result.headers['referrer-policy'][0].value).to.equal('strict-origin-when-cross-origin');
    expect(result.headers['content-security-policy'][0].key).to.equal('Content-Security-Policy');
    expect(result.headers['content-security-policy'][0].value).to.equal(buildCspHeaders(environment));
    expect(result.headers.server[0].key).to.equal('Server');
    expect(result.headers.server[0].value).to.equal('CompactConnect');
};

// ================================================================================================
// =                                        TESTS                                                 =
// ================================================================================================
describe(testFilename(__filename), () => {
    describe('Cloudfront security headers', () => {
        it('should successfully return the security headers for csg prod', async () => {
            const environment = environments.csg.prod;
            const request = {
                headers: {
                    host: [{
                        value: environment.webFrontend,
                    }],
                },
            };
            const response = {
                headers: {},
            };
            const config = lambdaConfig({
                lambdaPath: `index.js`,
                request,
                response,
            });
            const result = await runLambda(config);

            checkLambdaResult(environment, result);
        });
        it('should successfully return the security headers for csg test', async () => {
            const environment = environments.csg.test;
            const request = {
                headers: {
                    host: [{
                        value: environment.webFrontend,
                    }],
                },
            };
            const response = {
                headers: {},
            };
            const config = lambdaConfig({
                lambdaPath: `index.js`,
                request,
                response,
            });
            const result = await runLambda(config);

            checkLambdaResult(environment, result);
        });
        it('should successfully return the security headers for ia prod', async () => {
            const environment = environments.ia.prod;
            const request = {
                headers: {
                    host: [{
                        value: environment.webFrontend,
                    }],
                },
            };
            const response = {
                headers: {},
            };
            const config = lambdaConfig({
                lambdaPath: `index.js`,
                request,
                response,
            });
            const result = await runLambda(config);

            checkLambdaResult(environment, result);
        });
        it('should successfully return the security headers for ia test', async () => {
            const environment = environments.ia.test;
            const request = {
                headers: {
                    host: [{
                        value: environment.webFrontend,
                    }],
                },
            };
            const response = {
                headers: {},
            };
            const config = lambdaConfig({
                lambdaPath: `index.js`,
                request,
                response,
            });
            const result = await runLambda(config);

            checkLambdaResult(environment, result);
        });
        it('should successfully return the security headers for ia justin', async () => {
            const environment = environments.ia.justin;
            const request = {
                headers: {
                    host: [{
                        value: environment.webFrontend,
                    }],
                },
            };
            const response = {
                headers: {},
            };
            const config = lambdaConfig({
                lambdaPath: `index.js`,
                request,
                response,
            });
            const result = await runLambda(config);

            checkLambdaResult(environment, result);
        });
        it('should successfully return the security headers for csg prod when subdomain is missing', async () => {
            const environment = environments.csg.prod;
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
                lambdaPath: `index.js`,
                request,
                response,
            });
            const result = await runLambda(config);

            checkLambdaResult(environment, result);
        });
        it('should successfully return the security headers for csg prod when lambda event is missing the request domain', async () => {
            const environment = environments.csg.prod;
            const request = {
                origin: {},
            };
            const response = {
                headers: {},
            };
            const config = lambdaConfig({
                lambdaPath: `index.js`,
                request,
                response,
            });
            const result = await runLambda(config);

            checkLambdaResult(environment, result);
        });
    });
});
