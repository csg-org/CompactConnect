//
//  main.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/27/21.
//

import { createApp } from 'vue';
import envConfig from '@plugins/EnvConfig/envConfig.plugin';
import router from '@router/index';
import store from '@store/index';
import api from '@plugins/API/api.plugin';
import network from '@network/index';
import vClickOutside from 'click-outside-vue3';
import VueLazyload from 'vue3-lazyload';
import { VueResponsiveness } from 'vue-responsiveness';
import i18n from './i18n';
import App from './components/App/App.vue';
import './registerServiceWorker';

//
// INITIALIZE APP
//
const app = createApp(App);

// Enable vue-devtools. Can make environment-specific if needed.
app.config.performance = true;

// Inject store into API interceptors (avoids circular dependency)
network.dataApi.initInterceptors(store);

//
// INJECT PLUGINS
//
app.use(envConfig);
app.use(router);
app.use(store);
app.use(i18n);
app.use(api);
app.use(vClickOutside);
app.use(VueResponsiveness, {
    phone: 0,
    tablet: 770,
    desktop: 1024,
    largeDesktop: 1600,
    xLargeDesktop: 2400,
});

app.use(VueLazyload, {
    // https://github.com/murongg/vue3-lazyload
    observerOptions: {
        rootMargin: '0px',
        threshold: 0.1,
    },
    error: '/img/static/img-load-error.svg',
    // loading: 'dist/loading.gif',
    lifecycle: {
        loaded: (el) => {
            // Add ratio (wide / tall) class to image element
            const imgEl = el || document.createElement('img');
            const img = new Image();

            img.onload = () => {
                const { width, height } = img;

                if (width / height > 1) {
                    imgEl.classList.remove('tall');
                    imgEl.classList.add('wide');
                } else {
                    imgEl.classList.remove('wide');
                    imgEl.classList.add('tall');
                }
            };

            // img.src = src;
        },
    },
});

//
// ALLOW ACCESS TO VUE INSTANCE SERVICES
//
// Attach any services that aren't automatically attached to the Vue instance
const { globalProperties } = app.config;
const { t: $t, tm: $tm } = i18n.global;

if (!globalProperties.$t) {
    (globalProperties as any).$t = $t;
}

if (!globalProperties.$tm) {
    (globalProperties as any).$tm = $tm;
}

// Make Vue available globally
(window as any).Vue = app || {};

//
// MOUNT
//
app.mount('#jcc-app');

//
// E2E TESTS INJECTION
//
if ((window as any).Cypress) {
    (window as any).app = app;
}
