//
//  vue.config.js
//  InspiringApps modules
//
//  Created by InspiringApps on 04/27/2021.
//

//
// @NOTE: From the terminal, run `vue inspect` to output the webpack build config
//

const path = require('path');
const fs = require('fs');
const FaviconsWebpackPlugin = require('favicons-webpack-plugin');
const StyleLintPlugin = require('stylelint-webpack-plugin');

const env = process.env.NODE_ENV;
const ENV_PRODUCTION = 'production';
const ENV_TEST = 'test';
const baseUrl = process.env.BASE_URL;
const localDevPort = process.env.LOCAL_DEV_PORT;
const localDevProxy = {};
const shouldMockApi = (process.env.VUE_APP_MOCK_API === 'true');

const appName = 'TODO';
const appDescription = 'TODO';
const developerName = 'TODO';
const themeColor = '#1C7CB0'; // @TODO
const backgroundColor = '#FFFFFF'; // @TODO

// ============================================================================
// =                          LOCAL PROXY CONFIG                              =
// ============================================================================
// Configure the local dev server proxy rules
// https://webpack.js.org/configuration/dev-server/#devserverproxy
// localDevProxy[process.env.VUE_APP_API_EXAMPLE_ROOT] = { target: process.env.LOCAL_DEV_PROXY_EXAMPLE };
localDevProxy['/img'] = {
    // Proxy images that are created during build that we'd still like to see in the local `yarn serve` app
    // Requires that `yarn build` has been run at least once for the built images to exist in /dist
    target: `http://localhost:${localDevPort}`,
    selfHandleResponse: true,
    bypass: (req, res) => {
        if (req.url.includes('/img')) {
            const proxyImage = `${__dirname}/dist${req.url}`;
            const fileStream = fs.createReadStream(proxyImage);

            fileStream.on('open', () => {
                fileStream.pipe(res);
            });

            fileStream.on('error', (err) => {
                res.status((err.code === 'ENOENT') ? 404 : 500);
                res.send(err);
            });
        }

        return null; // Ignores bypass
    },
};

// ============================================================================
// =                     WEBPACK PLUGIN CUSTOMIZATION                         =
// ============================================================================
/**
 * eslint-webpack-plugin configuration (https://github.com/webpack-contrib/eslint-webpack-plugin)
 * Included with Vue CLI, so we are just chaining
 * @param  {array} args The webpack plugin options array.
 * @return {array}      The webpack plugin options array (updated by reference).
 */
// const eslintPlugin = (args) => {
//     const opts = args[0];
//
//     opts.extensions.push('.json');
//
//     return args;
// };

/**
 * html-webpack-plugin configuration (https://github.com/jantimon/html-webpack-plugin)
 * Included with Vue CLI, so we are just chaining
 * @param  {array} args The webpack plugin options array.
 * @return {array}      The webpack plugin options array (updated by reference).
 */
const htmlPlugin = (args) => {
    const opts = args[0];

    opts.favicon = null;
    opts.inject = true;

    return args;
};

/**
 * extract-css-plugin configuration (https://github.com/webpack/mini-css-extract-plugin)
 * Included with Vue CLI, so we are just chaining
 * @param  {array} args The webpack plugin options array.
 * @return {array}      The webpack plugin options array (updated by reference).
 */
const extractCssPlugin = (args) => {
    const opts = args[0];

    // Suppress CSS order warnings from mini-css-extract-plugin
    // These warnings do not affect functionality and are common in apps that use code splitting / chunking
    opts.ignoreOrder = true;

    return args;
};

/**
 * fork-ts-checker-webpack-plugin (https://github.com/TypeStrong/fork-ts-checker-webpack-plugin)
 * Included with Vue CLI, so we are just chaining
 * @param  {array} args The webpack plugin options array.
 * @return {array}      The webpack plugin options array (updated by reference).
 */
// const forkTsCheckerWebpackPlugin = (args) => {
//     const opts = args[0];
//
//     // opts.memoryLimit = 2048; // 2GB (plugin default)
//     // opts.memoryLimit = 4096; // 4GB
//     opts.memoryLimit = 8192; // 8GB
//
//     return args;
// };
const forkTsCheckerWebpackPlugin = (args) => args;

/**
 * favicons-webpack-plugin configuration (https://github.com/jantimon/favicons-webpack-plugin)
 * @type {FaviconsWebpackPlugin}
 */
const faviconsPlugin = new FaviconsWebpackPlugin({
    logo: './src/assets/logos/compact-connect-logo.png', // Your source logo (required). Plugin automatically creates all app icon assets from this image.
    cache: true, // Note: disabling caching may increase build times considerably
    inject: false, // (`true` requires html-webpack-plugin).
    prefix: 'img/icons/',
    outputPath: './img/icons',
    favicons: { // https://github.com/itgalaxy/favicons#usage
        appName,
        appDescription,
        developerName,
        developerURL: null,
        background: backgroundColor,
        theme_color: themeColor,
        icons: {
            favicons: true,     // Create regular favicons. `boolean` or `{ offset, background, mask, overlayGlow, overlayShadow }`
            android: true,      // Create Android homescreen icon. `boolean` or `{ offset, background, mask, overlayGlow, overlayShadow }`
            appleIcon: true,    // Create Apple touch icons. `boolean` or `{ offset, background, mask, overlayGlow, overlayShadow }`
            appleStartup: true, // Create Apple startup images. `boolean` or `{ offset, background, mask, overlayGlow, overlayShadow }`
            coast: false,       // Create Opera Coast icon. `boolean` or `{ offset, background, mask, overlayGlow, overlayShadow }`
            // firefox: true,      // Create Firefox OS icons. `boolean` or `{ offset, background, mask, overlayGlow, overlayShadow }`
            windows: true,      // Create Windows 8 tile icons. `boolean` or `{ offset, background, mask, overlayGlow, overlayShadow }`
            yandex: false       // Create Yandex browser icon. `boolean` or `{ offset, background, mask, overlayGlow, overlayShadow }`
        }
    }
});

/**
 * stylelint-webpack-plugin configuration (https://github.com/webpack-contrib/stylelint-webpack-plugin)
 * @type {StyleLintPlugin}
 */
const stylelintPlugin = new StyleLintPlugin({
    configFile: '.stylelintrc.json',
    files: 'src/**/*.less',
});

/**
 * Inject common style resources into a module rule.
 * @param {WebpackModuleRule} rule The webpack module rule.
 */
const addStyleResource = (rule) => {
    rule
        .use('style-resource')
        .loader('style-resources-loader')
        .options({
            patterns: [
                path.resolve(__dirname, './src/styles.common/index.less'),
            ],
        });
};

// ============================================================================
// =                             WEBPACK CONFIG                               =
// ============================================================================
module.exports = {
    publicPath: baseUrl || '/',
    lintOnSave: (env !== ENV_PRODUCTION),
    productionSourceMap: false,
    devServer: {
        port: localDevPort || 3000,
        allowedHosts: 'all', // allows local development with proxy domain
        client: {
            overlay: true,
        },
    },
    pwa: {
        // Overlaps w/ faviconsPlugin; setting here in case of ordering conflict
        name: appName,
        themeColor,
        msTileColor: backgroundColor,
        appleMobileWebAppCapable: 'yes',
        appleMobileWebAppStatusBarStyle: 'black-translucent',
        iconPaths: { // Null these out; faviconsPlugin above generates more - /public/index.html hardcodes them
            favicon32: null,
            favicon16: null,
            appleTouchIcon: null,
            maskIcon: null,
            msTileImage: null,
        },
        manifestOptions: {
            background_color: backgroundColor,
            icons: [
                {
                    src: './img/icons/android-chrome-192x192.png',
                    sizes: '192x192',
                    type: 'image/png'
                },
                {
                    src: './img/icons/android-chrome-512x512.png',
                    sizes: '512x512',
                    type: 'image/png'
                },
                // {
                //     src: './img/icons/android-chrome-maskable-192x192.png',
                //     sizes: '192x192',
                //     type: 'image/png',
                //     purpose: 'maskable'
                // },
                // {
                //     src: './img/icons/android-chrome-maskable-512x512.png',
                //     sizes: '512x512',
                //     type: 'image/png',
                //     purpose: 'maskable'
                // },
            ]
        },
        workboxOptions: {
            skipWaiting: true,
        },
    },
    chainWebpack: (config) => {
        // ================================= START: VUE COMPAT ============================================
        // config.resolve.alias.set('vue', '@vue/compat');
        //
        // config.module
        //     .rule('vue')
        //     .use('vue-loader')
        //     .tap((options) => {
        //         const compilerOptions = {
        //             compatConfig: {
        //                 MODE: 2,
        //             },
        //         };
        //
        //         return {
        //             ...options,
        //             compilerOptions
        //         };
        //     });
        // ================================== END: VUE COMPAT =============================================

        // Vue 3 bundle options - explicity setting helps with tree shaking
        // https://vuejs.org/api/compile-time-flags.html#vue-cli
        // https://github.com/vuejs/core/tree/main/packages/vue#bundler-build-feature-flags
        config.plugin('define').tap((definitions) => {
            Object.assign(definitions[0], {
                __VUE_OPTIONS_API__: 'true',
                __VUE_PROD_DEVTOOLS__: 'false',
                __VUE_PROD_HYDRATION_MISMATCH_DETAILS__: 'false'
            });

            return definitions;
        });

        // App entry point config: https://github.com/neutrinojs/webpack-chain#config-entrypoints
        // Remove the standard vue-cli entry point
        config.entryPoints.delete('app');
        // Add our own entry point(s)
        config.entry('app')
            .add('@babel/polyfill')
            .add('./src/polyfills.ts')
            .add('./src/main.ts')
            .end();

        // Update the ESLint plugin settings
        // config.plugin('eslint').tap(eslintPlugin);

        // Disable unwanted (but potential future) plugins
        // config.plugins.delete('pwa');
        // config.plugins.delete('workbox');

        // Update the HTML plugin settings
        config.plugin('html').tap(htmlPlugin);

        // Update the Typescript-Checker plugin settings
        config.plugin('fork-ts-checker').tap(forkTsCheckerWebpackPlugin);

        // Update the CSS-Build plugin settings (only exists for builds)
        if (env === ENV_PRODUCTION) {
            config.plugin('extract-css').tap(extractCssPlugin);
        }

        // Inject common LESS styles into each module
        // https://cli.vuejs.org/guide/css.html#automatic-imports
        const types = ['vue-modules', 'vue', 'normal-modules', 'normal'];

        types.forEach((type) => addStyleResource(config.module.rule('less').oneOf(type)));

        // Replace server API calls with Mock API (if configured)
        if (shouldMockApi || env === ENV_TEST) {
            config.resolve.alias.set('@network/data.api', path.resolve(__dirname, 'src/network/mocks/mock.data.api'));
        }

        // Set build size warnings
        config.performance.maxEntrypointSize(2048000);
        config.performance.maxAssetSize(2048000);
    },
    configureWebpack: {
        plugins: [
            faviconsPlugin,
            stylelintPlugin,
        ],
        resolve: {
            alias: {
                // Alias for ES/TS imports
                '@': path.join(__dirname, '/src'),
                '@assets': path.join(__dirname, '/src/assets'),
                '@components': path.join(__dirname, '/src/components'),
                '@data': path.join(__dirname, '/src/data'),
                '@locales': path.join(__dirname, '/src/locales'),
                '@models': path.join(__dirname, '/src/models'),
                '@network': path.join(__dirname, '/src/network'),
                '@pages': path.join(__dirname, '/src/pages'),
                '@plugins': path.join(__dirname, '/src/plugins'),
                '@router': path.join(__dirname, '/src/router'),
                '@store': path.join(__dirname, '/src/store'),
                '@styles.common': path.join(__dirname, '/src/styles.common/'),
                '@tests': path.join(__dirname, '/tests'),
            },
        },
        devServer: {
            proxy: localDevProxy,
        },
        devtool: (env === ENV_PRODUCTION) ? false : 'eval-cheap-source-map',
    },
};
