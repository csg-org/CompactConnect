//
//  LanguageSelector.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/8/2024.
//

import { expect } from 'chai';
import { mountFull } from '@tests/helpers/setup';
import LanguageSelector from '@components/LanguageSelector/LanguageSelector.vue';

describe('LanguageSelector component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountFull(LanguageSelector);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(LanguageSelector).exists()).to.equal(true);
    });
    it('should have a starting language', async () => {
        const wrapper = await mountFull(LanguageSelector);
        const component = wrapper.vm;

        expect(component.currentLanguage).to.equal('en');
    });
    it('should globally update the locale language', async () => {
        const wrapper = await mountFull(LanguageSelector);
        const component = wrapper.vm;
        const select = wrapper.find('select');

        await select.setValue('es');

        expect(component.$i18n.locale).to.equal('es');
    });
});
