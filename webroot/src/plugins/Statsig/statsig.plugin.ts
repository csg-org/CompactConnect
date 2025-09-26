//
//  statsig.plugin.ts
//  CompactConnect
//
//  Created by InspiringApps on 9/17/2025.
//

/* eslint-disable import/no-extraneous-dependencies */

import { config as envConfig, appEnvironments } from '@plugins/EnvConfig/envConfig.plugin';
import { StatsigClient, StatsigPlugin } from '@statsig/js-client';
import { StatsigSessionReplayPlugin } from '@statsig/session-replay';
import { StatsigAutoCapturePlugin } from '@statsig/web-analytics';
import moment from 'moment';

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

type StatsigClientMock = {
    updateUserAsync: (user: any) => Promise<any>;
    checkGate: (gateId?: string) => boolean;
}

export const getStatsigClientMock = async (isLiveFallback = false) => ({
    updateUserAsync: async (user) => user,
    checkGate: (gateId = '') => {
        const disabledGates = ['disabled-gate-1'];
        const isEnabled = (isLiveFallback) ? false : !disabledGates.includes(gateId);

        return isEnabled;
    },
});

export const getStatsigClient = async () => {
    const { isAppProduction, isAppBeta, isAppTest } = envConfig;
    const statsigEnvironment = getStatsigEnvironment();
    const plugins: Array<StatsigPlugin<StatsigClient>> = [];

    // Setup Statsig analytics
    if (isAppProduction || isAppBeta || isAppTest) {
        plugins.push(new StatsigAutoCapturePlugin());
    }

    // Setup Statsig session replay
    if (isAppProduction || isAppBeta || isAppTest) {
        plugins.push(new StatsigSessionReplayPlugin());
    }

    // Create and initialize the Statsig client
    let statsigClient: StatsigClient | StatsigClientMock = new StatsigClient(
        envConfig.statsigKey || '',
        {},
        {
            environment: { tier: statsigEnvironment },
            plugins,
        }
    );

    try {
        await statsigClient.initializeAsync();
    } catch (err) {
        console.warn(`[Statsig] Failed to initialize. Falling back to mock with disabled flags.`);
        console.error(err);
        statsigClient = await getStatsigClientMock(true);
    }

    return statsigClient;
};

export const initStatsig = async () => {
    const liveEnvironmentMaxWaitMs = moment.duration(2, 'seconds').asMilliseconds();
    const { isTest, isUsingMockApi } = envConfig;
    const isLiveEnvironment = !(isTest || isUsingMockApi);
    const mockStatsigClient = await getStatsigClientMock(isLiveEnvironment);
    // Don't allow Statsig remote failures to block app loading - only wait for a set amount of time before just using a mock
    const statsigClient = await Promise.race([
        (isLiveEnvironment) ? getStatsigClient() : mockStatsigClient,
        new Promise((resolve) => setTimeout(() => resolve(mockStatsigClient), liveEnvironmentMaxWaitMs)),
    ]);

    return statsigClient;
};

export default {
    install: (app, { statsigClient }) => {
        app.config.globalProperties.$features = statsigClient;
        app.config.globalProperties.$analytics = statsigClient;
    },
};
