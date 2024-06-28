//
//  Card.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 6/19/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import Card from '@components/Card/Card.vue';

describe('Card component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(Card);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(Card).exists()).to.equal(true);
    });
});
