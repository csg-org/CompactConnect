//
//  MockPopulate.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 6/20/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import MockPopulate from '@components/Forms/MockPopulate/MockPopulate.vue';

describe('MockPopulate component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(MockPopulate);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(MockPopulate).exists()).to.equal(true);
    });
});
