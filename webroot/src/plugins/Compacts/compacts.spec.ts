//
//  compacts.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 8/17/2026.
//

import chaiMatchPattern from 'chai-match-pattern';
import chai from 'chai';
import { config as envConfig } from '@plugins/EnvConfig/envConfig.plugin';
import compactsPlugin, {
    compactConfigs,
    enabledCompactConfigs,
    getCompactConfig,
    appModeFlags
} from '@plugins/Compacts/compacts.plugin';
import { AppModes, AppGroupModes } from '@/app.config';
import { CompactType, compactSetups } from '@utils/compactConfig';
import { mountShallow } from '@tests/helpers/setup';
import CompactSelector from '@components/CompactSelector/CompactSelector.vue';
import store from '@store/index';
import i18n from '@/i18n';

chai.use(chaiMatchPattern);

const { expect } = chai;

const buildApp = () => {
    const app = { config: { globalProperties: {} as any }};

    compactsPlugin.install(app);

    return app;
};

describe('Compacts plugin', async () => {
    afterEach(() => {
        envConfig.isAppProduction = false;
        store.dispatch('setAppMode', AppModes.JCC);
        i18n.global.locale.value = 'en';
    });
    it('should successfully include every configured compact', async () => {
        const compactTypes = compactConfigs.value.map((compactConfig) => compactConfig.type);

        expect(compactTypes).to.matchPattern([
            CompactType.ASLP,
            CompactType.OT,
            CompactType.COUNSELING,
            CompactType.COSMETOLOGY,
            CompactType.SOCIAL_WORK,
        ]);
    });
    it('should successfully merge locale display strings into each compact config', async () => {
        const aslp = getCompactConfig(CompactType.ASLP);

        expect(aslp).to.matchPattern({
            type: CompactType.ASLP,
            appMode: AppModes.JCC,
            isEnabled: true,
            name: 'Audiology and Speech Language Pathology',
            abbrev: 'ASLP',
        });
    });
    it('should successfully resolve compact display strings for the active locale', async () => {
        i18n.global.locale.value = 'es';

        expect(getCompactConfig(CompactType.SOCIAL_WORK)?.name).to.equal('Trabajo Social');

        i18n.global.locale.value = 'en';

        expect(getCompactConfig(CompactType.SOCIAL_WORK)?.name).to.equal('Social Work');
    });
    it('should successfully return null for an unknown compact type', async () => {
        expect(getCompactConfig('not-a-compact')).to.equal(null);
        expect(getCompactConfig(null)).to.equal(null);
    });
    it('should successfully enable every compact outside of app production', async () => {
        expect(compactSetups[CompactType.ASLP].isEnabled()).to.equal(true);
        expect(compactSetups[CompactType.OT].isEnabled()).to.equal(true);
        expect(compactSetups[CompactType.COUNSELING].isEnabled()).to.equal(true);
        expect(compactSetups[CompactType.COSMETOLOGY].isEnabled()).to.equal(true);
        expect(compactSetups[CompactType.SOCIAL_WORK].isEnabled()).to.equal(true);
    });
    it('should successfully gate compacts without prod infra to non-production environments', async () => {
        envConfig.isAppProduction = true;

        expect(compactSetups[CompactType.ASLP].isEnabled()).to.equal(true);
        expect(compactSetups[CompactType.OT].isEnabled()).to.equal(true);
        expect(compactSetups[CompactType.COUNSELING].isEnabled()).to.equal(true);
        expect(compactSetups[CompactType.COSMETOLOGY].isEnabled()).to.equal(false);
        expect(compactSetups[CompactType.SOCIAL_WORK].isEnabled()).to.equal(false);
    });
    it('should successfully install the compact lists as global properties', async () => {
        const app = buildApp();
        const { globalProperties } = app.config;

        expect(globalProperties.$compactsAll).to.matchPattern(compactConfigs.value);
        expect(globalProperties.$compactsEnabled).to.matchPattern(enabledCompactConfigs.value);
    });
    it('should successfully install app mode global properties that track the store', async () => {
        const app = buildApp();
        const { globalProperties } = app.config;

        store.dispatch('setAppMode', AppModes.COSMETOLOGY);

        expect(globalProperties.$appMode).to.equal(AppModes.COSMETOLOGY);
        expect(globalProperties.$appGroupMode).to.equal(AppGroupModes.MULTI_STATE);
        expect(globalProperties.$isAppModeCosmetology).to.equal(true);
        expect(globalProperties.$isAppModeJcc).to.equal(false);
        expect(globalProperties.$isAppGroupModeMultiState).to.equal(true);
        expect(globalProperties.$isAppGroupModePrivilegePurchase).to.equal(false);

        store.dispatch('setAppMode', AppModes.SOCIAL_WORK);

        expect(globalProperties.$appMode).to.equal(AppModes.SOCIAL_WORK);
        expect(globalProperties.$isAppModeSocialWork).to.equal(true);
        expect(globalProperties.$isAppModeCosmetology).to.equal(false);
    });
    it('should successfully expose the global properties on a mounted component', async () => {
        const wrapper = await mountShallow(CompactSelector);
        const component = wrapper.vm;

        store.dispatch('setAppMode', AppModes.COSMETOLOGY);

        expect(component.$appMode).to.equal(AppModes.COSMETOLOGY);
        expect(component.$appGroupMode).to.equal(AppGroupModes.MULTI_STATE);
        expect(component.$isAppModeCosmetology).to.equal(true);
        expect(component.$isAppModeJcc).to.equal(false);
        expect(component.$compactsAll.length).to.equal(5);
        expect(component.$compactsEnabled.length).to.equal(5);
    });
    it('should successfully install a global property for each app mode flag', async () => {
        const app = buildApp();
        const { globalProperties } = app.config;

        appModeFlags.forEach((appModeFlag) => {
            expect(globalProperties[`$${appModeFlag}`]).to.equal(store.getters[appModeFlag]);
        });
    });
    it('should successfully reset app env after test suite', async () => {
        expect(envConfig.isAppProduction).to.equal(false);
        expect(store.state.appMode).to.equal(AppModes.JCC);
        expect(i18n.global.locale.value).to.equal('en');
    });
});
