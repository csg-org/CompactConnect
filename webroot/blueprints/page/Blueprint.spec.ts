//
//  Blueprint.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on MM/DD/YYYY.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import Blueprint from '@pages/SubPath/Blueprint/Blueprint.vue';

describe('Blueprint page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(Blueprint);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(Blueprint).exists()).to.equal(true);
    });
});
