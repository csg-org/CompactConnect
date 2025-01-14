//
//  MilitaryStatusUpdate.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 12/20/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import MilitaryStatusUpdate from '@pages/MilitaryStatusUpdate/MilitaryStatusUpdate.vue';

describe('MilitaryStatusUpdate page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(MilitaryStatusUpdate);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(MilitaryStatusUpdate).exists()).to.equal(true);
    });
});
