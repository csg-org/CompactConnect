//
//  Section.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 8/25/2020.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import Section from '@components/Section/Section.vue';

describe('Section component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(Section);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(Section).exists()).to.equal(true);
    });
});
