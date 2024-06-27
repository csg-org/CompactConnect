import { createI18n } from 'vue-i18n';
import en from '@locales/en.json';
import es from '@locales/es.json';
import { defaultLanguage } from '@/app.config';

const i18n = createI18n({
    locale: defaultLanguage,
    fallbackLocale: defaultLanguage,
    messages: {
        en,
        es,
    },
});

export default i18n;
