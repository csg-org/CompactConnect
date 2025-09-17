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

export const initStatsig = async () => {
    const statsigEnvironment = getStatsigEnvironment();
    const statsigClient = new StatsigClient(
        envConfig.statsigKey || '',
        {},
        {
            environment: { tier: statsigEnvironment },
            plugins: [
                new StatsigSessionReplayPlugin(),
                new StatsigAutoCapturePlugin(),
            ],
        }
    );

    await statsigClient.initializeAsync();

    return statsigClient;
};

export default {
    install: (app, { statsigClient }) => {
        app.config.globalProperties.$features = statsigClient;
        app.config.globalProperties.$analytics = statsigClient;
    },
};
