//
//  ExampleLanguageSelector.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/8/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import ExampleLanguageSelector from '@components/StyleGuide/ExampleLanguageSelector/ExampleLanguageSelector.vue';

describe('ExampleLanguageSelector component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(ExampleLanguageSelector);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(ExampleLanguageSelector).exists()).to.equal(true);
    });
});
