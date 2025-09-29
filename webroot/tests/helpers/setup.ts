//
//  setup.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

/* eslint-disable import/no-extraneous-dependencies */
import { mount, shallowMount, config as vueTestConfig } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import routes from '@router/routes';
import { DataApi } from '@network/mocks/mock.data.api';
import mockStore from '@tests/mocks/mockStore';
import mockEnvConfig from '@tests/mocks/mockEnvConfig';
import { getStatsigClientMock } from '@plugins/Statsig/statsig.plugin';
import { relativeTimeFormats } from '@/app.config';
import { VueResponsiveness } from 'vue-responsiveness';
import i18n from '@/i18n';
import moment from 'moment';
import momentTz from 'moment-timezone';
import sinon from 'sinon';
import { VirtualConsole } from 'jsdom';

// Stabilize browser language default for tests
try {
    Object.defineProperty(window.navigator, 'language', { value: 'en-US', configurable: true });
} catch (err) {
    // ignore if not configurable in this environment
}

// Ensure transitions are stubbed in tests and avoid transition timing issues
vueTestConfig.global = vueTestConfig.global || {} as any;
vueTestConfig.global.stubs = {
    ...(vueTestConfig.global.stubs || {}),
    transition: true,
    'transition-group': true,
};

// Polyfill requestAnimationFrame() for tests
const requestAnimationFrameStub = (cb: FrameRequestCallback) => setTimeout(() => cb(0), 0) as unknown as number;
const cancelAnimationFrameStub = (id: number) => clearTimeout(id as unknown as NodeJS.Timeout);

(window as any).requestAnimationFrame = requestAnimationFrameStub;
(window as any).cancelAnimationFrame = cancelAnimationFrameStub;
(global as any).requestAnimationFrame = requestAnimationFrameStub;
(global as any).cancelAnimationFrame = cancelAnimationFrameStub;

// Polyfill matchMedia() for tests
window.matchMedia = sinon.stub().callsFake((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: sinon.spy(),
    removeListener: sinon.spy(),
    addEventListener: sinon.spy(),
    removeEventListener: sinon.spy(),
    dispatchEvent: sinon.spy(),
}));

// Silence JSDOM bug of not implementing navigation but also not supporting config or suppression
// https://github.com/jsdom/jsdom/issues/2112#issuecomment-673540137
declare global {
    interface Window {
        _virtualConsole: VirtualConsole;
    }
}
const listeners = window._virtualConsole.listeners('jsdomError'); // eslint-disable-line no-underscore-dangle
const originalListener = listeners && listeners[0];

window._virtualConsole.removeAllListeners('jsdomError'); // eslint-disable-line no-underscore-dangle
window._virtualConsole.addListener('jsdomError', (error) => { // eslint-disable-line no-underscore-dangle
    if (
        error.type !== 'not implemented'
        && error.message !== 'Not implemented: navigation (except hash changes)'
        && originalListener
    ) {
        originalListener(error);
    }
});

// Update moment relative-time formats to match app
const setMomentRelativeFormats = () => {
    moment.updateLocale('en', { relativeTime: relativeTimeFormats });
    momentTz.updateLocale('en', { relativeTime: relativeTimeFormats });
};

/**
 * Fail individual test if console error includes a given string in a watch list.
 * @param errorContent List of strings to look for in console errors
 *
 * Source: https://medium.com/@chris.washington_60485/vue-jest-properly-catch-unhandledpromiserejectionwarning-and-vue-warn-errors-in-jest-unit-tests-fcc45269146b
 */
const failTestOn = (errorWatchList: Array<string>) => {
    const { error } = console;

    console.error = (...args) => {
        for (let i = 0; i < args.length; i += 1) {
            const arg = args[i];

            if (typeof arg === 'string') {
                const foundErrorContent = errorWatchList.some((content) => arg.includes(content));

                if (foundErrorContent) {
                    args.forEach((a) => {
                        if (errorWatchList.some((content) => a.includes(content))) {
                            // Ensure desired test warnings/errors are displayed to the developer, even
                            // if Vue Test Utils `config.errorHandler` throws its own error.
                            console.warn('\n', a);
                        }
                    });
                    throw new Error(String(args));
                }
            }
        }
        error(...args);
    };
};

//
// Mocha setup / teardown methods
//
beforeEach(() => {
    const { tm: $tm, t: $t } = i18n.global;

    // Force English locale for every test
    (i18n.global as any).locale = 'en';
    (i18n.global as any).fallbackLocale = 'en';

    // Force global setup since main.ts works differently for tests
    (window as any).Vue = {
        config: {
            globalProperties: {
                $tm,
                $t,
            }
        }
    };
    setMomentRelativeFormats();

    // Reset the the scrollTo() polyfill
    window.scrollTo = () => { /* empty */ };

    // Ensure tests fail on what would otherwise just be vue-test-utils console output
    failTestOn(['Vue warn', 'unhandledRejection']);
});

// Trap when Mocha stumbles on promises
(process as any).on('unhandledRejection', (err) => {
    if (err) {
        console.error('unhandledRejection', err.stack);
    }
});

// Create stub instance of mock API
const mockApi = sinon.createStubInstance(DataApi);

/**
 * Shallow-mount a component with mocks.
 * @param  {Component} component        The Vue component.
 * @param  {Object}    [mountConfig={}] Addiitonal mount config options.
 * @return {Promise}                    The Vue Test Wrapper.
 */
const mountShallow = async (component, mountConfig: any = {}) => {
    const router = createRouter({ routes, history: createWebHistory() });
    const store = mockStore;
    const statsigClientMock = await getStatsigClientMock();
    const config: any = {
        global: {
            plugins: [
                router,
                store,
                [VueResponsiveness, {
                    phone: 0,
                    tablet: 770,
                    desktop: 1024,
                    largeDesktop: 1600,
                    xLargeDesktop: 2400,
                }],
                i18n,
            ],
            mocks: {
                $envConfig: mockEnvConfig,
                // $auth: TODO,
                $api: mockApi,
                $t: sinon.spy(() => ''),
                $i18n: { locale: 'en' },
                $features: statsigClientMock,
                $analytics: statsigClientMock,
            },
            stubs: {
                transition: true,
                'transition-group': true,
            },
        },
    };

    if (mountConfig?.props) {
        config.props = mountConfig.props;
    }

    if (mountConfig?.computed) {
        config.computed = mountConfig.computed;
    }

    // await router.isReady();

    return shallowMount(component, config);
};

/**
 * Full-mount a component with mocks.
 * @param  {Component} component        The Vue component.
 * @param  {Object}    [mountConfig={}] Addiitonal mount config options.
 * @return {Promise}                    The Vue Test Wrapper.
 */
const mountFull = async (component, mountConfig: any = {}) => {
    const router = createRouter({ routes, history: createWebHistory() });
    const store = mockStore;
    const statsigClientMock = await getStatsigClientMock();
    const config: any = {
        global: {
            plugins: [
                router,
                store,
                [VueResponsiveness, {
                    phone: 0,
                    tablet: 770,
                    desktop: 1024,
                    largeDesktop: 1600,
                    xLargeDesktop: 2400,
                }],
                i18n,
            ],
            mocks: {
                $envConfig: mockEnvConfig,
                // $auth: TODO,
                $api: mockApi,
                $t: sinon.spy(() => ''),
                $i18n: { locale: 'en' },
                $features: statsigClientMock,
                $analytics: statsigClientMock,
            },
            stubs: {
                transition: true,
                'transition-group': true,
            },
        },
    };

    if (mountConfig?.props) {
        config.props = mountConfig.props;
    }

    if (mountConfig?.computed) {
        config.computed = mountConfig.computed;
    }

    // await router.isReady();

    return mount(component, config);
};

export {
    setMomentRelativeFormats,
    mountShallow,
    mountFull,
};
