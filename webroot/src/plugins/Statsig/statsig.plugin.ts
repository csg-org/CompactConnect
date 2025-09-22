//
//  statsig.plugin.ts
//  CompactConnect
//
//  Created by InspiringApps on 9/17/2025.
//

/* eslint-disable import/no-extraneous-dependencies */

import { config as envConfig, appEnvironments } from '@plugins/EnvConfig/envConfig.plugin';
import { StatsigClient } from '@statsig/js-client';
import { StatsigSessionReplayPlugin } from '@statsig/session-replay';
import { StatsigAutoCapturePlugin } from '@statsig/web-analytics';

const STATSIG_PRODUCTION = 'production';
const STATSIG_STAGING = 'staging';
const STATSIG_DEVELOPMENT = 'development';

export const getStatsigEnvironment = () => {
    let statsigEnvironment = '';

    switch (envConfig.appEnv) {
    case appEnvironments.APP_PRODUCTION:
        statsigEnvironment = STATSIG_PRODUCTION;
        break;
    case appEnvironments.APP_BETA:
        statsigEnvironment = STATSIG_STAGING;
        break;
    case appEnvironments.APP_TEST_IA:
    case appEnvironments.APP_TEST_CSG:
    case appEnvironments.APP_LOCAL:
        statsigEnvironment = STATSIG_DEVELOPMENT;
        break;
    default:
        statsigEnvironment = STATSIG_PRODUCTION;
        break;
    }

    return statsigEnvironment;
};

export const getStatsigClient = async () => {
    const { isAppProduction, isAppBeta, isAppTest } = envConfig;
    const statsigEnvironment = getStatsigEnvironment();
    const plugins: any = [];

    // Setup Statsig analytics
    if (isAppProduction || isAppBeta || isAppTest) {
        plugins.push(new StatsigAutoCapturePlugin());
    }

    // Setup Statsig session replay
    if (isAppProduction || isAppBeta || isAppTest) {
        plugins.push(new StatsigSessionReplayPlugin());
    }

    // Create and initialize the Statsig client
    const statsigClient = new StatsigClient(
        envConfig.statsigKey || '',
        {},
        {
            environment: { tier: statsigEnvironment },
            plugins,
        }
    );

    await statsigClient.initializeAsync();

    return statsigClient;
};

export const getStatsigClientMock = async () => ({
    checkGate: (gateId = '') => {
        const disabledGates = ['disabled-gate-1'];

        return !disabledGates.includes(gateId);
    },
});

export const initStatsig = async () => {
    const { isTest, isUsingMockApi } = envConfig;
    const statsigClient = (isTest || isUsingMockApi) ? getStatsigClientMock() : await getStatsigClient();

    return statsigClient;
};

export default {
    install: (app, { statsigClient }) => {
        app.config.globalProperties.$features = statsigClient;
        app.config.globalProperties.$analytics = statsigClient;
    },
};
