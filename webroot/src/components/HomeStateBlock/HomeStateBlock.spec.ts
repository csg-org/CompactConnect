//
//  HomeStateBlock.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/3/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import HomeStateBlock from '@components/HomeStateBlock/HomeStateBlock.vue';

describe('HomeStateBlock component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(HomeStateBlock);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(HomeStateBlock).exists()).to.equal(true);
    });
});
