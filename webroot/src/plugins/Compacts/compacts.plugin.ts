//
//  compacts.plugin.ts
//  CompactConnect
//
//  Created by InspiringApps on 8/17/2026.
//

// https://vuejs.org/v2/guide/plugins.html

import { AppModes } from '@/app.config';
import {
    CompactType,
    CompactSetup,
    compactSetups
} from '@utils/compactConfig';
import { computed } from 'vue';
import i18n from '@/i18n';
import store from '@/store';

export interface CompactConfig {
    type: CompactType;
    appMode: AppModes;
    isEnabled: boolean;
    name: string;
    abbrev: string;
}

interface CompactTranslation {
    key?: string;
    name?: string;
    abbrev?: string;
}

//
// Merge the compacts configs (app.config) with the locale translation strings to get a full list of compacts.
//
export const compactConfigs = computed<Array<CompactConfig>>(() => {
    const translations = (i18n.global.tm('compacts') || []) as Array<CompactTranslation>;

    return Object.values(compactSetups).map((setup: CompactSetup) => {
        const translation = translations.find((compactTranslation) => compactTranslation.key === setup.type);

        return {
            type: setup.type,
            appMode: setup.appMode,
            isEnabled: setup.isEnabled(),
            name: translation?.name || '',
            abbrev: translation?.abbrev || '',
        };
    });
});

export const enabledCompactConfigs = computed<Array<CompactConfig>>(() =>
    compactConfigs.value.filter((compactConfig) => compactConfig.isEnabled));

export const getCompactConfig = (compactType?: CompactType | string | null): CompactConfig | null =>
    compactConfigs.value.find((compactConfig) => compactConfig.type === compactType) || null;

// Global flags that mirror the same-named global store getters
export const appModeFlags = [
    'isAppModeJcc',
    'isAppModeCosmetology',
    'isAppModeSocialWork',
    'isAppGroupModePrivilegePurchase',
    'isAppGroupModeMultiState',
] as const;

export type AppModeFlag = typeof appModeFlags[number];

//
// Installed each property as an accessor to maintain reactivity.
//
const defineGlobal = (app, key: string, get: () => any): void => {
    Object.defineProperty(app.config.globalProperties, key, {
        get,
        enumerable: true,
        configurable: true,
    });
};

export default {
    install: (app) => {
        defineGlobal(app, '$compactsAll', () => compactConfigs.value);
        defineGlobal(app, '$compactsEnabled', () => enabledCompactConfigs.value);
        defineGlobal(app, '$appMode', () => store.state.appMode);
        defineGlobal(app, '$appGroupMode', () => store.state.appGroupMode);

        appModeFlags.forEach((appModeFlag) => {
            defineGlobal(app, `$${appModeFlag}`, () => store.getters[appModeFlag]);
        });
    },
};
