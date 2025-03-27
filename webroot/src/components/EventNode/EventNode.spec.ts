//
//  EventNode.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 3/21/2025.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import EventNode from '@components/EventNode/EventNode.vue';

describe('EventNode component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(EventNode);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(EventNode).exists()).to.equal(true);
    });
});
