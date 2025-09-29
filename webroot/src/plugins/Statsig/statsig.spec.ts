//
//  statsig.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 9/29/2025.
//

import chaiMatchPattern from 'chai-match-pattern';
import chai from 'chai';
import { config as envConfig, appEnvironments } from '@plugins/EnvConfig/envConfig.plugin';
import statsigPlugin, {
    STATSIG_PRODUCTION,
    STATSIG_STAGING,
    STATSIG_DEVELOPMENT,
    getStatsigEnvironment,
    getStatsigClientMock,
    getStatsigClient,
    initStatsig
} from '@plugins/Statsig/statsig.plugin';
import { StatsigSessionReplayPlugin } from '@statsig/session-replay';
import { StatsigAutoCapturePlugin } from '@statsig/web-analytics';

chai.use(chaiMatchPattern);

const { expect } = chai;
const origAppEnv = envConfig.appEnv;

describe('Statsig plugin', async () => {
    afterEach(() => {
        envConfig.appEnv = origAppEnv;
        envConfig.isProduction = false;
        envConfig.isTest = true;
        envConfig.isDevelopment = false;
        envConfig.isAppProduction = false;
        envConfig.isAppBeta = false;
        envConfig.isAppTest = false;
        envConfig.isAppTestCsg = false;
        envConfig.isAppTestIa = false;
        envConfig.isUsingMockApi = true;
    });
    it('should get statsig environment for app production environment', async () => {
        envConfig.appEnv = appEnvironments.APP_PRODUCTION;
        const statsigEnvironment = getStatsigEnvironment();

        expect(statsigEnvironment).to.equal(STATSIG_PRODUCTION);
    });
    it('should get statsig environment for app unknown environment', async () => {
        envConfig.appEnv = '';
        const statsigEnvironment = getStatsigEnvironment();

        expect(statsigEnvironment).to.equal(STATSIG_PRODUCTION);
    });
    it('should get statsig environment for app beta environment', async () => {
        envConfig.appEnv = appEnvironments.APP_BETA;
        const statsigEnvironment = getStatsigEnvironment();

        expect(statsigEnvironment).to.equal(STATSIG_STAGING);
    });
    it('should get statsig environment for app csg-test environment', async () => {
        envConfig.appEnv = appEnvironments.APP_TEST_CSG;
        const statsigEnvironment = getStatsigEnvironment();

        expect(statsigEnvironment).to.equal(STATSIG_DEVELOPMENT);
    });
    it('should get statsig environment for app ia-test environment', async () => {
        envConfig.appEnv = appEnvironments.APP_TEST_IA;
        const statsigEnvironment = getStatsigEnvironment();

        expect(statsigEnvironment).to.equal(STATSIG_DEVELOPMENT);
    });
    it('should get statsig environment for app local environment', async () => {
        envConfig.appEnv = appEnvironments.APP_LOCAL;
        const statsigEnvironment = getStatsigEnvironment();

        expect(statsigEnvironment).to.equal(STATSIG_DEVELOPMENT);
    });
    it('should get statsig client mock for live environment', async () => {
        const statsigClientMock = await getStatsigClientMock(true);
        const initializeResponse = await statsigClientMock.initializeAsync();
        const updateUserResponse = await statsigClientMock.updateUserAsync(null);
        const checkGateResponse1 = statsigClientMock.checkGate();
        const checkGateResponse2 = statsigClientMock.checkGate('disabled-gate-1');

        expect(initializeResponse).to.equal(null);
        expect(updateUserResponse).to.equal(null);
        expect(checkGateResponse1).to.equal(false);
        expect(checkGateResponse2).to.equal(false);
    });
    it('should get statsig client mock for non-live environment', async () => {
        const statsigClientMock = await getStatsigClientMock();
        const initializeResponse = await statsigClientMock.initializeAsync();
        const updateUserResponse = await statsigClientMock.updateUserAsync(null);
        const checkGateResponse1 = statsigClientMock.checkGate();
        const checkGateResponse2 = statsigClientMock.checkGate('disabled-gate-1');

        expect(initializeResponse).to.equal(null);
        expect(updateUserResponse).to.equal(null);
        expect(checkGateResponse1).to.equal(true);
        expect(checkGateResponse2).to.equal(false);
    });
    it('should get statsig client with expected plugins (test runner)', async () => {
        const { _options: statsigOptions } = await getStatsigClient();

        expect(statsigOptions.plugins).to.matchPattern([]);
    });
    it('should get statsig client with expected plugins (app production)', async () => {
        envConfig.isAppProduction = true;

        const { _options: statsigOptions } = await getStatsigClient();

        expect(statsigOptions.plugins).to.matchPattern([new StatsigAutoCapturePlugin()]);
    });
    it('should get statsig client with expected plugins (app beta)', async () => {
        envConfig.isAppBeta = true;

        const { _options: statsigOptions } = await getStatsigClient();

        expect(statsigOptions.plugins).to.matchPattern([new StatsigSessionReplayPlugin()]);
    });
    it('should get statsig client with expected plugins (app test)', async () => {
        envConfig.isAppTest = true;

        const { _options: statsigOptions } = await getStatsigClient();

        expect(statsigOptions.plugins).to.matchPattern([new StatsigSessionReplayPlugin()]);
    });
    it('should init statsig client', async () => {
        const statsigClient = await initStatsig();
        const statsigClientMock = await getStatsigClientMock();

        expect(statsigClient).to.matchPattern(statsigClientMock);
    });
    it('should have default export as plugin installer', async () => {
        const app = {
            config: {
                globalProperties: {},
            }
        };
        const statsigClientMock = await getStatsigClientMock();

        statsigPlugin.install(app, { statsigClient: statsigClientMock });

        expect(app.config.globalProperties.$features).to.matchPattern(statsigClientMock);
        expect(app.config.globalProperties.$analytics).to.matchPattern(statsigClientMock);
    });
    it('should reset app env after test suite', async () => {
        expect(envConfig.appEnv).to.equal(origAppEnv);
        expect(envConfig.isProduction).to.equal(false);
        expect(envConfig.isTest).to.equal(true);
        expect(envConfig.isDevelopment).to.equal(false);
        expect(envConfig.isAppProduction).to.equal(false);
        expect(envConfig.isAppBeta).to.equal(false);
        expect(envConfig.isAppTest).to.equal(false);
        expect(envConfig.isAppTestCsg).to.equal(false);
        expect(envConfig.isAppTestIa).to.equal(false);
        expect(envConfig.isUsingMockApi).to.equal(true);
    });
});
