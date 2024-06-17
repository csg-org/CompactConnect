//
//  StyleGuide.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/28/2021.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import StyleGuide from '@pages/StyleGuide/StyleGuide.vue';

describe('StyleGuide page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(StyleGuide);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(StyleGuide).exists()).to.equal(true);
    });
});
