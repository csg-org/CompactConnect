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
            s3Upload: ``,
        },
        test: {
            webFrontend: `app.test.compactconnect.org`,
            dataApi: `api.test.compactconnect.org`,
            s3Upload: ``,
        },
    },
    ia: {
        prod: {
            webFrontend: `app.jcc.iaapi.io`,
            dataApi: `api.jcc.iaapi.io`,
            s3Upload: ``,
        },
        test: {
            webFrontend: `app.dev.jcc.iaapi.io`,
            dataApi: `api.dev.jcc.iaapi.io`,
            s3Upload: `test-persistentstack-mockbulkuploadsbucket0e8f27eb-4h1anohxetmp.s3.amazonaws.com`,
        },
    },
};
const buildCspHeaders = (environment) => {
    const dataApiUrl = (environment?.dataApi) ? `https://${environment.dataApi}` : '';
    const s3Url = (environment?.s3Upload) ? `https://${environment.s3Upload}` : '';
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
        '\'unsafe-inline\'', // Some of our inline SVGs have inline style
        'https://fonts.googleapis.com',
    ].join(' ');
    const cspStyleSrcElem = [
        '\'self\'',
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
        'https://cognito-idp.us-east-1.amazonaws.com'
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

// ================================================================================================
// =                                        TESTS                                                 =
// ================================================================================================
describe(testFilename(__filename), () => {
    describe('Cloudfront security headers', () => {
        it('should successfully return the security headers for ia test', async () => {
            const environment = environments.ia.test;
            const request = {
                origin: {
                    custom: {
                        domainName: environment.webFrontend,
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

            // console.log(JSON.stringify(result, null, 2)); // @DEBUG

            expect(result.headers['strict-transport-security'][0].key).to.equal('Strict-Transport-Security');
            expect(result.headers['strict-transport-security'][0].value).to.equal('max-age=31536000; includeSubdomains; preload');
            expect(result.headers['x-content-type-options'][0].key).to.equal('X-Content-Type-Options');
            expect(result.headers['x-content-type-options'][0].value).to.equal('nosniff');
            expect(result.headers['x-frame-options'][0].key).to.equal('X-Frame-Options');
            expect(result.headers['x-frame-options'][0].value).to.equal('DENY');
            expect(result.headers['x-xss-protection'][0].key).to.equal('X-Xss-Protection');
            expect(result.headers['x-xss-protection'][0].value).to.equal('1; mode=block');
            expect(result.headers['referrer-policy'][0].key).to.equal('Referrer-Policy');
            expect(result.headers['referrer-policy'][0].value).to.equal('strict-origin-when-cross-origin');
            expect(result.headers['content-security-policy'][0].key).to.equal('Content-Security-Policy');
            expect(result.headers['content-security-policy'][0].value).to.equal(buildCspHeaders(environment));
        });
        it('should successfully return the security headers for ia prod', async () => {
            const environment = environments.ia.prod;
            const request = {
                origin: {
                    custom: {
                        domainName: environment.webFrontend,
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

            // console.log(JSON.stringify(result, null, 2)); // @DEBUG

            expect(result.headers['strict-transport-security'][0].key).to.equal('Strict-Transport-Security');
            expect(result.headers['strict-transport-security'][0].value).to.equal('max-age=31536000; includeSubdomains; preload');
            expect(result.headers['x-content-type-options'][0].key).to.equal('X-Content-Type-Options');
            expect(result.headers['x-content-type-options'][0].value).to.equal('nosniff');
            expect(result.headers['x-frame-options'][0].key).to.equal('X-Frame-Options');
            expect(result.headers['x-frame-options'][0].value).to.equal('DENY');
            expect(result.headers['x-xss-protection'][0].key).to.equal('X-Xss-Protection');
            expect(result.headers['x-xss-protection'][0].value).to.equal('1; mode=block');
            expect(result.headers['referrer-policy'][0].key).to.equal('Referrer-Policy');
            expect(result.headers['referrer-policy'][0].value).to.equal('strict-origin-when-cross-origin');
            expect(result.headers['content-security-policy'][0].key).to.equal('Content-Security-Policy');
            expect(result.headers['content-security-policy'][0].value).to.equal(buildCspHeaders(environment));
        });
        it('should successfully return the security headers for csg test', async () => {
            const environment = environments.csg.test;
            const request = {
                origin: {
                    custom: {
                        domainName: environment.webFrontend,
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

            // console.log(JSON.stringify(result, null, 2)); // @DEBUG

            expect(result.headers['strict-transport-security'][0].key).to.equal('Strict-Transport-Security');
            expect(result.headers['strict-transport-security'][0].value).to.equal('max-age=31536000; includeSubdomains; preload');
            expect(result.headers['x-content-type-options'][0].key).to.equal('X-Content-Type-Options');
            expect(result.headers['x-content-type-options'][0].value).to.equal('nosniff');
            expect(result.headers['x-frame-options'][0].key).to.equal('X-Frame-Options');
            expect(result.headers['x-frame-options'][0].value).to.equal('DENY');
            expect(result.headers['x-xss-protection'][0].key).to.equal('X-Xss-Protection');
            expect(result.headers['x-xss-protection'][0].value).to.equal('1; mode=block');
            expect(result.headers['referrer-policy'][0].key).to.equal('Referrer-Policy');
            expect(result.headers['referrer-policy'][0].value).to.equal('strict-origin-when-cross-origin');
            expect(result.headers['content-security-policy'][0].key).to.equal('Content-Security-Policy');
            expect(result.headers['content-security-policy'][0].value).to.equal(buildCspHeaders(environment));
        });
        it('should successfully return the security headers for csg prod', async () => {
            const environment = environments.csg.prod;
            const request = {
                origin: {
                    custom: {
                        domainName: environment.webFrontend,
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

            // console.log(JSON.stringify(result, null, 2)); // @DEBUG

            expect(result.headers['strict-transport-security'][0].key).to.equal('Strict-Transport-Security');
            expect(result.headers['strict-transport-security'][0].value).to.equal('max-age=31536000; includeSubdomains; preload');
            expect(result.headers['x-content-type-options'][0].key).to.equal('X-Content-Type-Options');
            expect(result.headers['x-content-type-options'][0].value).to.equal('nosniff');
            expect(result.headers['x-frame-options'][0].key).to.equal('X-Frame-Options');
            expect(result.headers['x-frame-options'][0].value).to.equal('DENY');
            expect(result.headers['x-xss-protection'][0].key).to.equal('X-Xss-Protection');
            expect(result.headers['x-xss-protection'][0].value).to.equal('1; mode=block');
            expect(result.headers['referrer-policy'][0].key).to.equal('Referrer-Policy');
            expect(result.headers['referrer-policy'][0].value).to.equal('strict-origin-when-cross-origin');
            expect(result.headers['content-security-policy'][0].key).to.equal('Content-Security-Policy');
            expect(result.headers['content-security-policy'][0].value).to.equal(buildCspHeaders(environment));
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

            // console.log(JSON.stringify(result, null, 2)); // @DEBUG

            expect(result.headers['strict-transport-security'][0].key).to.equal('Strict-Transport-Security');
            expect(result.headers['strict-transport-security'][0].value).to.equal('max-age=31536000; includeSubdomains; preload');
            expect(result.headers['x-content-type-options'][0].key).to.equal('X-Content-Type-Options');
            expect(result.headers['x-content-type-options'][0].value).to.equal('nosniff');
            expect(result.headers['x-frame-options'][0].key).to.equal('X-Frame-Options');
            expect(result.headers['x-frame-options'][0].value).to.equal('DENY');
            expect(result.headers['x-xss-protection'][0].key).to.equal('X-Xss-Protection');
            expect(result.headers['x-xss-protection'][0].value).to.equal('1; mode=block');
            expect(result.headers['referrer-policy'][0].key).to.equal('Referrer-Policy');
            expect(result.headers['referrer-policy'][0].value).to.equal('strict-origin-when-cross-origin');
            expect(result.headers['content-security-policy'][0].key).to.equal('Content-Security-Policy');
            expect(result.headers['content-security-policy'][0].value).to.equal(buildCspHeaders(environment));
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

            // console.log(JSON.stringify(result, null, 2)); // @DEBUG

            expect(result.headers['strict-transport-security'][0].key).to.equal('Strict-Transport-Security');
            expect(result.headers['strict-transport-security'][0].value).to.equal('max-age=31536000; includeSubdomains; preload');
            expect(result.headers['x-content-type-options'][0].key).to.equal('X-Content-Type-Options');
            expect(result.headers['x-content-type-options'][0].value).to.equal('nosniff');
            expect(result.headers['x-frame-options'][0].key).to.equal('X-Frame-Options');
            expect(result.headers['x-frame-options'][0].value).to.equal('DENY');
            expect(result.headers['x-xss-protection'][0].key).to.equal('X-Xss-Protection');
            expect(result.headers['x-xss-protection'][0].value).to.equal('1; mode=block');
            expect(result.headers['referrer-policy'][0].key).to.equal('Referrer-Policy');
            expect(result.headers['referrer-policy'][0].value).to.equal('strict-origin-when-cross-origin');
            expect(result.headers['content-security-policy'][0].key).to.equal('Content-Security-Policy');
            expect(result.headers['content-security-policy'][0].value).to.equal(buildCspHeaders(environment));
        });
    });
});
